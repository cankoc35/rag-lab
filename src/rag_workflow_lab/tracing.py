"""Raw-SQL trace writers and explicit retrieval/reranking/model-call wrappers."""

from hashlib import sha256
from dataclasses import asdict
import json
from uuid import uuid4

from rag_workflow_lab.embeddings import QUERY_PREFIX
from rag_workflow_lab.llm import generate_text
from rag_workflow_lab.retrieval import (
    HYBRID_CANDIDATES, RERANK_CANDIDATES, RRF_K, rerank_candidates, retrieve, retrieve_hybrid,
)


def _json(value):
    return json.dumps(value, allow_nan=False) if value is not None else None


def start_trace(connection, question: str, workflow: str, *, run_id=None, question_id=None, configuration=None) -> str:
    """Insert a question attempt; the caller controls the writer transaction."""
    trace_id = str(uuid4())
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO traces (trace_id, run_id, question_id, workflow, question, configuration)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb)
        """, (trace_id, run_id, question_id, workflow, question, _json(configuration or {})))
    return trace_id


def finish_trace(connection, trace_id: str, *, answer=None, error=None) -> None:
    """Finish an open trace once, preserving completed observations."""
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE traces SET finished_at = clock_timestamp(), status = %s,
                              final_answer = %s, error = %s::jsonb
            WHERE trace_id = %s AND status = 'running'
        """, ("error" if error is not None else "ok", answer, _json(error), trace_id))
        if cursor.rowcount != 1:
            raise ValueError("Trace is missing or already finished.")


def start_span(connection, trace_id: str, kind: str, name: str, inputs: dict, *, parent_span_id=None) -> str:
    """Insert one operation; a parent must belong to the same trace."""
    span_id = str(uuid4())
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO spans (span_id, trace_id, parent_span_id, kind, name, inputs)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb)
        """, (span_id, trace_id, parent_span_id, kind, name, _json(inputs)))
    return span_id


def finish_span(connection, span_id: str, *, outputs=None, usage=None, cost=None, error=None) -> None:
    """Finish an operation; unknown usage/cost remain SQL NULL."""
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE spans SET finished_at = clock_timestamp(), status = %s,
                             outputs = %s::jsonb, usage = %s::jsonb,
                             cost = %s::jsonb, error = %s::jsonb
            WHERE span_id = %s AND status = 'running'
        """, ("error" if error is not None else "ok", _json(outputs), _json(usage),
              _json(cost), _json(error), span_id))
        if cursor.rowcount != 1:
            raise ValueError("Span is missing or already finished.")


def generate_with_trace(writer, trace_id, name, client, generator, *, instructions, prompt,
                        text_format=None, parent_span_id=None) -> dict:
    """Persist the exact request before calling the model; retain partial output/usage."""
    inputs = {"instructions": instructions, "prompt": prompt, "generator": asdict(generator),
              "instructions_sha256": sha256(instructions.encode()).hexdigest(),
              "service_tier": "default", "store": False}
    if text_format is not None:
        inputs["text_format"] = text_format
    span_id = start_span(writer, trace_id, "llm", name, inputs, parent_span_id=parent_span_id)
    try:
        result = generate_text(client, generator, instructions=instructions, prompt=prompt, text_format=text_format)
    except Exception as exc:
        finish_span(writer, span_id, error={"type": type(exc).__name__, "message": "Model request failed."})
        raise
    ok = result["status"] == "completed" and bool(result["answer"].strip())
    error = None if ok else {"type": "IncompleteResponse", "message": "No completed, nonempty response was returned."}
    finish_span(writer, span_id, outputs={key: value for key, value in result.items() if key != "usage"},
                usage=result["usage"], error=error)
    return result


def retrieve_reranked_with_trace(connection, writer, embedder, index_id, question, score_passage,
                                *, trace_id, reranker_settings) -> list[dict]:
    """Record fused candidates and the full reranked order under the workflow's trace."""
    if writer is connection or not writer.autocommit:
        raise ValueError("Tracing requires a separate autocommit writer connection.")
    span_id = start_span(writer, trace_id, "retrieval", "hybrid_retrieval", {
        "question": question, "index_id": index_id, "candidates_per_method": HYBRID_CANDIDATES,
        "rrf_k": RRF_K, "limit": RERANK_CANDIDATES,
        "query_input_sha256": sha256((QUERY_PREFIX + question).encode()).hexdigest(),
    })
    try:
        candidates = retrieve_hybrid(connection, embedder, index_id, question, limit=RERANK_CANDIDATES)
    except Exception as exc:
        finish_span(writer, span_id, error={"type": type(exc).__name__, "message": "Hybrid retrieval failed."})
        raise
    # Explicit fields exclude gold annotations or arbitrary caller metadata.
    chunks = [{**{key: match[key] for key in (
        "chunk_id", "snapshot_id", "source_id", "title", "url", "token_count", "text",
        "distance", "text_score", "dense_rank", "full_text_rank", "rrf_score",
    )}, "metadata": {"heading_path": match["metadata"]["heading_path"]}} for match in candidates]
    finish_span(writer, span_id, outputs={"chunks": chunks})
    span_id = start_span(writer, trace_id, "reranking", "rerank", {
        "question": question, "candidates": chunks, "reranker": reranker_settings,
        "passage_format": "heading_path joined by ' > ', then two newlines, then whole text",
        "limit": 5,
    })
    try:
        ranked = rerank_candidates(question, candidates, score_passage)
    except Exception as exc:
        finish_span(writer, span_id, error={"type": type(exc).__name__, "message": "Reranking failed."})
        raise
    finish_span(writer, span_id, outputs={
        "ranking": [{"chunk_id": match["chunk_id"], "rrf_rank": match["rrf_rank"],
                     "reranker_score": match["reranker_score"]} for match in ranked],
        "selected_chunk_ids": [match["chunk_id"] for match in ranked[:5]],
    })
    return ranked[:5]


def retrieve_with_trace(connection, writer, embedder, index_id: str, question: str, limit: int = 5,
                        *, trace_id=None, run_id=None, question_id=None, configuration=None) -> tuple[list[dict], str]:
    """Record one dense retrieval using a separate autocommit writer.

    Logging errors abort the call rather than silently dropping observations.
    Only explicit safe fields are recorded; driver/exception messages are omitted.
    An existing trace_id stays open for its owning workflow to finish.
    """
    if writer is connection or not writer.autocommit:
        raise ValueError("Tracing requires a separate autocommit writer connection.")
    owns_trace = trace_id is None
    if owns_trace:
        settings = embedder.settings
        trace_id = start_trace(writer, question, "dense_retrieval", run_id=run_id,
                               question_id=question_id, configuration={
            **(configuration or {}),
            "embedding": {"model_id": settings.model_id, "revision": settings.revision,
                          "dimensions": settings.dimensions, "device": settings.device,
                          "max_tokens": settings.max_tokens},
            "retrieval": {"index_id": index_id, "method": "dense", "limit": limit,
                          "distance_metric": "cosine"},
        })
    span_id = start_span(writer, trace_id, "retrieval", "dense_retrieval", {
        "question": question, "index_id": index_id, "limit": limit,
        "query_input_sha256": sha256((QUERY_PREFIX + question).encode()).hexdigest(),
    })
    try:
        matches = retrieve(connection, embedder, index_id, question, limit=limit)
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": "Dense retrieval failed."}
        finish_span(writer, span_id, error=error)
        if owns_trace:
            finish_trace(writer, trace_id, error=error)
        raise
    chunks = [{"rank": rank, **{key: match[key] for key in (
        "chunk_id", "snapshot_id", "source_id", "url", "title", "token_count", "distance",
    )}} for rank, match in enumerate(matches, 1)]
    finish_span(writer, span_id, outputs={"score_type": "cosine_distance", "chunks": chunks})
    if owns_trace:
        finish_trace(writer, trace_id)
    return matches, trace_id
