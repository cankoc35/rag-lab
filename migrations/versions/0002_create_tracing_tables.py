"""Create question traces and operation spans using raw SQL."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE traces (
            trace_id UUID PRIMARY KEY,
            run_id TEXT,
            question_id TEXT,
            workflow TEXT NOT NULL,
            question TEXT NOT NULL,
            started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
            finished_at TIMESTAMPTZ,
            status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'ok', 'error')),
            final_answer TEXT,
            configuration JSONB NOT NULL DEFAULT '{}',
            error JSONB,
            CHECK ((status = 'running') = (finished_at IS NULL)),
            CHECK (finished_at >= started_at)
        )
    """)
    op.execute("CREATE INDEX traces_run_id_idx ON traces (run_id, started_at)")
    op.execute("""
        CREATE TABLE spans (
            span_id UUID PRIMARY KEY,
            trace_id UUID NOT NULL REFERENCES traces (trace_id),
            parent_span_id UUID,
            kind TEXT NOT NULL,
            name TEXT NOT NULL,
            started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
            finished_at TIMESTAMPTZ,
            status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'ok', 'error')),
            inputs JSONB NOT NULL,
            outputs JSONB,
            usage JSONB,
            cost JSONB,
            error JSONB,
            UNIQUE (trace_id, span_id),
            FOREIGN KEY (trace_id, parent_span_id) REFERENCES spans (trace_id, span_id),
            CHECK (parent_span_id IS DISTINCT FROM span_id),
            CHECK ((status = 'running') = (finished_at IS NULL)),
            CHECK (finished_at >= started_at)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE spans")
    op.execute("DROP TABLE traces")
