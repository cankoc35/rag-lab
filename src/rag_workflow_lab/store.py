"""Explicit PostgreSQL checks; corpus storage and vector search remain pending."""

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
