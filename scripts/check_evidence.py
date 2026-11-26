# /// script
# requires-python = ">=3.11"
# dependencies = ["openai==3.51.0"]
# ///
"""Compare evidence policies on saved Qwen rankings; only sufficiency calls an API."""

import argparse
from contextlib import ExitStack
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter

from rag_workflow_lab.config import load_settings
from rag_workflow_lab.evaluation.dataset import select_questions
from rag_workflow_lab.evidence import MODES, assess_evidence
from scripts.check_document_questions import validate


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/evaluation/dev/expanded_questions_v1_8.json"
REPORT = ROOT / "outputs/reranking/qwen4b-probe-20261125T202218873027Z.json"


def load_contexts(dataset_path: Path, report_path: Path, question_id: str | None) -> tuple:
    """Bind raw questions and the same top-five whole passages to pinned sources."""
    dataset_check = validate(dataset_path)
    dataset = json.loads(dataset_path.read_text())
    report = json.loads(report_path.read_text())
    if (report["report_type"] != "reranker_probe" or report["candidate_limit"] != 20
            or report["dataset"]["dataset_sha256"] != dataset_check["dataset_sha256"]):
        raise ValueError("Expected a saved reranker report for the exact selected dataset.")
    rows = {q["question_id"]: q for q in report["questions"]}
    if len(rows) != len(report["questions"]):
        raise ValueError("Saved report has duplicate question IDs.")
    chunks = {}
    for source in dataset["source_state"]["sources"]:
        for chunk in json.loads((ROOT / source["files"]["chunks"]["path"]).read_text())["chunks"]:
            chunks[chunk["chunk_id"]] = (source, chunk)
    contexts = []
    for question in select_questions(dataset, question_id):
        row = rows.get(question["question_id"])
        if row is None or row["question"] != question["question"]:
            raise ValueError("Saved report is missing a selected raw question.")
        ranking = row["ranking"]
        if (len(ranking) != 20 or len({m["chunk_id"] for m in ranking}) != 20
                or any(not math.isfinite(m["reranker_score"]) or not 0 <= m["reranker_score"] <= 1
                       for m in ranking)
                or ranking != sorted(ranking, key=lambda m: (-m["reranker_score"], m["rrf_rank"]))):
            raise ValueError("Expected twenty unique candidates in saved reranked order.")
        matches = []
        for match in ranking[:5]:
            source, chunk = chunks[match["chunk_id"]]
            if (match["snapshot_id"], match["source_id"]) != (source["snapshot_id"], source["source_id"]):
                raise ValueError("Saved candidate source differs from the pinned chunk.")
            matches.append({**match, "text": chunk["text"], "metadata": {"heading_path": chunk["heading_path"]}})
        contexts.append((question, matches))
    return dataset_check, report, contexts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=MODES, required=True, help="Separate comparison condition.")
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--report", type=Path, default=REPORT, help="Saved top-20 Qwen reranking report.")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--question-id", help="One development question, for example P19.")
    selection.add_argument("--all", action="store_true", help="Check all questions in the dataset.")
    parser.add_argument("--call-api", action="store_true", help="Allow one paid sufficiency request per question.")
    args = parser.parse_args(argv)
    if args.mode == "sufficiency" and not args.call_api:
        parser.error("Sufficiency mode requires --call-api; baseline/threshold are offline.")
    if args.mode != "sufficiency" and args.call_api:
        parser.error("--call-api is only used with sufficiency mode.")
    if args.call_api and not os.environ.get("OPENAI_API_KEY", "").strip():
        parser.error("Set OPENAI_API_KEY or load .env with uv --env-file.")
    try:
        dataset_check, source, contexts = load_contexts(args.dataset, args.report, args.question_id)
        generator = load_settings(ROOT / "configs/pilot.toml").generator
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"Evidence inputs failed: {type(exc).__name__}. Check the dataset/report pins.\n")
    if args.mode == "sufficiency" and generator is None:
        parser.error("Pilot configuration requires generator settings.")

    created = datetime.now(timezone.utc)
    run_id = created.strftime(f"evidence-{args.mode}-%Y%m%dT%H%M%S%fZ")
    records = []
    with ExitStack() as stack:
        client = None
        if args.call_api:
            from openai import OpenAI
            client = stack.enter_context(OpenAI(base_url="https://api.openai.com/v1", timeout=30, max_retries=0))
        for question, matches in contexts:
            print(f"{question['question_id']}: {args.mode}, same five saved chunks...", file=sys.stderr, flush=True)
            started = perf_counter()
            try:
                result = assess_evidence(question["question"], matches, mode=args.mode,
                                         client=client, generator=generator)
            except Exception as exc:
                result = {"mode": args.mode, "allowed": False, "decision": "error",
                          "error": {"type": type(exc).__name__, "message": "Evidence check failed; batch stopped."}}
            records.append({**question, "context": matches, "elapsed_seconds": perf_counter() - started,
                            "evidence_check": result})
            if result["decision"] == "error":
                break
    failed = any(row["evidence_check"]["decision"] == "error" for row in records)
    report = {
        "schema_version": 1, "report_type": "evidence_policy_check", "run_id": run_id,
        "created_at": created.isoformat(), "mode": args.mode, "dataset": dataset_check,
        "source_report": {"path": str(args.report.resolve()), "sha256": sha256(args.report.read_bytes()).hexdigest()},
        "index": source["index"], "reranker_settings": source["settings"], "context_limit": 5,
        "checker_settings": asdict(generator) if args.call_api else None,
        "scope": "Development evidence decisions, not final answers or an answer-accuracy grade.",
        "database_access": False, "retrieval_rerun": False, "reranker_inference": False,
        "answer_generation": False, "batch_stopped_on_error": failed,
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "code_sha256": {p: sha256((ROOT / p).read_bytes()).hexdigest() for p in (
            "scripts/check_evidence.py", "scripts/check_evidence.py.lock", "configs/pilot.toml",
            "src/rag_workflow_lab/evidence.py", "src/rag_workflow_lab/llm.py",
            "src/rag_workflow_lab/prompts/sufficiency_v1.md")},
        "selected_questions": len(contexts), "questions": records,
    }
    output = ROOT / "outputs/evidence" / f"{run_id}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"report": str(output), "checked": len(records),
                      "allowed": sum(row["evidence_check"]["allowed"] for row in records), "error": failed}))
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
