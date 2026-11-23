# /// script
# requires-python = ">=3.11"
# dependencies = ["openai==3.51.0", "psycopg[binary]==3.3.8"]
# ///
"""Run the LLM-only control on development questions; no retrieval or corpus reads."""

import argparse
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
from rag_workflow_lab.evaluation.dataset import select_questions
from rag_workflow_lab.workflows.llm_only import answer_question


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/evaluation/dev/document_questions.json"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET, help="Development dataset JSON; default: PostgreSQL P01–P06.")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--question-id", help="Run one development question, for example P01.")
    selection.add_argument("--all", action="store_true", help="Run all pinned development questions.")
    parser.add_argument("--call-api", action="store_true", help="Allow one paid request per question and trace writes.")
    args = parser.parse_args(argv)
    if not args.call_api:
        parser.error("Pass --call-api to allow paid requests and trace writes.")
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        parser.error("Set OPENAI_API_KEY in the environment or load .env with uv --env-file.")

    import psycopg
    from openai import OpenAI, OpenAIError

    created = datetime.now(timezone.utc)
    run_id = created.strftime("llm-only-%Y%m%dT%H%M%S%fZ")
    try:
        dataset_bytes = args.dataset.read_bytes()
        dataset = json.loads(dataset_bytes)
        questions = select_questions(dataset, args.question_id)
        generator = load_settings(ROOT / "configs/pilot.toml").generator
        if generator is None:
            raise ValueError("Pilot config requires generator settings.")
        provenance = {
            "dataset": {"dataset_id": dataset["dataset_id"], "dataset_version": dataset["dataset_version"]},
            "dataset_sha256": sha256(dataset_bytes).hexdigest(),
            "dataset_path": str(args.dataset.resolve()),
            "source_state_id": dataset["source_state"]["source_state_id"],
            "libraries": {name: version(name) for name in ("openai", "psycopg")},
            "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)),
            "code_sha256": {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in (
                "scripts/run_llm_only.py", "scripts/run_llm_only.py.lock", "configs/pilot.toml",
                "src/rag_workflow_lab/config.py", "src/rag_workflow_lab/llm.py",
                "src/rag_workflow_lab/evaluation/dataset.py", "src/rag_workflow_lab/tracing.py",
                "src/rag_workflow_lab/workflows/llm_only.py", "src/rag_workflow_lab/prompts/llm_only_v1.md",
            )},
        }
        print(f"Selected {len(questions)} question(s); run {run_id}. No retrieval.", file=sys.stderr, flush=True)
        database = load_database_settings()
        records = []
        with psycopg.connect(**database.connect_kwargs(), autocommit=True,
                              options="-c statement_timeout=5000") as writer, \
                OpenAI(base_url="https://api.openai.com/v1", timeout=30, max_retries=0) as client:
            started = perf_counter()
            for question in questions:
                question_id = question["question_id"]
                print(f"{question_id}: generating without documents or tools...", file=sys.stderr, flush=True)
                question_started = perf_counter()
                result = answer_question(writer, client, generator, question["question"],
                                         run_id=run_id, question_id=question_id, configuration=provenance)
                records.append({**question, "elapsed_seconds": perf_counter() - question_started, **result})
                print(f"{question_id}: {result['status']} (trace {result['trace_id']}).", file=sys.stderr, flush=True)
            elapsed = perf_counter() - started
        report = {
            "schema_version": 2, "workflow": "llm_only", "run_id": run_id, "created_at": created.isoformat(),
            "scope": "Development LLM-only answers; no automatic quality or memorization grade.",
            "retrieval_enabled": False, "elapsed_seconds": elapsed, **provenance, "questions": records,
        }
        output = ROOT / "outputs/answers" / f"{run_id}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
    except OpenAIError as exc:
        parser.exit(2, f"OpenAI request failed ({type(exc).__name__}); inspect traces for run {run_id}.\n")
    except psycopg.Error:
        parser.exit(2, "LLM-only failed. Check the database connection and trace writer.\n")
    except (OSError, ValueError) as exc:
        parser.exit(2, f"LLM-only failed: {exc}\n")
    print(json.dumps({"report": str(output), "run_id": run_id, "questions": len(records),
                      "completed_answers": sum(record["ok"] for record in records)}, indent=2))
    return 0 if all(record["ok"] for record in records) else 2


if __name__ == "__main__":
    raise SystemExit(main())
