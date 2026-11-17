"""Offline import-input checks using a synthetic saved snapshot."""

import hashlib
from dataclasses import asdict
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.import_corpus import load_corpus
from rag_workflow_lab.contracts import TokenizerSpec
from rag_workflow_lab.ingestion.chunk import chunk_document, serialize_chunk
from rag_workflow_lab.ingestion.markdown import ingest_markdown, load_markdown_snapshots


ROOT = Path(__file__).resolve().parents[2]


class CorpusInputTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.chunk_dir = self.root / "chunks"
        self.chunk_dir.mkdir()
        self.allowlist = self.root / "sources.json"
        source = json.loads((ROOT / "data/corpus/sources.json").read_text())["sources"][0]
        self.allowlist.write_text(json.dumps({"schema_version": 1, "status": "selected", "sources": [source]}))
        source["selection"]["section_ids"] = []
        folder = self.root / "snapshots/PG-EXPLAIN-test"
        folder.mkdir(parents=True)
        html = (ROOT / "tests/fixtures/postgresql_docbook.html").read_bytes()
        self.html_path = folder / "source.html"
        self.html_path.write_bytes(html)
        snapshot = {
            "snapshot_id": folder.name, "source": source, "downloaded_at": "2026-11-12T00:00:00Z",
            "resolved_url": source["url"], "http_status": 200, "content_type": "text/html",
            "charset": "utf-8", "size_bytes": len(html), "sha256": hashlib.sha256(html).hexdigest(),
            "local_path": "source.html",
        }
        (folder / "manifest.json").write_text(json.dumps({"schema_version": 1, "snapshot": snapshot}))
        self.snapshot = snapshot
        self.payload = {"schema_version": 1, "source_id": source["source_id"], "snapshot_id": folder.name,
                        "chunks": [{"chunk_id": "test-chunk", "source_id": source["source_id"],
                                    "snapshot_id": folder.name, "source_sha256": snapshot["sha256"],
                                    "source_url": source["url"], "parser_version": "postgresql-html-v1",
                                    "text": "SELECT 'quoted';\n  -- preserved whitespace",
                                    "embedding_text": "search_document: SELECT 'quoted';",
                                    "token_count": 12, "heading_path": ["Fixture SQL"]}]}
        self.chunk_path = self.chunk_dir / f"{folder.name}.json"
        self.write_chunks()
        network = patch("socket.socket.connect", side_effect=AssertionError("Unexpected network access"))
        network.start()
        self.addCleanup(network.stop)

    def write_chunks(self):
        self.chunk_path.write_text(json.dumps(self.payload))

    def load(self):
        return load_corpus(self.chunk_dir, self.root / "snapshots", self.allowlist)

    def test_preserves_inputs_and_reads_only_allowlisted_sources(self):
        (self.chunk_dir / "UNSELECTED-gold.json").write_text("not corpus JSON")
        snapshots, chunks = self.load()
        self.assertEqual(snapshots, [self.snapshot])
        self.assertEqual(chunks, self.payload["chunks"])

    def test_requires_one_chunk_file_per_source(self):
        self.chunk_path.unlink()
        with self.assertRaisesRegex(ValueError, "found 0"):
            self.load()
        self.write_chunks()
        (self.chunk_dir / "PG-EXPLAIN-other.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "found 2"):
            self.load()

    def test_rejects_changed_raw_source(self):
        self.html_path.write_bytes(self.html_path.read_bytes() + b"<!-- changed -->")
        with self.assertRaises(ValueError):
            self.load()

    def test_rejects_chunk_provenance_mismatches(self):
        chunk = self.payload["chunks"][0]
        for key in ("source_id", "snapshot_id", "source_sha256", "source_url", "parser_version"):
            original = chunk[key]
            chunk[key] = "different"
            self.write_chunks()
            with self.subTest(field=key), self.assertRaisesRegex(ValueError, "provenance mismatch"):
                self.load()
            chunk[key] = original

    def test_rejects_duplicate_chunk_ids(self):
        self.payload["chunks"] *= 2
        self.write_chunks()
        with self.assertRaisesRegex(ValueError, "Duplicate chunk ID"):
            self.load()

    def test_rejects_payload_snapshot_path_mismatch(self):
        self.payload["snapshot_id"] = "../outside"
        self.write_chunks()
        with self.assertRaisesRegex(ValueError, "Invalid chunk file"):
            self.load()


class MarkdownCorpusInputTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        source_dir = self.root / "sources"
        source_dir.mkdir()
        for path in (ROOT / "data/corpus/synthetic").glob("*"):
            if path.suffix in {".md", ".json"}:
                (source_dir / path.name).write_bytes(path.read_bytes())
        self.allowlist = source_dir / "sources.json"
        result = ingest_markdown(self.allowlist, self.root / "snapshots")
        self.run = Path(result["output_dir"])
        self.chunks = self.root / "chunks"
        self.chunks.mkdir()
        tokenizer = TokenizerSpec("fixture/tokenizer", "fixture", "fixture", 1024)
        self.expected_snapshots, self.expected_chunks = [], []
        for manifest, document in load_markdown_snapshots(self.allowlist, self.run):
            chunks = chunk_document(document, count_tokens=lambda text: len(text.split()) + 2, tokenizer=tokenizer)
            payload = {"schema_version": 1, "source_id": document.source_id,
                       "snapshot_id": document.snapshot_id, "chunks": [asdict(chunk) for chunk in chunks]}
            (self.chunks / (document.snapshot_id + ".json")).write_text(json.dumps(payload))
            self.expected_snapshots.append(json.loads(manifest.read_text())["snapshot"])
            self.expected_chunks.extend(json.loads(json.dumps(payload["chunks"])))

    def load(self):
        return load_corpus(self.chunks, self.root / "unused-html", self.allowlist, markdown_run=self.run)

    def test_preserves_exact_markdown_records_and_ignores_unselected_files(self):
        (self.chunks / "UNSELECTED-gold.json").write_text("not corpus JSON")
        with patch("socket.socket.connect", side_effect=AssertionError("Network forbidden")):
            snapshots, chunks = self.load()
        self.assertEqual(snapshots, self.expected_snapshots)
        self.assertEqual(chunks, self.expected_chunks)
        self.assertTrue(all("captured_at" in snapshot and "http_status" not in snapshot for snapshot in snapshots))

    def test_rejects_changed_rendered_text_blocks_tables_and_missing_content(self):
        path = next(self.chunks.glob("LOCAL-INVENTORY-*.json"))
        original = json.loads(path.read_text())
        for defect in ("text", "embedding_text", "block", "table", "missing_content"):
            payload = json.loads(json.dumps(original))
            chunk = payload["chunks"][0]
            if defect in {"text", "embedding_text"}:
                chunk[defect] += " changed"
            elif defect == "block":
                chunk["blocks"][0]["text"] += " changed"
                chunk["text"] = chunk["blocks"][0]["text"]
                chunk["embedding_text"] = serialize_chunk(chunk["text"], tuple(chunk["heading_path"]))
            elif defect == "table":
                table = next(block for item in payload["chunks"] for block in item["blocks"] if block["kind"] == "table")
                table["table_rows"][1][0]["text"] = "changed table cell"
            else:
                payload["chunks"].pop(0)
            path.write_text(json.dumps(payload))
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                self.load()
        path.write_text(json.dumps(original))

    def test_requires_one_chunk_file_for_each_markdown_source(self):
        next(self.chunks.glob("LOCAL-POLICY-*.json")).unlink()
        with self.assertRaisesRegex(ValueError, "found 0"):
            self.load()


if __name__ == "__main__":
    unittest.main()
