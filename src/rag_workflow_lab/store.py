"""Raw-SQL database checks and immutable snapshot/chunk storage."""

from dataclasses import dataclass

from rag_workflow_lab.config import DatabaseSettings


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
