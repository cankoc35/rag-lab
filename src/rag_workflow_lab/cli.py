"""CLI for local checks, explicit DB checks/downloads and offline parsing."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from rag_workflow_lab import __version__
from rag_workflow_lab.config import load_database_settings, load_settings
from rag_workflow_lab.ingestion.download import SourceDownloadError, download_source, load_sources
from rag_workflow_lab.ingestion.parse import parse_snapshot
from rag_workflow_lab.store import DatabaseCheckError, check_database


def main(argv: list[str] | None = None) -> int:
    """Run an explicit command; never start network/model operations on import."""
    parser = argparse.ArgumentParser(
        prog="rag-workflow-lab",
        description="RAG Workflow Lab development scaffold.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command")
    for name, help_text in (
        ("check-config", "Read and validate local TOML settings."),
        ("check-sources", "Read and validate the selected source list without downloading."),
        ("download-source", "Download one selected HTML source and save its snapshot manifest."),
        ("parse-source", "Parse one saved, allowlisted HTML snapshot without network access."),
    ):
        check = commands.add_parser(name, help=help_text)
        check.add_argument("--config", type=Path, default=Path("configs/pilot.toml"))
        if name == "download-source":
            check.add_argument("--source-id", required=True)
            check.add_argument("--timeout", type=float, default=30.0, help="Socket timeout in seconds (default: 30).")
        if name == "parse-source":
            check.add_argument("--source-id", required=True)
            check.add_argument("--manifest", type=Path, required=True)
    commands.add_parser("check-db", help="Check PostgreSQL and pgvector with read-only SQL using POSTGRES_* settings.")
    args = parser.parse_args(argv)

    if args.command == "check-db":
        try:
            result = check_database(load_database_settings())
        except (ValueError, DatabaseCheckError) as exc:
            parser.exit(2, f"Database check failed: {exc}\n")
        print(json.dumps({"status": "ok", **asdict(result)}, indent=2))
        return 0

    if args.command in {"check-config", "check-sources", "download-source", "parse-source"}:
        try:
            settings = load_settings(args.config)
            if args.command in {"download-source", "parse-source"}:
                sources = load_sources(settings.sources_manifest)
                source = next((source for source in sources if source.source_id == args.source_id), None)
                if source is None:
                    raise ValueError(f"Unknown selected source_id: {args.source_id}")
                if args.command == "parse-source":
                    payload = {"schema_version": 1, "document": asdict(parse_snapshot(args.manifest, source))}
                else:
                    output_dir = settings.local_data_dir / "snapshots"
                    snapshot = download_source(source, output_dir, timeout=args.timeout)
                    payload = {
                        "manifest_path": str(output_dir / snapshot.snapshot_id / "manifest.json"),
                        "snapshot": asdict(snapshot),
                    }
            elif args.command == "check-sources":
                sources = load_sources(settings.sources_manifest)
                payload = {
                    "sources_manifest": str(settings.sources_manifest),
                    "source_count": len(sources),
                    "sources": [asdict(source) for source in sources],
                }
            else:
                payload = {
                    "project_name": settings.project_name,
                    "config_path": str(settings.config_path),
                    "sources_manifest": str(settings.sources_manifest),
                    "local_data_dir": str(settings.local_data_dir),
                }
        except (OSError, ValueError, SourceDownloadError) as exc:
            parser.exit(2, f"Operation failed: {exc}\n")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    parser.print_help()
    return 0
