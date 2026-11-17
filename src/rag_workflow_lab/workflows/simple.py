"""Dense retrieval and one evidence-backed answer, recorded under one trace."""

from dataclasses import asdict
from hashlib import sha256
from importlib.resources import files

from rag_workflow_lab.llm import build_answer_input, generate_text
from rag_workflow_lab.tracing import finish_span, finish_trace, retrieve_with_trace, start_span, start_trace


PROMPT_VERSION = "answer_v1"


def answer_question(connection, writer, embedder, client, generator, index_id: str, question: str,
                    *, run_id=None, question_id=None, configuration=None) -> dict:
    """Use only the raw question and retrieved chunks; callers own clients/connections."""
    if writer is connection or not writer.autocommit:
        raise ValueError("Tracing requires a separate autocommit writer connection.")
    instructions = files("rag_workflow_lab").joinpath(f"prompts/{PROMPT_VERSION}.md").read_text(encoding="utf-8")
    settings = embedder.settings
    trace_id = start_trace(writer, question, "simple", run_id=run_id, question_id=question_id,
                           configuration={
        **(configuration or {}), "generator": asdict(generator),
        "embedding": {"model_id": settings.model_id, "revision": settings.revision,
                      "dimensions": settings.dimensions, "device": settings.device,
                      "max_tokens": settings.max_tokens},
        "retrieval": {"index_id": index_id, "method": "dense", "limit": 5, "distance_metric": "cosine"},
        "answer_prompt": {"version": PROMPT_VERSION, "sha256": sha256(instructions.encode()).hexdigest()},
        "context_policy": "All retrieved chunks, whole and untruncated; no final token budget selected.",
    })
    try:
        matches, _ = retrieve_with_trace(connection, writer, embedder, index_id, question, trace_id=trace_id)
    except Exception as exc:
        finish_trace(writer, trace_id, error={"type": type(exc).__name__, "message": "Simple retrieval failed."})
        raise

    prompt, sources = build_answer_input(question, matches)
    span_id = start_span(writer, trace_id, "llm", "answer", {
        "instructions": instructions, "prompt": prompt, "sources": sources,
        "generator": asdict(generator), "service_tier": "default", "store": False,
    })
    try:
        result = generate_text(client, generator, instructions=instructions, prompt=prompt)
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": "Answer generation failed."}
        finish_span(writer, span_id, error=error)
        finish_trace(writer, trace_id, error=error)
        raise

    ok = result["status"] == "completed" and bool(result["answer"].strip())
    error = None if ok else {"type": "IncompleteAnswer", "message": "No completed, nonempty answer was returned."}
    finish_span(writer, span_id, outputs={key: value for key, value in result.items() if key != "usage"},
                usage=result["usage"], error=error)
    finish_trace(writer, trace_id, answer=result["answer"], error=error)
    return {"trace_id": trace_id, "sources": sources, "ok": ok, **result}
