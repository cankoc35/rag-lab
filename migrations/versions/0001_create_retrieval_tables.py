"""Create retrieval tables"""

from alembic import op

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("""
        CREATE TABLE source_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            downloaded_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE chunks (
            chunk_id TEXT PRIMARY KEY,
            snapshot_id TEXT NOT NULL REFERENCES source_snapshots (snapshot_id),
            text TEXT NOT NULL,
            embedding_text TEXT NOT NULL,
            token_count INTEGER NOT NULL CHECK (token_count > 0),
            metadata JSONB NOT NULL DEFAULT '{}'
        )
    """)
    op.execute("""
        CREATE TABLE embedding_indexes (
            index_id TEXT PRIMARY KEY,
            model_id TEXT NOT NULL,
            model_revision TEXT NOT NULL,
            dimensions INTEGER NOT NULL CHECK (dimensions = 768),
            chunk_set_sha256 TEXT NOT NULL,
            settings JSONB NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE chunk_embeddings (
            index_id TEXT NOT NULL REFERENCES embedding_indexes (index_id),
            chunk_id TEXT NOT NULL REFERENCES chunks (chunk_id),
            input_sha256 TEXT NOT NULL,
            embedding vector(768) NOT NULL,
            PRIMARY KEY (index_id, chunk_id)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE chunk_embeddings")
    op.execute("DROP TABLE embedding_indexes")
    op.execute("DROP TABLE chunks")
    op.execute("DROP TABLE source_snapshots")
