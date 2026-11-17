"""One independent model call per raw question, without documents or tools."""

from dataclasses import asdict
from hashlib import sha256
from importlib.resources import files

from rag_workflow_lab.llm import generate_text
from rag_workflow_lab.tracing import finish_span, finish_trace, start_span, start_trace


PROMPT_VERSION = "llm_only_v1"


def answer_question(writer, client, generator, question: str, *, run_id=None, question_id=None,
                    configuration=None) -> dict:
    """Use the database only for tracing; no corpus/index/embedding input is accepted."""
    if not writer.autocommit:
        raise ValueError("LLM-only tracing requires an autocommit writer connection.")
    instructions = files("rag_workflow_lab").joinpath(f"prompts/{PROMPT_VERSION}.md").read_text(encoding="utf-8")
    trace_id = start_trace(writer, question, "llm_only", run_id=run_id, question_id=question_id,
                           configuration={
        **(configuration or {}), "generator": asdict(generator),
        "retrieval": {"enabled": False}, "tools": [],
        "answer_prompt": {"version": PROMPT_VERSION, "sha256": sha256(instructions.encode()).hexdigest()},
        "context_policy": "Raw question only; no documents, gold, tool results or prior responses.",
    })
    span_id = start_span(writer, trace_id, "llm", "answer", {
        "instructions": instructions, "prompt": question, "sources": [],
        "generator": asdict(generator), "service_tier": "default", "store": False,
    })
    try:
        result = generate_text(client, generator, instructions=instructions, prompt=question)
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
    return {"trace_id": trace_id, "sources": [], "ok": ok, **result}
