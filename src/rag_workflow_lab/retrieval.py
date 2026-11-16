"""Combine local query embeddings with index-scoped dense SQL search."""

from rag_workflow_lab.embeddings import (
    ADAPTER_VERSION, DOCUMENT_PREFIX, NORMALIZATION, QUERY_PREFIX, NomicEmbedder,
)
from rag_workflow_lab.store import get_embedding_index, search_chunks


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
