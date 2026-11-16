"""One text-generation call through the OpenAI Responses API, without DB access."""

from rag_workflow_lab.config import GeneratorSettings


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
