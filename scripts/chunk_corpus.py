# /// script
# requires-python = ">=3.11"
# dependencies = ["tokenizers==0.22.2"]
# ///
"""Chunk the pilot's saved HTML snapshots with the cached Nomic tokenizer.

Run with PYTHONPATH=src and uv --offline. No downloads or model inference.
Select exactly one saved snapshot per allowlisted source. All documents are
validated before a new output directory is created; existing runs are preserved.
"""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import tokenizers

from measure_block_tokens import FILES, MODEL_ID, REVISION, ROOT, prepare_tokenizer
from rag_workflow_lab.contracts import TokenizerSpec
from rag_workflow_lab.ingestion.chunk import CHUNKER_VERSION, ChunkSettings, chunk_document
from rag_workflow_lab.ingestion.download import load_sources
from rag_workflow_lab.ingestion.parse import parse_snapshot


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args) -> dict:
    if args.output_dir.exists():
        raise ValueError(f"Output directory already exists: {args.output_dir}")
    if tokenizers.__version__ != "0.22.2":
        raise ValueError("Run with the pinned tokenizers==0.22.2 dependency")
    tokenizer = prepare_tokenizer(args.tokenizer_dir, allow_download=False)
    setup = {
        "model_id": MODEL_ID, "revision": REVISION, "files_sha256": FILES,
        "backend": "tokenizers==0.22.2", "add_special_tokens": True,
        "truncation": False, "padding": False,
    }
    config = json.loads((args.tokenizer_dir / "tokenizer_config.json").read_text(encoding="utf-8"))
    spec = TokenizerSpec(
        identifier=MODEL_ID, revision=REVISION,
        fingerprint=hashlib.sha256(json.dumps(setup, sort_keys=True).encode()).hexdigest(),
        max_input_tokens=config["model_max_length"],
    )

    def count(text):
        return len(tokenizer.encode(text, add_special_tokens=True).ids)

    if count("test " * 9000) != 9002:
        raise ValueError("Tokenizer must count long inputs without truncation")
    settings = ChunkSettings()
    outputs, statistics, inputs = {}, [], []
    for source in load_sources(args.sources_manifest):
        candidates = sorted(args.snapshots_dir.glob(f"{source.source_id}-*/manifest.json"))
        if len(candidates) != 1:
            raise ValueError(
                f"Expected one snapshot for {source.source_id}, found {len(candidates)}. "
                "Use --snapshots-dir to select a directory with one snapshot per source."
            )
        manifest = candidates[0]
        document = parse_snapshot(manifest, source)
        chunks = chunk_document(document, count_tokens=count, tokenizer=spec, settings=settings)
        if chunks != chunk_document(document, count_tokens=count, tokenizer=spec, settings=settings):
            raise ValueError(f"Nondeterministic chunk output: {source.source_id}")
        expected = [(i, block) for i, block in enumerate(document.blocks, 1) if block.kind != "heading"]
        actual = [(i, block) for chunk in chunks for i, block in zip(chunk.block_indices, chunk.blocks)]
        if actual != expected:
            raise ValueError(f"Source blocks lost, duplicated or changed: {source.source_id}")
        for chunk in chunks:
            if count(chunk.embedding_text) != chunk.token_count or chunk.token_count > settings.max_tokens:
                raise ValueError(f"Invalid complete-input token count: {chunk.chunk_id}")
            if any(block.heading_path != chunk.heading_path for block in chunk.blocks):
                raise ValueError(f"Chunk crosses heading boundaries: {chunk.chunk_id}")
        sizes = [chunk.token_count for chunk in chunks]
        statistics.append({
            "source_id": source.source_id, "parsed_blocks": len(document.blocks),
            "content_blocks": len(expected), "chunks": len(chunks),
            "code_blocks_preserved": sum(block.kind == "code" for _, block in actual),
            "tables_preserved": sum(block.kind == "table" for _, block in actual),
            "min_tokens": min(sizes, default=0), "max_tokens": max(sizes, default=0),
            "over_target": sum(size > settings.target_tokens for size in sizes),
        })
        inputs.append({
            "manifest": str(manifest.resolve()), "manifest_sha256": file_hash(manifest),
            "source_id": source.source_id, "snapshot_id": document.snapshot_id,
            "source_sha256": document.source_sha256,
        })
        outputs[document.snapshot_id + ".json"] = {
            "schema_version": 1, "source_id": source.source_id,
            "snapshot_id": document.snapshot_id,
            "heading_blocks": [
                {"block_index": i, "block": asdict(block)}
                for i, block in enumerate(document.blocks, 1) if block.kind == "heading"
            ],
            "chunks": [asdict(chunk) for chunk in chunks],
        }
    summary = {
        "schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Offline chunking verification, not embedding or retrieval evaluation",
        "settings": asdict(settings), "chunker_version": CHUNKER_VERSION,
        "tokenizer_setup": setup, "tokenizer": asdict(spec), "inputs": inputs,
        "code_sha256": {
            str(path.relative_to(ROOT)): file_hash(path) for path in (
                Path(__file__).resolve(), ROOT / "scripts/measure_block_tokens.py",
                ROOT / "src/rag_workflow_lab/contracts.py",
                ROOT / "src/rag_workflow_lab/ingestion/chunk.py",
                ROOT / "src/rag_workflow_lab/ingestion/parse.py",
            )
        },
        "sources": statistics,
        "verification": "All content blocks preserved exactly once in source order; "
        "SQL whitespace and table cells unchanged; section boundaries and token limits "
        "checked; repeated calls identical; network blocked.",
    }
    args.output_dir.mkdir(parents=True)
    for name, payload in {**outputs, "summary.json": summary}.items():
        with (args.output_dir / name).open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    return {"output_dir": str(args.output_dir), "sources": statistics}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources-manifest", type=Path, default=ROOT / "data/corpus/sources.json")
    parser.add_argument("--snapshots-dir", type=Path, default=ROOT / "data/local/snapshots")
    parser.add_argument("--tokenizer-dir", type=Path, default=(
        ROOT / "data/local/tokenizers/nomic-embed-text-v1.5" / REVISION
    ))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/local/chunks" / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    ))
    args = parser.parse_args()
    try:
        with patch("socket.socket.connect", side_effect=OSError("Network disabled for chunking")):
            result = run(args)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
