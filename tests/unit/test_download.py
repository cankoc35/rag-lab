"""Offline snapshot tests; HTTP responses are simulated, never downloaded."""

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from datetime import datetime
from email.message import Message
from hashlib import sha256
from http.client import IncompleteRead
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from rag_workflow_lab.cli import main
from rag_workflow_lab.ingestion.download import (
    SourceDownloadError,
    SourceManifestError,
    download_source,
    load_sources,
)


ROOT = Path(__file__).resolve().parents[2]
HTML = b'<!doctype html><html><body><h2>Using EXPLAIN</h2><pre>SELECT 1;</pre></body></html>\n'


class FakeResponse(io.BytesIO):
    def __init__(self, url: str, content: bytes = HTML, *, status: int = 200,
                 content_type: str = "text/html; charset=utf-8"):
        super().__init__(content)
        self.status = status
        self.url = url
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def geturl(self) -> str:
        return self.url


class DownloadSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.output_dir = self.root / "snapshots"
        self.source = load_sources(ROOT / "data/corpus/sources.json")[0]
        factory_patch = patch("rag_workflow_lab.ingestion.download.build_opener")
        self.factory = factory_patch.start()
        self.addCleanup(factory_patch.stop)
        self.http = self.factory.return_value.open
        self.http.return_value = FakeResponse(self.source.url)
        network_patch = patch("socket.create_connection", side_effect=AssertionError("Unexpected network access"))
        network_patch.start()
        self.addCleanup(network_patch.stop)

    def test_preserves_raw_html_with_portable_verified_metadata(self) -> None:
        snapshot = download_source(self.source, self.output_dir, timeout=7)
        folder = self.output_dir / snapshot.snapshot_id
        record = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        saved = (folder / record["snapshot"]["local_path"]).read_bytes()
        self.assertEqual(saved, HTML)
        self.assertEqual(record["schema_version"], 1)
        self.assertEqual(snapshot.sha256, sha256(saved).hexdigest())
        self.assertEqual(record["snapshot"]["sha256"], snapshot.sha256)
        self.assertEqual(snapshot.size_bytes, len(saved))
        self.assertEqual(snapshot.source, self.source)
        self.assertEqual(snapshot.resolved_url, self.source.url)
        self.assertEqual(snapshot.http_status, 200)
        self.assertEqual(snapshot.content_type, "text/html")
        self.assertEqual(snapshot.charset, "utf-8")
        self.assertIsNotNone(datetime.fromisoformat(snapshot.downloaded_at).tzinfo)
        self.assertFalse(Path(snapshot.local_path).is_absolute())
        self.assertFalse((folder / "manifest.json.partial").exists())
        request = self.http.call_args.args[0]
        self.assertEqual(request.full_url, self.source.url)
        self.assertEqual(self.http.call_args.kwargs["timeout"], 7)

    def test_repeated_download_preserves_previous_snapshot_and_existing_files(self) -> None:
        self.output_dir.mkdir()
        sentinel = self.output_dir / "existing.txt"
        sentinel.write_text("keep", encoding="utf-8")
        self.http.side_effect = [
            FakeResponse(self.source.url),
            FakeResponse(self.source.url, HTML + b"<!-- changed -->"),
        ]
        first = download_source(self.source, self.output_dir)
        first_folder = self.output_dir / first.snapshot_id
        first_manifest = (first_folder / "manifest.json").read_bytes()
        second = download_source(self.source, self.output_dir)
        self.assertNotEqual(first.snapshot_id, second.snapshot_id)
        self.assertEqual((first_folder / first.local_path).read_bytes(), HTML)
        self.assertEqual((first_folder / "manifest.json").read_bytes(), first_manifest)
        self.assertNotEqual(first.sha256, second.sha256)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_http_connection_and_timeout_failures_create_no_snapshot(self) -> None:
        cases = [
            (HTTPError(self.source.url, 404, "Not Found", Message(), None), "HTTP 404"),
            (HTTPError(self.source.url, 302, "Found", Message(), None), "HTTP 302"),
            (URLError("offline"), "download failed"),
            (TimeoutError("timed out"), "timed out"),
            (URLError(TimeoutError("timed out")), "timed out"),
        ]
        for failure, message in cases:
            with self.subTest(failure=failure):
                self.http.side_effect = failure
                with self.assertRaisesRegex(SourceDownloadError, message):
                    download_source(self.source, self.output_dir)
                self.assertFalse(self.output_dir.exists())

    def test_incomplete_body_creates_no_snapshot(self) -> None:
        response = FakeResponse(self.source.url)
        response.read = Mock(side_effect=IncompleteRead(b"partial", 100))
        self.http.return_value = response
        with self.assertRaisesRegex(SourceDownloadError, "download failed"):
            download_source(self.source, self.output_dir)
        self.assertFalse(self.output_dir.exists())

    def test_rejects_empty_non_html_partial_or_unexpected_responses(self) -> None:
        compressed = FakeResponse(self.source.url)
        compressed.headers["Content-Encoding"] = "gzip"
        cases = [
            (FakeResponse(self.source.url, b""), "empty HTML"),
            (FakeResponse(self.source.url, b'{}', content_type="application/json"), "expected HTML"),
            (FakeResponse(self.source.url, status=206), "expected HTTP 200"),
            (FakeResponse("https://example.com/other.html"), "response URL differs"),
            (compressed, "compressed response"),
        ]
        for response, message in cases:
            with self.subTest(message=message):
                self.http.return_value = response
                with self.assertRaisesRegex(SourceDownloadError, message):
                    download_source(self.source, self.output_dir)
                self.assertFalse(self.output_dir.exists())

    def test_invalid_timeout_or_source_fails_before_network_access(self) -> None:
        for timeout in (0, -1, float("nan"), float("inf"), True):
            with self.subTest(timeout=timeout):
                with self.assertRaisesRegex(ValueError, "finite positive"):
                    download_source(self.source, self.output_dir, timeout=timeout)
        with self.assertRaises(SourceManifestError):
            download_source(replace(self.source, source_id="../outside"), self.output_dir)
        with self.assertRaises(SourceManifestError):
            download_source(replace(self.source, url="https://example.com/unselected.html"), self.output_dir)
        self.factory.assert_not_called()
        self.assertFalse(self.output_dir.exists())

    def test_manifest_save_failure_cleans_only_its_new_directory(self) -> None:
        self.output_dir.mkdir()
        sentinel = self.output_dir / "existing.txt"
        sentinel.write_text("keep", encoding="utf-8")
        with patch.object(Path, "replace", side_effect=OSError("disk error")):
            with self.assertRaisesRegex(SourceDownloadError, "cannot save snapshot"):
                download_source(self.source, self.output_dir)
        self.assertEqual(list(self.output_dir.iterdir()), [sentinel])
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_section_selection_is_recorded_without_trimming_raw_html(self) -> None:
        source = load_sources(ROOT / "data/corpus/sources.json")[-1]
        self.http.return_value = FakeResponse(source.url)
        snapshot = download_source(source, self.output_dir)
        folder = self.output_dir / snapshot.snapshot_id
        self.assertEqual((folder / snapshot.local_path).read_bytes(), HTML)
        record = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(record["snapshot"]["source"]["selection"], {
            "mode": "sections",
            "section_ids": ["MONITORING-PG-STAT-REPLICATION-VIEW"],
        })

    def write_config(self) -> Path:
        config = self.root / "pilot.toml"
        config.write_text(
            '[project]\nname = "test"\n[paths]\n'
            f'sources_manifest = "{ROOT / "data/corpus/sources.json"}"\n'
            'local_data_dir = "local"\n', encoding="utf-8",
        )
        return config

    def test_cli_downloads_only_the_requested_source(self) -> None:
        config = self.write_config()
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(["download-source", "--config", str(config),
                           "--source-id", "PG-EXPLAIN", "--timeout", "5"])
        record = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(record["snapshot"]["source"]["source_id"], "PG-EXPLAIN")
        self.assertTrue(Path(record["manifest_path"]).is_file())
        self.http.assert_called_once()
        self.assertEqual(self.http.call_args.args[0].full_url, self.source.url)
        self.assertEqual(self.http.call_args.kwargs["timeout"], 5)

    def test_cli_unknown_source_fails_without_downloading(self) -> None:
        config = self.write_config()
        error = io.StringIO()
        with redirect_stderr(error), self.assertRaises(SystemExit) as raised:
            main(["download-source", "--config", str(config), "--source-id", "PG-UNKNOWN"])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("Unknown selected source_id", error.getvalue())
        self.factory.assert_not_called()
        self.assertFalse((self.root / "local").exists())


if __name__ == "__main__":
    unittest.main()
