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
transaction. Application tables now exist; corpus storage operations remain pending.
Alembic is now installed and configured for manually written raw-SQL
migrations. Revision `0001` was applied on 2026-11-07, creating the four
retrieval tables; their initial contents are empty.
Retrieval, generator calls and workflow/evaluation runners are not implemented.
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
resume commands. On 2026-11-08 the PostgreSQL container was stopped; the applied
schema above is the last verified database state, not a current health check.

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
  connections. Revision `0001` is applied; application storage/search remain pending.
- A local embedding model for indexing and retrieval.
- Initial pilot embedding model: `nomic-ai/nomic-embed-text-v1.5`, pinned revision,
  768-dimensional output through Sentence Transformers, CPU float32 initially.
- Local open-source and affordable hosted LLMs are both under consideration for generation and tool calling; providers and exact models are TBD. A weak local model should not obscure system-level improvements.
- LangGraph for the agentic workflow (chosen; start with the simplest working baseline).
- Self-hosted MLflow for tracing, with PostgreSQL as its backend store (chosen; not set up yet). A tracing platform is not itself the research contribution.

The corpus snapshot/coverage, LLM provider/models, and exact experimental
protocol remain open; a local embedding model is installed, while the generator remains unselected. Using a hosted model may send
prompts and retrieved text to its provider; choose the corpus accordingly.

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
does not require the pilot TOML file. Application tables exist; corpus storage
and search remain pending. MLflow is not configured.

Alembic reads the same environment settings. Check the current schema revision:

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python alembic current
```

The repository head and the applied database revision are both `0001`.
The four retrieval tables were verified on 2026-11-07. See the
[migration setup](docs/POSTGRES_SETUP.md#alembic-migrations) for installation
and revision commands. Raw-SQL revisions belong in `migrations/versions/`.

Offline unit tests use the Python standard library:

```sh
PYTHONPATH=src python3.11 -m unittest discover -s tests/unit -v
```

Downloader tests simulate HTTP responses; parser tests use a small synthetic
DocBook fixture; chunking tests use synthetic blocks and a test token counter.
Database settings tests cover defaults, environment overrides, validation and
password handling. DB-check tests use a fake driver for SQL results, resource
cleanup, CLI output and safe failures. All 80 unit tests run offline without a database, driver,
local snapshots, tokenizer packages or models.
Real network verification is run separately with the explicit `download-source`
command; the four saved snapshots were also checked through the offline parser CLI.

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
