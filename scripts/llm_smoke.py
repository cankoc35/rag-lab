# /// script
# requires-python = ">=3.11"
# dependencies = ["openai==3.51.0"]
# ///
"""Opt-in, single-request Luna connectivity check; no corpus, retrieval or DB access."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys
import time

from rag_workflow_lab.config import load_settings
from rag_workflow_lab.llm import generate_text


ROOT = Path(__file__).resolve().parents[1]
INSTRUCTIONS = "Reply in one short English sentence."
PROMPT = "Reply with exactly: Luna API smoke test passed."


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/pilot.toml")
    parser.add_argument("--call-api", action="store_true", help="Allow one paid OpenAI request.")
    args = parser.parse_args(argv)
    if not args.call_api:
        parser.error("Pass --call-api to allow one paid request.")
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        parser.error("Set OPENAI_API_KEY in the environment or load .env with uv --env-file.")
    try:
        settings = load_settings(args.config).generator
        if settings is None:
            raise ValueError("Config has no generator section.")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    from openai import OpenAI, OpenAIError

    print(f"Sending one request to {settings.model_id}...", file=sys.stderr, flush=True)
    started = time.perf_counter()
    try:
        with OpenAI(base_url="https://api.openai.com/v1", timeout=30, max_retries=0) as client:
            result = generate_text(client, settings, instructions=INSTRUCTIONS, prompt=PROMPT)
    except OpenAIError as exc:
        print(f"OpenAI request failed ({type(exc).__name__}).", file=sys.stderr)
        return 2
    print(json.dumps({
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": asdict(settings), "openai_version": version("openai"),
        "instructions": INSTRUCTIONS, "prompt": PROMPT,
        "elapsed_seconds": time.perf_counter() - started, **result,
    }, indent=2))
    return 0 if result["status"] == "completed" and result["answer"].strip() else 2


if __name__ == "__main__":
    raise SystemExit(main())
