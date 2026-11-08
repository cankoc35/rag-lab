"""Offline adapter/config checks with fake inference; no ML imports or downloads."""

from dataclasses import replace
from hashlib import sha256
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from rag_workflow_lab.config import EmbeddingSettings, load_settings
from rag_workflow_lab.embeddings import (
    DOCUMENT_PREFIX, MODEL_FILES, MODEL_ID, MODEL_REVISION, QUERY_PREFIX,
    EmbeddingError, NomicEmbedder, verify_model_files,
)


class FakeBackend:
    max_tokens = 8192

    def __init__(self):
        self.calls = []
        self.vector = (1.0,) + (0.0,) * 767

    def complete_token_ids(self, text):
        return tuple(range(len(text.split()) + 2))

    def forward_token_ids(self, text):
        return self.complete_token_ids(text)

    def encode_normalized(self, text):
        self.calls.append(text)
        return self.vector


class EmbeddingTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.settings = EmbeddingSettings(MODEL_ID, MODEL_REVISION, self.root)
        self.backend = FakeBackend()
        self.embedder = NomicEmbedder(self.settings, self.backend)
        network = patch("socket.socket.connect", side_effect=AssertionError("Unexpected network access"))
        network.start()
        self.addCleanup(network.stop)

    def test_document_keeps_existing_prefix_and_whitespace(self):
        text = DOCUMENT_PREFIX + "EXPLAIN\n\nSELECT *\n    FROM items;\n"
        result = self.embedder.embed_document(text)
        self.assertEqual(self.backend.calls, [text])
        self.assertEqual(result.task, "document")
        self.assertEqual(result.input_sha256, sha256(text.encode()).hexdigest())
        self.assertEqual(result.token_count, len(self.backend.complete_token_ids(text)))
        self.assertEqual(result.model_revision, MODEL_REVISION)
        self.assertEqual(len(result.vector), 768)

    def test_query_receives_exactly_one_query_prefix(self):
        question = "Can NULL replay_lag mean zero?"
        result = self.embedder.embed_query(question)
        self.assertEqual(self.backend.calls, [QUERY_PREFIX + question])
        self.assertEqual(result.task, "query")
        self.assertEqual(result.model_id, MODEL_ID)
        self.assertAlmostEqual(math.sqrt(sum(v * v for v in result.vector)), 1)

    def test_empty_and_wrong_or_double_prefix_inputs_never_reach_model(self):
        for text in ("", "  ", "SELECT 1;", QUERY_PREFIX + "question", DOCUMENT_PREFIX,
                     DOCUMENT_PREFIX + DOCUMENT_PREFIX + "body", DOCUMENT_PREFIX + QUERY_PREFIX + "body"):
            with self.subTest(document=text), self.assertRaises(EmbeddingError):
                self.embedder.embed_document(text)
        for text in ("", "  ", QUERY_PREFIX + "question", " " + DOCUMENT_PREFIX + "body"):
            with self.subTest(query=text), self.assertRaises(EmbeddingError):
                self.embedder.embed_query(text)
        self.assertEqual(self.backend.calls, [])

    def test_complete_input_budget_counts_prefix_and_special_tokens(self):
        self.embedder.embed_query("word " * 1021)  # prefix + body + two specials = 1024
        self.assertEqual(len(self.backend.calls), 1)
        with self.assertRaisesRegex(EmbeddingError, "not truncated"):
            self.embedder.embed_query("word " * 1022)
        self.assertEqual(len(self.backend.calls), 1)

    def test_changed_or_truncated_forward_token_ids_are_rejected(self):
        for change in (lambda ids: ids[:-1], lambda ids: (999,) + ids[1:]):
            with self.subTest(change=change), patch.object(
                self.backend, "forward_token_ids",
                side_effect=lambda text: change(self.backend.complete_token_ids(text)),
            ), self.assertRaisesRegex(EmbeddingError, "changes or truncates"):
                self.embedder.embed_query("question")
        self.assertEqual(self.backend.calls, [])

    def test_invalid_vector_dimensions_finiteness_and_norm_are_rejected(self):
        for vector in ((1.0,) * 767, (float("nan"),) + (0.0,) * 767,
                       (float("inf"),) + (0.0,) * 767, (0.0,) * 768, (2.0,) + (0.0,) * 767):
            self.backend.vector = vector
            with self.subTest(vector_head=vector[:1]), self.assertRaises(EmbeddingError):
                self.embedder.embed_query("question")

    def test_wrong_model_revision_dimensions_device_or_budget_is_explicit(self):
        for settings in (replace(self.settings, model_id="other/model"),
                         replace(self.settings, revision="0" * 40),
                         replace(self.settings, dimensions=1024),
                         replace(self.settings, device="mps"),
                         replace(self.settings, max_tokens=0),
                         replace(self.settings, max_tokens=True),
                         replace(self.settings, max_tokens=8193)):
            with self.subTest(settings=settings), self.assertRaises(EmbeddingError):
                NomicEmbedder(settings, self.backend)

    def test_missing_cache_fails_before_importing_ml_libraries(self):
        import builtins
        original = builtins.__import__

        def reject_ml(name, *args, **kwargs):
            if name in {"torch", "sentence_transformers"}:
                raise AssertionError("ML import before checking local files")
            return original(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=reject_ml), self.assertRaisesRegex(
            EmbeddingError, "download-model"
        ):
            NomicEmbedder.from_local(self.settings)

    def test_cached_model_manifest_and_tampered_file_detection(self):
        folder = self.settings.model_dir
        folder.mkdir(parents=True)
        records = {}
        for name in MODEL_FILES:
            path = folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            data = ("synthetic asset " + name).encode()
            path.write_bytes(data)
            records[name] = {"sha256": sha256(data).hexdigest(), "size_bytes": len(data)}
        manifest = {"schema_version": 1, "model_id": MODEL_ID, "revision": MODEL_REVISION, "files": records}
        (folder / "model_manifest.json").write_text(json.dumps(manifest))
        self.assertEqual(verify_model_files(self.settings), manifest)
        (folder / "model.safetensors").write_bytes(b"changed")
        with self.assertRaisesRegex(EmbeddingError, "checksum mismatch"):
            verify_model_files(self.settings)

    def write_config(self, section=""):
        path = self.root / "pilot.toml"
        path.write_text('[project]\nname="fixture"\n[paths]\nsources_manifest="sources.json"\nlocal_data_dir="local"\n' + section)
        return path

    def test_legacy_config_needs_no_model_and_embedding_paths_are_relative(self):
        self.assertIsNone(load_settings(self.write_config()).embedding)
        section = f'[embedding]\nmodel_id="{MODEL_ID}"\nrevision="{MODEL_REVISION}"\nmodels_dir="models"\n'
        settings = load_settings(self.write_config(section)).embedding
        self.assertEqual(settings.models_dir, self.root / "models")
        self.assertEqual(settings.model_dir, self.root / "models/nomic-ai--nomic-embed-text-v1.5" / MODEL_REVISION)
        self.assertEqual(settings.max_tokens, 1024)

    def test_invalid_embedding_config_is_rejected_without_model_loading(self):
        valid = f'[embedding]\nmodel_id="{MODEL_ID}"\nrevision="{MODEL_REVISION}"\nmodels_dir="models"\n'
        for section in ("[embedding]\n", valid.replace(MODEL_REVISION, "main"),
                        valid.replace(MODEL_ID, "../model"), valid + 'dimensions=true\n',
                        valid + 'max_tokens=0\n', valid + 'device="mps"\n'):
            with self.subTest(section=section), self.assertRaises(ValueError):
                load_settings(self.write_config(section))


if __name__ == "__main__":
    unittest.main()
