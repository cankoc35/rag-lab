"""Check local source boundaries and preservation of Atlas evidence blocks."""

from contextlib import redirect_stdout
from dataclasses import asdict
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from rag_workflow_lab.cli import main
from rag_workflow_lab.ingestion.markdown import (
    PARSER_VERSION, ingest_markdown, load_markdown_snapshots, parse_markdown,
)
from rag_workflow_lab.ingestion.parse import SourceParseError


ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / "data/corpus/synthetic"


def parse(text):
    return parse_markdown(text.encode(), source_id="FIXTURE", snapshot_id="fixture-v1",
                          source_url="file:///fixture.md", title="Fixture")


class MarkdownParserTests(unittest.TestCase):
    def test_preserves_headings_code_tables_and_line_anchors(self):
        text = "# Root\n\n## Details\n\nProse with `a` and **b**.\n\n```sql\nSELECT a | b\n  FROM example;\n```\n\n| Name | Size |\n| --- | ---: |\n| device_events | 6.2 GB |\n\n## Next\n\nOther content.\n"
        document = parse(text)
        self.assertEqual(document.parser_version, PARSER_VERSION)
        self.assertEqual([b.kind for b in document.blocks],
                         ["heading", "heading", "paragraph", "code", "table", "heading", "paragraph"])
        code, table = document.blocks[3:5]
        self.assertEqual(code.text, "SELECT a | b\n  FROM example;")
        self.assertEqual(code.heading_path, ("Root", "Details"))
        self.assertEqual(code.anchor, "L7")
        self.assertEqual(table.anchor, "L12")
        self.assertTrue(all(cell.is_header for cell in table.table_rows[0]))
        self.assertEqual([cell.text for cell in table.table_rows[1]], ["device_events", "6.2 GB"])
        self.assertEqual(document.blocks[-1].heading_path, ("Root", "Next"))

    def test_rejects_incomplete_or_unsupported_table_and_code_blocks(self):
        cases = ["No heading", "# Root\n\n```sql\nSELECT 1;",
                 "# Root\n\n| Name |", "# Root\n\n| A |\n| --- |\n| x | y |",
                 "# Root\n\n| A |\n| invalid |", "# Root\n\n| A |\n| --- |\n| x\\|y |"]
        for text in cases:
            with self.subTest(text=text), self.assertRaises(SourceParseError):
                parse(text)

    def test_real_atlas_sources_keep_inventory_and_policy_evidence(self):
        inventory = parse((SOURCES / "atlas_inventory.md").read_text())
        policy = parse((SOURCES / "atlas_operations_policy.md").read_text())
        table = next(b for b in inventory.blocks if b.kind == "table")
        self.assertEqual(len(table.table_rows), 6)
        self.assertEqual(table.table_rows[1][0].text, "`atlas_app.device_events`")
        self.assertIn("customer_id = $1", next(b.text for b in inventory.blocks if b.kind == "code"))
        self.assertIn("Unknown", next(b.text for b in policy.blocks if b.kind == "table"))
        self.assertTrue(all(b.heading_path and b.anchor for b in inventory.blocks + policy.blocks))


class MarkdownIngestionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sources = self.root / "sources"
        self.sources.mkdir()
        for path in SOURCES.glob("*"):
            if path.is_file() and path.suffix in {".json", ".md"}:
                (self.sources / path.name).write_bytes(path.read_bytes())
        self.manifest = self.sources / "sources.json"
        self.output = self.root / "output"

    def test_saves_exact_copies_and_blocks_without_overwriting_earlier_runs(self):
        with patch("socket.socket.connect", side_effect=AssertionError("Network forbidden")):
            first = ingest_markdown(self.manifest, self.output)
            earlier = {p: p.read_bytes() for p in Path(first["output_dir"]).rglob("*") if p.is_file()}
            second = ingest_markdown(self.manifest, self.output)
        self.assertNotEqual(first["output_dir"], second["output_dir"])
        self.assertEqual([s["snapshot_id"] for s in first["sources"]], [s["snapshot_id"] for s in second["sources"]])
        for result in first["sources"]:
            manifest = Path(result["manifest_path"])
            snapshot = json.loads(manifest.read_text())["snapshot"]
            content = (manifest.parent / snapshot["local_path"]).read_bytes()
            self.assertEqual(content, (self.sources / snapshot["local_path"]).read_bytes())
            document = parse_markdown(content, source_id=snapshot["source"]["source_id"],
                                      snapshot_id=snapshot["snapshot_id"],
                                      source_url=snapshot["source"]["url"], title=snapshot["source"]["title"])
            parsed = json.loads(Path(result["parsed_path"]).read_text())["document"]
            self.assertEqual(parsed, json.loads(json.dumps(asdict(document))))
            self.assertEqual(snapshot["sha256"], document.source_sha256)
            self.assertNotIn("http_status", snapshot)
        self.assertTrue(all(p.read_bytes() == content for p, content in earlier.items()))

    def test_changed_second_source_fails_before_creating_output(self):
        (self.sources / "atlas_operations_policy.md").write_text("# Changed source\n")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            ingest_markdown(self.manifest, self.output)
        self.assertFalse(self.output.exists())

    def test_rejects_invalid_schema_ids_paths_and_formats(self):
        original = json.loads(self.manifest.read_text())
        changes = [{"source_id": original["sources"][0]["source_id"]},
                   {"source_id": "../outside"}, {"path": "../gold.md"},
                   {"path": original["sources"][0]["path"]}, {"format": "html"}]
        for change in changes:
            manifest = json.loads(json.dumps(original))
            manifest["sources"][1].update(change)
            self.manifest.write_text(json.dumps(manifest))
            with self.subTest(change=change), self.assertRaises(ValueError):
                ingest_markdown(self.manifest, self.output)
            self.assertFalse(self.output.exists())
        original["schema_version"] = True
        self.manifest.write_text(json.dumps(original))
        with self.assertRaisesRegex(ValueError, "schema_version"):
            ingest_markdown(self.manifest, self.output)

    def test_rejects_source_symlink_outside_manifest_directory(self):
        path = self.sources / "atlas_inventory.md"
        outside = self.root / path.name
        outside.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "remain beside"):
            ingest_markdown(self.manifest, self.output)
        self.assertFalse(self.output.exists())

    def test_failed_write_preserves_existing_output(self):
        self.output.mkdir()
        sentinel = self.output / "existing.txt"
        sentinel.write_text("keep")
        with patch.object(Path, "write_text", side_effect=OSError("Disk full")):
            with self.assertRaises(OSError):
                ingest_markdown(self.manifest, self.output)
        self.assertEqual(list(self.output.iterdir()), [sentinel])

    def test_cli_ingests_only_explicit_markdown_sources_offline(self):
        config = self.root / "pilot.toml"
        config.write_text('[project]\nname = "test"\n[paths]\nsources_manifest = "unused.json"\nlocal_data_dir = "local"\n')
        output = io.StringIO()
        with redirect_stdout(output), patch("socket.socket.connect", side_effect=AssertionError("Network forbidden")):
            result = main(["ingest-markdown", "--config", str(config), "--sources-manifest", str(self.manifest)])
        record = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(record["document_state"], "atlas-docs-v1")
        self.assertEqual([s["source_id"] for s in record["sources"]], ["LOCAL-INVENTORY", "LOCAL-POLICY"])
        self.assertTrue(all(Path(s["parsed_path"]).is_file() for s in record["sources"]))

    def test_snapshot_reader_uses_copies_without_live_source_files(self):
        result = ingest_markdown(self.manifest, self.output)
        for path in self.sources.glob("*.md"):
            path.unlink()
        with patch("socket.socket.connect", side_effect=AssertionError("Network forbidden")):
            documents = load_markdown_snapshots(self.manifest, Path(result["output_dir"]))
        self.assertEqual([doc.source_id for _, doc in documents], ["LOCAL-INVENTORY", "LOCAL-POLICY"])
        self.assertEqual([len(doc.blocks) for _, doc in documents], [19, 18])

    def test_snapshot_reader_rejects_changed_raw_metadata_or_saved_blocks(self):
        for filename in ("atlas_inventory.md", "manifest.json", "parsed.json"):
            with self.subTest(filename=filename):
                result = ingest_markdown(self.manifest, self.output)
                folder = Path(result["sources"][0]["manifest_path"]).parent
                path = folder / filename
                if filename.endswith(".md"):
                    path.write_text(path.read_text() + "\nChanged evidence.\n")
                else:
                    record = json.loads(path.read_text())
                    if filename == "manifest.json":
                        record["snapshot"]["document_state"] = "other-state"
                    else:
                        record["document"]["blocks"][2]["text"] = "Changed evidence."
                    path.write_text(json.dumps(record))
                with self.assertRaises(ValueError):
                    load_markdown_snapshots(self.manifest, Path(result["output_dir"]))

    def test_snapshot_reader_rejects_missing_or_duplicate_snapshots(self):
        for duplicate in (False, True):
            with self.subTest(duplicate=duplicate):
                result = ingest_markdown(self.manifest, self.output)
                run = Path(result["output_dir"])
                folder = Path(result["sources"][0]["manifest_path"]).parent
                if duplicate:
                    shutil.copytree(folder, run / "LOCAL-INVENTORY-duplicate")
                else:
                    shutil.rmtree(folder)
                with self.assertRaisesRegex(ValueError, "Expected one Markdown snapshot"):
                    load_markdown_snapshots(self.manifest, run)

    def test_snapshot_reader_rejects_changed_allowlist(self):
        result = ingest_markdown(self.manifest, self.output)
        record = json.loads(self.manifest.read_text())
        record["document_state"] = "atlas-docs-v2"
        self.manifest.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "metadata differs"):
            load_markdown_snapshots(self.manifest, Path(result["output_dir"]))

    def test_snapshot_reader_rejects_raw_copy_symlink_outside_snapshot(self):
        result = ingest_markdown(self.manifest, self.output)
        folder = Path(result["sources"][0]["manifest_path"]).parent
        path = folder / "atlas_inventory.md"
        path.unlink()
        path.symlink_to(self.sources / path.name)
        with self.assertRaisesRegex(ValueError, "remain beside"):
            load_markdown_snapshots(self.manifest, Path(result["output_dir"]))


if __name__ == "__main__":
    unittest.main()
