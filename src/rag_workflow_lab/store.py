"""Raw-SQL database checks, immutable storage and dense chunk search."""

from dataclasses import dataclass
import json

from rag_workflow_lab.config import DatabaseSettings
from rag_workflow_lab.embeddings import DIMENSIONS, EmbeddingResult


class DatabaseCheckError(RuntimeError):
    """A database check failed; messages omit driver details and credentials."""


@dataclass(frozen=True)
class DatabaseCheckResult:
    """Verified server/extension versions, without connection credentials."""

    postgresql_version: str
    pgvector_version: str
    read_only: bool


def check_database(settings: DatabaseSettings) -> DatabaseCheckResult:
    """Run read-only SQL checks, loading Psycopg only on explicit invocation.

    Connection timeout comes from settings; each statement has a five-second
    timeout. Connection/cursor contexts close resources on success or failure.
    """
    try:
        import psycopg
    except ImportError:
        raise DatabaseCheckError(
            "Psycopg is unavailable. Install the 'database' optional dependencies "
            "and run with that Python environment."
        ) from None

    try:
        with psycopg.connect(
            **settings.connect_kwargs(), options="-c statement_timeout=5000"
        ) as connection:
            connection.read_only = True
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                if cursor.fetchone() != (1,):
                    raise DatabaseCheckError("PostgreSQL did not return the expected connectivity result.")

                cursor.execute("SELECT version(), current_setting('transaction_read_only')")
                version = cursor.fetchone()
                if version is None or len(version) != 2 or not isinstance(version[0], str) or not version[0].strip():
                    raise DatabaseCheckError("PostgreSQL did not return a server version.")
                if version[1] != "on":
                    raise DatabaseCheckError("PostgreSQL did not confirm a read-only transaction.")

                cursor.execute(
                    "SELECT extversion FROM pg_catalog.pg_extension WHERE extname = %s",
                    ("vector",),
                )
                extension = cursor.fetchone()
                if extension is None:
                    raise DatabaseCheckError("Required extension 'vector' is not installed in the configured database.")
                if len(extension) != 1 or not isinstance(extension[0], str) or not extension[0].strip():
                    raise DatabaseCheckError("PostgreSQL did not return a version for extension 'vector'.")

                result = DatabaseCheckResult(
                    postgresql_version=version[0], pgvector_version=extension[0], read_only=True,
                )
    except psycopg.Error:
        # Driver errors can contain connection information; never echo them.
        raise DatabaseCheckError(
            "PostgreSQL check failed. Verify the service, POSTGRES_* settings "
            "and database permissions."
        ) from None
    return result


def save_snapshots(connection, snapshots: list[dict]) -> None:
    """Save snapshot records; the caller owns the transaction.

    Repeated identical records are accepted. Changed records with an existing
    ID raise ValueError so the caller can roll back the whole import.
    """
    with connection.cursor() as cursor:
        for snapshot in snapshots:
            source = snapshot["source"]
            cursor.execute("""
                INSERT INTO source_snapshots
                    (snapshot_id, source_id, title, url, sha256, downloaded_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (snapshot_id) DO UPDATE
                SET snapshot_id = EXCLUDED.snapshot_id
                WHERE (source_snapshots.source_id, source_snapshots.title,
                       source_snapshots.url, source_snapshots.sha256,
                       source_snapshots.downloaded_at)
                    = (EXCLUDED.source_id, EXCLUDED.title, EXCLUDED.url,
                       EXCLUDED.sha256, EXCLUDED.downloaded_at)
            """, (snapshot["snapshot_id"], source["source_id"], source["title"],
                  source["url"], snapshot["sha256"], snapshot["downloaded_at"]))
            if cursor.rowcount != 1:
                raise ValueError(f"Stored snapshot differs: {snapshot['snapshot_id']}")


def save_chunks(connection, chunks: list[dict]) -> None:
    """Save exact chunk inputs and remaining fields as JSONB metadata."""
    from psycopg.types.json import Jsonb

    columns = {"chunk_id", "snapshot_id", "text", "embedding_text", "token_count"}
    with connection.cursor() as cursor:
        for chunk in chunks:
            metadata = {key: value for key, value in chunk.items() if key not in columns}
            cursor.execute("""
                INSERT INTO chunks
                    (chunk_id, snapshot_id, text, embedding_text, token_count, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE
                SET chunk_id = EXCLUDED.chunk_id
                WHERE (chunks.snapshot_id, chunks.text, chunks.embedding_text,
                       chunks.token_count, chunks.metadata)
                    = (EXCLUDED.snapshot_id, EXCLUDED.text, EXCLUDED.embedding_text,
                       EXCLUDED.token_count, EXCLUDED.metadata)
            """, (chunk["chunk_id"], chunk["snapshot_id"], chunk["text"],
                  chunk["embedding_text"], chunk["token_count"], Jsonb(metadata)))
            if cursor.rowcount != 1:
                raise ValueError(f"Stored chunk differs: {chunk['chunk_id']}")


def save_embedding_index(connection, index: dict) -> None:
    """Save immutable model/corpus settings; the caller owns the transaction."""
    from psycopg.types.json import Jsonb

    if index["dimensions"] != DIMENSIONS:
        raise ValueError("Embedding indexes must use 768 dimensions.")
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO embedding_indexes
                (index_id, model_id, model_revision, dimensions, chunk_set_sha256, settings)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (index_id) DO UPDATE
            SET index_id = EXCLUDED.index_id
            WHERE (embedding_indexes.model_id, embedding_indexes.model_revision,
                   embedding_indexes.dimensions, embedding_indexes.chunk_set_sha256,
                   embedding_indexes.settings)
                = (EXCLUDED.model_id, EXCLUDED.model_revision, EXCLUDED.dimensions,
                   EXCLUDED.chunk_set_sha256, EXCLUDED.settings)
        """, (index["index_id"], index["model_id"], index["model_revision"],
              index["dimensions"], index["chunk_set_sha256"], Jsonb(index["settings"])))
        if cursor.rowcount != 1:
            raise ValueError(f"Stored embedding index differs: {index['index_id']}")


def save_embeddings(connection, index_id: str, embeddings: list[tuple[str, EmbeddingResult]]) -> None:
    """Save (chunk_id, document result) pairs without changing existing records.

    Input hashes must match stored chunk inputs. The caller owns the transaction.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT model_id, model_revision, dimensions FROM embedding_indexes WHERE index_id = %s", (index_id,))
        index = cursor.fetchone()
        if index is None:
            raise ValueError(f"Unknown embedding index: {index_id}")
        for chunk_id, result in embeddings:
            if result.task != "document" or (result.model_id, result.model_revision, len(result.vector)) != index:
                raise ValueError(f"Embedding model, revision, dimensions or task mismatch: {chunk_id}")
            # Text casting avoids an extra pgvector adapter dependency.
            vector = json.dumps(result.vector, allow_nan=False)
            cursor.execute("""
                INSERT INTO chunk_embeddings (index_id, chunk_id, input_sha256, embedding)
                SELECT %s, chunk_id, %s, %s::vector FROM chunks
                WHERE chunk_id = %s
                  AND encode(sha256(convert_to(embedding_text, 'UTF8')), 'hex') = %s
                ON CONFLICT (index_id, chunk_id) DO UPDATE
                SET chunk_id = EXCLUDED.chunk_id
                WHERE chunk_embeddings.input_sha256 = EXCLUDED.input_sha256
                  AND chunk_embeddings.embedding = EXCLUDED.embedding
            """, (index_id, result.input_sha256, vector, chunk_id, result.input_sha256))
            if cursor.rowcount != 1:
                raise ValueError(f"Missing chunk, input hash mismatch or conflicting embedding: {chunk_id}")


def get_embedding_index(connection, index_id: str) -> dict:
    """Read the selected index metadata without committing or opening a connection."""
    from psycopg.rows import dict_row

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute("""
            SELECT index_id, model_id, model_revision, dimensions, chunk_set_sha256, settings
            FROM embedding_indexes WHERE index_id = %s
        """, (index_id,))
        index = cursor.fetchone()
    if index is None:
        raise ValueError(f"Unknown embedding index: {index_id}")
    return index


def search_chunks(connection, index_id: str, query_vector: tuple[float, ...], limit: int = 5) -> list[dict]:
    """Return source-linked chunks ordered by cosine distance (lower is closer).

    Uses an existing connection without committing. An empty or unknown index
    returns no matches. The caller must use the selected index's embedding model.
    """
    if limit < 1:
        raise ValueError("Result limit must be positive.")
    if len(query_vector) != DIMENSIONS or not any(query_vector):
        raise ValueError("Query vector must have 768 dimensions and be nonzero.")
    vector = json.dumps(query_vector, allow_nan=False)

    from psycopg.rows import dict_row

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute("""
            SELECT c.chunk_id, c.snapshot_id, c.text, c.token_count, c.metadata,
                   s.source_id, s.title, s.url,
                   e.embedding <=> %s::vector AS distance
            FROM chunk_embeddings AS e
            JOIN chunks AS c ON c.chunk_id = e.chunk_id
            JOIN source_snapshots AS s ON s.snapshot_id = c.snapshot_id
            WHERE e.index_id = %s
            ORDER BY distance, c.chunk_id
            LIMIT %s
        """, (vector, index_id, limit))
        return cursor.fetchall()
