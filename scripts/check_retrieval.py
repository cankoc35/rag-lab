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
"""Check development evidence ranks with dense, full-text or hybrid retrieval."""

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
from rag_workflow_lab.retrieval import HYBRID_CANDIDATES, RRF_K, retrieve, retrieve_hybrid
from rag_workflow_lab.store import get_embedding_index, search_chunks_full_text
from rag_workflow_lab.tracing import retrieve_with_trace


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/evaluation/dev/document_questions.json"
CUTOFFS = (5, 10, 20)
MEASUREMENT_VERSION = "annotated-evidence-v1"
FULL_TEXT_SETTINGS = {"configuration": "english", "query_parser": "normalized_lexemes_or_v1",
                      "operator": "OR", "ranking": "ts_rank_cd", "normalization": 0,
                      "document_field": "chunks.text"}


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


def measure_evidence(question: dict, ranks: dict) -> dict:
    """Measure annotated support after retrieval; unannotated passages remain unjudged."""
    evidence_chunks = {e["evidence_id"]: e["chunk_id"] for e in question["evidence"]}
    chunk_ranks = {cid: ranks.get(cid) for cid in evidence_chunks.values()}
    requirement_ranks = {}
    if chunk_ranks:
        for requirement in question["answer_requirements"]:
            support = [ranks.get(evidence_chunks[eid]) for eid in requirement["supporting_evidence_ids"]]
            found = [rank for rank in support if rank is not None]
            if requirement["support_mode"] == "any":
                rank = min(found) if found else None
            else:
                rank = max(found) if len(found) == len(support) else None
            requirement_ranks[requirement["requirement_id"]] = rank

    chunk_hits, requirement_hits, recall, coverage, unannotated = {}, {}, {}, {}, {}
    for k in CUTOFFS:
        key = str(k)
        chunk_hits[key] = [cid for cid, rank in chunk_ranks.items() if rank is not None and rank <= k]
        requirement_hits[key] = [rid for rid, rank in requirement_ranks.items() if rank is not None and rank <= k]
        recall[key] = len(chunk_hits[key]) / len(chunk_ranks) if chunk_ranks else None
        coverage[key] = len(requirement_hits[key]) / len(requirement_ranks) if requirement_ranks else None
        unannotated[key] = [cid for cid, rank in ranks.items() if rank <= k and cid not in chunk_ranks]
    return {
        "evidence_chunk_ranks": chunk_ranks, "evidence_chunk_hits_at_k": chunk_hits,
        "evidence_chunk_recall_at_k": recall,
        "requirement_ranks": requirement_ranks, "requirements_supported_at_k": requirement_hits,
        "requirement_coverage_at_k": coverage,
        "alternative_evidence_review": {
            "status": "not_reviewed", "unannotated_chunk_ids_at_k": unannotated,
        } if chunk_ranks else None,
    }


def check_retrieval(connection, embedder, index_id: str, dataset: dict, *,
                    trace_connection=None, run_id=None, configuration=None, method="dense") -> dict:
    """Retrieve each raw question once, then measure annotated chunk and claim support."""
    if method != "dense" and trace_connection is not None:
        raise ValueError("Only dense diagnostic tracing is implemented.")
    score_fields = {
        "dense": ("distance",), "full-text": ("text_score",),
        "hybrid": ("rrf_score", "dense_rank", "full_text_rank", "distance", "text_score"),
    }[method]
    query_prefix = "" if method == "full-text" else QUERY_PREFIX
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
        if method == "hybrid":
            matches = retrieve_hybrid(connection, embedder, index_id, question["question"], limit=count)
        elif method == "full-text":
            matches = search_chunks_full_text(connection, index_id, question["question"], limit=count)
        elif trace_connection is None:
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
        measurements = measure_evidence(question, ranks)
        records.append({
            "question_id": question["question_id"], "question": question["question"],
            "question_type": question["question_type"],
            "primary_bucket": question.get("primary_bucket"),
            "scenario_family_id": question.get("scenario_family_id"),
            "answerability": question.get("answerability", "answerable"),
            "positive_evidence_applicable": bool(evidence_ranks),
            "unanswerability": question.get("unanswerability"),
            "query_input_sha256": sha256((query_prefix + question["question"]).encode()).hexdigest(),
            "returned_chunks": len(matches),
            "elapsed_seconds": elapsed, "evidence_ranks": evidence_ranks, "evidence_hits_at_k": hits,
            **measurements,
            "ranking": [{key: match[key] for key in (
                "chunk_id", "source_id", "snapshot_id", "url", "token_count",
            ) + score_fields} for match in matches],
        })
        if trace_id is not None:
            records[-1]["trace_id"] = trace_id
        total = len(measurements["evidence_chunk_ranks"])
        summary = ", ".join(f"@{k}={len(measurements['evidence_chunk_hits_at_k'][str(k)])}/{total}"
                            for k in CUTOFFS)
        if not evidence_ranks:
            summary = "N/A (no positive evidence; inspect returned context and abstention separately)"
        print(f"{question['question_id']}: unique annotated chunk hits {summary}", file=sys.stderr, flush=True)
    positives = [record for record in records if record["positive_evidence_applicable"]]
    summary = {"answerable_questions": len(positives), "unanswerable_questions": len(records) - len(positives)}
    for metric in ("evidence_chunk_recall_at_k", "requirement_coverage_at_k"):
        summary["mean_" + metric] = {
            str(k): sum(record[metric][str(k)] for record in positives) / len(positives) if positives else None
            for k in CUTOFFS
        }
    summary["all_requirements_supported_rate_at_k"] = {
        str(k): sum(record["requirement_coverage_at_k"][str(k)] == 1 for record in positives) / len(positives)
        if positives else None for k in CUTOFFS
    }
    return {"measurement_version": MEASUREMENT_VERSION, "indexed_chunks": count,
            "cutoffs": list(CUTOFFS), "summary": summary, "questions": records}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-id", required=True, help="Existing embedding index to inspect.")
    parser.add_argument("--dataset", type=Path, default=DATASET, help="Development dataset JSON; default: PostgreSQL P01–P06.")
    parser.add_argument("--method", choices=("dense", "full-text", "hybrid"), default="dense", help="Retrieval method; default: dense.")
    parser.add_argument("--trace", action="store_true", help="Write dense diagnostic traces; requires applied migration 0002.")
    args = parser.parse_args()
    if args.method != "dense" and args.trace:
        parser.error("--trace currently supports only the dense diagnostic.")

    import psycopg
    from check_document_questions import validate

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    try:
        print("Checking pinned development references...", file=sys.stderr, flush=True)
        dataset_check = validate(args.dataset)
        dataset = json.loads(args.dataset.read_text())
        created = datetime.now(timezone.utc)
        run_id = args.method + created.strftime("-%Y%m%dT%H%M%S%fZ")
        libraries = ("psycopg",) if args.method == "full-text" else (
            "sentence-transformers", "transformers", "torch", "tokenizers", "psycopg",
        )
        provenance = {
            "measurement_version": MEASUREMENT_VERSION,
            "dataset": dataset_check, "dataset_path": str(args.dataset.resolve()),
            "source_state_id": dataset["source_state"]["source_state_id"],
            "libraries": {name: version(name) for name in libraries},
            "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)),
            "code_sha256": {name: file_sha256(ROOT / name) for name in (
                "scripts/check_retrieval.py", "scripts/check_retrieval.py.lock",
                "scripts/check_document_questions.py", "configs/pilot.toml",
                "docs/EVALUATION_PLAN.md",
                "src/rag_workflow_lab/retrieval.py", "src/rag_workflow_lab/store.py",
                "src/rag_workflow_lab/embeddings.py", "src/rag_workflow_lab/tracing.py",
            )},
        }
        if args.method != "full-text":
            settings = load_settings(ROOT / "configs/pilot.toml")
            provenance["model_manifest_sha256"] = file_sha256(settings.embedding.model_dir / "model_manifest.json")
        if args.method != "dense":
            provenance["full_text_settings"] = FULL_TEXT_SETTINGS
        if args.method == "hybrid":
            provenance["fusion_settings"] = {
                "method": "rrf", "rank_constant": RRF_K, "candidates_per_method": HYBRID_CANDIDATES,
                "weights": {"dense": 1.0, "full_text": 1.0},
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
            embedder = None
            if args.method != "full-text":
                print("Loading the cached Nomic model once...", file=sys.stderr, flush=True)
                embedder = NomicEmbedder.from_local(settings.embedding)
            writer = None
            if args.trace:
                print("Opening a separate trace writer...", file=sys.stderr, flush=True)
                writer = stack.enter_context(psycopg.connect(
                    **database.connect_kwargs(), autocommit=True, options="-c statement_timeout=5000"
                ))
            result = check_retrieval(connection, embedder, args.index_id, dataset, method=args.method,
                                     trace_connection=writer, run_id=run_id,
                                     configuration={**provenance, "index": index})

        report = {
            "schema_version": 3, "run_id": run_id, "created_at": created.isoformat(),
            "scope": "Development annotated chunk/claim coverage, not exhaustive semantic recall, answer grades or a held-out benchmark.",
            "index": index, "read_only": not args.trace, "retrieval_read_only": True,
            "tracing_enabled": args.trace,
            "method": args.method, "query_prefix": "" if args.method == "full-text" else QUERY_PREFIX,
            **provenance,
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
