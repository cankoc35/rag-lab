# Local PostgreSQL + pgvector Compose setup

**Updated:** 2026-11-18. Compose, extension bootstrap and raw-SQL Alembic
migrations are implemented. The current service passed read-only `check-db`
with PostgreSQL 18.6 + pgvector 0.8.7; revision is `0002`. Six snapshots,
61 chunks and two separate indexes/61 vectors are committed: 49 PostgreSQL,
12 Atlas. The original PostgreSQL index/vectors are preserved. Dense query retrieval and
retrieval/LLM tracing are verified with one Simple P04 answer; the Luna
connectivity smoke also passed.
See [STATUS](STATUS.md) for checks and [history](STATUS_HISTORY.md) for earlier
setup, import, rollback and indexing records. Recheck service state when resuming.

## Configuration

[compose.yaml](../compose.yaml) defines one `postgres` service:

- PostgreSQL 18 with pgvector 0.8.7, using `pgvector/pgvector:0.8.7-pg18-trixie`.
  The multi-architecture image digest is pinned in the file for reproducibility;
  the tag supports native ARM64 and AMD64.
- Database `rag_workflow_lab` and user `rag_lab` by default.
- Host binding `127.0.0.1:5432`; `POSTGRES_PORT` changes the host port.
- A required, nonempty `POSTGRES_PASSWORD` from the local environment/`.env`.
  The committed [.env.example](../.env.example) documents the variables;
  set your local password in `.env`.
- A project-scoped named volume, `rag-workflow-lab_postgres_data`, mounted at
  `/var/lib/postgresql`, the data-volume location for PostgreSQL 18 images.
- A read-only [000_extensions.sql](../sql/retrieval/000_extensions.sql) mount
  that enables `vector` when initializing a new, empty volume. A missing host
  SQL file fails rather than creating an empty directory in its place.
- A TCP `pg_isready` healthcheck, so initial socket-only setup does not count
  as final readiness. Graceful shutdown gets 30 seconds.

Python and the local embedding model run on the Mac. This Docker bootstrap
creates only the `vector` extension; Alembic subsequently creates retrieval
tables. The Psycopg connection check and snapshot/chunk storage are implemented,
and the corpus and embeddings are imported. Project-owned trace tables are
applied and one P04 trace/span is verified; sandbox fixtures remain separate work.
MLflow was rejected by the
owner on 2026-11-16; see [TRACING_PLAN.md](TRACING_PLAN.md).

## Python driver and environment settings

Application database access uses raw SQL without an ORM. The optional
`database` extra pins `psycopg[binary]==3.3.8`; binary wheels include the client
libraries needed by the driver. The `migrations` extra pins Alembic 1.20.1
and SQLAlchemy 2.1.8. Install the database tooling into a local environment:

```sh
uv venv --python python3.11 .venv
uv pip install --python .venv/bin/python --requirements pyproject.toml --extra database --extra migrations --default-index https://pypi.org/simple
```

The dependency install does not install the project itself; run from the
source checkout with `PYTHONPATH=src`. Locally verified versions are Psycopg
3.3.8, psycopg-binary 3.3.8 and typing-extensions 4.16.0 on Python 3.11.15.
SQLAlchemy is used only by Alembic; application queries use Psycopg directly.

`load_database_settings()` in [config.py](../src/rag_workflow_lab/config.py)
reads these process-environment variables when explicitly called:

| Variable | Default / requirement |
| --- | --- |
| `POSTGRES_HOST` | `127.0.0.1` for Python running on the Mac |
| `POSTGRES_PORT` | `5432`; integer from 1 through 65535 |
| `POSTGRES_DB` | `rag_workflow_lab` |
| `POSTGRES_USER` | `rag_lab` |
| `POSTGRES_PASSWORD` | Required, nonempty; no default |
| `POSTGRES_CONNECT_TIMEOUT` | `5` seconds; positive 32-bit integer |

The loader rejects blank values and NUL characters. Password punctuation and
surrounding whitespace are preserved; Psycopg receives separate keyword
arguments rather than a constructed URL. The settings repr excludes the
password. `connect_kwargs()` includes credentials for Psycopg connection
call and must not be logged or serialized into run artifacts.

Python does not load `.env` automatically. After setting up your local `.env`,
load it explicitly to inspect settings with the password omitted:

```sh
PYTHONPATH=src uv run --no-project --env-file .env --python .venv/bin/python python -c "from rag_workflow_lab.config import load_database_settings; print(load_database_settings())"
```

This reads configuration only, without opening a DB connection. Existing
ingestion/config commands continue to work without DB credentials. URL-style
retrieval/sandbox settings remain reserved; the current loader reads only the
six variables above. `check-db` uses these settings for the explicit connection
check below; corpus import and vector search use the same settings.

## Start the project service

With Docker running, use the repository root:

```sh
cp -n .env.example .env
chmod 600 .env
```

Set `POSTGRES_PASSWORD` in `.env` to a nonempty local password. Keep an existing
`.env` if already configured. `POSTGRES_DB`, `POSTGRES_USER` and `POSTGRES_PORT`
can also be adjusted there; use another host port if 5432 is already occupied.
For Python, use the explicit environment loader described above.

```sh
docker compose config --quiet
docker compose up -d --wait postgres
docker compose ps
```

The quiet validation command avoids printing the resolved environment values.
Compose reads `.env` automatically; it is excluded from Git. The named volume
stores database data outside the repository and survives container recreation.

### Check the Python connection

With the optional driver installed and the service running, use:

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python -m rag_workflow_lab check-db
```

The command loads environment settings without requiring `configs/pilot.toml`.
`cli.py` calls `store.check_database()` to run three raw-SQL checks:

1. `SELECT 1` must return the expected connectivity result.
2. The server reports its version and confirms `transaction_read_only = on`.
3. A parameterized `pg_catalog.pg_extension` query finds extension `vector`.

Success returns exit code 0 and JSON with `status: "ok"`,
`postgresql_version`, `pgvector_version` and `read_only: true`. The local
live check reported PostgreSQL 18.6 and pgvector 0.8.7; the command reports
installed versions rather than enforcing those exact version strings.
Each SQL statement has a five-second timeout; connection timeout comes from
the settings above. Connection/cursor contexts close after success or failure.

Missing settings, unavailable Psycopg, a missing `vector` extension or driver
failure produce exit code 2 and an English error on stderr. Output omits
credentials and raw driver errors. This command performs no schema/data
mutations; migrations and corpus storage/search are separate steps.

Open a database shell using the container's configured user/database:

```sh
docker compose exec postgres sh -c 'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Then check pgvector:

```sql
SELECT extversion FROM pg_extension WHERE extname = 'vector';
```

Expected extension version: `0.8.7`. Exit psql with `\q`. To stop the service
while retaining its volume:

```sh
docker compose stop postgres
```

Image initialization scripts and `POSTGRES_*` bootstrap settings apply when
creating an empty database volume. Later schema changes must be applied as
explicit migrations; modifying the mounted SQL does not rerun it on existing
data, and changing the `.env` password does not rotate an existing DB password.

## Alembic migrations

[alembic.ini](../alembic.ini) points to [migrations/](../migrations/README.md).
Its `env.py` reuses `load_database_settings()` and builds the connection URL
in memory, preserving password punctuation without putting credentials in
the INI file. Python still needs the explicit `.env` loading shown below.

Check the connected database's current revision:

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python alembic current
```

Repository head and database `current` are both `0002`.
Revision `0001` was applied on 2026-11-07 following the owner's instruction.
The owner authorized `0002` on 2026-11-16. It adds `traces`/`spans`; four tracing
DB tests and one real P04 trace/span passed. The earlier review hold is lifted.
The opt-in checker `--trace` mode is available. See [TRACING_PLAN.md](TRACING_PLAN.md).
A successful `current` exits with code 0 and inspects the revision without
applying migrations.

The [initial revision](../migrations/versions/0001_create_retrieval_tables.py)
contains the four table definitions, keys, JSONB metadata and `vector(768)`.
It enables `vector` if needed; downgrade keeps that shared extension.
The four tables were created and verified; their initial row counts are zero.
Preview its SQL without connecting to a database:

```sh
POSTGRES_PASSWORD=offline-preview .venv/bin/alembic upgrade 0001 --sql
POSTGRES_PASSWORD=offline-preview .venv/bin/alembic downgrade 0001:base --sql
```

The revision passed offline rendering and PostgreSQL syntax parsing, followed
by live application and catalog checks on 2026-11-07. Generated previews are under
`outputs/validation/retrieval-schema-0001/`.

For a later schema change, create another revision:

```sh
.venv/bin/alembic revision -m "Describe schema change"
```

Write raw SQL using `op.execute()` inside its `upgrade()` and `downgrade()`
functions. ORM metadata/autogeneration are not configured. Revision `0002`
was applied with the owner's authorization using:

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python alembic upgrade 0002
```

Alembic revisions under `migrations/versions/` are the schema history.
Docker's extension bootstrap remains separate. The old comment-only
`sql/retrieval/001_initial.sql` scaffold is preserved and is not executed by Alembic.

## Atlas document import

Atlas snapshot/chunk import uses the same raw-SQL writers and one transaction:

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python scripts/import_corpus.py \
  --sources-manifest data/corpus/synthetic/sources.json \
  --markdown-run data/local/markdown/atlas-docs-v1-ssme1pql \
  --chunks-dir data/local/chunks/atlas-docs-v1-section-blocks-v1
```

The owner-authorized run added two snapshots/12 chunks and was repeated with
identical logical row fingerprints. Local `captured_at` is stored in the legacy
`source_snapshots.downloaded_at` acquisition column; no migration was needed.
Snapshot metadata remains in the immutable local manifests, and exact chunk
fields are preserved in the DB columns/JSONB. No embeddings are generated here.
All 181 offline unit tests and 22 temporary-table DB integration tests passed;
independent read-back verified all Atlas fields and unchanged older records.
Record: `outputs/validation/atlas-import-20261118.json`.

The later source-filtered Nomic run committed Atlas's 12 vectors in a separate
index, preserving all earlier rows. Totals are now two indexes/61 vectors;
revision remains `0002`. All 181 unit/24 DB tests passed. Index IDs, commands
and read-back evidence are in [STATUS](STATUS.md) and [COMMANDS](COMMANDS.md).

## Embedding storage functions

[store.py](../src/rag_workflow_lab/store.py) now provides
`save_embedding_index(connection, index)` for model/revision, dimensions,
chunk-set hash and settings, and `save_embeddings(connection, index_id, embeddings)`
for `(chunk_id, EmbeddingResult)` pairs. The caller owns the connection and
transaction, including rollback of an index and its vectors on failure.

The functions accept identical repeats and reject conflicting payloads.
Vector writes check model/revision/dimensions, document task, finite values
and the SHA-256 of the stored `embedding_text`. Vector text is passed as a
bound parameter and cast to `vector`, using the existing Psycopg dependency.
The checks passed with synthetic vectors in temporary tables: 89 offline tests
and eight opt-in DB tests. At that earlier check, public tables contained four
snapshots, 49 chunks and zero embedding indexes/vectors. The corpus indexing
script is now implemented and the owner completed its committed run. One index
and 49 vectors are present. Dense SQL search is now implemented below.

## Dense search function

`search_chunks(connection, index_id, query_vector, limit=5)` in
[store.py](../src/rag_workflow_lab/store.py) runs a parameterized SELECT using
pgvector's [cosine-distance operator](https://github.com/pgvector/pgvector#querying).
Lower distance ranks first, with chunk ID breaking ties. It returns dictionaries
containing chunk/snapshot/source IDs, text, token count, metadata, title/URL and
`distance`. The caller supplies the selected index's query vector and owns the
connection/transaction. The function neither writes nor commits. Empty/unknown
indexes return no matches; invalid vector dimensions, zero/nonfinite vectors
and nonpositive limits fail. The default limit is an API convenience, not a
frozen experimental setting. No migration or new dependency is needed.

All 96 offline unit tests and 14 opt-in DB tests passed on 2026-11-14. New checks
cover ranking/limits, source metadata, index isolation and transaction ownership.
The public corpus/index fingerprints were unchanged. A read-only self-search
using an existing document vector also passed; no model inference or P01–P06
evaluation was performed. Record: `outputs/validation/dense-search-2026-11-14.json`.
The subsequent query retrieval step below uses this search.

## Query retrieval

`get_embedding_index(connection, index_id)` reads the chosen index metadata
and raises `ValueError` for an unknown ID. `retrieve(connection, embedder,
index_id, question, limit=5)` in [retrieval.py](../src/rag_workflow_lab/retrieval.py)
uses it to check model/revision/dimensions and embedding settings before calling
the existing query adapter and dense search. The caller loads the model once,
reuses it across questions and owns the DB connection/transaction. No SQL writes,
model loading or gold reads occur inside `retrieve()`.

On 2026-11-14, 101 offline unit tests and 15 opt-in DB tests passed. A separate
real-model P01–P06 diagnostic used read-only access to the existing index;
public records/counts were unchanged. P05's annotated evidence is absent from
the top five, so inspect its ranking before widening retrieval/answer tests.
See the [diagnostic table](../data/evaluation/dev/README.md#first-dense-retrieval-check)
and local report `outputs/validation/query-retrieval-2026-11-14.json`.

## Verification and next step

On 2026-11-17, all 19 DB integration tests passed using temporary tables and
synthetic vectors; no model inference or production writes are part of them.
The public counts/fingerprints are checked in the general review record linked
from STATUS. Initial Compose checks separately verified startup, vector SQL
and volume persistence in a temporary project; the detailed records remain
in STATUS_HISTORY.

The Simple P04 check passed with
retrieval and LLM spans under one trace. Existing `0002` columns hold the exact
prompt, source map, output and usage; no new migration was needed. The corpus/index
need no rerun for broader Simple answer checks using the
[prepared runner](../README.md#run-simple-rag). Import/index/retrieval commands are in
[README](../README.md#postgresql-and-corpus); local paths and model settings
are in [HANDOFF](HANDOFF.md).

Upstream references: [pgvector Docker images](https://github.com/pgvector/pgvector#docker),
[Postgres image data paths and initialization](https://hub.docker.com/_/postgres),
[Compose interpolation](https://docs.docker.com/reference/compose-file/interpolation/),
[Psycopg installation](https://www.psycopg.org/psycopg3/docs/basic/install.html),
[Psycopg connection parameters](https://www.psycopg.org/psycopg3/docs/api/connections.html#psycopg.Connection.connect),
[Psycopg read-only transactions](https://www.psycopg.org/psycopg3/docs/api/connections.html#psycopg.Connection.read_only)
and [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html).
