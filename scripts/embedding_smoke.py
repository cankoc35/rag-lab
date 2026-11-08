# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "sentence-transformers==5.3.0",
#   "transformers==5.5.0",
#   "torch==2.10.0",
#   "tokenizers==0.22.2",
# ]
# ///
"""Opt-in local embedding smoke: one largest chunk and one development question.

Use PYTHONPATH=src with uv. Downloads require --download-model. Subsequent
model loading/inference is offline; vectors and metadata go to a fresh run
directory, never into the source artifacts or evaluation labels.
"""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import time
from unittest.mock import patch

from check_document_questions import validate
from rag_workflow_lab.config import load_settings
from rag_workflow_lab.embeddings import (
    ADAPTER_VERSION, DOCUMENT_PREFIX, MODEL_FILES, MODEL_ID, MODEL_REVISION,
    NORMALIZATION, QUERY_PREFIX, EmbeddingError, NomicEmbedder, file_sha256,
)


ROOT = Path(__file__).resolve().parents[1]


def download_model(settings) -> None:
    """Only fixed public model assets; no pickle weights or repository Python files."""
    if settings.model_id != MODEL_ID or settings.revision != MODEL_REVISION:
        raise ValueError("Download requires the configured pinned Nomic snapshot.")
    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=settings.model_id, revision=settings.revision,
        local_dir=str(settings.model_dir), allow_patterns=list(MODEL_FILES),
        token=False, max_workers=2,
    )
    manifest = {
        "schema_version": 1, "model_id": settings.model_id, "revision": settings.revision,
        "files": {name: {
            "sha256": file_sha256(settings.model_dir / name),
            "size_bytes": (settings.model_dir / name).stat().st_size,
        } for name in MODEL_FILES},
    }
    path = settings.model_dir / "model_manifest.json"
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != manifest:
            raise ValueError("Existing model manifest differs; it was not overwritten.")
    else:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2)
            handle.write("\n")


def run(args) -> dict:
    if args.output_dir.exists():
        raise ValueError(f"Output directory already exists: {args.output_dir}")
    settings = load_settings(args.config)
    if settings.embedding is None:
        raise ValueError("Config has no embedding section.")
    validate(args.dataset)
    data = json.loads(args.dataset.read_text(encoding="utf-8"))
    question = next((q for q in data["questions"] if q["question_id"] == args.question_id), None)
    if question is None:
        raise ValueError(f"Unknown development question: {args.question_id}")
    chunks = []
    for source in data["source_state"]["sources"]:
        payload = json.loads((ROOT / source["files"]["chunks"]["path"]).read_text(encoding="utf-8"))
        chunks.extend(payload["chunks"])
    selected = max(chunks, key=lambda chunk: chunk["token_count"])
    if args.download_model:
        download_model(settings.embedding)
    started = time.perf_counter()
    with patch("socket.socket.connect", side_effect=OSError("Network disabled during local inference")):
        embedder = NomicEmbedder.from_local(settings.embedding)
        load_seconds = time.perf_counter() - started
        for chunk in chunks:
            if embedder.count_tokens(chunk["embedding_text"]) != chunk["token_count"]:
                raise ValueError(f"Tokenizer differs from the saved chunk count: {chunk['chunk_id']}")
        started = time.perf_counter()
        document = embedder.embed_document(selected["embedding_text"])
        query = embedder.embed_query(question["question"])
        encode_seconds = time.perf_counter() - started
        try:
            embedder.embed_query("word " * settings.embedding.max_tokens)
        except EmbeddingError as exc:
            if "not truncated" not in str(exc):
                raise
        else:
            raise ValueError("Oversized query was not rejected before inference.")

    code_paths = [
        Path(__file__).resolve(), ROOT / "src/rag_workflow_lab/embeddings.py",
        ROOT / "src/rag_workflow_lab/config.py", ROOT / "pyproject.toml", args.config.resolve(),
    ]
    lock = Path(str(Path(__file__).resolve()) + ".lock")
    if lock.exists():
        code_paths.append(lock)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True, check=False).stdout.strip() or None
    report = {
        "schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Runtime smoke only: no ranking, retrieval score, generator or database",
        "adapter_version": ADAPTER_VERSION,
        "model": {
            "model_id": settings.embedding.model_id, "revision": settings.embedding.revision,
            "model_dir": str(settings.embedding.model_dir.relative_to(ROOT)),
            "manifest_sha256": file_sha256(settings.embedding.model_dir / "model_manifest.json"),
            "device": "cpu", "dtype": "float32", "cpu_threads": 2,
            "dimensions": 768, "application_max_tokens": settings.embedding.max_tokens,
            "normalization": NORMALIZATION, "trust_remote_code": False,
            "implementation": "transformers.models.nomic_bert.modeling_nomic_bert",
        },
        "runtime": {"python": platform.python_version(), "platform": platform.platform(),
                    "packages": {p: version(p) for p in (
                        "sentence-transformers", "transformers", "torch", "tokenizers",
                        "huggingface-hub", "numpy", "safetensors",
                    )}},
        "dataset": {"dataset_id": data["dataset_id"], "dataset_version": data["dataset_version"],
                    "sha256": file_sha256(args.dataset)},
        "document": {"chunk_id": selected["chunk_id"], "source_id": selected["source_id"],
                     "snapshot_id": selected["snapshot_id"], "block_indices": selected["block_indices"],
                     "input_text": selected["embedding_text"], "embedding": asdict(document)},
        "query": {"question_id": question["question_id"],
                  "input_text": QUERY_PREFIX + question["question"], "embedding": asdict(query)},
        "checks": {
            "saved_chunk_token_counts_matched": len(chunks),
            "full_forward_token_ids_match_untruncated_inputs": True,
            "one_task_prefix_per_input": True, "finite_unit_vectors": True,
            "oversized_query_rejected": True, "inference_network_blocked": True,
        },
        "timing_seconds": {"load_and_integrity_check": load_seconds, "encode_pair": encode_seconds},
        "code_commit": commit,
        "code_sha256": {str(p.relative_to(ROOT)): file_sha256(p) for p in code_paths},
    }
    args.output_dir.mkdir(parents=True)
    with (args.output_dir / "smoke.json").open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return {
        "report": str(args.output_dir / "smoke.json"), "dimensions": len(document.vector),
        "document_tokens": document.token_count, "query_tokens": query.token_count,
        "document_norm": math.sqrt(sum(x * x for x in document.vector)),
        "query_norm": math.sqrt(sum(x * x for x in query.vector)), "checks": report["checks"],
    }


def main() -> None:
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/pilot.toml")
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/evaluation/dev/document_questions.json")
    parser.add_argument("--question-id", default="P04")
    parser.add_argument("--download-model", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/embeddings" / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    ))
    args = parser.parse_args()
    try:
        result = run(args)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
