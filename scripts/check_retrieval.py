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
"""Check a development dataset's evidence ranks with local inference and read-only SQL."""

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter

from rag_workflow_lab.config import load_database_settings, load_settings
from rag_workflow_lab.embeddings import NomicEmbedder, QUERY_PREFIX, file_sha256
from rag_workflow_lab.retrieval import retrieve
from rag_workflow_lab.store import get_embedding_index
from rag_workflow_lab.tracing import retrieve_with_trace


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/evaluation/dev/document_questions.json"
CUTOFFS = (5, 10, 20)


def validate_index_scope(connection, index_id: str, dataset: dict) -> None:
    """Require exactly the pinned chunks and embedding inputs, including negative-case scope."""
    expected = {}
    for source in dataset["source_state"]["sources"]:
        document = json.loads((ROOT / source["files"]["chunks"]["path"]).read_text())
        for chunk in document["chunks"]:
            expected[chunk["chunk_id"]] = (source["snapshot_id"], chunk["embedding_text"])
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT c.chunk_id, c.snapshot_id, c.embedding_text, e.input_sha256
            FROM chunk_embeddings e JOIN chunks c USING (chunk_id)
            WHERE e.index_id = %s
        """, (index_id,))
        rows = cursor.fetchall()
    actual = {cid: (snapshot, text) for cid, snapshot, text, _ in rows}
    if actual != expected or any(sha256(text.encode()).hexdigest() != checksum
                                 for _, _, text, checksum in rows):
        raise ValueError("Selected index does not match the dataset's complete pinned chunk/input scope.")


def check_retrieval(connection, embedder, index_id: str, dataset: dict, *,
                    trace_connection=None, run_id=None, configuration=None) -> dict:
    """Retrieve each raw question once, then inspect annotated evidence IDs."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM chunk_embeddings WHERE index_id = %s", (index_id,))
        count = cursor.fetchone()[0]
    if count == 0:
        raise ValueError("The selected index has no stored vectors.")

    records = []
    for question in dataset["questions"]:
        print(f"Retrieving {question['question_id']}...", file=sys.stderr, flush=True)
        start = perf_counter()
        trace_id = None
        if trace_connection is None:
            matches = retrieve(connection, embedder, index_id, question["question"], limit=count)
        else:
            matches, trace_id = retrieve_with_trace(
                connection, trace_connection, embedder, index_id, question["question"], limit=count,
                run_id=run_id, question_id=question["question_id"], configuration=configuration,
            )
        elapsed = perf_counter() - start
        ranks = {match["chunk_id"]: rank for rank, match in enumerate(matches, 1)}
        evidence_ranks = {e["evidence_id"]: ranks.get(e["chunk_id"]) for e in question["evidence"]}
        hits = {str(k): [eid for eid, rank in evidence_ranks.items() if rank is not None and rank <= k]
                for k in CUTOFFS}
        records.append({
            "question_id": question["question_id"], "question": question["question"],
            "answerability": question.get("answerability", "answerable"),
            "positive_evidence_applicable": bool(evidence_ranks),
            "query_input_sha256": sha256((QUERY_PREFIX + question["question"]).encode()).hexdigest(),
            "elapsed_seconds": elapsed, "evidence_ranks": evidence_ranks, "evidence_hits_at_k": hits,
            "ranking": [{key: match[key] for key in (
                "chunk_id", "source_id", "snapshot_id", "url", "distance", "token_count",
            )} for match in matches],
        })
        if trace_id is not None:
            records[-1]["trace_id"] = trace_id
        summary = ", ".join(f"@{k}={len(hits[str(k)])}/{len(evidence_ranks)}" for k in CUTOFFS)
        if not evidence_ranks:
            summary = "N/A (no positive evidence; inspect returned context and abstention separately)"
        print(f"{question['question_id']}: annotated hits {summary}", file=sys.stderr, flush=True)
    return {"indexed_chunks": count, "cutoffs": list(CUTOFFS), "questions": records}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-id", required=True, help="Existing embedding index to inspect.")
    parser.add_argument("--dataset", type=Path, default=DATASET, help="Development dataset JSON; default: PostgreSQL P01–P06.")
    parser.add_argument("--trace", action="store_true", help="Write question traces; requires applied migration 0002.")
    args = parser.parse_args()

    import psycopg
    from check_document_questions import validate

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    try:
        print("Checking pinned development references...", file=sys.stderr, flush=True)
        dataset_check = validate(args.dataset)
        dataset = json.loads(args.dataset.read_text())
        settings = load_settings(ROOT / "configs/pilot.toml")
        created = datetime.now(timezone.utc)
        run_id = created.strftime("dense-%Y%m%dT%H%M%S%fZ")
        provenance = {
            "dataset": dataset_check, "dataset_path": str(args.dataset.resolve()),
            "source_state_id": dataset["source_state"]["source_state_id"],
            "libraries": {name: version(name) for name in (
                "sentence-transformers", "transformers", "torch", "tokenizers", "psycopg",
            )},
            "model_manifest_sha256": file_sha256(settings.embedding.model_dir / "model_manifest.json"),
            "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)),
            "code_sha256": {name: file_sha256(ROOT / name) for name in (
                "scripts/check_retrieval.py", "scripts/check_retrieval.py.lock",
                "scripts/check_document_questions.py", "configs/pilot.toml",
                "src/rag_workflow_lab/retrieval.py", "src/rag_workflow_lab/store.py",
                "src/rag_workflow_lab/embeddings.py", "src/rag_workflow_lab/tracing.py",
            )},
        }
        print("Connecting to PostgreSQL in read-only mode...", file=sys.stderr, flush=True)
        database = load_database_settings()
        with ExitStack() as stack:
            connection = stack.enter_context(psycopg.connect(
                **database.connect_kwargs(), options="-c statement_timeout=5000"
            ))
            connection.read_only = True
            index = get_embedding_index(connection, args.index_id)
            validate_index_scope(connection, args.index_id, dataset)
            print("Loading the cached Nomic model once...", file=sys.stderr, flush=True)
            embedder = NomicEmbedder.from_local(settings.embedding)
            writer = None
            if args.trace:
                print("Opening a separate trace writer...", file=sys.stderr, flush=True)
                writer = stack.enter_context(psycopg.connect(
                    **database.connect_kwargs(), autocommit=True, options="-c statement_timeout=5000"
                ))
            result = check_retrieval(connection, embedder, args.index_id, dataset,
                                     trace_connection=writer, run_id=run_id,
                                     configuration={**provenance, "index": index})

        report = {
            "schema_version": 2, "run_id": run_id, "created_at": created.isoformat(),
            "scope": "Development annotation-ID diagnostics, not answer-quality grades or a held-out benchmark.",
            "index": index, "read_only": not args.trace, "retrieval_read_only": True,
            "tracing_enabled": args.trace,
            "query_prefix": QUERY_PREFIX, **provenance,
            **result,
        }
        output = ROOT / "outputs/retrieval" / f"{run_id}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
    except psycopg.Error:
        parser.exit(2, "Retrieval check failed. Check the database connection and schema.\n")
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Retrieval check failed: {exc}\n")
    print(json.dumps({"report": str(output), "questions": len(result["questions"])}))


if __name__ == "__main__":
    main()
