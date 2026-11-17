"""One text-generation call through the OpenAI Responses API, without DB access."""

import json

from rag_workflow_lab.config import GeneratorSettings


def build_answer_input(question: str, matches: list[dict]) -> tuple[str, list[dict]]:
    """Label whole retrieved chunks; keep citation labels separate from gold evidence IDs."""
    sources = [{"label": f"S{rank}", **{key: match[key] for key in (
        "chunk_id", "snapshot_id", "source_id", "title", "url", "distance", "token_count",
    )}} for rank, match in enumerate(matches, 1)]
    evidence = [{**source, "text": match["text"]} for source, match in zip(sources, matches)]
    return json.dumps({"question": question, "sources": evidence}, ensure_ascii=False, indent=2), sources


def generate_text(client, settings: GeneratorSettings, *, instructions: str, prompt: str) -> dict:
    """Return text, completion status and reported usage; the caller owns the client."""
    response = client.responses.create(
        model=settings.model_id,
        instructions=instructions,
        input=prompt,
        reasoning={"effort": settings.reasoning_effort},
        max_output_tokens=settings.max_output_tokens,
        service_tier="default",
        store=False,
    )
    return {
        "response_id": response.id,
        "model": response.model,
        "status": response.status,
        "answer": response.output_text,
        "usage": response.usage.model_dump(mode="json") if response.usage is not None else None,
        "incomplete_reason": response.incomplete_details.reason if response.incomplete_details else None,
    }
