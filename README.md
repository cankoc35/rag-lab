# RAG Workflow Lab

A PostgreSQL documentation and sandbox-database assistant for an Agentic RAG
thesis. The working study compares Simple, Enhanced and Agentic RAG, then an
adaptive router. The final research question and protocol remain open.

Repository content is English; conversation with the owner may be Turkish.
For a new session, follow [AGENTS.md](AGENTS.md), then read
[context](docs/PROJECT_CONTEXT.md), [status](docs/STATUS.md),
[roadmap](docs/ROADMAP.md) and [handoff](docs/HANDOFF.md).

## Current status

| Area | Implemented | Remaining |
| --- | --- | --- |
| Corpus | Four PostgreSQL 18 HTML snapshots; parsing and 49 section-aware chunks | Synthetic runbooks and sandbox fixtures |
| Embeddings / DB | Pinned local Nomic, 768 dimensions; four snapshots, 49 chunks, one index/49 vectors | Broader corpus coverage |
| Retrieval | Dense search, query embedding and repeatable P01–P06 checker at 5/10/20 | Hybrid search and reranking |
| Tracing | Applied revision `0002`; verified retrieval trace/span | LLM and tool instrumentation |
| Generation | Luna Responses API client and locked opt-in smoke | API key/live smoke, context/prompt and answer workflow |
| Evaluation | Six source-verified development questions out of 20 pilot records | P07–P20 verification, held-out set and final protocol |

The first dense diagnostic found annotated evidence in the top five for five
of six questions. P05 showed wording sensitivity; these are development
observations, not answer-quality or held-out results. See the
[diagnostic](data/evaluation/dev/README.md#p05-wording-diagnosis).

**Next:** Set `OPENAI_API_KEY`, run the Luna smoke, then build one source-cited
P04 answer. Full workflows, tools, LangGraph orchestration and the router are
not implemented. Current checks and dated evidence are in [STATUS](docs/STATUS.md).

## Working design

- **Simple:** one dense retrieval pass, then one answer call.
- **Enhanced:** dense + PostgreSQL full-text search, RRF merge/deduplication,
  reranking and the same answer setup. Relevant tools follow fixed Python steps.
- **Agentic:** comparable tool access with dynamic decisions; details deferred.

Share corpus/chunks, dense embedding settings, generator/settings, answer
prompt and maximum context budget. Keep development and final-test sets
separate. Include LLM-only, changed-evidence and insufficient-evidence controls.

The proposed router comparison asks whether acceptable quality can be retained
at lower cost/latency than always using Agentic RAG. Relevant tool access,
router overhead and a predefined quality margin must be controlled. No novelty
or performance advantage is claimed. See the [method](docs/METHOD_DESIGN.md),
[evaluation draft](docs/EVALUATION_PLAN.md) and [literature review](docs/LITERATURE_GAPS.md).
The [papers](docs/papers/rag-papers/README.md) are background, not the retrieval corpus.

## Stack

Python 3.11+, PostgreSQL + pgvector in Docker, parameterized Psycopg SQL and
raw-SQL Alembic migrations. SQLAlchemy is migration infrastructure only.
Nomic Embed Text v1.5 runs locally; OpenAI `gpt-6-luna` is the initial generator
with reasoning `none` and a 1000-output-token limit. LangGraph is selected for
later agentic work. Project-owned PostgreSQL tracing replaces MLflow.
Dependency pins are in [pyproject.toml](pyproject.toml) and script lockfiles.

## Run the scaffold

Run from the repository root. Ingestion checks use the standard library:

```sh
PYTHONPATH=src python3.11 -m rag_workflow_lab --help
PYTHONPATH=src python3.11 -m rag_workflow_lab check-config --config configs/pilot.toml
PYTHONPATH=src python3.11 -m rag_workflow_lab check-sources --config configs/pilot.toml
```

`check-config` validates TOML paths/settings; `check-sources` validates the
allowlist. Neither connects to a database/model nor downloads documents.
Download one selected source explicitly, then parse its saved snapshot offline:

```sh
PYTHONPATH=src python3.11 -m rag_workflow_lab download-source --source-id PG-EXPLAIN --timeout 30
PYTHONPATH=src python3.11 -m rag_workflow_lab parse-source --source-id PG-EXPLAIN --manifest data/local/snapshots/PG-EXPLAIN-20261102T173311Z-yhdhybna/manifest.json
```

Each download preserves previous snapshots. The parser verifies source/hash
metadata and preserves headings, SQL and tables within the selected scope.
The pilot already has four pinned snapshots; fresh downloads may invalidate
its evidence references. Snapshot IDs/hashes are in [STATUS](docs/STATUS.md).

Chunk the saved snapshots with the cached tokenizer, or check one local
embedding pair after its explicit initial setup:

```sh
PYTHONPATH=src uv run --offline --no-project --python 3.11 scripts/chunk_corpus.py
PYTHONPATH=src HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --offline --locked --no-project --python 3.11 scripts/embedding_smoke.py
```

See [chunking](docs/CHUNKING.md), [token measurements](docs/TOKEN_COUNTS.md) and
[embedding setup](docs/EMBEDDING_SETUP.md) for contracts and first-time downloads.
New chunk runs and embedding reports preserve existing artifacts. Model files,
`data/local/`, `outputs/`, `.env` and `.venv` are Git-ignored.

### PostgreSQL and corpus

Copy `.env.example` to `.env` if needed and set a local password. Follow the
[database guide](docs/POSTGRES_SETUP.md) for dependency/migration setup. Python
reads process environment variables; `uv --env-file` loads `.env` explicitly.

```sh
docker compose config --quiet
docker compose up -d --wait postgres
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python -m rag_workflow_lab check-db
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python alembic current
```

`check-db` is read-only. The existing project DB and repository head are `0002`;
see [migrations](migrations/README.md) and [tracing](docs/TRACING_PLAN.md).
The current corpus and vectors are already imported. For a new DB, the
following commands **commit** their respective records:

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python scripts/import_corpus.py
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/index_corpus.py
```

The importer validates saved source/chunk provenance and preserves exact
embedding inputs. Identical records are accepted; conflicting IDs roll back
the transaction. Use `--chunks-dir PATH` to select another saved chunk run.
The indexer embeds every stored chunk with cached Nomic and records exact
inputs/model/runtime fingerprints. Both print JSON results without reading
gold data; the indexer also streams progress. Index identity includes code
hashes; an unnecessary rerun after a source change can create a new index identity.

### Retrieval diagnostic

Reuse the committed index:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/check_retrieval.py \
  --index-id nomic-d4a8ebdbce1253c45ea50734d984a14a6258d9f1e7a332fd56964011eb886447
```

This validates pinned references, loads Nomic once and obtains full ranks in a
read-only transaction. Annotated evidence hits at 5/10/20 and provenance go to
`outputs/retrieval/`; progress goes to stderr and the report path to stdout.
Add `--trace` for a separate autocommit writer and one trace/span per question;
without it no trace records are written. See [checker modes](docs/TRACING_PLAN.md#checker-modes).

For application code, load the model once and pass a caller-owned connection:

```python
from rag_workflow_lab.retrieval import retrieve

matches = retrieve(connection, embedder, index_id, question, limit=5)
```

## Check the Luna API client

Set `OPENAI_API_KEY` in your existing Git-ignored `.env`. Generator settings
are in `configs/pilot.toml`; OpenAI SDK `3.51.0` is pinned in the optional
`generation` extra and the script's separate lockfile.

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/llm_smoke.py --call-api
```

Omit `--offline` once on a fresh machine to download locked dependencies.
The script requires `--call-api` and a key, then sends one fixed English
message with a 30-second timeout, zero retries, Standard processing and
`store=False`. Disabling response storage is not a zero-data-retention guarantee.
JSON output contains text, completion status, model/response IDs, usage,
settings, SDK version and elapsed time. Partial/empty replies return exit code
2; provider errors print only their type. This tests connectivity, not RAG
quality, and reads no corpus/dataset or DB. No hosted call is verified yet.

## Verification

Default tests need no API, DB, model or local corpus:

```sh
PYTHONPATH=src python3.11 -m unittest discover -s tests/unit -v
```

Check pinned question evidence separately; this needs saved artifacts but no model:

```sh
python3.11 scripts/check_document_questions.py
```

DB tests are opt-in and use temporary tables/synthetic vectors. They require
the local DB and applied `0002`, and leave public records unchanged:

```sh
PYTHONPATH=src RAG_LAB_TEST_DB=1 uv run --offline --no-project --env-file .env --python .venv/bin/python python -m unittest discover -s tests/integration -v
```

Current test counts and verification limits are in [STATUS](docs/STATUS.md).
Paid calls and downloads remain explicit. Record sources, versions, failures,
latency and cost before claiming improvements; keep secrets and private traces
outside Git. The first end-to-end milestone is a CLI that cites retrieved
sources and can report insufficient evidence.
