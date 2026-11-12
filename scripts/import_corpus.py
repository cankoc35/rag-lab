"""Import the pilot's saved snapshots and chunks in one database transaction."""

import argparse
import json
from pathlib import Path

from rag_workflow_lab.config import load_database_settings, load_settings
from rag_workflow_lab.ingestion.download import load_sources
from rag_workflow_lab.ingestion.parse import parse_snapshot
from rag_workflow_lab.store import save_chunks, save_snapshots


ROOT = Path(__file__).resolve().parents[1]


def load_corpus(chunk_dir: Path, snapshots_dir: Path, sources_manifest: Path) -> tuple[list, list]:
    """Read one chunk file per allowlisted source and verify its snapshot."""
    snapshots, chunks = [], []
    chunk_ids = set()
    for source in load_sources(sources_manifest):
        files = sorted(chunk_dir.glob(f"{source.source_id}-*.json"))
        if len(files) != 1:
            raise ValueError(f"Expected one chunk file for {source.source_id}, found {len(files)}.")
        payload = json.loads(files[0].read_text(encoding="utf-8"))
        snapshot_id = payload["snapshot_id"]
        if (payload["schema_version"] != 1 or payload["source_id"] != source.source_id
                or files[0].name != f"{snapshot_id}.json" or not payload["chunks"]):
            raise ValueError(f"Invalid chunk file for {source.source_id}.")
        manifest = snapshots_dir / snapshot_id / "manifest.json"
        document = parse_snapshot(manifest, source)
        if document.snapshot_id != snapshot_id:
            raise ValueError(f"Snapshot identity mismatch: {snapshot_id}")
        snapshots.append(json.loads(manifest.read_text(encoding="utf-8"))["snapshot"])
        for chunk in payload["chunks"]:
            if (chunk["source_id"], chunk["snapshot_id"], chunk["source_sha256"],
                chunk["source_url"], chunk["parser_version"]) != (
                    source.source_id, snapshot_id, document.source_sha256,
                    document.source_url, document.parser_version):
                raise ValueError(f"Chunk provenance mismatch: {chunk['chunk_id']}")
            if chunk["chunk_id"] in chunk_ids:
                raise ValueError(f"Duplicate chunk ID: {chunk['chunk_id']}")
            chunk_ids.add(chunk["chunk_id"])
            chunks.append(chunk)
    return snapshots, chunks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks-dir", type=Path, default=(
        ROOT / "data/local/chunks/pilot-section-blocks-v1"
    ))
    args = parser.parse_args()
    try:
        import psycopg
    except ImportError:
        parser.exit(2, "Install the 'database' optional dependencies first.\n")

    try:
        settings = load_settings(ROOT / "configs/pilot.toml")
        snapshots, chunks = load_corpus(
            args.chunks_dir, settings.local_data_dir / "snapshots", settings.sources_manifest,
        )
        database = load_database_settings()
        with psycopg.connect(
            **database.connect_kwargs(), options="-c statement_timeout=5000"
        ) as connection:
            save_snapshots(connection, snapshots)
            save_chunks(connection, chunks)
    except psycopg.Error:
        parser.exit(2, "Corpus import failed. Check the database connection and schema; no changes committed.\n")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Corpus import failed: {exc}\n")
    print(json.dumps({"status": "imported", "snapshots": len(snapshots), "chunks": len(chunks)}, indent=2))


if __name__ == "__main__":
    main()
