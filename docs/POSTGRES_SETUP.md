# Local PostgreSQL + pgvector Compose setup

**Last updated:** 2026-11-08. **Status:** Compose configuration and extension bootstrap
are implemented. Startup, health, vector SQL and volume persistence were
verified in a temporary, separate Compose project, which was then removed.
The persistent project service is started explicitly using the owner's `.env`.
The Python `check-db` command has also passed against that service with
PostgreSQL 18.6, pgvector 0.8.7 and a verified read-only transaction.
Alembic revision `0001` was applied on 2026-11-07; all four retrieval tables
were verified and empty at that check.

**Runtime check, 2026-11-08:** The project container is `exited`, and `check-db`
returned exit code 2. The service was not started in this documentation session.
Start the existing service and inspect its revision before resuming DB work;
the historical verification below does not establish current availability.

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
tables. The Psycopg connection check is implemented; corpus store operations,
sandbox fixtures and MLflow remain separate steps.

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
check below; application storage/search remain future work.

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

Repository `heads`/`history` and database `current` now report revision `0001`.
It was applied on 2026-11-07 following the owner's explicit instruction.
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
functions. ORM metadata/autogeneration are not configured. Apply a prepared revision with:

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python alembic upgrade head
```

Alembic revisions under `migrations/versions/` are the schema history.
Docker's extension bootstrap remains separate. The old comment-only
`sql/retrieval/001_initial.sql` scaffold is preserved and is not executed by Alembic.

## Verification and next step

Compose schema validation passed, including the loopback binding, PG18 volume
path, read-only init mount and rejection of a missing/empty password. A live
check with disposable credentials and a unique project name verified:

1. Healthy PostgreSQL 18 and installed pgvector 0.8.7.
2. A cosine-distance SQL expression using the `vector` type.
3. A test row surviving container recreation with the same named volume.
4. Cleanup of the temporary project's container, network and test volume.

Local verification record:
`outputs/validation/compose-20261106T180311247594Z.json`.
No application chunks, embeddings or evaluation records were imported. Python
code was unchanged in this step; the previous 59-unit-test result is recorded
in STATUS, while this step used Compose and live database checks.

The Python connection/extension check subsequently passed on the persistent
project service with PostgreSQL 18.6, pgvector 0.8.7 and a verified read-only
transaction. All 80 offline unit tests passed, including 11 fake-driver/CLI
checks added for this command. Alembic 1.20.1 and SQLAlchemy 2.1.8 are now
installed and configured. A temporary revision generated valid offline
raw-SQL upgrade/downgrade output. Live `alembic current` passed and left the
public table list unchanged at zero tables during setup. Revision `0001` was
subsequently applied on 2026-11-07. Catalog checks confirmed its four empty
retrieval tables, primary/foreign keys, CHECK constraints and `vector(768)`.

Next implement raw-SQL snapshot/chunk import into the existing tables, then
corpus embedding/indexing and retrieval. See [HANDOFF.md](HANDOFF.md) for the
existing local inputs and resume checks.

Upstream references: [pgvector Docker images](https://github.com/pgvector/pgvector#docker),
[Postgres image data paths and initialization](https://hub.docker.com/_/postgres),
[Compose interpolation](https://docs.docker.com/reference/compose-file/interpolation/),
[Psycopg installation](https://www.psycopg.org/psycopg3/docs/basic/install.html),
[Psycopg connection parameters](https://www.psycopg.org/psycopg3/docs/api/connections.html#psycopg.Connection.connect),
[Psycopg read-only transactions](https://www.psycopg.org/psycopg3/docs/api/connections.html#psycopg.Connection.read_only)
and [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html).
