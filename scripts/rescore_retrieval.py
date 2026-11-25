"""Rescore saved rankings offline: python -m scripts.rescore_retrieval --help."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from scripts.check_document_questions import ROOT, read_pinned, require, validate
from scripts.check_retrieval import CUTOFFS, MEASUREMENT_VERSION, measure_evidence, summarize


def rescore(report: dict, original: dict, revised: dict) -> dict:
    """Change annotations only; retain raw rankings, queries and measured timings."""
    require(report["schema_version"] == 4 and report["measurement_version"] == MEASUREMENT_VERSION
            and report["cutoffs"] == list(CUTOFFS), "Expected a schema-4 annotated-evidence-v2 report.")
    require(original["source_state"] == revised["source_state"], "Source state changed; rerun retrieval.")
    require(report["dataset"]["dataset_id"] == original["dataset_id"] == revised["dataset_id"]
            and report["dataset"]["dataset_version"] == original["dataset_version"], "Original dataset mismatch.")
    records = report["questions"]
    require(len(records) == len(original["questions"]) == len(revised["questions"]), "Question count changed.")
    updated = []
    for row, old, new in zip(records, original["questions"], revised["questions"]):
        for key in ("question_id", "question", "question_type", "answerability", "primary_bucket", "scenario_family_id"):
            require(row.get(key) == old.get(key) == new.get(key), f"Question identity changed: {key}")
        if old.get("answerability") == "unanswerable":
            require(old == new, "Negative records changed; review their scope separately.")
        ranks = {match["chunk_id"]: rank for rank, match in enumerate(row["ranking"], 1)}
        require(len(ranks) == len(row["ranking"]), "Duplicate chunks in saved ranking.")
        evidence_ranks = {e["evidence_id"]: ranks.get(e["chunk_id"]) for e in new["evidence"]}
        updated.append({**row, "evidence_ranks": evidence_ranks,
            "evidence_hits_at_k": {str(k): [eid for eid, rank in evidence_ranks.items() if rank is not None and rank <= k]
                                   for k in CUTOFFS},
            **measure_evidence(new, ranks)})
    return {"measurement_version": MEASUREMENT_VERSION, "cutoffs": list(CUTOFFS),
            "summary": summarize(updated), "questions": updated}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path, help="Revised annotations with one pinned parent.")
    parser.add_argument("--report", required=True, type=Path, help="Original schema-4 retrieval report.")
    args = parser.parse_args()
    dataset_check = validate(args.dataset)
    revised = json.loads(args.dataset.read_text())
    require(len(revised["derived_from"]) == 1, "Expected one pinned parent dataset.")
    parent_path, parent_bytes = read_pinned(revised["derived_from"][0], ROOT)
    validate(parent_path)
    raw = args.report.read_bytes()
    report = json.loads(raw)
    require(report["dataset"]["dataset_sha256"] == sha256(parent_bytes).hexdigest(), "Report/parent hash mismatch.")
    result = rescore(report, json.loads(parent_bytes), revised)
    created = datetime.now(timezone.utc)
    run_id = report["method"] + created.strftime("-rescore-%Y%m%dT%H%M%S%fZ")
    result = {"schema_version": 1, "report_type": "retrieval_annotation_rescore",
        "run_id": run_id, "created_at": created.isoformat(), "method": report["method"],
        "dataset": dataset_check, "dataset_path": str(args.dataset.resolve()), "index": report["index"],
        "source_report": {"path": str(args.report.resolve()), "sha256": sha256(raw).hexdigest(),
                          "run_id": report["run_id"], "dataset": report["dataset"]},
        "code_sha256": {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in (
            "scripts/rescore_retrieval.py", "scripts/check_retrieval.py", "scripts/check_document_questions.py")},
        "retrieval_rerun": False, "database_access": False, "model_calls": 0,
        "timing_origin": "Reused original retrieval timings; no new timing measurement.", **result}
    output = ROOT / "outputs/retrieval" / (run_id + ".json")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"report_path": str(output), "summary": result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
