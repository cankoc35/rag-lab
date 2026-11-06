# /// script
# requires-python = ">=3.11"
# dependencies = ["tokenizers==0.22.2"]
# ///
"""Measure saved parser blocks with a pinned candidate tokenizer, without a model.

Run with uv; tokenizer downloads require the explicit --download-tokenizer flag.
Existing parsed documents and reports are never overwritten.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
from urllib.request import urlopen

import tokenizers
from tokenizers import Tokenizer


ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "nomic-ai/nomic-embed-text-v1.5"
REVISION = "e9b6763023c676ca8431644204f50c2b100d9aab"
FILES = {
    "tokenizer.json": "d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66",
    "tokenizer_config.json": "d7e0000bcc80134debd2222220427e6bf5fa20a669f40a0d0d1409cc18e0a9bc",
    "special_tokens_map.json": "5d5b662e421ea9fac075174bb0688ee0d9431699900b90662acd44b2a350503a",
    "sentence_bert_config.json": "9ee3935137f87c9ce6662ae17fe7afb7c9c64744a41247359fd228dc37e627b3",
}
PREFIX = "search_document: "
KINDS = {"heading", "paragraph", "code", "table"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare_tokenizer(directory: Path, allow_download: bool) -> Tokenizer:
    """Fetch only public tokenizer metadata when requested; verify every file."""
    for name, expected in FILES.items():
        path = directory / name
        if not path.exists():
            if not allow_download:
                raise ValueError(f"Missing {path}; use --download-tokenizer once.")
            url = f"https://huggingface.co/{MODEL_ID}/resolve/{REVISION}/{name}"
            with urlopen(url, timeout=30) as response:
                data = response.read()
            if sha256(data) != expected:
                raise ValueError(f"Downloaded tokenizer checksum mismatch: {name}")
            directory.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as handle:
                handle.write(data)
        if sha256(path.read_bytes()) != expected:
            raise ValueError(f"Cached tokenizer checksum mismatch: {name}")

    tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
    tokenizer.no_truncation()
    tokenizer.no_padding()
    return tokenizer


def contextual_text(block: dict) -> str:
    """Keep body text intact; prepend ancestors except to a heading itself."""
    body = block["text"]
    if block["kind"] == "heading" or not block["heading_path"]:
        return PREFIX + body
    return PREFIX + " > ".join(block["heading_path"]) + "\n\n" + body


def summarize(records: list[dict]) -> dict:
    """Use nearest-rank percentiles and strict greater-than threshold counts."""
    values = sorted(record["contextual_tokens"] for record in records)
    return {
        "blocks": len(values),
        "body_tokens_total": sum(record["body_tokens"] for record in records),
        "contextual_tokens_total": sum(values),
        "min": values[0],
        "p50": values[math.ceil(0.50 * len(values)) - 1],
        "p95": values[math.ceil(0.95 * len(values)) - 1],
        "max": values[-1],
        "over": {
            str(limit): sum(value > limit for value in values)
            for limit in (256, 512, 768, 1024, 8192)
        },
    }


def measure(parsed_dir: Path, tokenizer: Tokenizer) -> tuple[list, list]:
    files = sorted(parsed_dir.glob("*.json"))
    if not files:
        raise ValueError(f"No parsed JSON documents found in {parsed_dir}")
    inputs, records, source_ids = [], [], set()
    for path in files:
        data = path.read_bytes()
        payload = json.loads(data)
        if payload["schema_version"] != 1:
            raise ValueError(f"Unsupported parsed schema: {path}")
        document = payload["document"]
        source_id = document["source_id"]
        if source_id in source_ids:
            raise ValueError(f"Multiple snapshots for {source_id}; select one per source.")
        source_ids.add(source_id)
        inputs.append({
            "parsed_file": str(path.resolve().relative_to(ROOT))
            if path.resolve().is_relative_to(ROOT) else str(path.resolve()),
            "parsed_sha256": sha256(data),
            **{key: document[key] for key in (
                "source_id", "snapshot_id", "source_url", "source_sha256", "parser_version"
            )},
        })
        for index, block in enumerate(document["blocks"], start=1):
            if block["kind"] not in KINDS or not block["text"].strip():
                raise ValueError(f"Invalid/empty block {index} in {path}")
            body = tokenizer.encode(block["text"], add_special_tokens=False)
            prefixed = tokenizer.encode(PREFIX + block["text"], add_special_tokens=True)
            contextual = tokenizer.encode(contextual_text(block), add_special_tokens=True)
            if contextual.ids[0] != 101 or contextual.ids[-1] != 102:
                raise ValueError("Expected [CLS]/[SEP] boundary tokens")
            records.append({
                "source_id": source_id,
                "snapshot_id": document["snapshot_id"],
                "block_index": index,
                "kind": block["kind"],
                "heading_path": block["heading_path"],
                "anchor": block["anchor"],
                "body_characters": len(block["text"]),
                "body_tokens": len(body.ids),
                "prefixed_tokens": len(prefixed.ids),
                "contextual_tokens": len(contextual.ids),
                "unknown_tokens": contextual.ids.count(tokenizer.token_to_id("[UNK]")),
            })
    if not records:
        raise ValueError("Parsed documents contain no blocks")
    return inputs, records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parsed-dir", type=Path, default=ROOT / "data/local/parsed")
    parser.add_argument("--tokenizer-dir", type=Path, default=(
        ROOT / "data/local/tokenizers/nomic-embed-text-v1.5" / REVISION
    ))
    parser.add_argument("--download-tokenizer", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    output = args.output or ROOT / "outputs/token-counts" / (
        now.strftime("%Y%m%dT%H%M%S%fZ") + ".json"
    )
    if output.exists():
        parser.error(f"Output already exists: {output}")
    if tokenizers.__version__ != "0.22.2":
        parser.error("Run using the pinned tokenizers==0.22.2 dependency")
    try:
        tokenizer = prepare_tokenizer(args.tokenizer_dir, args.download_tokenizer)
        # Exercise an input beyond the advertised limit to catch silent truncation.
        probe_tokens = len(tokenizer.encode("test " * 9000, add_special_tokens=True).ids)
        if probe_tokens != 9002 or tokenizer.truncation or tokenizer.padding:
            raise ValueError("Tokenizer must count complete unpadded, untruncated inputs")
        inputs, records = measure(args.parsed_dir, tokenizer)
        config = json.loads((args.tokenizer_dir / "tokenizer_config.json").read_text())
        sentence_config = json.loads((args.tokenizer_dir / "sentence_bert_config.json").read_text())
        summary = {
            "overall": summarize(records),
            "by_source": {
                source: summarize([r for r in records if r["source_id"] == source])
                for source in sorted({r["source_id"] for r in records})
            },
            "by_kind": {
                kind: summarize([r for r in records if r["kind"] == kind])
                for kind in sorted({r["kind"] for r in records})
            },
        }
        report = {
            "schema_version": 1,
            "measured_at": now.isoformat(),
            "scope": "Parsed blocks, not finished chunks or embedding quality",
            "tokenizer": {
                "model_id": MODEL_ID, "revision": REVISION, "files_sha256": FILES,
                "tokenizers_version": tokenizers.__version__,
                "configured_model_max_length": config["model_max_length"],
                "configured_sentence_max_seq_length": sentence_config["max_seq_length"],
                "truncation": False, "padding": False,
            },
            "measurement": {
                "serialization_version": "block-context-v1",
                "prefix": PREFIX,
                "body_tokens": "Body only; special tokens excluded",
                "prefixed_tokens": "Prefix + body; [CLS] and [SEP] included",
                "contextual_tokens": (
                    "Prefix + heading_path joined with ' > ' + two newlines + body; "
                    "[CLS] and [SEP] included. Headings/empty paths use prefix + body."
                ),
                "table_serialization": "Existing ParsedBlock.text, unchanged",
                "percentiles": "Nearest rank",
                "thresholds": "Strictly greater than; applied to contextual_tokens",
                "untruncated_probe_tokens": probe_tokens,
                "python_version": platform.python_version(),
                "script_sha256": sha256(Path(__file__).read_bytes()),
            },
            "inputs": inputs, "summary": summary, "blocks": records,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps({"output": str(output), "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
