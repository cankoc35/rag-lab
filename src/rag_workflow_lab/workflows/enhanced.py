"""Reranked context with explicit evidence policies; final answers/tools follow later."""

from rag_workflow_lab.evidence import MODES, assess_evidence
from rag_workflow_lab.retrieval import retrieve_reranked


def prepare_context(connection, embedder, index_id: str, question: str, score_passage,
                    *, mode: str, client=None, generator=None) -> dict:
    """Return usable context only when the selected policy allows generation."""
    if mode not in MODES:
        raise ValueError(f"Evidence mode must be one of {MODES}.")
    matches = retrieve_reranked(connection, embedder, index_id, question, score_passage)
    check = assess_evidence(question, matches, mode=mode, client=client, generator=generator)
    return {"context": matches if check["allowed"] else [],
            "retrieved_chunks": matches, "evidence_check": check}
