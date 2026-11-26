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
"""Run traced Enhanced development answers with cached Nomic/Qwen; hosted calls require opt-in."""

import argparse
from datetime import datetime, timezone
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter
import tomllib

from rag_workflow_lab.config import load_database_settings, load_settings
from rag_workflow_lab.embeddings import NomicEmbedder, file_sha256
from rag_workflow_lab.evaluation.dataset import select_questions
from rag_workflow_lab.evidence import MODES
from rag_workflow_lab.store import get_embedding_index
from rag_workflow_lab.workflows.enhanced import answer_question
from scripts.check_document_questions import validate
from scripts.check_retrieval import validate_index_scope
from scripts.reranker_smoke import TOKENIZER_FILES, WEIGHT_FILES, score


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/evaluation/dev/expanded_questions_v1_8.json"


def load_reranker(settings: dict, model_dir: Path):
    """Load the configured local snapshot without downloads or remote code."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if settings["device"] == "mps" and not torch.backends.mps.is_available():
        raise ValueError("MPS is unavailable for the configured reranker.")
    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(
        model_dir, local_files_only=True, trust_remote_code=False, use_safetensors=True,
        dtype=getattr(torch, settings["dtype"]),
    ).to(settings["device"]).eval()
    if settings["device"] == "mps":
        torch.mps.synchronize()
    return model, tokenizer


def run_questions(connection, writer, embedder, client, generator, index_id, questions, model, tokenizer,
                  reranker, *, mode, run_id, configuration) -> list[dict]:
    """Reuse loaded resources; preserve completed records and stop on operational errors."""
    records = []
    for question in questions:
        question_id = question["question_id"]
        print(f"{question_id}: hybrid retrieval, reranking and {mode}...", file=sys.stderr, flush=True)
        scored = 0

        def score_passage(raw_question, passage):
            nonlocal scored
            scored += 1
            print(f"  {question_id}: scoring candidate {scored}...", file=sys.stderr, flush=True)
            return score(model, tokenizer, raw_question, passage, reranker)

        started = perf_counter()
        try:
            result = answer_question(connection, embedder, client, generator, index_id, question["question"],
                                     score_passage, mode=mode, writer=writer, reranker_settings=reranker,
                                     run_id=run_id, question_id=question_id, configuration=configuration)
        except Exception as exc:
            result = {"ok": False, "outcome": "error", "trace_id": None, "answer": None,
                      "error": {"type": type(exc).__name__, "message": "Enhanced workflow failed; inspect traces by run/question ID."}}
        records.append({**question, "elapsed_seconds": perf_counter() - started, **result})
        print(f"{question_id}: {result['outcome']} (trace {result['trace_id']}).", file=sys.stderr, flush=True)
        if not result["ok"]:
            break
    return records


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-id", required=True, help="Existing index with exactly the dataset's pinned source/chunk scope.")
    parser.add_argument("--dataset", type=Path, default=DATASET, help="Development dataset; default: expanded v1.8, 120 questions.")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--question-id", action="append", help="Run a question, for example P07; repeat for a small batch.")
    selection.add_argument("--all", action="store_true", help="Run every question; up to two hosted calls per question.")
    parser.add_argument("--mode", choices=MODES, default="threshold_sufficiency", help="Evidence policy; default: threshold_sufficiency.")
    parser.add_argument("--call-api", action="store_true", help="Allow hosted requests and DB trace writes; rejected gates make no request.")
    args = parser.parse_args(argv)
    if not args.call_api:
        parser.error("Pass --call-api to allow hosted requests and trace writes.")
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        parser.error("Set OPENAI_API_KEY or load .env with uv --env-file.")

    import psycopg
    from openai import OpenAI

    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
                      TOKENIZERS_PARALLELISM="false")
    created = datetime.now(timezone.utc)
    run_id = created.strftime("enhanced-%Y%m%dT%H%M%S%fZ")
    try:
        print("Checking references, question selection and settings...", file=sys.stderr, flush=True)
        dataset_check = validate(args.dataset)
        dataset = json.loads(args.dataset.read_text())
        if args.question_id and len(set(args.question_id)) != len(args.question_id):
            raise ValueError("Question IDs must be unique.")
        questions = ([select_questions(dataset, qid)[0] for qid in args.question_id]
                     if args.question_id else select_questions(dataset, None))
        settings = load_settings(ROOT / "configs/pilot.toml")
        if settings.embedding is None or settings.generator is None:
            raise ValueError("Pilot config requires embedding and generator settings.")
        reranker_path = ROOT / "configs/reranker.toml"
        reranker = tomllib.loads(reranker_path.read_text())["reranker"]
        model_dir = (reranker_path.parent / reranker["models_dir"] /
                     reranker["model_id"].replace("/", "--") / reranker["revision"]).resolve()
        provenance = {
            "dataset": dataset_check, "dataset_path": str(args.dataset.resolve()),
            "dataset_sha256": file_sha256(args.dataset),
            "source_state_id": dataset["source_state"]["source_state_id"],
            "libraries": {name: version(name) for name in (
                "sentence-transformers", "transformers", "torch", "tokenizers", "psycopg", "openai",
            )},
            "model_manifest_sha256": file_sha256(settings.embedding.model_dir / "model_manifest.json"),
            "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)),
            "code_sha256": {name: file_sha256(ROOT / name) for name in (
                "scripts/run_enhanced_rag.py", "scripts/run_enhanced_rag.py.lock", "scripts/reranker_smoke.py",
                "scripts/check_document_questions.py", "scripts/check_retrieval.py", "configs/pilot.toml", "configs/reranker.toml",
                "src/rag_workflow_lab/config.py", "src/rag_workflow_lab/evaluation/dataset.py",
                "src/rag_workflow_lab/embeddings.py", "src/rag_workflow_lab/store.py", "src/rag_workflow_lab/retrieval.py",
                "src/rag_workflow_lab/evidence.py", "src/rag_workflow_lab/tracing.py", "src/rag_workflow_lab/llm.py",
                "src/rag_workflow_lab/workflows/enhanced.py", "src/rag_workflow_lab/prompts/answer_v1.md",
                "src/rag_workflow_lab/prompts/sufficiency_v1.md",
            )},
        }
        print(f"Selected {len(questions)} question(s); run {run_id}. Checking index scope...", file=sys.stderr, flush=True)
        database = load_database_settings()
        with psycopg.connect(**database.connect_kwargs(), options="-c statement_timeout=5000") as connection:
            connection.read_only = True
            index = get_embedding_index(connection, args.index_id)
            validate_index_scope(connection, args.index_id, dataset)
            print("Hashing cached Qwen files...", file=sys.stderr, flush=True)
            provenance["reranker_files_sha256"] = {name: file_sha256(model_dir / name) for name in (
                *reranker.get("tokenizer_files", TOKENIZER_FILES), *reranker.get("weight_files", WEIGHT_FILES),
            )}
            print("Loading cached Nomic once...", file=sys.stderr, flush=True)
            started = perf_counter()
            embedder = NomicEmbedder.from_local(settings.embedding)
            load_seconds = {"embedding": perf_counter() - started}
            print(f"Loading {reranker['model_id']} once...", file=sys.stderr, flush=True)
            started = perf_counter()
            model, tokenizer = load_reranker(reranker, model_dir)
            load_seconds["reranker"] = perf_counter() - started
            with psycopg.connect(**database.connect_kwargs(), autocommit=True,
                                  options="-c statement_timeout=5000") as writer, \
                    OpenAI(base_url="https://api.openai.com/v1", timeout=30, max_retries=0) as client:
                started = perf_counter()
                records = run_questions(connection, writer, embedder, client, settings.generator, args.index_id,
                                        questions, model, tokenizer, reranker, mode=args.mode, run_id=run_id,
                                        configuration={**provenance, "index": index})
                elapsed = perf_counter() - started
        failed = any(not record["ok"] for record in records)
        report = {"schema_version": 1, "report_type": "enhanced_answers", "run_id": run_id,
                  "created_at": created.isoformat(), "mode": args.mode, "index": index, **provenance,
                  "scope": "Development answers; execution outcomes do not grade correctness or grounding.",
                  "reranker_settings": reranker, "load_seconds": load_seconds, "elapsed_seconds": elapsed,
                  "requested_questions": len(questions), "batch_stopped_on_error": failed, "questions": records}
        output = ROOT / "outputs/answers" / f"{run_id}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x") as stream:
            json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
    except Exception as exc:
        parser.exit(2, f"Enhanced setup/report failed ({type(exc).__name__}); inspect traces for run {run_id} if present.\n")
    print(json.dumps({"report": str(output), "run_id": run_id, "processed": len(records),
                      **{name: sum(record["outcome"] == name for record in records)
                         for name in ("answered", "abstained", "error")}}, indent=2))
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
