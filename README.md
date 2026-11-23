# RAG Workflow Lab

A PostgreSQL documentation and sandbox-database assistant for an Agentic RAG
thesis. The working study compares Simple, Enhanced and Agentic RAG, then an
adaptive router. The final research question and protocol remain open.

Repository content is English; conversation with the owner may be Turkish.
For a new session, follow [AGENTS.md](AGENTS.md), then read
[context](docs/PROJECT_CONTEXT.md), [status](docs/STATUS.md),
[roadmap](docs/ROADMAP.md) and [handoff](docs/HANDOFF.md).

For copyable terminal commands and their options, see the
[command reference](docs/COMMANDS.md).
The [supervisor discussion materials](docs/presentations/2026-11-23/README.md)
contain an annotated pipeline diagram and a one-page project briefing.

## Current status

| Area | Implemented | Remaining |
| --- | --- | --- |
| Corpus | Four PostgreSQL HTML + two Atlas Markdown snapshots; all 61 chunks imported | Sandbox fixtures and changed document states |
| Embeddings / DB | Six snapshots, 61 chunks; separate PostgreSQL/Atlas indexes with 49/12 vectors | Broader corpus coverage |
| Retrieval | Dense search and dataset-selected checks; Atlas positive evidence ranks 1–3 | Hybrid search and reranking |
| Tracing | Applied `0002`; retrieval and LLM spans under one Simple trace | Tool instrumentation and batch reporting |
| Generation | Simple/LLM-only PostgreSQL and Atlas batches compared; Atlas P19 abstention verified | Changed-evidence controls and broader evaluation |
| Evaluation | Ten verified development questions in separate PostgreSQL/Atlas subsets | P10–P18/P20 verification, held-out set and final protocol |

The first dense diagnostic found annotated evidence in the top five for five
of six questions. P05 showed wording sensitivity; these are development
observations, not answer-quality or held-out results. See the
[diagnostic](data/evaluation/dev/README.md#p05-wording-diagnosis).

The first [paired development comparison](docs/LLM_ONLY_COMPARISON.md) found
four Simple and three LLM-only answers meeting recorded requirements. Simple
was more complete on P02/P04, LLM-only on P05; both were partial on P03.
This is one six-question check, not a held-out result.
The synthetic [Atlas inventory](data/corpus/synthetic/atlas_inventory.md) and
[operations policy](data/corpus/synthetic/atlas_operations_policy.md) are now
written with shared state `atlas-docs-v1`. Both were snapshotted and parsed offline.
Their 25 content blocks now form 12 local chunks, all below 512 tokens;
Atlas's two snapshots and 12 chunks are imported and embedded in a separate index.
Its [four-question subset](data/evaluation/dev/atlas_questions.json)
now has verified reference answers, answerability and pinned evidence.
The first Atlas retrieval check found all annotated positive evidence in the
top three. P19 returned Atlas policy text, which does not establish a Boreal
limit. The later [Atlas answer comparison](docs/LLM_ONLY_COMPARISON.md#atlas-source-specific-comparison--2026-11-18)
found two complete Simple answers and one partial P09 (the reporting role is
not explicit); LLM-only abstained on all three answerable questions. Both
abstained on P19 without assigning Boreal a numeric limit.
**Proposed next step:** a separately versioned changed-evidence control.
Enhanced, tools, LangGraph and the router remain unimplemented.
See [STATUS](docs/STATUS.md).

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

Snapshot and parse the two explicitly allowlisted Atlas Markdown documents:

```sh
PYTHONPATH=src .venv/bin/python -m rag_workflow_lab ingest-markdown --sources-manifest data/corpus/synthetic/sources.json
```

This offline command verifies pinned source hashes and writes exact Markdown
copies, manifests and `parsed.json` in a new `data/local/markdown/` run folder.
It preserves headings, prose, tables, SQL and source-line anchors using the
existing block contract. It makes no model/DB calls. The HTML source manifest
and `parse-source` remain unchanged. To measure/chunk a
saved Atlas run, use the same chunk runner with explicit Markdown inputs:

```sh
PYTHONPATH=src uv run --offline --no-project --python 3.11 scripts/chunk_corpus.py \
  --sources-manifest data/corpus/synthetic/sources.json \
  --markdown-run data/local/markdown/atlas-docs-v1-ssme1pql
```

This saves new chunk JSON and per-content-block token counts under
`data/local/chunks/`. The import runner supports both HTML and explicit
Markdown inputs; use the Atlas command below to commit its saved records.

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
The current corpus and original PostgreSQL vectors are already imported. For a new DB, the
following commands **commit** their respective records:

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python scripts/import_corpus.py
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/index_corpus.py
```

Import the two Atlas snapshots and 12 chunks (already committed locally):

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python scripts/import_corpus.py \
  --sources-manifest data/corpus/synthetic/sources.json \
  --markdown-run data/local/markdown/atlas-docs-v1-ssme1pql \
  --chunks-dir data/local/chunks/atlas-docs-v1-section-blocks-v1
```

Imports use one transaction; repeating identical inputs preserves records.
No migration was needed. For local snapshots, the legacy `downloaded_at`
column stores their `captured_at` acquisition time. Importing does not generate
embeddings. Index only Atlas's 12 chunks with the repeatable source filter
(already committed locally):

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/index_corpus.py \
  --source-id LOCAL-INVENTORY --source-id LOCAL-POLICY
```

Without `--source-id`, the indexer selects all stored chunks. A requested
source without chunks fails before inference or writes. Source selection is
recorded in index settings; the original PostgreSQL index/49 vectors are preserved.

The importer validates saved source/chunk provenance and preserves exact
embedding inputs. Identical records are accepted; conflicting IDs roll back
the transaction. Use `--chunks-dir PATH` to select another saved chunk run.
The indexer embeds the selected stored chunks with cached Nomic and records exact
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
To check Atlas's four unchanged questions against its separate index:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/check_retrieval.py \
  --dataset data/evaluation/dev/atlas_questions.json \
  --index-id nomic-b98238adf1e5b69036fc64a756e3171b7459ad8842e8c3ea280fe9a777ad8ddf
```

The selected index must match the dataset's complete pinned chunk/input scope.
P19 has no positive evidence, so hit scoring is N/A; retrieving similar Atlas
text does not answer its Boreal question. This check makes no generator call.
See the [Atlas results](data/evaluation/dev/README.md#atlas-retrieval-diagnostic--2026-11-18).

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
quality, and reads no corpus/dataset or DB. The first live call passed on
2026-11-17; usage and the local report path are in [STATUS](docs/STATUS.md).

## Run Simple RAG

With the existing corpus/index, cached Nomic model, applied `0002` and API key:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/run_simple_rag.py \
  --index-id nomic-d4a8ebdbce1253c45ea50734d984a14a6258d9f1e7a332fd56964011eb886447 --question-id P04 --call-api
```

Replace `--question-id P04` with `--all` to run all questions in dataset order.
The default is the six-question PostgreSQL dataset. For Atlas's four questions:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/run_simple_rag.py \
  --dataset data/evaluation/dev/atlas_questions.json \
  --index-id nomic-b98238adf1e5b69036fc64a756e3171b7459ad8842e8c3ea280fe9a777ad8ddf --all --call-api
```

The index must match the selected dataset's complete pinned chunk/input scope;
wrong scope fails before model loading, trace writes or paid calls.
Select exactly one question mode; unknown IDs fail before
loading the model or opening DB/API clients. The former `simple_rag_smoke.py`
and its lockfile were renamed to `run_simple_rag.py` and its matching lockfile.

This **makes one paid request per question and writes traces**. `--offline` only prevents
dependency downloads; it does not block the API. On a fresh machine, omit it
once to install locked dependencies. The model is loaded once and DB/API
clients are reused. For each question, the runner retrieves five whole chunks
and labels them S1–S5. Only the raw question and
retrieved evidence enter Luna's input; gold stays outside generation.
`answer_v1.md` requests cited answers or insufficient-evidence responses.

Each question gets a `simple` trace with retrieval and LLM spans; traces share
the batch `run_id`. The LLM span stores the exact
instructions/input, label-to-source map, response and reported usage. Unknown
cost remains NULL. Partial/empty answers fail explicitly. The client uses the
same timeout/retry/settings policy as the connectivity smoke.
The schema-version-2 JSON report under `outputs/answers/` contains a `questions`
list with each answer, sources, usage, duration and trace ID. Reports do not
overwrite older runs; exact prompts are in PostgreSQL. A returned incomplete
answer is saved and makes the exit code 2. Provider/DB exceptions stop the
batch without retries; existing autocommitted traces remain inspectable, but
that interrupted batch has no final JSON report. No automatic grading is added.

The first P04 call passed a post-run editorial check on
2026-11-17. This single development check does not establish overall quality
or isolate prior knowledge. A later six-question batch completed with four
answers meeting recorded requirements and two partial answers (P03/P05),
based on post-run editorial review. See [development results](data/evaluation/dev/README.md#first-simple-answer-batch).
See [tracing](docs/TRACING_PLAN.md).

## Run the LLM-only control

Use the same questions and Luna settings, with an own-knowledge prompt and
no retrieved evidence. This **makes paid calls and writes traces**:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/run_llm_only.py --all --call-api
```

Replace `--all` with `--question-id P01` to select one question. No index or
embedding model is needed; PostgreSQL is used only for logging. Each question
gets one `llm_only` trace and one LLM span, with no sources/tools/history.
The raw question is unchanged. `llm_only_v1` permits the model's prior knowledge
and labels the task PostgreSQL 18; no question-specific facts are added.
Simple's prompt is preserved. Reports go to `outputs/answers/llm-only-*.json`.
The first live control batch completed and was independently verified;
see the [paired comparison](docs/LLM_ONLY_COMPARISON.md).
See the [options and comparison notes](docs/COMMANDS.md#llm-only-control).

For the unchanged Atlas questions, add
`--dataset data/evaluation/dev/atlas_questions.json`. Only raw question text
enters generation; corpus files and evaluation gold are not used as context.
Both runners record the selected dataset path/hash. The first four-question
Atlas comparison completed; see the [results](docs/LLM_ONLY_COMPARISON.md#atlas-source-specific-comparison--2026-11-18).

## Verification

Default tests need no API, DB, model or local corpus:

```sh
PYTHONPATH=src python3.11 -m unittest discover -s tests/unit -v
```

Check pinned question evidence separately; this needs saved artifacts but no model:

```sh
python3.11 scripts/check_document_questions.py
python3.11 scripts/check_document_questions.py --dataset data/evaluation/dev/atlas_questions.json
```

The default remains the unchanged P01–P06 PostgreSQL baseline. The separate
Atlas subset contains P07–P09 and P19; its last case has no positive answer
evidence. The diagnostic and both answer runners support `--dataset`; omission
retains the PostgreSQL baseline. These reference checks make no model/DB calls.

DB tests are opt-in and use temporary tables/synthetic vectors. They require
the local DB and applied `0002`, and leave public records unchanged:

```sh
PYTHONPATH=src RAG_LAB_TEST_DB=1 uv run --offline --no-project --env-file .env --python .venv/bin/python python -m unittest discover -s tests/integration -v
```

Current test counts and verification limits are in [STATUS](docs/STATUS.md).
Paid calls and downloads remain explicit. Record sources, versions, failures,
latency and cost before claiming improvements; keep secrets and private traces
outside Git. The one-question Simple path is implemented; broader answer and
abstention behavior still need real development checks.
