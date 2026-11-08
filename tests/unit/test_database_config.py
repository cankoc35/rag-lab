"""Offline database configuration checks; no driver, .env file or DB required."""

from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from rag_workflow_lab.cli import main
from rag_workflow_lab.config import load_database_settings, load_settings


class DatabaseConfigTests(unittest.TestCase):
    def setUp(self):
        network = patch("socket.socket.connect", side_effect=AssertionError("Unexpected network access"))
        network.start()
        self.addCleanup(network.stop)
        self.environment = {"POSTGRES_PASSWORD": "synthetic-test-secret"}

    def test_local_defaults_match_compose_when_only_password_is_supplied(self):
        settings = load_database_settings(self.environment)
        self.assertEqual(settings.connect_kwargs(), {
            "host": "127.0.0.1", "port": 5432, "dbname": "rag_workflow_lab",
            "user": "rag_lab", "password": "synthetic-test-secret", "connect_timeout": 5,
        })

    def test_overrides_preserve_credentials_without_url_or_sql_interpolation(self):
        password = "  synthetic @:/?#%'\\$ secret  "
        settings = load_database_settings({
            "POSTGRES_HOST": "postgres", "POSTGRES_PORT": "15432",
            "POSTGRES_DB": "fixture database", "POSTGRES_USER": "fixture user",
            "POSTGRES_PASSWORD": password, "POSTGRES_CONNECT_TIMEOUT": "12",
        })
        self.assertEqual(settings.connect_kwargs(), {
            "host": "postgres", "port": 15432, "dbname": "fixture database",
            "user": "fixture user", "password": password, "connect_timeout": 12,
        })

    def test_process_environment_is_read_at_call_time(self):
        with patch.dict(os.environ, self.environment, clear=True):
            self.assertEqual(load_database_settings().password, "synthetic-test-secret")
            os.environ["POSTGRES_PORT"] = "15433"
            self.assertEqual(load_database_settings().port, 15433)

    def test_explicit_mapping_does_not_fall_back_to_process_credentials(self):
        with patch.dict(os.environ, self.environment, clear=True):
            with self.assertRaisesRegex(ValueError, "POSTGRES_PASSWORD"):
                load_database_settings({})

    def test_missing_empty_and_nul_settings_fail_without_echoing_values(self):
        with self.assertRaisesRegex(ValueError, "POSTGRES_PASSWORD"):
            load_database_settings({})
        for key in ("POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"):
            for value in ("", " \t", "synthetic-sensitive-value\x00"):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError) as raised:
                    load_database_settings({**self.environment, key: value})
                self.assertIn(key, str(raised.exception))
                self.assertNotIn("synthetic-sensitive-value", str(raised.exception))

    def test_port_range_and_integer_format_are_validated(self):
        for port in ("1", "65535"):
            self.assertEqual(load_database_settings({**self.environment, "POSTGRES_PORT": port}).port, int(port))
        for port in ("0", "65536", "-1", "+5432", "5432.0", " 5432 ", "", "NaN",
                     "9" * 5000, "synthetic-sensitive-value", "５４３２"):
            with self.subTest(port=port[:24]), self.assertRaisesRegex(ValueError, "POSTGRES_PORT") as raised:
                load_database_settings({**self.environment, "POSTGRES_PORT": port})
            self.assertIsNone(raised.exception.__cause__)
            self.assertIsNone(raised.exception.__context__)
            self.assertNotIn("synthetic-sensitive-value", str(raised.exception))

    def test_connection_timeout_requires_a_positive_integer(self):
        for value in ("0", "-1", "1.5", "NaN", "", "2147483648"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "POSTGRES_CONNECT_TIMEOUT"):
                load_database_settings({**self.environment, "POSTGRES_CONNECT_TIMEOUT": value})
        self.assertEqual(load_database_settings({**self.environment, "POSTGRES_CONNECT_TIMEOUT": "10"}).connect_timeout, 10)

    def test_settings_repr_omits_password(self):
        settings = load_database_settings(self.environment)
        self.assertNotIn("synthetic-test-secret", repr(settings))
        self.assertNotIn("password=", str(settings))

    def test_loading_database_settings_does_not_read_files(self):
        with patch("builtins.open", side_effect=AssertionError("Unexpected file read")), patch.object(
            Path, "open", side_effect=AssertionError("Unexpected file read")
        ):
            self.assertEqual(load_database_settings(self.environment).port, 5432)

    def test_toml_settings_and_existing_cli_remain_independent_of_database_settings(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "pilot.toml"
            path.write_text('[project]\nname="fixture"\n[paths]\nsources_manifest="sources.json"\nlocal_data_dir="local"\n')
            with patch.dict(os.environ, {**self.environment, "POSTGRES_PORT": "invalid"}, clear=True):
                self.assertEqual(load_settings(path).project_name, "fixture")
                output = StringIO()
                with redirect_stdout(output):
                    self.assertEqual(main(["check-config", "--config", str(path)]), 0)
                self.assertEqual(json.loads(output.getvalue())["project_name"], "fixture")
                self.assertNotIn("synthetic-test-secret", output.getvalue())


if __name__ == "__main__":
    unittest.main()
