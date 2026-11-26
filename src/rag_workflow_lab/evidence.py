"""Compare an unfiltered baseline, a question-score gate and context sufficiency."""

from hashlib import sha256
from importlib.resources import files
import json
import math
import re

from rag_workflow_lab.llm import generate_text


MODES = ("baseline", "threshold", "sufficiency")
THRESHOLD = 0.95
PROMPT_VERSION = "sufficiency_v1"
QUOTE_CHECK_VERSION = "source_span_v2"
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["status", "reason", "evidence", "missing_information"],
    "properties": {
        "status": {"type": "string", "enum": ["sufficient", "partial", "insufficient"]},
        "reason": {"type": "string"},
        "missing_information": {"type": "array", "items": {"type": "string"}},
        "evidence": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["source_label", "quote"],
            "properties": {"source_label": {"type": "string"}, "quote": {"type": "string"}},
        }},
    },
}


def _source_quote(quote: str, text: str) -> str | None:
    """Recover literal source text; formatting recovery requires a unique span."""
    if quote in text:
        return quote
    pattern = r"\s+".join(re.escape(word) for word in quote.split())
    match = re.search(pattern, text)
    if match:
        return match.group()

    # Keep original positions while ignoring bold markers and whitespace runs.
    parts = [m for m in re.finditer(r"\*\*|\s+|.", text, re.DOTALL) if m.group() != "**"]
    plain = "".join(" " if m.group().isspace() else m.group() for m in parts)
    needle = " ".join(quote.replace("**", "").split())
    if not needle:
        return None
    pattern = re.escape(needle)
    if needle[0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        pattern = f"[{needle[0]}{needle[0].lower()}]" + re.escape(needle[1:])
    matches = list(re.finditer(r"(?<!\w)" + pattern + r"(?!\w)", plain))
    if len(matches) != 1:
        return None
    start, end = matches[0].span()
    return text[parts[start].start():parts[end - 1].end()]


def validate_assessment(data: dict, sources: list[dict]) -> list[dict]:
    """Validate structure/attribution and return source quotes, not entailment."""
    if (not isinstance(data, dict) or set(data) != set(SCHEMA["required"])
            or data["status"] not in SCHEMA["properties"]["status"]["enum"]
            or not isinstance(data["reason"], str) or not data["reason"].strip()
            or not isinstance(data["evidence"], list)
            or not isinstance(data["missing_information"], list)):
        raise ValueError("Invalid sufficiency assessment structure.")
    if any(not isinstance(item, str) or not item.strip() for item in data["missing_information"]):
        raise ValueError("Missing-information entries must be nonempty strings.")
    texts = {source["label"]: source["text"] for source in sources}
    verified = []
    for evidence in data["evidence"]:
        if not isinstance(evidence, dict) or set(evidence) != {"source_label", "quote"}:
            raise ValueError("Invalid evidence reference.")
        label, quote = evidence["source_label"], evidence["quote"]
        if (not isinstance(label, str) or label not in texts or not isinstance(quote, str)
                or not quote.strip()):
            raise ValueError("Evidence requires a known source and a nonempty quote.")
        actual = _source_quote(quote, texts[label])
        if actual is None:
            raise ValueError("Evidence must match a passage in its cited source; formatting recovery must be unique.")
        verified.append({"source_label": label, "quote": actual})
    if data["status"] == "sufficient":
        if not data["evidence"] or data["missing_information"]:
            raise ValueError("Sufficient context requires evidence and no missing information.")
    elif not data["missing_information"] or (data["status"] == "partial" and not data["evidence"]):
        raise ValueError("Partial/insufficient context must identify missing information.")
    return verified


def assess_evidence(question: str, matches: list[dict], *, mode: str,
                    client=None, generator=None) -> dict:
    """Assess already selected chunks; only sufficiency makes one model call.

    A threshold pass is not a sufficiency judgment. Partial, insufficient or
    invalid model output never permits answer generation. No source is filtered.
    """
    if mode not in MODES:
        raise ValueError(f"Evidence mode must be one of {MODES}.")
    result = {"mode": mode, "allowed": False, "decision": "no_evidence"}
    if not matches:
        return result
    if mode == "baseline":
        return {**result, "allowed": True, "decision": "unchecked"}
    if mode == "threshold":
        scores = [match["reranker_score"] for match in matches]
        if any(not math.isfinite(value) or not 0 <= value <= 1 for value in scores):
            raise ValueError("Threshold mode requires finite scores between zero and one.")
        maximum = max(scores)
        allowed = maximum >= THRESHOLD
        return {**result, "allowed": allowed, "decision": "score_pass" if allowed else "score_reject",
                "threshold": THRESHOLD, "maximum_score": maximum}
    if client is None or generator is None:
        raise ValueError("Sufficiency mode requires a caller-owned client and generator settings.")

    sources = [{"label": f"S{rank}", **{key: match[key] for key in (
        "chunk_id", "snapshot_id", "source_id", "text",
    )}, "heading_path": match["metadata"]["heading_path"]}
        for rank, match in enumerate(matches, 1)]
    instructions = files("rag_workflow_lab").joinpath(f"prompts/{PROMPT_VERSION}.md").read_text(encoding="utf-8")
    prompt = json.dumps({"question": question, "sources": sources}, ensure_ascii=False, indent=2)
    response = generate_text(client, generator, instructions=instructions, prompt=prompt,
                             text_format={"type": "json_schema", "name": PROMPT_VERSION,
                                          "strict": True, "schema": SCHEMA})
    result.update(decision="error", prompt_version=PROMPT_VERSION, quote_validation=QUOTE_CHECK_VERSION,
                  instructions_sha256=sha256(instructions.encode()).hexdigest(),
                  instructions=instructions, prompt=prompt, response=response)
    if response["status"] != "completed" or not response["answer"].strip():
        return {**result, "error": "Evidence check did not return a completed, nonempty response."}
    try:
        assessment = json.loads(response["answer"])
        verified = validate_assessment(assessment, sources)
    except ValueError as exc:
        return {**result, "error": str(exc)}
    return {**result, "allowed": assessment["status"] == "sufficient",
            "decision": assessment["status"], "assessment": assessment,
            "verified_evidence": verified}
