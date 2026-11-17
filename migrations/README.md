# Database migrations

Alembic manages schema versions. Write raw SQL inside `upgrade()` and
`downgrade()` with `op.execute()`. Application queries use Psycopg without an ORM.

The environment reads `POSTGRES_*` through `load_database_settings()`;
load your local `.env` explicitly with `uv run --env-file .env`.
SQLAlchemy is used only for migration connections. ORM metadata and
autogeneration are not configured.

Revision files belong in `migrations/versions/`. The existing
`sql/retrieval/000_extensions.sql` remains Docker's extension bootstrap;
the comment-only `001_initial.sql` is an earlier scaffold, not an Alembic revision.

Revision [0001](versions/0001_create_retrieval_tables.py) was applied on
2026-11-07. It creates the four retrieval tables and enables `vector` if absent.
Downgrade removes the tables in reverse dependency order and keeps `vector`,
which may already belong to the Docker bootstrap or other database objects.

`chunks.metadata` preserves heading/anchor/block information and chunking/
tokenizer provenance from the existing chunk artifacts. `embedding_indexes.settings`
records adapter, prefix, normalization and runtime settings. Its
`chunk_set_sha256` identifies the fixed collection of chunk IDs and input hashes.
Current vector storage is fixed at 768 dimensions.

Local Markdown import reuses this schema. The legacy `downloaded_at` column
stores the source acquisition time: HTTP download time for official docs and
the manifest's `captured_at` for local Atlas snapshots. Atlas import needed no
new migration; repository/database head remains `0002`.

Application was explicitly authorized by the owner; database revision, tables,
keys and vector dimensions were verified. The tables were initially empty;
the later corpus import/indexing populated them.

Revision [0002](versions/0002_create_tracing_tables.py) was applied on
2026-11-16 following the owner's instruction, superseding the prior review hold.
It adds question `traces` and operation `spans` with JSONB payloads, lifecycle
checks and parent-span isolation. Repository/database revisions are both `0002`.
Four tracing DB tests passed and one real P04 retrieval trace/span is committed
and verified. Corpus/index records are unchanged. See the
[tracing guide](../docs/TRACING_PLAN.md) for code, tests and verification details.

See [the setup guide](../docs/POSTGRES_SETUP.md#alembic-migrations) for commands.
