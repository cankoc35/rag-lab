"""Check reference ranks and cutoff coverage without models or a database."""

from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, call, patch

from scripts.check_retrieval import check_retrieval, main, measure_evidence, validate_index_scope


class CheckRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.connection = MagicMock()
        self.connection.cursor.return_value.__enter__.return_value.fetchone.return_value = (49,)
        self.embedder = Mock()
        self.matches = [{
            "chunk_id": f"chunk-{i}", "source_id": "fixture", "snapshot_id": "snapshot",
            "url": "https://example.org", "distance": i / 100, "token_count": 10,
        } for i in range(1, 50)]
        self.question = {
            "question_id": "P01", "question": "Which index can be used?", "expected_answer": "Gold must not reach retrieval.",
            "question_type": "direct_document",
            "evidence": [{"evidence_id": name, "chunk_id": f"chunk-{rank}"}
                         for name, rank in (("E1", 5), ("E2", 10), ("E3", 20), ("E4", 21), ("E5", 50))],
            "answer_requirements": [
                {"requirement_id": "R1", "support_mode": "any", "supporting_evidence_ids": ["E1", "E2"]},
                {"requirement_id": "R2", "support_mode": "all", "supporting_evidence_ids": ["E2", "E3"]},
                {"requirement_id": "R3", "support_mode": "all", "supporting_evidence_ids": ["E1", "E5"]},
            ],
        }
        self.search = self.enterContext(patch("scripts.check_retrieval.retrieve", return_value=self.matches))
        self.enterContext(redirect_stderr(StringIO()))

    def test_cutoff_boundaries_and_missing_evidence_have_explicit_ranks(self):
        result = check_retrieval(self.connection, self.embedder, "index", {"questions": [self.question]})
        record = result["questions"][0]
        self.assertEqual(result["cutoffs"], [5, 10, 20])
        self.assertEqual(record["evidence_ranks"], {"E1": 5, "E2": 10, "E3": 20, "E4": 21, "E5": None})
        self.assertEqual(record["evidence_hits_at_k"], {
            "5": ["E1"], "10": ["E1", "E2"], "20": ["E1", "E2", "E3"],
        })
        self.assertEqual(len(record["ranking"]), 49)
        self.assertEqual(record["ranking"][0]["snapshot_id"], "snapshot")

    def test_duplicate_annotations_count_once_per_chunk(self):
        question = {**self.question, "evidence": [*self.question["evidence"],
                                                  {"evidence_id": "E6", "chunk_id": "chunk-5"}]}
        result = check_retrieval(self.connection, self.embedder, "index", {"questions": [question]})
        record = result["questions"][0]
        self.assertEqual(record["evidence_hits_at_k"]["5"], ["E1", "E6"])
        self.assertEqual(record["evidence_chunk_hits_at_k"]["5"], ["chunk-5"])
        self.assertEqual(len(record["evidence_chunk_ranks"]), 5)
        self.assertEqual(record["evidence_chunk_recall_at_k"], {"5": .2, "10": .4, "20": .6})
        self.assertEqual(record["evidence_chunk_precision_at_k"]["5"], .2)
        self.assertEqual(record["reciprocal_rank_at_k"]["5"], .2)
        self.assertAlmostEqual(record["ndcg_at_k"]["5"], .13120507751234178)

    def test_ranking_metrics_match_a_hand_calculated_two_reference_example(self):
        question = {**self.question, "evidence": self.question["evidence"][:2],
                    "answer_requirements": self.question["answer_requirements"][:1]}
        metrics = measure_evidence(question, {"chunk-5": 2, "chunk-10": 5})
        self.assertEqual(metrics["evidence_chunk_precision_at_k"], {"5": .4, "10": .2, "20": .1})
        self.assertEqual(metrics["reciprocal_rank_at_k"], {"5": .5, "10": .5, "20": .5})
        for k in ("5", "10", "20"):
            self.assertAlmostEqual(metrics["ndcg_at_k"][k], .6240505200038379)
        earlier = measure_evidence(question, {"chunk-5": 1, "chunk-10": 3})
        self.assertEqual(earlier["evidence_chunk_precision_at_k"], metrics["evidence_chunk_precision_at_k"])
        self.assertGreater(earlier["reciprocal_rank_at_k"]["5"], metrics["reciprocal_rank_at_k"]["5"])
        self.assertGreater(earlier["ndcg_at_k"]["5"], metrics["ndcg_at_k"]["5"])

    def test_short_results_keep_precision_denominator_k(self):
        question = {**self.question, "evidence": self.question["evidence"][:2],
                    "answer_requirements": self.question["answer_requirements"][:1]}
        metrics = measure_evidence(question, {"chunk-5": 1, "chunk-10": 2})
        self.assertEqual(metrics["evidence_chunk_precision_at_k"], {"5": .4, "10": .2, "20": .1})
        self.assertEqual(metrics["evidence_chunk_recall_at_k"], {"5": 1, "10": 1, "20": 1})
        self.assertEqual(metrics["ndcg_at_k"], {"5": 1, "10": 1, "20": 1})

    def test_ndcg_ideal_uses_reference_count_not_just_returned_hits(self):
        question = {**self.question, "evidence": self.question["evidence"][:3],
                    "answer_requirements": self.question["answer_requirements"][:1]}
        metrics = measure_evidence(question, {"chunk-5": 1, "chunk-10": 2})
        self.assertAlmostEqual(metrics["ndcg_at_k"]["5"], .7653606369886217)

    def test_ndcg_ideal_is_limited_to_the_requested_cutoff(self):
        question = {**self.question, "evidence": [
            {"evidence_id": f"E{i}", "chunk_id": f"chunk-{i}"} for i in range(1, 11)
        ]}
        metrics = measure_evidence(question, {f"chunk-{i}": i for i in range(1, 11)})
        self.assertEqual(metrics["evidence_chunk_recall_at_k"]["5"], .5)
        self.assertEqual(metrics["evidence_chunk_precision_at_k"]["5"], 1)
        self.assertEqual(metrics["ndcg_at_k"], {"5": 1, "10": 1, "20": 1})

    def test_first_reference_outside_cutoff_scores_zero_until_it_is_included(self):
        metrics = measure_evidence(self.question, {"chunk-5": 10})
        self.assertEqual(metrics["reciprocal_rank_at_k"], {"5": 0, "10": .1, "20": .1})
        self.assertEqual(metrics["evidence_chunk_precision_at_k"], {"5": 0, "10": .1, "20": .05})
        self.assertEqual(metrics["ndcg_at_k"]["5"], 0)
        self.assertGreater(metrics["ndcg_at_k"]["10"], 0)

    def test_any_and_all_requirements_use_the_first_sufficient_cutoff(self):
        ranks = {"chunk-5": 5, "chunk-10": 10, "chunk-20": 20}
        metrics = measure_evidence(self.question, ranks)
        self.assertEqual(metrics["requirement_ranks"], {"R1": 5, "R2": 20, "R3": None})
        self.assertEqual(metrics["requirements_supported_at_k"], {
            "5": ["R1"], "10": ["R1"], "20": ["R1", "R2"],
        })
        self.assertEqual(metrics["requirement_coverage_at_k"], {"5": 1/3, "10": 1/3, "20": 2/3})
        # An alternative can support any, but a missing member cannot support all.
        metrics = measure_evidence(self.question, {"chunk-10": 3})
        self.assertEqual(metrics["requirement_ranks"], {"R1": 3, "R2": None, "R3": None})

    def test_all_requirement_can_use_two_annotations_from_one_returned_chunk(self):
        question = {**self.question,
                    "evidence": [{"evidence_id": eid, "chunk_id": "shared"} for eid in ("E1", "E2")],
                    "answer_requirements": [{"requirement_id": "R", "support_mode": "all",
                                             "supporting_evidence_ids": ["E1", "E2"]}]}
        metrics = measure_evidence(question, {"shared": 5})
        self.assertEqual(metrics["evidence_chunk_recall_at_k"]["5"], 1)
        self.assertEqual(metrics["requirement_ranks"], {"R": 5})
        self.assertEqual(metrics["requirement_coverage_at_k"]["5"], 1)

    def test_unannotated_chunks_remain_candidates_for_manual_review(self):
        metrics = measure_evidence(self.question, {"possible-alternative": 1, "chunk-5": 6})
        review = metrics["alternative_evidence_review"]
        self.assertEqual(review["status"], "not_reviewed")
        self.assertEqual(review["unannotated_chunk_ids_at_k"]["5"], ["possible-alternative"])
        self.assertEqual(review["unannotated_chunk_ids_at_k"]["10"], ["possible-alternative"])
        self.assertEqual(metrics["evidence_chunk_recall_at_k"]["5"], 0)
        self.assertEqual(metrics["requirement_coverage_at_k"]["5"], 0)

    def test_summary_uses_per_question_means_and_excludes_unanswerable_cases(self):
        second = {**self.question, "question_id": "P02",
                  "evidence": [{"evidence_id": "E1", "chunk_id": "chunk-1"}],
                  "answer_requirements": [{"requirement_id": "R", "support_mode": "any",
                                           "supporting_evidence_ids": ["E1"]}]}
        negative = {**self.question, "question_id": "P19", "answerability": "unanswerable", "evidence": []}
        result = check_retrieval(self.connection, self.embedder, "index", {"questions": [self.question, second, negative]})
        summary = result["summary"]
        self.assertEqual(summary["answerable_questions"], 2)
        self.assertEqual(summary["unanswerable_questions"], 1)
        self.assertAlmostEqual(summary["mean_evidence_chunk_recall_at_k"]["5"], .6)
        self.assertAlmostEqual(summary["mean_requirement_coverage_at_k"]["5"], 2/3)
        self.assertAlmostEqual(summary["mean_evidence_chunk_precision_at_k"]["5"], .2)
        self.assertAlmostEqual(summary["mean_reciprocal_rank_at_k"]["5"], .6)
        self.assertAlmostEqual(summary["mean_ndcg_at_k"]["5"], .5656025387561709)
        self.assertEqual(summary["all_requirements_supported_rate_at_k"]["5"], .5)

    def test_each_original_question_is_retrieved_once_without_gold(self):
        second = {**self.question, "question_id": "P02", "question": "Can lag be NULL?"}
        check_retrieval(self.connection, self.embedder, "index", {"questions": [self.question, second]})
        self.assertEqual(self.search.call_args_list, [
            call(self.connection, self.embedder, "index", self.question["question"], limit=49),
            call(self.connection, self.embedder, "index", second["question"], limit=49),
        ])
        self.connection.commit.assert_not_called()

    def test_an_empty_index_fails_before_retrieving_questions(self):
        self.connection.cursor.return_value.__enter__.return_value.fetchone.return_value = (0,)
        with self.assertRaisesRegex(ValueError, "no stored vectors"):
            check_retrieval(self.connection, self.embedder, "empty", {"questions": [self.question]})
        self.search.assert_not_called()

    def test_full_text_uses_raw_question_without_embedding_or_gold_and_keeps_its_score(self):
        match = {key: value for key, value in self.matches[0].items() if key != "distance"}
        match["text_score"] = 0.2
        with patch("scripts.check_retrieval.search_chunks_full_text", return_value=[match]) as search:
            result = check_retrieval(self.connection, None, "index", {"questions": [self.question]}, method="full-text")
        search.assert_called_once_with(self.connection, "index", self.question["question"], limit=49)
        record = result["questions"][0]
        self.assertEqual(record["ranking"], [match])
        self.assertEqual(record["returned_chunks"], 1)
        self.assertEqual(record["query_input_sha256"], sha256(self.question["question"].encode()).hexdigest())
        self.assertTrue(all(rank is None for rank in record["evidence_ranks"].values()))
        self.search.assert_not_called()

    def test_full_text_empty_results_are_not_padded_with_unmatched_chunks(self):
        with patch("scripts.check_retrieval.search_chunks_full_text", return_value=[]):
            result = check_retrieval(self.connection, None, "index", {"questions": [self.question]}, method="full-text")
        record = result["questions"][0]
        self.assertEqual(record["ranking"], [])
        self.assertEqual(record["evidence_hits_at_k"], {"5": [], "10": [], "20": []})
        self.assertEqual(record["evidence_chunk_recall_at_k"], {"5": 0, "10": 0, "20": 0})
        self.assertEqual(record["requirement_coverage_at_k"], {"5": 0, "10": 0, "20": 0})
        for metric in ("evidence_chunk_precision_at_k", "reciprocal_rank_at_k", "ndcg_at_k"):
            self.assertEqual(record[metric], {"5": 0, "10": 0, "20": 0})
        self.search.assert_not_called()

    def test_hybrid_passes_only_raw_question_and_records_component_ranks(self):
        match = {**self.matches[4], "rrf_score": 1/61 + 1/62, "dense_rank": 1,
                 "full_text_rank": 2, "text_score": .7}
        with patch("scripts.check_retrieval.retrieve_hybrid", return_value=[match]) as search:
            result = check_retrieval(self.connection, self.embedder, "index", {"questions": [self.question]}, method="hybrid")
        search.assert_called_once_with(self.connection, self.embedder, "index", self.question["question"], limit=49)
        self.assertEqual(result["questions"][0]["ranking"], [match])
        self.assertEqual(result["questions"][0]["evidence_ranks"]["E1"], 1)
        self.search.assert_not_called()

    def test_cli_rejects_full_text_tracing_before_loading_or_connecting(self):
        for method in ("full-text", "hybrid"):
            with (self.subTest(method=method),
                  patch("sys.argv", ["check_retrieval.py", "--index-id", "index", "--method", method, "--trace"]),
                  patch("scripts.check_retrieval.NomicEmbedder.from_local") as load,
                  self.assertRaises(SystemExit) as stopped):
                main()
            self.assertEqual(stopped.exception.code, 2)
            load.assert_not_called()

    def test_unanswerable_question_keeps_its_ranking_without_positive_hit_scoring(self):
        question = {**self.question, "question_id": "P19", "answerability": "unanswerable", "evidence": [],
                    "question_type": "insufficient_evidence", "primary_bucket": "NEG01",
                    "scenario_family_id": "missing-policy", "unanswerability": {"reason": "missing_policy"}}
        progress = StringIO()
        with redirect_stderr(progress):
            result = check_retrieval(self.connection, self.embedder, "index", {"questions": [question]})
        record = result["questions"][0]
        self.assertFalse(record["positive_evidence_applicable"])
        self.assertEqual(record["answerability"], "unanswerable")
        self.assertEqual(record["evidence_ranks"], {})
        self.assertEqual(len(record["ranking"]), 49)
        self.assertEqual(record["primary_bucket"], "NEG01")
        self.assertEqual(record["scenario_family_id"], "missing-policy")
        self.assertEqual(record["unanswerability"], {"reason": "missing_policy"})
        self.assertEqual(record["evidence_chunk_recall_at_k"], {"5": None, "10": None, "20": None})
        self.assertEqual(record["requirement_coverage_at_k"], {"5": None, "10": None, "20": None})
        for metric in ("evidence_chunk_precision_at_k", "reciprocal_rank_at_k", "ndcg_at_k"):
            self.assertEqual(record[metric], {"5": None, "10": None, "20": None})
            self.assertEqual(result["summary"]["mean_" + metric], {"5": None, "10": None, "20": None})
        self.assertEqual(record["requirement_ranks"], {})
        self.assertIsNone(record["alternative_evidence_review"])
        self.assertEqual(result["summary"]["mean_evidence_chunk_recall_at_k"]["5"], None)
        self.assertEqual(result["summary"]["all_requirements_supported_rate_at_k"]["5"], None)
        self.assertIn("N/A (no positive evidence", progress.getvalue())
        self.assertNotIn("0/0", progress.getvalue())

    def test_index_scope_requires_exact_pinned_membership_snapshots_and_inputs(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            text = "search_document: A pinned source"
            (root / "chunks.json").write_text(json.dumps({"chunks": [{"chunk_id": "chunk", "embedding_text": text}]}))
            dataset = {"source_state": {"sources": [{"snapshot_id": "snapshot", "files": {"chunks": {"path": "chunks.json"}}}]}}
            row = ("chunk", "snapshot", text, sha256(text.encode()).hexdigest())
            cursor = self.connection.cursor.return_value.__enter__.return_value
            with patch("scripts.check_retrieval.ROOT", root):
                cursor.fetchall.return_value = [row]
                validate_index_scope(self.connection, "index", dataset)
                for rows in ([], [row, ("extra", *row[1:])], [("chunk", "other-snapshot", *row[2:])],
                             [("chunk", "snapshot", text + "changed", row[3])], [(*row[:3], "0" * 64)]):
                    with self.subTest(rows=rows), self.assertRaisesRegex(ValueError, "complete pinned chunk/input scope"):
                        cursor.fetchall.return_value = rows
                        validate_index_scope(self.connection, "index", dataset)
        self.embedder.assert_not_called()

    def test_cli_passes_an_explicit_dataset_to_reference_validation_before_model_loading(self):
        validate = Mock(side_effect=ValueError("fixture validation stop"))
        with (
            patch.dict(sys.modules, {"psycopg": SimpleNamespace(Error=RuntimeError),
                                    "check_document_questions": SimpleNamespace(validate=validate)}),
            patch("sys.argv", ["check_retrieval.py", "--index-id", "index", "--dataset", "atlas.json"]),
            patch("scripts.check_retrieval.NomicEmbedder.from_local") as load_model,
            self.assertRaises(SystemExit) as stopped,
        ):
            main()
        self.assertEqual(stopped.exception.code, 2)
        validate.assert_called_once_with(Path("atlas.json"))
        load_model.assert_not_called()

    def test_tracing_links_each_question_to_its_trace_and_batch_without_changing_ranks(self):
        writer = Mock()
        with patch("scripts.check_retrieval.retrieve_with_trace", return_value=(self.matches, "trace")) as traced:
            result = check_retrieval(self.connection, self.embedder, "index", {"questions": [self.question]},
                                     trace_connection=writer, run_id="batch", configuration={"dataset_version": "1.0"})
        traced.assert_called_once_with(self.connection, writer, self.embedder, "index", self.question["question"],
                                       limit=49, run_id="batch", question_id="P01", configuration={"dataset_version": "1.0"})
        self.assertEqual(result["questions"][0]["trace_id"], "trace")
        self.assertEqual(result["questions"][0]["evidence_ranks"]["E3"], 20)
        self.search.assert_not_called()

    def test_cli_trace_flag_opens_a_writer_and_preserves_the_batch_link_in_json(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "questions.json"
            dataset.write_text(json.dumps({"source_state": {"source_state_id": "fixture-state"}}))
            reader, writer = MagicMock(), MagicMock()
            reader.__enter__.return_value = reader
            writer.__enter__.return_value = writer
            driver = SimpleNamespace(Error=RuntimeError, connect=Mock(side_effect=[reader, writer]))
            embedding = SimpleNamespace(model_dir=root)
            result = {"questions": [{"question_id": "P01", "trace_id": "trace"}]}
            output = StringIO()
            with (
                patch.dict(sys.modules, {"psycopg": driver, "check_document_questions": SimpleNamespace(validate=Mock(return_value={"dataset_version": "fixture"}))}),
                patch.dict("os.environ", {}),
                patch("sys.argv", ["check_retrieval.py", "--index-id", "index", "--trace"]),
                patch("scripts.check_retrieval.ROOT", root),
                patch("scripts.check_retrieval.DATASET", dataset),
                patch("scripts.check_retrieval.load_settings", return_value=SimpleNamespace(embedding=embedding)),
                patch("scripts.check_retrieval.load_database_settings", return_value=SimpleNamespace(connect_kwargs=lambda: {})),
                patch("scripts.check_retrieval.NomicEmbedder.from_local", return_value=self.embedder),
                patch("scripts.check_retrieval.get_embedding_index", return_value={"index_id": "index"}),
                patch("scripts.check_retrieval.validate_index_scope"),
                patch("scripts.check_retrieval.check_retrieval", return_value=result) as check,
                patch("scripts.check_retrieval.file_sha256", return_value="fixture-hash"),
                patch("scripts.check_retrieval.version", return_value="fixture-version"),
                patch("scripts.check_retrieval.subprocess.check_output", side_effect=["fixture-head", " M fixture"]),
                redirect_stdout(output),
            ):
                main()
            report = json.loads(Path(json.loads(output.getvalue())["report"]).read_text())
            self.assertTrue(reader.read_only)
            self.assertTrue(driver.connect.call_args_list[1].kwargs["autocommit"])
            self.assertIs(check.call_args.kwargs["trace_connection"], writer)
            self.assertEqual(check.call_args.kwargs["run_id"], report["run_id"])
            self.assertTrue(report["retrieval_read_only"] and report["tracing_enabled"])
            self.assertFalse(report["read_only"])
            self.assertEqual(report["schema_version"], 4)
            self.assertEqual(report["measurement_version"], "annotated-evidence-v2")
            self.assertEqual(report["questions"][0]["trace_id"], "trace")

    def test_cli_full_text_needs_no_model_settings_weights_or_ml_packages(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "questions.json"
            dataset.write_text(json.dumps({"source_state": {"source_state_id": "fixture-state"}}))
            reader = MagicMock()
            reader.__enter__.return_value = reader
            driver = SimpleNamespace(Error=RuntimeError, connect=Mock(return_value=reader))
            output = StringIO()
            with (
                patch.dict(sys.modules, {"psycopg": driver, "check_document_questions": SimpleNamespace(validate=Mock(return_value={}))}),
                patch("sys.argv", ["check_retrieval.py", "--index-id", "index", "--dataset", str(dataset), "--method", "full-text"]),
                patch("scripts.check_retrieval.ROOT", root),
                patch("scripts.check_retrieval.load_settings", side_effect=AssertionError("No model settings needed")),
                patch("scripts.check_retrieval.NomicEmbedder.from_local", side_effect=AssertionError("No model loading")),
                patch("scripts.check_retrieval.load_database_settings", return_value=SimpleNamespace(connect_kwargs=lambda: {})),
                patch("scripts.check_retrieval.get_embedding_index", return_value={"index_id": "index"}),
                patch("scripts.check_retrieval.validate_index_scope"),
                patch("scripts.check_retrieval.check_retrieval", return_value={"questions": []}) as check,
                patch("scripts.check_retrieval.file_sha256", return_value="fixture-hash"),
                patch("scripts.check_retrieval.version", return_value="fixture-version") as version,
                patch("scripts.check_retrieval.subprocess.check_output", side_effect=["fixture-head", ""]),
                redirect_stdout(output),
            ):
                main()
            report = json.loads(Path(json.loads(output.getvalue())["report"]).read_text())
            version.assert_called_once_with("psycopg")
            self.assertTrue(reader.read_only and report["read_only"])
            self.assertEqual(driver.connect.call_count, 1)
            self.assertIsNone(check.call_args.args[1])
            self.assertEqual(check.call_args.kwargs["method"], "full-text")
            self.assertEqual(report["query_prefix"], "")
            self.assertEqual(report["full_text_settings"]["operator"], "OR")
            self.assertNotIn("model_manifest_sha256", report)


if __name__ == "__main__":
    unittest.main()
