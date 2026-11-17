"""Verify reference boundaries using small fixtures without local corpus files."""

from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rag_workflow_lab.contracts import TokenizerSpec
from rag_workflow_lab.evaluation.dataset import select_questions
from rag_workflow_lab.ingestion.chunk import ChunkSettings, chunk_document
from rag_workflow_lab.ingestion.markdown import parse_markdown
from scripts.check_document_questions import validate


class QuestionReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        folder = self.root / "snapshot"
        folder.mkdir()

        def save(path, value):
            path.write_text(json.dumps(value))
            return {"path": str(path.relative_to(self.root)), "sha256": sha256(path.read_bytes()).hexdigest()}

        raw = b"# Atlas fixture\n\nAtlas has a five-second lag limit.\n\nThe replica role is reporting.\n"
        raw_path = folder / "source.md"
        raw_path.write_bytes(raw)
        source = {"source_id": "LOCAL-TEST", "title": "Atlas fixture", "format": "markdown",
                  "path": "source.md", "document_version": "1.0", "sha256": sha256(raw).hexdigest()}
        allowlist = save(self.root / "sources.json", {"schema_version": 1, "document_state": "fixture-v1", "sources": [source]})
        source_url = "file:///fixture/source.md"
        document = parse_markdown(raw, source_id=source["source_id"], snapshot_id="fixture-snapshot",
                                  source_url=source_url, title=source["title"])
        tokenizer = TokenizerSpec("fixture/tokenizer", "fixture", "fixture", 1024)
        chunks = chunk_document(document, count_tokens=lambda text: len(text.split()) + 2, tokenizer=tokenizer)
        snapshot = {"snapshot_id": document.snapshot_id, "source": {**source, "url": source_url},
                    "document_state": "fixture-v1", "source_manifest_sha256": allowlist["sha256"],
                    "local_path": raw_path.name, "sha256": source["sha256"], "size_bytes": len(raw)}
        files = {"manifest": save(folder / "manifest.json", {"snapshot": snapshot}),
                 "raw_markdown": {"path": "snapshot/source.md", "sha256": source["sha256"]},
                 "parsed": save(folder / "parsed.json", {"schema_version": 1, "document": asdict(document)}),
                 "chunks": save(folder / "chunks.json", {"schema_version": 1, "source_id": source["source_id"],
                               "snapshot_id": document.snapshot_id, "chunks": [asdict(c) for c in chunks]})}

        def evidence(qid, number, block_index):
            block = document.blocks[block_index - 1]
            return {"evidence_id": f"{qid}-E{number}", "source_id": source["source_id"],
                    "snapshot_id": document.snapshot_id, "chunk_id": chunks[0].chunk_id,
                    "block_index": block_index, "block_sha256": sha256(block.text.encode()).hexdigest(),
                    "heading_path": list(block.heading_path), "anchor": block.anchor,
                    "citation_url": source_url + "#" + block.anchor,
                    "span": {"start": 0, "end": len(block.text), "text": block.text}}

        def question(qid, mode, records):
            return {"question_id": qid, "question_type": "direct_document", "question": "Fixture question?",
                    "verification_status": "source_verified", "answerability": "answerable",
                    "expected_answer": "SECRET GOLD", "evidence": records,
                    "answer_requirements": [{"requirement_id": qid + "-R1", "statement": "Fixture reference claim.",
                        "support_mode": mode, "supporting_evidence_ids": [r["evidence_id"] for r in records]}]}

        positive = question("P07", "any", [evidence("P07", 1, 2)])
        combined = question("P09", "all", [evidence("P09", 1, 2), evidence("P09", 2, 3)])
        combined["question_type"] = "multi_document"
        negative = question("P19", "corpus_scope", [])
        negative.update({"question_type": "insufficient_evidence", "question": "What is Boreal's lag limit?",
                         "answerability": "unanswerable", "unanswerability": {
                             "target_entity": "Boreal", "checked_source_ids": ["LOCAL-TEST"],
                             "review_note": "The complete fixture contains only Atlas facts."}})
        self.dataset = {"schema_version": 1, "dataset_id": "fixture-dev", "dataset_version": "1.0.0",
                        "split": "dev", "language": "en", "status": "source_verified",
                        "source_state": {"document_state": "fixture-v1", "sources_manifest": allowlist,
                            "chunking": {"chunker_version": chunks[0].chunker_version,
                                "serialization_version": chunks[0].serialization_version,
                                "tokenizer": asdict(tokenizer), "settings": asdict(ChunkSettings())},
                            "sources": [{"source_id": source["source_id"], "snapshot_id": document.snapshot_id,
                                "source_url": source_url, "parser_version": document.parser_version, "files": files}]},
                        "questions": [positive, combined, negative]}
        self.path = self.root / "questions.json"

    def check(self, dataset=None):
        self.path.write_text(json.dumps(dataset or self.dataset))
        return validate(self.path, root=self.root)

    def test_validates_alternative_combined_and_absence_references_offline(self):
        with patch("socket.socket.connect", side_effect=AssertionError("Network forbidden")):
            report = self.check()
        self.assertEqual(report["answerable_questions"], 2)
        self.assertEqual(report["unanswerable_questions"], 1)
        self.assertEqual(report["evidence_records"], 3)

    def test_rejects_unknown_chunks_bad_spans_and_broken_combined_support(self):
        for defect in ("chunk", "span", "all_reference", "empty_reference"):
            dataset = deepcopy(self.dataset)
            if defect == "chunk":
                dataset["questions"][0]["evidence"][0]["chunk_id"] = "missing"
            elif defect == "span":
                dataset["questions"][0]["evidence"][0]["span"]["text"] = "wrong quote"
            else:
                dataset["questions"][1]["answer_requirements"][0]["supporting_evidence_ids"] = ["missing"] if defect == "all_reference" else []
            with self.subTest(defect=defect), self.assertRaises((ValueError, KeyError)):
                self.check(dataset)

    def test_rejects_unanswerable_cases_with_positive_evidence_or_invalid_scope(self):
        for defect in ("evidence", "scope", "present_entity", "answerability", "support_mode"):
            dataset = deepcopy(self.dataset)
            question = dataset["questions"][-1]
            if defect == "evidence":
                record = deepcopy(dataset["questions"][0]["evidence"][0])
                record["evidence_id"] = "P19-E1"
                question["evidence"] = [record]
            elif defect == "scope":
                question["unanswerability"]["checked_source_ids"] = []
            elif defect == "present_entity":
                question["unanswerability"]["target_entity"] = "Atlas"
            elif defect == "answerability":
                question["answerability"] = "answerable"
            else:
                question["answer_requirements"][0]["support_mode"] = "any"
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                self.check(dataset)

    def test_rejects_wrong_document_state_or_pinned_file_hash(self):
        for defect in ("state", "hash"):
            dataset = deepcopy(self.dataset)
            if defect == "state":
                dataset["source_state"]["document_state"] = "wrong-state"
            else:
                dataset["source_state"]["sources"][0]["files"]["raw_markdown"]["sha256"] = "0" * 64
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                self.check(dataset)

    def test_runtime_selection_excludes_gold_and_absence_review(self):
        selected = select_questions(self.dataset, None)
        self.assertEqual(selected, [{"question_id": q["question_id"], "question": q["question"]}
                                    for q in self.dataset["questions"]])
        self.assertNotIn("SECRET GOLD", json.dumps(selected))
        self.assertNotIn("unanswerability", json.dumps(selected))


if __name__ == "__main__":
    unittest.main()
