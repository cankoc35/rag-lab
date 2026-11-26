"""Index-scoped dense retrieval, equal-weight dense/full-text rank fusion and reranking."""

from collections.abc import Callable

from rag_workflow_lab.embeddings import (
    ADAPTER_VERSION, DOCUMENT_PREFIX, NORMALIZATION, QUERY_PREFIX, NomicEmbedder,
)
from rag_workflow_lab.store import get_embedding_index, search_chunks, search_chunks_full_text


RRF_K = 60
HYBRID_CANDIDATES = 20
RERANK_CANDIDATES = 20


def retrieve(connection, embedder: NomicEmbedder, index_id: str, question: str, limit: int = 5) -> list[dict]:
    """Validate index compatibility, embed a raw question and return cited chunks.

    The caller loads/reuses the model and owns the connection/transaction.
    Only question text reaches the embedder; this function reads no gold data.
    """
    index = get_embedding_index(connection, index_id)
    settings = embedder.settings
    if (index["model_id"], index["model_revision"], index["dimensions"]) != (
        settings.model_id, settings.revision, settings.dimensions,
    ):
        raise ValueError("Embedding model, revision or dimensions differ from the selected index.")

    expected = {
        "adapter_version": ADAPTER_VERSION,
        "document_prefix": DOCUMENT_PREFIX, "query_prefix": QUERY_PREFIX,
        "normalization": NORMALIZATION, "device": settings.device,
        "dtype": "float32", "max_tokens": settings.max_tokens,
    }
    if any(index["settings"].get(key) != value for key, value in expected.items()):
        raise ValueError("Embedding settings differ from the selected index.")

    query = embedder.embed_query(question)
    return search_chunks(connection, index_id, query.vector, limit=limit)


def reciprocal_rank_fusion(dense_matches: list[dict], full_text_matches: list[dict]) -> list[dict]:
    """Sum 1/(60 + rank) per list, deduplicate by chunk ID and retain source ranks."""
    fused = {}
    for method, score_key, matches in (("dense", "distance", dense_matches),
                                        ("full_text", "text_score", full_text_matches)):
        for rank, match in enumerate(matches, 1):
            chunk_id = match["chunk_id"]
            if chunk_id not in fused:
                fused[chunk_id] = {**match, "rrf_score": 0.0, "dense_rank": None,
                                   "full_text_rank": None, "distance": None, "text_score": None}
            item = fused[chunk_id]
            item[method + "_rank"] = rank
            item[score_key] = match[score_key]
            item["rrf_score"] += 1 / (RRF_K + rank)
    return sorted(fused.values(), key=lambda item: (-item["rrf_score"], item["chunk_id"]))


def retrieve_hybrid(connection, embedder: NomicEmbedder, index_id: str, question: str,
                    limit: int = 5) -> list[dict]:
    """Fuse up to 20 candidates per method from one index; no reranker or answer call."""
    if limit < 1:
        raise ValueError("Result limit must be positive.")
    dense = retrieve(connection, embedder, index_id, question, limit=HYBRID_CANDIDATES)
    full_text = search_chunks_full_text(connection, index_id, question, limit=HYBRID_CANDIDATES)
    return reciprocal_rank_fusion(dense, full_text)[:limit]


def retrieve_reranked(connection, embedder: NomicEmbedder, index_id: str, question: str,
                      score_passage: Callable[[str, str], float], limit: int = 5) -> list[dict]:
    """Rerank the fused top 20 with a caller-loaded scorer and return the best `limit`.

    `score_passage(question, passage)` should wrap the pinned native Qwen scorer
    in scripts/reranker_smoke.py. Each passage is the stored heading path plus the
    whole chunk text, as in the saved-candidate probe: no embedding prefix, gold
    data or truncation. Results keep source fields, `rrf_rank` and `reranker_score`;
    equal scores keep RRF order.
    """
    if not 1 <= limit <= RERANK_CANDIDATES:
        raise ValueError(f"Result limit must be between 1 and {RERANK_CANDIDATES}.")
    candidates = retrieve_hybrid(connection, embedder, index_id, question, limit=RERANK_CANDIDATES)
    return rerank_candidates(question, candidates, score_passage)[:limit]


def rerank_candidates(question: str, candidates: list[dict], score_passage) -> list[dict]:
    """Score whole passages and retain all results so tracing can inspect the ranking."""
    ranked = []
    for rank, match in enumerate(candidates, 1):
        passage = " > ".join(match["metadata"]["heading_path"]) + "\n\n" + match["text"]
        ranked.append({**match, "rrf_rank": rank, "reranker_score": score_passage(question, passage)})
    ranked.sort(key=lambda item: (-item["reranker_score"], item["rrf_rank"]))
    return ranked
