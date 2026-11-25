# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "transformers==5.5.0",
#   "torch==2.10.0",
#   "tokenizers==0.22.2",
# ]
# ///
"""Prepare pinned Qwen reranker inputs or run an opt-in two-passage local smoke."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
from time import perf_counter
import tomllib


ROOT = Path(__file__).resolve().parents[1]
TOKENIZER_FILES = ("config.json", "tokenizer.json", "tokenizer_config.json", "chat_template.jinja",
                   "special_tokens_map.json", "merges.txt", "vocab.json")
WEIGHT_FILES = ("model.safetensors.index.json", "model-00001-of-00002.safetensors",
                "model-00002-of-00002.safetensors")


def checksum(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pair_tokens(tokenizer, question: str, document: str, instruction: str) -> list[int]:
    """Use the pinned model's own reranker template; no truncation or gold input."""
    return tokenizer.apply_chat_template([
        {"role": "system", "content": instruction},
        {"role": "query", "content": question},
        {"role": "document", "content": document},
    ], tokenize=True, add_generation_prompt=False, truncation=False, return_dict=False)


def yes_probability(yes: float, no: float) -> float:
    if not all(math.isfinite(value) for value in (yes, no)):
        raise ValueError("Reranker returned non-finite logits.")
    maximum = max(yes, no)
    yes, no = math.exp(yes - maximum), math.exp(no - maximum)
    return yes / (yes + no)


def score(model, tokenizer, question: str, document: str, settings: dict) -> float:
    import torch

    ids = pair_tokens(tokenizer, question, document, settings["instruction"])
    if len(ids) > settings["max_tokens"]:
        raise ValueError("Reranker input exceeds max_tokens; it was not truncated.")
    tokens = torch.tensor([ids], device=settings["device"])
    with torch.inference_mode():
        logits = model(input_ids=tokens, attention_mask=torch.ones_like(tokens),
                       use_cache=False, logits_to_keep=1).logits[0, -1]
    yes, no = logits[[tokenizer.convert_tokens_to_ids("yes"), tokenizer.convert_tokens_to_ids("no")]].float().tolist()
    return yes_probability(yes, no)


def score_batch(model, tokenizer, question: str, documents: list[str], settings: dict) -> list[float]:
    """Left-pad complete inputs and score each pair at its final real token."""
    import torch

    rows = [pair_tokens(tokenizer, question, document, settings["instruction"]) for document in documents]
    width = max(map(len, rows))
    if width > settings["max_tokens"]:
        raise ValueError("Reranker input exceeds max_tokens; it was not truncated.")
    tokens = torch.tensor([[tokenizer.pad_token_id] * (width - len(row)) + row for row in rows],
                          device=settings["device"])
    mask = torch.tensor([[0] * (width - len(row)) + [1] * len(row) for row in rows],
                        device=settings["device"])
    positions = (mask.cumsum(dim=-1) - 1).clamp(min=0)
    with torch.inference_mode():
        logits = model(input_ids=tokens, attention_mask=mask, position_ids=positions,
                       use_cache=False, logits_to_keep=1).logits[:, -1]
    values = logits[:, [tokenizer.convert_tokens_to_ids("yes"), tokenizer.convert_tokens_to_ids("no")]].float().tolist()
    return [yes_probability(yes, no) for yes, no in values]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/reranker.toml", help="Pinned reranker TOML; defaults to Qwen4B.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare", action="store_true", help="Download tokenizer/config only and check all saved RRF top-20 inputs.")
    mode.add_argument("--download-model", action="store_true", help="Download the configured weights, then run the local smoke.")
    args = parser.parse_args()
    config_path = args.config.resolve()
    settings = tomllib.loads(config_path.read_text())["reranker"]
    tokenizer_files = tuple(settings.get("tokenizer_files", TOKENIZER_FILES))
    weight_files = tuple(settings.get("weight_files", WEIGHT_FILES))
    tag = "qwen" + settings["model_id"].split("-")[-1].lower().replace(".", "")
    model_dir = (config_path.parent / settings["models_dir"] / settings["model_id"].replace("/", "--") / settings["revision"]).resolve()
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    if args.prepare or args.download_model:
        from huggingface_hub import snapshot_download

        files = tokenizer_files + (weight_files if args.download_model else ())
        print("Downloading pinned tokenizer/config" + (" and weights..." if args.download_model else "..."), flush=True)
        snapshot_download(settings["model_id"], revision=settings["revision"], local_dir=model_dir,
                          allow_patterns=list(files), token=False, max_workers=2)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True, trust_remote_code=False)
    report = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
        "model_id": settings["model_id"], "revision": settings["revision"], "settings": settings,
        "config_sha256": checksum(config_path), "script_sha256": checksum(Path(__file__)),
        "lock_sha256": checksum(Path(__file__ + ".lock")),
        "platform": platform.platform(), "mps_available": torch.backends.mps.is_available(),
        "packages": {name: version(name) for name in ("torch", "transformers", "tokenizers", "huggingface-hub")},
        "tokenizer_sha256": {name: checksum(model_dir / name) for name in tokenizer_files},
        "database_access": False, "hosted_model_calls": 0}
    if args.prepare:
        from check_document_questions import validate

        dataset_path = (config_path.parent / settings["dataset"]).resolve()
        report_path = (config_path.parent / settings["retrieval_report"]).resolve()
        report["dataset"] = validate(dataset_path)
        dataset = json.loads(dataset_path.read_text())
        retrieval = json.loads(report_path.read_text())
        if retrieval["method"] != "hybrid" or retrieval["source_state_id"] != dataset["source_state"]["source_state_id"]:
            raise ValueError("Expected the saved shared-scope hybrid report.")
        if [(q["question_id"], q["question"]) for q in retrieval["questions"]] != [(q["question_id"], q["question"]) for q in dataset["questions"]]:
            raise ValueError("Saved questions differ from the current dataset.")
        chunks = {c["chunk_id"]: c for s in dataset["source_state"]["sources"]
                  for c in json.loads((ROOT / s["files"]["chunks"]["path"]).read_text())["chunks"]}
        pairs = []
        for question in retrieval["questions"]:
            for match in question["ranking"][:20]:
                chunk = chunks[match["chunk_id"]]
                text = " > ".join(chunk["heading_path"]) + "\n\n" + chunk["text"]
                ids = pair_tokens(tokenizer, question["question"], text, settings["instruction"])
                pairs.append({"question_id": question["question_id"], "chunk_id": chunk["chunk_id"],
                              "tokens": len(ids), "input_ids_sha256": sha256(json.dumps(ids).encode()).hexdigest()})
        report.update(mode="tokenizer_preparation", weight_inference=False,
            retrieval_report_sha256=checksum(report_path), pairs=pairs,
            maximum_tokens=max(p["tokens"] for p in pairs),
            oversized_pairs=sum(p["tokens"] > settings["max_tokens"] for p in pairs))
    else:
        if settings["device"] == "mps" and not torch.backends.mps.is_available():
            raise ValueError("MPS is unavailable; local smoke was not started.")
        print(f"Loading {settings['model_id']} locally...", flush=True)
        started = perf_counter()
        model = AutoModelForCausalLM.from_pretrained(model_dir, local_files_only=True,
            trust_remote_code=False, use_safetensors=True, dtype=getattr(torch, settings["dtype"])).to(settings["device"]).eval()
        if settings["device"] == "mps": torch.mps.synchronize()
        load_seconds = perf_counter() - started
        question = "Which command displays a PostgreSQL query plan?"
        documents = ["Use EXPLAIN to inspect the query execution plan.", "Atlas backup retention is fourteen successful generations."]
        print("Scoring two fixed passages...", flush=True)
        started = perf_counter()
        scores = [score(model, tokenizer, question, text, settings) for text in documents]
        if settings["device"] == "mps": torch.mps.synchronize()
        report.update(mode="local_runtime_smoke", weight_inference=True, question=question,
            documents=documents, scores=scores, relevant_above_unrelated=scores[0] > scores[1],
            load_seconds=load_seconds, scoring_seconds=perf_counter() - started,
            weights_sha256={name: checksum(model_dir / name) for name in weight_files})
    output = ROOT / "outputs/reranking" / (tag + datetime.now(timezone.utc).strftime("-%Y%m%dT%H%M%S%fZ.json"))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"report_path": str(output), **{key: report[key] for key in (
        "mode", "weight_inference", "mps_available", "maximum_tokens", "oversized_pairs", "scores") if key in report}}, indent=2))
    if report.get("oversized_pairs", 0) or not report.get("relevant_above_unrelated", True):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
