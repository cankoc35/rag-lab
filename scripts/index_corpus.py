# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "sentence-transformers==5.3.0",
#   "transformers==5.5.0",
#   "torch==2.10.0",
#   "tokenizers==0.22.2",
#   "psycopg[binary]==3.3.8",
# ]
# ///
"""Embed all stored corpus chunks locally and commit one reproducible index."""

import argparse
from hashlib import sha256
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys

from rag_workflow_lab.config import EmbeddingSettings, load_database_settings, load_settings
from rag_workflow_lab.embeddings import (
    ADAPTER_VERSION, DOCUMENT_PREFIX, NORMALIZATION, QUERY_PREFIX, NomicEmbedder, file_sha256,
)
from rag_workflow_lab.store import save_embedding_index, save_embeddings


ROOT = Path(__file__).resolve().parents[1]


def build_index(chunks: list[tuple[str, str, int]], embedding: EmbeddingSettings, runtime: dict) -> dict:
    """Identify the exact chunk inputs, model and runtime independently of row order."""
    inputs = [(chunk_id, sha256(text.encode("utf-8")).hexdigest())
              for chunk_id, text, _ in sorted(chunks)]
    index = {
        "model_id": embedding.model_id, "model_revision": embedding.revision,
        "dimensions": embedding.dimensions,
        "chunk_set_sha256": sha256(json.dumps(inputs).encode()).hexdigest(),
        "settings": {
            **runtime, "indexer_version": "corpus-index-v1", "adapter_version": ADAPTER_VERSION,
            "document_prefix": DOCUMENT_PREFIX, "query_prefix": QUERY_PREFIX,
            "normalization": NORMALIZATION, "device": embedding.device,
            "dtype": "float32", "max_tokens": embedding.max_tokens,
        },
    }
    index_id = "nomic-" + sha256(json.dumps(index, sort_keys=True).encode()).hexdigest()
    return {"index_id": index_id, **index}


def index_corpus(connection, embedder: NomicEmbedder, runtime: dict) -> dict:
    """Generate exact document inputs and save the index in the caller's transaction."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT chunk_id, embedding_text, token_count FROM chunks ORDER BY chunk_id")
        chunks = cursor.fetchall()
    if not chunks:
        raise ValueError("No stored chunks. Run scripts/import_corpus.py first.")
    print(f"Found {len(chunks)} chunks.", file=sys.stderr, flush=True)
    index = build_index(chunks, embedder.settings, runtime)
    results = []
    for position, (chunk_id, text, tokens) in enumerate(chunks, 1):
        print(f"Embedding chunk {position}/{len(chunks)} ({tokens} tokens)...", file=sys.stderr, flush=True)
        result = embedder.embed_document(text)
        if result.token_count != tokens:
            raise ValueError(f"Stored token count differs from the model tokenizer: {chunk_id}")
        results.append((chunk_id, result))
    print("Saving index and embeddings...", file=sys.stderr, flush=True)
    save_embedding_index(connection, index)
    save_embeddings(connection, index["index_id"], results)
    return {"status": "indexed", "index_id": index["index_id"],
            "chunks": len(results), "dimensions": index["dimensions"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/pilot.toml")
    args = parser.parse_args()
    print("Starting corpus indexing...", file=sys.stderr, flush=True)
    try:
        import psycopg
    except ImportError:
        parser.exit(2, "Run this script with its uv dependency environment.\n")

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    try:
        settings = load_settings(args.config)
        if settings.embedding is None:
            raise ValueError("Config has no embedding section.")
        print(f"Loading local model {settings.embedding.model_id}...", file=sys.stderr, flush=True)
        embedder = NomicEmbedder.from_local(settings.embedding)
        print("Model loaded.", file=sys.stderr, flush=True)
        runtime = {
            "lock_sha256": file_sha256(ROOT / "scripts/index_corpus.py.lock"),
            "model_manifest_sha256": file_sha256(settings.embedding.model_dir / "model_manifest.json"),
            "libraries": {name: version(name) for name in (
                "sentence-transformers", "transformers", "torch", "tokenizers", "psycopg",
            )},
            "code_sha256": {name: file_sha256(ROOT / name) for name in (
                "scripts/index_corpus.py", "src/rag_workflow_lab/embeddings.py", "src/rag_workflow_lab/store.py",
            )},
        }
        database = load_database_settings()
        print("Connecting to PostgreSQL...", file=sys.stderr, flush=True)
        with psycopg.connect(
            **database.connect_kwargs(), options="-c statement_timeout=5000"
        ) as connection:
            result = index_corpus(connection, embedder, runtime)
    except psycopg.Error:
        parser.exit(2, "Corpus indexing failed. Check the database connection and schema.\n")
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Corpus indexing failed: {exc}\n")
    print("Index committed.", file=sys.stderr, flush=True)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
