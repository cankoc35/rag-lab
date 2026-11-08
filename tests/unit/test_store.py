"""Offline DB-check/CLI tests with a fake driver; no PostgreSQL required."""

import builtins
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict
from io import StringIO
import json
import os
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from rag_workflow_lab.cli import main
from rag_workflow_lab.config import load_database_settings
from rag_workflow_lab.store import DatabaseCheckError, check_database


class FakeDriverError(Exception):
    pass


class DatabaseCheckTests(unittest.TestCase):
    def setUp(self):
        self.secret = "synthetic-private-password"
        self.environment = {"POSTGRES_PASSWORD": self.secret}
        self.settings = load_database_settings(self.environment)
        self.connection = MagicMock()
        self.connection.__enter__.return_value = self.connection
        self.cursor = self.connection.cursor.return_value.__enter__.return_value
        self.cursor.fetchone.side_effect = [(1,), ("PostgreSQL 18 fixture", "on"), ("0.8.7",)]
        self.driver = SimpleNamespace(
            Error=FakeDriverError, connect=MagicMock(return_value=self.connection),
        )
        driver = patch.dict(sys.modules, {"psycopg": self.driver})
        driver.start()
        self.addCleanup(driver.stop)
        network = patch("socket.socket.connect", side_effect=AssertionError("Unexpected network access"))
        network.start()
        self.addCleanup(network.stop)

    def assert_contexts_exited(self):
        self.connection.__exit__.assert_called_once()
        self.connection.cursor.return_value.__exit__.assert_called_once()

    def test_check_uses_read_only_sql_timeouts_parameters_and_closes_contexts(self):
        def require_read_only(*args):
            self.assertIs(self.connection.read_only, True)

        self.cursor.execute.side_effect = require_read_only
        result = check_database(self.settings)
        self.driver.connect.assert_called_once_with(
            **self.settings.connect_kwargs(), options="-c statement_timeout=5000",
        )
        self.assertEqual(asdict(result), {
            "postgresql_version": "PostgreSQL 18 fixture", "pgvector_version": "0.8.7", "read_only": True,
        })
        self.assertNotIn(self.secret, repr(result))
        self.cursor.execute.assert_any_call("SELECT 1")
        self.cursor.execute.assert_any_call(
            "SELECT extversion FROM pg_catalog.pg_extension WHERE extname = %s", ("vector",),
        )
        self.assert_contexts_exited()

    def test_missing_vector_is_a_failed_check_with_cleanup(self):
        self.cursor.fetchone.side_effect = [(1,), ("PostgreSQL 18 fixture", "on"), None]
        with self.assertRaisesRegex(DatabaseCheckError, "'vector' is not installed"):
            check_database(self.settings)
        self.assert_contexts_exited()

    def test_server_must_confirm_read_only_before_extension_query(self):
        self.cursor.fetchone.side_effect = [(1,), ("PostgreSQL 18 fixture", "off")]
        with self.assertRaisesRegex(DatabaseCheckError, "read-only transaction"):
            check_database(self.settings)
        self.assertEqual(self.cursor.execute.call_count, 2)
        self.assert_contexts_exited()

    def test_unexpected_ping_or_empty_versions_are_rejected(self):
        for rows in ([(0,)], [None], [(1,), None], [(1,), ("", "on")],
                     [(1,), ("PostgreSQL 18 fixture", "on"), ("",)]):
            self.cursor.fetchone.side_effect = rows
            with self.subTest(rows=rows), self.assertRaises(DatabaseCheckError):
                check_database(self.settings)

    def test_connection_failure_omits_driver_details_and_credentials(self):
        self.driver.connect.side_effect = FakeDriverError("connection password=" + self.secret)
        with self.assertRaisesRegex(DatabaseCheckError, "Verify the service") as raised:
            check_database(self.settings)
        self.assertNotIn(self.secret, str(raised.exception))
        self.assertTrue(raised.exception.__suppress_context__)
        self.connection.__enter__.assert_not_called()

    def test_query_failure_is_redacted_and_contexts_exit(self):
        self.cursor.execute.side_effect = FakeDriverError(self.secret)
        with self.assertRaises(DatabaseCheckError) as raised:
            check_database(self.settings)
        self.assertNotIn(self.secret, str(raised.exception))
        self.assert_contexts_exited()

    def test_missing_driver_has_install_guidance(self):
        original_import = builtins.__import__

        def reject_driver(name, *args, **kwargs):
            if name == "psycopg":
                raise ImportError(self.secret)
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=reject_driver):
            with self.assertRaisesRegex(DatabaseCheckError, "'database' optional dependencies") as raised:
                check_database(self.settings)
        self.assertNotIn(self.secret, str(raised.exception))
        self.driver.connect.assert_not_called()

    def test_cli_prints_versions_without_credentials_or_toml_loading(self):
        output = StringIO()
        with patch.dict(os.environ, self.environment, clear=True), patch(
            "rag_workflow_lab.cli.load_settings", side_effect=AssertionError("Unexpected TOML load")
        ), redirect_stdout(output):
            self.assertEqual(main(["check-db"]), 0)
        self.assertEqual(json.loads(output.getvalue()), {
            "status": "ok", "postgresql_version": "PostgreSQL 18 fixture",
            "pgvector_version": "0.8.7", "read_only": True,
        })
        self.assertNotIn(self.secret, output.getvalue())
        self.assertNotIn("password", output.getvalue())

    def test_cli_missing_password_exits_before_loading_driver(self):
        output, error = StringIO(), StringIO()
        with patch.dict(os.environ, {}, clear=True), redirect_stdout(output), redirect_stderr(error):
            with self.assertRaises(SystemExit) as raised:
                main(["check-db"])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("POSTGRES_PASSWORD", error.getvalue())
        self.assertEqual(output.getvalue(), "")
        self.driver.connect.assert_not_called()

    def test_cli_connection_failure_returns_nonzero_without_sensitive_details(self):
        self.driver.connect.side_effect = FakeDriverError(self.secret)
        output, error = StringIO(), StringIO()
        with patch.dict(os.environ, self.environment, clear=True), redirect_stdout(output), redirect_stderr(error):
            with self.assertRaises(SystemExit) as raised:
                main(["check-db"])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("Verify the service", error.getvalue())
        self.assertNotIn(self.secret, error.getvalue())
        self.assertEqual(output.getvalue(), "")

    def test_help_lists_check_db_without_opening_a_connection(self):
        output = StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("check-db", output.getvalue())
        self.driver.connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
