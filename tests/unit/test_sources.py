"""Offline contract tests for source-manifest loading and CLI validation."""

from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from rag_workflow_lab.cli import main
from rag_workflow_lab.ingestion.download import SourceManifestError, load_sources


ROOT = Path(__file__).resolve().parents[2]


def valid_manifest() -> dict:
    return {
        "schema_version": 1,
        "status": "selected",
        "sources": [{
            "source_id": "PG-EXPLAIN",
            "title": "Using EXPLAIN",
            "url": "https://www.postgresql.org/docs/18/using-explain.html",
            "format": "html",
            "postgresql_version": "18",
            "selection": {"mode": "page"},
        }],
    }


class LoadSourcesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "sources.json"

    def write_manifest(self, document: object) -> None:
        self.path.write_text(json.dumps(document), encoding="utf-8")

    def test_repository_manifest_loads_four_sources_offline(self) -> None:
        with patch("socket.create_connection", side_effect=AssertionError("Network access")):
            sources = load_sources(ROOT / "data/corpus/sources.json")
        self.assertEqual(
            [source.source_id for source in sources],
            ["PG-EXPLAIN", "PG-MULTI", "PG-PARTIAL", "PG-STATS"],
        )
        self.assertTrue(all(source.postgresql_version == "18" for source in sources))
        self.assertEqual(sources[0].selection.mode, "page")
        self.assertEqual(sources[-1].selection.mode, "sections")
        self.assertEqual(
            sources[-1].selection.section_ids,
            ("MONITORING-PG-STAT-REPLICATION-VIEW",),
        )

    def test_preserves_unicode_and_does_not_modify_manifest(self) -> None:
        document = valid_manifest()
        document["sources"][0]["title"] = "Statistics — example"
        self.write_manifest(document)
        before = self.path.read_bytes()
        source = load_sources(str(self.path))[0]
        self.assertEqual(source.title, "Statistics — example")
        self.assertEqual(self.path.read_bytes(), before)

    def test_unreadable_or_malformed_file_has_clear_error(self) -> None:
        with self.assertRaisesRegex(SourceManifestError, "Cannot read source manifest"):
            load_sources(self.path)
        self.path.write_text('{"sources": [}', encoding="utf-8")
        with self.assertRaisesRegex(SourceManifestError, "Invalid JSON.*line 1, column"):
            load_sources(self.path)
        self.path.write_bytes(b"\xff")
        with self.assertRaisesRegex(SourceManifestError, "Cannot read source manifest"):
            load_sources(self.path)

    def test_rejects_unsupported_or_incomplete_manifest(self) -> None:
        cases = [
            ([], "manifest must be a JSON object"),
            ({**valid_manifest(), "schema_version": True}, "schema_version"),
            ({**valid_manifest(), "schema_version": 2}, "schema_version"),
            ({**valid_manifest(), "status": "draft"}, "status"),
            ({**valid_manifest(), "sources": []}, "sources must be a non-empty list"),
            ({**valid_manifest(), "sources": {}}, "sources must be a non-empty list"),
        ]
        for document, message in cases:
            with self.subTest(document=document):
                self.write_manifest(document)
                with self.assertRaisesRegex(SourceManifestError, message):
                    load_sources(self.path)

    def test_rejects_missing_wrong_type_or_blank_source_fields(self) -> None:
        for field in ("source_id", "title", "url", "format", "postgresql_version"):
            for invalid in (None, 18, "", "   "):
                with self.subTest(field=field, value=invalid):
                    document = valid_manifest()
                    if invalid is None:
                        del document["sources"][0][field]
                    else:
                        document["sources"][0][field] = invalid
                    self.write_manifest(document)
                    with self.assertRaisesRegex(SourceManifestError, rf"sources\[0\].{field}"):
                        load_sources(self.path)

    def test_rejects_duplicate_source_id_or_url(self) -> None:
        for duplicate_field in ("source_id", "url"):
            with self.subTest(field=duplicate_field):
                document = valid_manifest()
                other = deepcopy(document["sources"][0])
                if duplicate_field == "source_id":
                    other["url"] = "https://www.postgresql.org/docs/18/indexes-partial.html"
                else:
                    other["source_id"] = "PG-OTHER"
                document["sources"].append(other)
                self.write_manifest(document)
                with self.assertRaisesRegex(SourceManifestError, "sources\\[1\\]: duplicate"):
                    load_sources(self.path)

    def test_rejects_unversioned_mismatched_or_noncanonical_urls(self) -> None:
        urls = [
            "https://www.postgresql.org/docs/current/using-explain.html",
            "https://www.postgresql.org/docs/17/using-explain.html",
            "http://www.postgresql.org/docs/18/using-explain.html",
            "https://example.com/docs/18/using-explain.html",
            "https://www.postgresql.org/docs/18/using-explain.html#section",
            "https://www.postgresql.org/docs/18/using-explain.html?version=18",
            "HTTPS://www.postgresql.org/docs/18/using-explain.html",
            "https://www.postgresql.org/docs/18/using-explain.html?",
            "https://www.postgresql.org/docs/18/using-explain.html#",
            "https://www.postgresql.org/docs/18/../17/using-explain.html",
        ]
        for url in urls:
            with self.subTest(url=url):
                document = valid_manifest()
                document["sources"][0]["url"] = url
                self.write_manifest(document)
                with self.assertRaisesRegex(SourceManifestError, r"sources\[0\].url"):
                    load_sources(self.path)

    def test_rejects_ambiguous_or_incomplete_section_selection(self) -> None:
        selections = [
            None,
            {"mode": "unknown"},
            {"mode": "page", "section_ids": ["SECTION"]},
            {"mode": "sections"},
            {"mode": "sections", "section_ids": []},
            {"mode": "sections", "section_ids": "SECTION"},
            {"mode": "sections", "section_ids": [1]},
            {"mode": "sections", "section_ids": ["HAS SPACE"]},
            {"mode": "sections", "section_ids": ["SECTION", "SECTION"]},
        ]
        for selection in selections:
            with self.subTest(selection=selection):
                document = valid_manifest()
                document["sources"][0]["selection"] = selection
                self.write_manifest(document)
                with self.assertRaisesRegex(SourceManifestError, r"sources\[0\].selection"):
                    load_sources(self.path)

    def test_cli_checks_sources_using_config_relative_paths(self) -> None:
        self.write_manifest(valid_manifest())
        config = Path(self.directory.name) / "pilot.toml"
        config.write_text(
            '[project]\nname = "test"\n[paths]\n'
            'sources_manifest = "sources.json"\nlocal_data_dir = "local"\n',
            encoding="utf-8",
        )
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(["check-sources", "--config", str(config)])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue())["source_count"], 1)


if __name__ == "__main__":
    unittest.main()
