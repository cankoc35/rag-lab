"""Reranked retrieval, evidence checks and a source-backed answer; tools follow later."""

from dataclasses import asdict
from hashlib import sha256
from importlib.resources import files

from rag_workflow_lab.evidence import (
    MODES, PROMPT_VERSION as CHECKER_PROMPT_VERSION, QUOTE_CHECK_VERSION, THRESHOLD, assess_evidence,
)
from rag_workflow_lab.llm import build_answer_input, generate_text
from rag_workflow_lab.retrieval import HYBRID_CANDIDATES, RERANK_CANDIDATES, RRF_K, retrieve_reranked
from rag_workflow_lab.tracing import (
    finish_span, finish_trace, generate_with_trace, retrieve_reranked_with_trace, start_span, start_trace,
)


PROMPT_VERSION = "answer_v1"


def prepare_context(connection, embedder, index_id: str, question: str, score_passage,
                    *, mode: str, client=None, generator=None, writer=None, trace_id=None,
                    reranker_settings=None) -> dict:
    """Return usable context only when the selected policy allows generation."""
    if mode not in MODES:
        raise ValueError(f"Evidence mode must be one of {MODES}.")
    if writer is None:
        matches = retrieve_reranked(connection, embedder, index_id, question, score_passage)
        check = assess_evidence(question, matches, mode=mode, client=client, generator=generator)
    else:
        matches = retrieve_reranked_with_trace(connection, writer, embedder, index_id, question, score_passage,
                                              trace_id=trace_id, reranker_settings=reranker_settings)
        span_id = start_span(writer, trace_id, "validation", "evidence_check", {
            "question": question, "mode": mode, "threshold": THRESHOLD,
            "chunk_ids": [match["chunk_id"] for match in matches],
            "prompt_version": CHECKER_PROMPT_VERSION, "quote_validation": QUOTE_CHECK_VERSION,
        })
        try:
            check = assess_evidence(question, matches, mode=mode, client=client, generator=generator,
                                    writer=writer, trace_id=trace_id, parent_span_id=span_id)
        except Exception as exc:
            finish_span(writer, span_id, error={"type": type(exc).__name__, "message": "Evidence check failed."})
            raise
        error = None if check["decision"] != "error" else {
            "type": "EvidenceCheckError", "message": "Evidence check returned invalid or incomplete output.",
        }
        finish_span(writer, span_id, outputs=check, error=error)
    return {"context": matches if check["allowed"] else [],
            "retrieved_chunks": matches, "evidence_check": check}


def answer_question(connection, embedder, client, generator, index_id: str, question: str,
                    score_passage, *, mode: str, writer=None, reranker_settings=None,
                    run_id=None, question_id=None, configuration=None) -> dict:
    """Optionally record the entire workflow using a separate autocommit writer.

    The caller supplies the loaded scorer's settings; no model identity is inferred.
    Without a writer, the existing untraced behavior is preserved.
    """
    if mode not in MODES:
        raise ValueError(f"Evidence mode must be one of {MODES}.")
    if writer is None:
        return _answer_question(connection, embedder, client, generator, index_id, question, score_passage, mode=mode)
    if writer is connection or not writer.autocommit:
        raise ValueError("Tracing requires a separate autocommit writer connection.")
    if reranker_settings is None:
        raise ValueError("Traced Enhanced answers require the loaded scorer's reranker settings.")
    reranker = {key: reranker_settings[key] for key in ("model_id", "revision", "device", "dtype", "max_tokens", "instruction")}
    settings = embedder.settings
    trace_id = start_trace(writer, question, "enhanced", run_id=run_id, question_id=question_id, configuration={
        **(configuration or {}), "generator": asdict(generator) if generator is not None else None,
        "embedding": {key: getattr(settings, key) for key in ("model_id", "revision", "dimensions", "device", "max_tokens")},
        "retrieval": {"index_id": index_id, "method": "hybrid", "candidates_per_method": HYBRID_CANDIDATES,
                      "rrf_k": RRF_K, "rerank_candidates": RERANK_CANDIDATES, "context_limit": 5},
        "reranker": {**reranker, "batch_size": 1}, "evidence_mode": mode, "threshold": THRESHOLD,
        "answer_prompt_version": PROMPT_VERSION, "checker_prompt_version": CHECKER_PROMPT_VERSION,
        "quote_validation": QUOTE_CHECK_VERSION,
    })
    try:
        result = _answer_question(connection, embedder, client, generator, index_id, question, score_passage,
                                  mode=mode, writer=writer, trace_id=trace_id, reranker_settings=reranker)
    except Exception as exc:
        finish_trace(writer, trace_id, error={"type": type(exc).__name__, "message": "Enhanced workflow failed."})
        raise
    error = None if result["ok"] else {
        "type": "EnhancedOutputError", "message": "Evidence check or answer output was invalid or incomplete.",
    }
    finish_trace(writer, trace_id, answer=result["answer"], error=error)
    return {"trace_id": trace_id, **result}


def _answer_question(connection, embedder, client, generator, index_id, question, score_passage,
                     *, mode, writer=None, trace_id=None, reranker_settings=None) -> dict:
    """Generate from accepted context; normal evidence rejection returns a fixed abstention."""
    prepared = prepare_context(connection, embedder, index_id, question, score_passage,
                               mode=mode, client=client, generator=generator, writer=writer,
                               trace_id=trace_id, reranker_settings=reranker_settings)
    check = prepared["evidence_check"]
    if not check["allowed"]:
        error = check["decision"] == "error"
        return {**prepared, "ok": not error, "outcome": "error" if error else "abstained",
                "answer": None if error else "The supplied evidence is insufficient to answer this question.",
                "sources": [], "generation": None}

    instructions = files("rag_workflow_lab").joinpath(f"prompts/{PROMPT_VERSION}.md").read_text(encoding="utf-8")
    prompt, sources = build_answer_input(question, prepared["context"])
    if writer is None:
        response = generate_text(client, generator, instructions=instructions, prompt=prompt)
    else:
        response = generate_with_trace(writer, trace_id, "answer", client, generator,
                                       instructions=instructions, prompt=prompt)
    ok = response["status"] == "completed" and bool(response["answer"].strip())
    return {**prepared, "ok": ok, "outcome": "answered" if ok else "error",
            "answer": response["answer"], "sources": sources, "generation": {
                "prompt_version": PROMPT_VERSION,
                "instructions_sha256": sha256(instructions.encode()).hexdigest(),
                "instructions": instructions, "prompt": prompt, "generator": asdict(generator),
                "service_tier": "default", "store": False, "response": response,
            }}
