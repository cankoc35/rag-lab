"""Small raw-SQL trace/span writers and an explicit traced retrieval wrapper."""

from hashlib import sha256
import json
from uuid import uuid4

from rag_workflow_lab.embeddings import QUERY_PREFIX
from rag_workflow_lab.retrieval import retrieve


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
