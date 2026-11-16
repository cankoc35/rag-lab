# RAG Workflow Lab

An exploratory project to build a useful, tool-using Agentic RAG chatbot and learn the engineering behind it. The initial use case is a PostgreSQL documentation and sandbox-database assistant; the final thesis title/question remains open.

## Current status

Pilot preparation is underway. The owner approved PostgreSQL documentation
plus synthetic deployment runbooks as the initial corpus direction, with
frozen sandbox DB state for non-retrieval tools. LLM-only, changed-evidence,
and insufficient-evidence controls will be included. The owner confirmed that
the corpus, questions/datasets, prompts, answers and evaluation text will all
be in English; multilingual support is not required. The Python package and
module scaffold now exist, with a working CLI for config/source checks.
Source loading/validation and explicit single-source HTML downloading are
implemented. All four selected PostgreSQL 18 pages are saved as individual
HTML snapshots with verified hashes; synthetic pilot documents are still
pending. Offline HTML parsing is implemented and all four saved snapshots
have been parsed into source-linked JSON blocks. All 184 blocks have
[token measurements](docs/TOKEN_COUNTS.md) using a pinned candidate tokenizer.
[Section-aware chunking](docs/CHUNKING.md) now produces 49 verified chunks
with a 512-token target and 1024-token ceiling, preserving code and tables.
The [first six development questions](data/evaluation/dev/document_questions.json)
now have source-verified answers and evidence mapped to those chunks.
[Local Nomic embeddings](docs/EMBEDDING_SETUP.md) now work: a pinned model
produces normalized 768-dimensional document/query vectors. A one-chunk,
one-question runtime check and its offline repeat passed. A
[PostgreSQL + pgvector Compose setup](docs/POSTGRES_SETUP.md) is now configured
and passed temporary live checks. The optional Psycopg 3 driver, environment
settings and `check-db` command are implemented. The command passed against
the local service with PostgreSQL 18.6, pgvector 0.8.7 and a verified read-only
transaction. Application tables and raw-SQL snapshot/chunk storage now exist.
The [import script](scripts/import_corpus.py) has committed four snapshots and
49 chunks. Independent field checks and a second import confirmed unchanged
contents and counts.
Alembic is now installed and configured for manually written raw-SQL
migrations. Revision `0001` was applied on 2026-11-07, creating the four
retrieval tables. The DB contains four snapshots, 49 chunks, one embedding
index and 49 vectors.
Embedding index/vector save functions and the [indexing script](scripts/index_corpus.py)
are implemented. Two full 49-chunk runs with real local Nomic inference passed
with identical index IDs/vectors, then rolled back. The owner subsequently
ran the script for a committed index; its vectors match the verification run.
Dense retrieval is implemented: `retrieval.retrieve()` checks index/model
compatibility, embeds a raw question and calls `store.search_chunks()`.
The first six-question diagnostic found annotated evidence in the top five
for five questions; P05's follow-up showed strong query-wording sensitivity.
The repeatable [retrieval checker](scripts/check_retrieval.py) now records
full ranks and annotated evidence hits at 5/10/20. Two real-model runs matched;
P05 has no annotated hits at 5/10 and two of three at 20. A small OpenAI
Responses API client and an opt-in Luna smoke script are implemented; hosted
inference has not run because the API key is not configured. Full
workflow/evaluation runners remain pending.
The [source allowlist](data/corpus/sources.json) now selects four PostgreSQL 18
documentation pages; the statistics page is scoped to `pg_stat_replication`.
The [pilot scope](docs/PILOT_SCOPE.md) contains 20 question records: P01–P06
have a verified development subset; P07–P20 remain drafts.
The [code structure](docs/CODE_STRUCTURE.md) maps that target to shared modules
and staged implementation. All planned module paths have been created at the
owner's request; most modules currently contain responsibility notes only.

**Repository language:** All documentation, source code comments/docstrings,
messages, prompts and data are maintained in English. Turkish is used only
for conversation with the owner, not for repository content.

**Confirmed direction:** The supervisor liked the Agentic RAG thesis direction,
and the project will continue with it. The comparison and adaptive router below
are the current working research question; their exact protocol and final title
remain to be agreed. A draft [method-level design](docs/METHOD_DESIGN.md) is now
available.

For a new session, read the [project context](docs/PROJECT_CONTEXT.md) and
[current status](docs/STATUS.md) to see decisions, open questions, and the
next concrete step. Follow the reading order in [AGENTS.md](AGENTS.md), then
use the [session handoff](docs/HANDOFF.md) for code paths, local artifacts and
resume commands. On 2026-11-12 PostgreSQL was healthy with revision `0001`;
the corpus and its 49 document embeddings are committed. Dense SQL search
and query retrieval passed live checks on 2026-11-14. P05's full ranks and
wording probes and the development cutoff sweep are recorded. Trace/span code
and migration `0002` are applied and verified with one real P04 question.
The Luna client passed offline checks. Run its explicit API smoke after setting
the key, then prepare the evidence-context/answer-prompt contract.
See the [development diagnostic](data/evaluation/dev/README.md#p05-wording-diagnosis).

The [papers reading list](docs/papers/rag-papers/README.md) contains background literature,
not a retrieval corpus or evaluation dataset. The proposed implementation
sequence is documented in the [development roadmap](docs/ROADMAP.md).

## Initial direction

1. Prepare a versioned PostgreSQL documentation snapshot and synthetic deployment runbooks for the chosen pilot use case.
2. Verify the draft pilot questions and their expected answers against the saved sources and sandbox fixtures.
3. Build a simple RAG baseline that retrieves evidence, cites sources, and says when the evidence is insufficient.
4. Add enhanced and agentic workflows in the same project, sharing ingestion, retrieval, model, and tool components where appropriate.
5. Compare the three workflows on answer quality, evidence use, tool behavior, latency, and cost. Use the failures to guide improvements such as hybrid search or reranking.

The pilot questions are for development; keep any eventual thesis test set separate.

**Initial workflow design approved by the owner, 2026-11-13:** Simple uses
dense retrieval followed by one answer call. Enhanced uses dense + PostgreSQL
full-text retrieval, RRF merge/deduplication, reranking and the same answer
setup. Its relevant tool calls follow predefined Python steps. Corpus,
embedding settings, generator/prompt and maximum context token budget are
shared. Agentic details, reranker/generator choices and numeric budgets remain
open; further additions can be considered later. These are design decisions,
not implemented workflows. See the
[operational definitions](docs/METHOD_DESIGN.md#approved-initial-simple-and-enhanced-design).

## Thesis direction

The working study compares simple, enhanced, and Agentic RAG on the same
questions, then tests whether a router can choose a cheaper workflow when
agentic control is unnecessary. Document-only, live-tool, and combined-source
questions are planned. The supervisor has endorsed continuing with Agentic
RAG; the precise research question, corpus snapshot and coverage, tool
contracts, metrics, and quality threshold remain open.

Earlier alternatives were minimum observability for failure localization and
privacy-preserving RAG over Enron. They are background, not active thesis
directions. See [project context](docs/PROJECT_CONTEXT.md) for their history.

## Working adaptive-RAG research question

> For questions requiring documents, live tool data, or both, can a router
> choose among simple, enhanced, and Agentic RAG workflows and achieve
> acceptable answer quality at lower cost and latency than always using
> Agentic RAG?

The proposed contribution is a **controlled empirical comparison of when
agentic control is worth its overhead**. Build all three workflows from shared
components and run them on the same held-out questions. Give enhanced and
agentic workflows comparable access to the relevant tools so that their
difference tests fixed steps versus dynamic, iterative decisions. Treat simple
RAG's lack of live-tool access as an explicit limitation, not a fair
architecture-only failure. Compare a router with always-simple,
always-enhanced, and always-agentic policies; include the router's own cost,
latency, and mistakes. Define the acceptable quality margin before final
testing. Cost reduction without an acceptable quality result is not success.

The question set should distinguish direct document lookup, multi-document
reasoning, live-tool lookup, and questions needing **both** documents and live
data. Record verified answers and required evidence; keep development and
final test questions separate. The initial domain is PostgreSQL; the initial
public-documentation allowlist is selected, while the full corpus, DB tools,
router design, metrics, and quality margin remain open.
An LLM-only control and questions requiring newly authored local facts or
changed DB state will help distinguish prior knowledge from source use.

**Closest literature:** [Ferrazzi et al. (ACL Industry 2026)](https://aclanthology.org/2026.acl-industry.5/)
compare naive, enhanced, and agentic RAG, but their agent has only a retrieval
tool and the cost analysis chiefly compares enhanced with agentic.
[Adaptive-RAG (NAACL 2024)](https://aclanthology.org/2024.naacl-long.389/)
routes among no, single-step, and iterative retrieval;
[MBA-RAG (COLING 2025)](https://aclanthology.org/2025.coling-main.218/)
studies quality-aware, cost-aware retrieval selection; and
[RAGRouter-Bench (2026 preprint)](https://arxiv.org/abs/2602.00296)
compares five retrieval paradigms and routing. Live-source routing is also
studied in [DynaRAG (2026 preprint)](https://arxiv.org/abs/2603.18012)
and document/database routing in
[Learning to Route (2025 preprint)](https://arxiv.org/abs/2510.02388).
Thus, neither routing nor adding a live tool is claimed as a new invention.
The exact contribution must be narrowed after deeper review and demonstrated
by the experiment; a negative result is valid.

The [literature comparison](docs/LITERATURE_GAPS.md) is a source-backed draft
of what close papers tested and which relevant limitations remain. The
[evaluation plan](docs/EVALUATION_PLAN.md) proposes metric and result-recording
rules so every workflow and the router can be measured consistently. Neither
document is a finished review or approved protocol.

## Working stack decisions and open choices

- Python 3.11+ for the application.
- PostgreSQL with pgvector in local Docker Compose for document storage and
  vector search (configured and checked from Python; retrieval tables are created).
- Application database access uses parameterized raw SQL without an ORM.
  Psycopg 3.3.8 is pinned in the optional `database` dependencies and installed
  locally. Environment settings and read-only connection checks are implemented;
  Alembic 1.20.1 handles migrations with SQLAlchemy 2.1.8 used only for migration
  connections. Revision `0001` is applied; snapshot/chunk storage is implemented,
  and both corpus and embeddings are imported. Dense SQL search is implemented;
  query embedding/search orchestration is implemented and locally checked.
- A local embedding model for indexing and retrieval.
- Initial pilot embedding model: `nomic-ai/nomic-embed-text-v1.5`, pinned revision,
  768-dimensional output through Sentence Transformers, CPU float32 initially.
- OpenAI Responses API with `gpt-6-luna` for the initial generator (owner-approved
  implementation, 2026-11-17): reasoning `none`, maximum 1000 output tokens.
  The pinned SDK and smoke script are prepared; no hosted response is verified yet.
- LangGraph for the agentic workflow (chosen; start with the simplest working baseline).
- Project-owned PostgreSQL tracing through Psycopg/raw SQL (owner decision,
  2026-11-16). MLflow is no longer selected. The
  [trace/span code and migration `0002`](docs/TRACING_PLAN.md) are applied.
  A real P04 query committed one verified trace/span; LLM/tool logging follows later.

The corpus snapshot/coverage and exact experimental protocol remain open;
Nomic and Luna are the initial embedding/generator choices. Hosted calls send
prompts and retrieved text to the provider; choose the corpus accordingly.

## Check the Luna API client

Set your own `OPENAI_API_KEY` in the existing Git-ignored `.env`; the empty
entry in `.env.example` documents its name. The SDK reads the environment.
Generator settings live in `configs/pilot.toml`. OpenAI SDK `3.51.0` is pinned
in the optional `generation` extra and the script's separate dependency lock.

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/llm_smoke.py --call-api
```

On a fresh machine, omit `--offline` once to download the locked dependencies.
The script requires `--call-api` and a key before creating a client. It sends
one fixed English test message, with a 30-second timeout, no automatic
retries, Standard processing and `store=False`. The provider's response
storage is disabled; this is not a zero-data-retention guarantee.
The JSON output includes the answer, model/response IDs, completion status,
reported usage, settings, SDK version and elapsed time. Partial or empty
responses exit with code 2; provider errors print only their type.
This checks connectivity, not RAG answer quality. It reads no corpus/dataset
and writes no DB records. Retrieval context, the answer prompt, Simple RAG
and LLM tracing are the next steps.

## Run the scaffold

From the repository root, use Python 3.11+; the current ingestion CLI has no
third-party runtime dependencies and can run directly from the source checkout:

```sh
PYTHONPATH=src python3.11 -m rag_workflow_lab --help
PYTHONPATH=src python3.11 -m rag_workflow_lab check-config --config configs/pilot.toml
PYTHONPATH=src python3.11 -m rag_workflow_lab check-sources --config configs/pilot.toml
```

The config check reads TOML and resolves paths relative to that config file;
it does not validate a populated corpus or connect to models/databases.
`check-sources` reads that allowlist and validates schema version 1,
`status: selected`, required source fields, unique IDs/URLs, versioned official
PostgreSQL HTML URLs, and page/section selection. It prints the validated
records without downloading content. Downloading is an explicit network action:

```sh
PYTHONPATH=src python3.11 -m rag_workflow_lab download-source --source-id PG-EXPLAIN --timeout 30
```

Only that source is fetched, with a finite socket timeout and no redirects.
Each successful call creates a new directory under `data/local/snapshots/`
containing raw HTML and `manifest.json`; previous snapshots are preserved.
The manifest records the source definition, UTC download time, response URL,
HTTP status/type/charset, byte size, SHA-256 and a file path relative to the
manifest directory. This is a single-source snapshot, not the full frozen
corpus. The four current snapshot IDs and hashes are recorded in
[STATUS.md](docs/STATUS.md).

Parse an existing snapshot without network access:

```sh
PYTHONPATH=src python3.11 -m rag_workflow_lab parse-source --source-id PG-EXPLAIN --manifest data/local/snapshots/PG-EXPLAIN-20261102T173311Z-yhdhybna/manifest.json
```

`parse-source` matches the snapshot to the configured source allowlist and
checks the saved byte size/SHA-256 before parsing. It prints JSON without
changing the inputs. The PostgreSQL DocBook parser removes navigation,
TOC, scripts and styles, preserves heading paths, SQL whitespace and table
cells, and applies page/section scope. PG-STATS yields only the selected
replication section, including its table and NULL-lag notes.
Source/snapshot IDs, URL, raw hash, parser version and block anchors are
retained. The four locally generated example outputs are under
`data/local/parsed/` (Git-ignored); these are content blocks, not chunks.
This parser expects the pilot's explicitly closed DocBook HTML structure;
Markdown, arbitrary web layouts and nested content tables are unsupported.

Chunk all four saved snapshots with the cached candidate tokenizer, without
network access or model weights:

```sh
PYTHONPATH=src uv run --offline --no-project --python 3.11 scripts/chunk_corpus.py
```

The [chunking guide](docs/CHUNKING.md) describes the API, counting contract and
output metadata. This development script uses an isolated `tokenizers==0.22.2`
environment and the existing local tokenizer cache. It writes to a new directory
under `data/local/chunks/`; application runtime dependencies remain unchanged.

Check the six development questions' pinned source/chunk references offline:

```sh
python3.11 scripts/check_document_questions.py
```

The [development-data guide](data/evaluation/dev/README.md) describes the
reference answers and evidence alternatives. This check requires saved local
artifacts, uses only the standard library, and performs no model evaluation.

The optional [embedding setup](docs/EMBEDDING_SETUP.md) has an opt-in download
and runtime check. After its first model/dependency download, repeat offline:

```sh
PYTHONPATH=src HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --offline --locked --no-project --python 3.11 scripts/embedding_smoke.py
```

Model weights stay under `data/local/models/`; reports go under
`outputs/embeddings/`. The script embeds one chunk and one raw question;
it does not perform corpus indexing or retrieval evaluation.

Start [PostgreSQL + pgvector](docs/POSTGRES_SETUP.md) after setting the password
in a local `.env` copied from `.env.example`:

```sh
docker compose config --quiet
docker compose up -d --wait postgres
```

Compose uses a pinned image, loopback port, named volume, extension bootstrap
and healthcheck. The [Python database setup](docs/POSTGRES_SETUP.md#python-driver-and-environment-settings)
documents the optional Psycopg installation and `load_database_settings()`.
It reads `POSTGRES_*` from the process environment without connecting; use
`uv run --env-file .env` to load a local file explicitly. After installing the
optional database dependencies, check the connection and installed extension:

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python -m rag_workflow_lab check-db
```

`check-db` runs read-only SQL and prints server/pgvector versions as JSON.
Missing credentials, a missing driver/extension or a DB failure produce exit
code 2; credentials and raw driver errors are omitted from output. The command
does not require the pilot TOML file. Application tables and snapshot/chunk
storage and dense query retrieval exist; hosted generator inference remains pending.
Trace persistence is implemented; migration `0002` and a real retrieval trace are verified.

Alembic reads the same environment settings. Check the current schema revision:

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python alembic current
```

The repository head and applied database revision are both `0002`.
The owner authorized application on 2026-11-16; the two tracing tables and
a real P04 trace/span passed verification. The
[tracing guide](docs/TRACING_PLAN.md) links the migration, writers and results.
The four retrieval tables were verified on 2026-11-07. See the
[migration setup](docs/POSTGRES_SETUP.md#alembic-migrations) for installation
and revision commands. Raw-SQL revisions belong in `migrations/versions/`.

Import the existing saved snapshots and chunks when ready to populate the DB:

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python scripts/import_corpus.py
```

This command **commits** the four snapshots and 49 chunks in one transaction.
It reads the pilot source allowlist, verifies saved HTML/manifests with the
existing parser and checks chunk provenance. It preserves exact embedding
inputs and all remaining chunk fields as JSONB metadata. Identical repeats
are accepted; different contents for an existing ID fail and roll back the
whole import. Printed counts describe processed records, including existing
matches. The command does not generate embeddings or read evaluation data.
Use `--chunks-dir PATH` to select another saved chunk run.

Create the embedding index from **all chunks currently stored in the retrieval DB**:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/index_corpus.py
```

This command **commits** index metadata and document vectors in one transaction.
The current corpus has 49 chunks. It loads cached Nomic weights locally and
uses each exact `embedding_text`, checking its token count before saving.
The chunk/input fingerprint, model revision, normalization/prefix settings,
library versions, model-manifest/lock hashes and code hashes determine the index ID.
Identical repeats reuse that ID and must preserve vectors/counts. The script
has its own [dependency lockfile](scripts/index_corpus.py.lock), retaining the
smoke environment's ML versions and adding Psycopg. Cached dependencies/model
files are required for this offline command. There is no retrieval or generation.
The current pilot index is already committed; no rerun is needed for it.
Progress messages are flushed to stderr during startup, model loading,
each chunk and saving/commit. The final JSON result remains on stdout.

Offline unit tests use the Python standard library:

```sh
PYTHONPATH=src python3.11 -m unittest discover -s tests/unit -v
```

Downloader tests simulate HTTP responses; parser tests use a small synthetic
DocBook fixture; chunking tests use synthetic blocks and a test token counter.
Database settings tests cover defaults, environment overrides, validation and
password handling. DB-check tests use a fake driver for SQL results, resource
cleanup, CLI output and safe failures. Import-input tests verify source checks,
provenance, duplicate IDs and allowlist boundaries. Embedding-storage validation
checks model/revision/dimensions, task and nonfinite values. Index identity tests
cover ordering, exact inputs, configuration changes and visible CLI progress
with a separate JSON result. Search-input checks reject wrong dimensions, zero/
nonfinite vectors and nonpositive result limits. Retrieval checks verify index/
model compatibility and question/vector forwarding. Checker tests cover cutoff
boundaries, missing evidence, raw-question isolation and empty indexes.
All 114 unit tests run offline without a database, driver,
local snapshots, tokenizer packages or models.
Real network verification is run separately with the explicit `download-source`
command; the four saved snapshots were also checked through the offline parser CLI.

Fifteen opt-in storage/indexing/search/retrieval tests require the local DB and applied revision `0001`:

```sh
PYTHONPATH=src RAG_LAB_TEST_DB=1 uv run --offline --no-project --env-file .env --python .venv/bin/python python -m unittest discover -s tests/integration -v
```

Four additional tracing tests require `0002` and passed after its application
on 2026-11-16. They use temporary table clones; a separate one-question check
committed the first trace/span to public tables.

They use temporary tables cloned from the schema, close without committing,
and verify corpus/index/vector round trips, identical/conflicting repeats,
input hashes, index isolation and transaction rollback. Embedding tests use
synthetic vectors and perform no model inference. They also exercise the indexer
with a fake embedder, including empty-corpus and stale-token-count failures.
Search checks verify cosine ranking, result limits, citation metadata, index
isolation and caller-owned transactions. A fake-query-embedding check also
exercises metadata loading and retrieval through real SQL.

The Python API accepts an already loaded model and connection:

```python
from rag_workflow_lab.retrieval import retrieve

matches = retrieve(connection, embedder, index_id, question, limit=5)
```

The caller loads `NomicEmbedder.from_local(settings.embedding)` once and reuses
it. A separate opt-in real-model check ran P01–P06
against the existing index without changing DB data. Its
[diagnostic results](data/evaluation/dev/README.md#first-dense-retrieval-check)
are development observations, not a held-out or answer-quality result.

Repeat the development retrieval check using the existing index:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/check_retrieval.py \
  --index-id nomic-d4a8ebdbce1253c45ea50734d984a14a6258d9f1e7a332fd56964011eb886447
```

This checks pinned dataset references, loads the cached model once, opens a
read-only connection and retrieves each original question once over the full
selected index. It computes annotated evidence hits at 5/10/20 from those
ranks and writes a new JSON report under `outputs/retrieval/`. Phase/question
progress goes to stderr; stdout contains the report path. Its lockfile retains
the indexer's package versions. Cached model/dependencies, source artifacts,
the existing DB and `.env` settings are required. See the
[results and interpretation](data/evaluation/dev/README.md#repeatable-retrieval-checker).

The checker also accepts `--trace` to persist one question trace and retrieval
span per question and link their IDs into the JSON report. Migration `0002` is
now applied, so this mode is available. Without it, the
checker keeps its existing read-only behavior and opens no trace writer. See
[prepared tracing behavior](docs/TRACING_PLAN.md#checker-modes).

## First milestone

Prepare the [pilot sources and expected evidence](docs/PILOT_SCOPE.md), then
implement ingestion and retrieval in the existing scaffold before adding answer
generation. Review the method design with the supervisor in parallel. The
first end-to-end milestone is a CLI that retrieves sources, cites evidence,
and can report insufficient evidence.

## Working principles

- Measure behavior before claiming that the agent improves on basic RAG.
- Keep the simple baseline available for comparison as the system grows.
- Record sources, model and prompt versions, tool calls, failures, latency, and approximate API cost when experiments begin.
- Do not commit API keys, private documents, or sensitive traces.
