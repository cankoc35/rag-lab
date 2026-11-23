# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "sentence-transformers==5.3.0",
#   "transformers==5.5.0",
#   "torch==2.10.0",
#   "tokenizers==0.22.2",
#   "psycopg[binary]==3.3.8",
#   "openai==3.51.0",
# ]
# ///
"""Run Simple RAG on selected development questions; paid calls and DB traces are opt-in."""

import argparse
from datetime import datetime, timezone
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter

from rag_workflow_lab.config import load_database_settings, load_settings
from rag_workflow_lab.embeddings import NomicEmbedder, file_sha256
from rag_workflow_lab.evaluation.dataset import select_questions
from rag_workflow_lab.store import get_embedding_index
from rag_workflow_lab.workflows.simple import answer_question


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/evaluation/dev/document_questions.json"


def run_questions(connection, writer, embedder, client, generator, index_id: str, questions: list[dict],
                  *, run_id: str, configuration: dict) -> list[dict]:
    """Call the existing workflow once per question; provider/DB exceptions stop the batch."""
    records = []
    for question in questions:
        question_id = question["question_id"]
        print(f"{question_id}: retrieving five chunks, then generating an answer...", file=sys.stderr, flush=True)
        started = perf_counter()
        result = answer_question(connection, writer, embedder, client, generator, index_id,
                                 question["question"], run_id=run_id, question_id=question_id,
                                 configuration=configuration)
        records.append({**question, "elapsed_seconds": perf_counter() - started, **result})
        print(f"{question_id}: {result['status']} (trace {result['trace_id']}).", file=sys.stderr, flush=True)
    return records


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-id", required=True, help="Existing embedding index to use.")
    parser.add_argument("--dataset", type=Path, default=DATASET, help="Development dataset JSON; default: PostgreSQL P01–P06.")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--question-id", help="Run one development question, for example P01.")
    selection.add_argument("--all", action="store_true", help="Run all questions in the pinned development dataset.")
    parser.add_argument("--call-api", action="store_true", help="Allow one paid request per question and trace writes.")
    args = parser.parse_args(argv)
    if not args.call_api:
        parser.error("Pass --call-api to allow paid requests and trace writes.")
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        parser.error("Set OPENAI_API_KEY in the environment or load .env with uv --env-file.")

    import psycopg
    from openai import OpenAI, OpenAIError
    from check_document_questions import validate
    from check_retrieval import validate_index_scope

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    created = datetime.now(timezone.utc)
    run_id = created.strftime("simple-%Y%m%dT%H%M%S%fZ")
    try:
        print("Checking pinned references and selecting questions...", file=sys.stderr, flush=True)
        dataset_check = validate(args.dataset)
        dataset = json.loads(args.dataset.read_text())
        questions = select_questions(dataset, args.question_id)
        settings = load_settings(ROOT / "configs/pilot.toml")
        if settings.generator is None or settings.embedding is None:
            raise ValueError("Pilot config requires generator and embedding settings.")
        provenance = {
            "dataset": dataset_check, "dataset_sha256": file_sha256(args.dataset),
            "dataset_path": str(args.dataset.resolve()),
            "source_state_id": dataset["source_state"]["source_state_id"],
            "libraries": {name: version(name) for name in (
                "sentence-transformers", "transformers", "torch", "tokenizers", "psycopg", "openai",
            )},
            "model_manifest_sha256": file_sha256(settings.embedding.model_dir / "model_manifest.json"),
            "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)),
            "code_sha256": {name: file_sha256(ROOT / name) for name in (
                "scripts/run_simple_rag.py", "scripts/run_simple_rag.py.lock",
                "scripts/check_document_questions.py", "scripts/check_retrieval.py", "configs/pilot.toml",
                "src/rag_workflow_lab/config.py", "src/rag_workflow_lab/llm.py",
                "src/rag_workflow_lab/evaluation/dataset.py",
                "src/rag_workflow_lab/workflows/simple.py", "src/rag_workflow_lab/prompts/answer_v1.md",
                "src/rag_workflow_lab/retrieval.py", "src/rag_workflow_lab/store.py",
                "src/rag_workflow_lab/embeddings.py", "src/rag_workflow_lab/tracing.py",
            )},
        }
        print(f"Selected {len(questions)} question(s); run {run_id}.", file=sys.stderr, flush=True)
        database = load_database_settings()
        with psycopg.connect(**database.connect_kwargs(), options="-c statement_timeout=5000") as connection:
            connection.read_only = True
            index = get_embedding_index(connection, args.index_id)
            validate_index_scope(connection, args.index_id, dataset)
            print("Loading the cached Nomic model once...", file=sys.stderr, flush=True)
            embedder = NomicEmbedder.from_local(settings.embedding)
            with psycopg.connect(**database.connect_kwargs(), autocommit=True,
                                  options="-c statement_timeout=5000") as writer, \
                    OpenAI(base_url="https://api.openai.com/v1", timeout=30, max_retries=0) as client:
                started = perf_counter()
                records = run_questions(connection, writer, embedder, client, settings.generator,
                                        args.index_id, questions, run_id=run_id,
                                        configuration={**provenance, "index": index})
                elapsed = perf_counter() - started
        report = {
            "schema_version": 2, "run_id": run_id, "created_at": created.isoformat(),
            "scope": "Development answers, not a benchmark or an answer-quality grade.",
            "index": index, "elapsed_seconds": elapsed, **provenance, "questions": records,
        }
        output = ROOT / "outputs/answers" / f"{run_id}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
    except OpenAIError as exc:
        parser.exit(2, f"OpenAI request failed ({type(exc).__name__}); inspect traces for run {run_id}.\n")
    except psycopg.Error:
        parser.exit(2, "Simple RAG failed. Check the database connection and trace writer.\n")
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Simple RAG failed: {exc}\n")
    print(json.dumps({"report": str(output), "run_id": run_id, "questions": len(records),
                      "completed_answers": sum(record["ok"] for record in records)}, indent=2))
    return 0 if all(record["ok"] for record in records) else 2


if __name__ == "__main__":
    raise SystemExit(main())
