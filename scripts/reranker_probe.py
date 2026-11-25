# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "transformers==5.5.0",
#   "torch==2.10.0",
#   "tokenizers==0.22.2",
# ]
# ///
"""Rerank explicitly selected saved RRF top-20 lists with a pinned local Qwen model."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
from time import perf_counter
import tomllib

from scripts.check_document_questions import ROOT, read_pinned, require, validate
from scripts.check_retrieval import MEASUREMENT_VERSION, measure_evidence, summarize
from scripts.reranker_smoke import TOKENIZER_FILES, WEIGHT_FILES, checksum, score, score_batch
from scripts.rescore_retrieval import rescore


def load_inputs(settings: dict, question_ids: list[str] | None) -> tuple:
    config_dir = ROOT / "configs"
    dataset_path = (config_dir / settings["dataset"]).resolve()
    report_path = (config_dir / settings["retrieval_report"]).resolve()
    dataset_check = validate(dataset_path)
    dataset = json.loads(dataset_path.read_text())
    report = json.loads(report_path.read_text())
    _, parent_bytes = read_pinned(dataset["derived_from"][0], ROOT)
    require(report["method"] == "hybrid", "Expected a saved hybrid report.")
    require(report["dataset"]["dataset_sha256"] == sha256(parent_bytes).hexdigest(), "Report/parent hash mismatch.")
    updated = rescore(report, json.loads(parent_bytes), dataset)
    questions = {q["question_id"]: q for q in dataset["questions"]}
    rows = {q["question_id"]: q for q in updated["questions"]}
    if question_ids is None:
        question_ids = list(questions)
    require(len(set(question_ids)) == len(question_ids) and set(question_ids) <= questions.keys(),
            "Question IDs must be known and unique.")
    chunks = {c["chunk_id"]: c for s in dataset["source_state"]["sources"]
              for c in json.loads((ROOT / s["files"]["chunks"]["path"]).read_text())["chunks"]}
    selected = [(questions[qid], rows[qid]["ranking"][:20]) for qid in question_ids]
    return dataset_check, report, selected, chunks


def rerank(question: str, candidates: list[dict], chunks: dict, model, tokenizer, settings: dict,
           batch_size: int = 1) -> list[dict]:
    """Score only raw question/document text; retain every candidate and source field."""
    ranked = []
    for start in range(0, len(candidates), batch_size):
        batch = candidates[start:start + batch_size]
        documents = []
        for candidate in batch:
            chunk = chunks[candidate["chunk_id"]]
            documents.append(" > ".join(chunk["heading_path"]) + "\n\n" + chunk["text"])
        started = perf_counter()
        values = ([score(model, tokenizer, question, documents[0], settings)] if batch_size == 1
                  else score_batch(model, tokenizer, question, documents, settings))
        elapsed = perf_counter() - started
        for rank, (candidate, value) in enumerate(zip(batch, values, strict=True), start + 1):
            ranked.append({**candidate, "rrf_rank": rank, "reranker_score": value,
                           "scoring_seconds": elapsed if batch_size == 1 else None})
        print(f"  Scored {start + len(batch)}/{len(candidates)} (batch size {len(batch)})", flush=True)
    return sorted(ranked, key=lambda item: (-item["reranker_score"], item["rrf_rank"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/reranker.toml", help="Pinned reranker TOML; defaults to Qwen4B.")
    parser.add_argument("--batch-size", type=int, default=1, help="Pairs per forward pass; default: 1.")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--question-id", action="append", help="Repeat for each development question to probe.")
    selection.add_argument("--all", action="store_true", help="Rerank every question in the configured dataset.")
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive.")
    config_path = args.config.resolve()
    settings = tomllib.loads(config_path.read_text())["reranker"]
    tag = "qwen" + settings["model_id"].split("-")[-1].lower().replace(".", "")
    dataset_check, source, selected, chunks = load_inputs(settings, args.question_id)
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false",
                      HF_HUB_DISABLE_TELEMETRY="1")
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    require(settings["device"] == "mps" and torch.backends.mps.is_available(), "This probe requires MPS.")
    model_dir = (config_path.parent / settings["models_dir"] / settings["model_id"].replace("/", "--") / settings["revision"]).resolve()
    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True, trust_remote_code=False)
    print(f"Loading {settings['model_id']} locally...", flush=True)
    started = perf_counter()
    model = AutoModelForCausalLM.from_pretrained(model_dir, local_files_only=True, trust_remote_code=False,
        use_safetensors=True, dtype=getattr(torch, settings["dtype"])).to(settings["device"]).eval()
    torch.mps.synchronize()
    load_seconds = perf_counter() - started
    records = []
    for question, candidates in selected:
        print(f"Reranking {question['question_id']} ({len(candidates)} candidates)...", flush=True)
        started = perf_counter()
        ranking = rerank(question["question"], candidates, chunks, model, tokenizer, settings, args.batch_size)
        elapsed = perf_counter() - started
        before = measure_evidence(question, {m["chunk_id"]: i for i, m in enumerate(candidates, 1)})
        after = measure_evidence(question, {m["chunk_id"]: i for i, m in enumerate(ranking, 1)})
        records.append({"question_id": question["question_id"], "question": question["question"],
            "primary_bucket": question["primary_bucket"], "answerability": question["answerability"],
            "positive_evidence_applicable": bool(question["evidence"]), "elapsed_seconds": elapsed,
            "rrf_measurements": before, "ranking": ranking, **after})
        print(f"Finished {question['question_id']} in {elapsed:.2f}s", flush=True)
    created = datetime.now(timezone.utc)
    report = {"schema_version": 2, "report_type": "reranker_probe", "created_at": created.isoformat(),
        "measurement_version": MEASUREMENT_VERSION, "cutoffs": [5, 10, 20], "settings": settings,
        "dataset": dataset_check, "index": source["index"], "candidate_limit": 20,
        "source_report": {"path": settings["retrieval_report"], "sha256": checksum((config_path.parent / settings["retrieval_report"]).resolve())},
        "config_path": str(config_path), "config_sha256": checksum(config_path),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "code_sha256": {name: checksum(ROOT / name) for name in (
            "scripts/reranker_probe.py", "scripts/reranker_smoke.py", "scripts/check_retrieval.py",
            "scripts/check_document_questions.py", "scripts/rescore_retrieval.py")},
        "lock_sha256": checksum(Path(__file__ + ".lock")),
        "weights_sha256": {name: checksum(model_dir / name) for name in settings.get("weight_files", WEIGHT_FILES)},
        "tokenizer_sha256": {name: checksum(model_dir / name) for name in settings.get("tokenizer_files", TOKENIZER_FILES)},
        "packages": {name: version(name) for name in ("torch", "transformers", "tokenizers")},
        "load_seconds": load_seconds, "scoring_seconds": sum(r["elapsed_seconds"] for r in records),
        "batch_size": args.batch_size,
        "timing_note": "Includes first inference without a separate warm-up; per-pair times are null when batching.",
        "database_access": False, "hosted_model_calls": 0, "retrieval_rerun": False,
        "rrf_summary": summarize([{**r, **r["rrf_measurements"]} for r in records]),
        "summary": summarize(records), "questions": records}
    output = ROOT / "outputs/reranking" / (tag + created.strftime("-probe-%Y%m%dT%H%M%S%fZ.json"))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"report_path": str(output), "scoring_seconds": report["scoring_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
