# Project context

This file helps a new session understand **why** the project exists and
**which decisions** guide it. Read [STATUS.md](STATUS.md) for current progress
and the next task, [ROADMAP.md](ROADMAP.md) for stages, and
[README.md](../README.md) for a brief overview. The
[session handoff](HANDOFF.md) maps the current code, local artifacts and resume
checks. Last updated: **2026-11-12**.

## Purpose and boundaries

- **Confirmed:** Build a practically useful, tool-using Agentic RAG chatbot
  while developing AI engineering skills. This repository is not a project
  for creating a separate general-purpose RAG testing platform.
- **Confirmed:** According to the owner, the supervisor liked the Agentic RAG
  direction; work will continue in this area. The three-workflow and adaptive
  router comparison is the current research draft. The final thesis title,
  experimental protocol and contribution statement remain open.
- **Confirmed:** The repository/folder name is `rag-workflow-lab`. This does
  not determine the final thesis title or research direction.
- **Confirmed (owner, 2026-11-01):** The initial pilot will explain PostgreSQL
  documentation and inspect an example database's state. The corpus direction
  is official PostgreSQL docs plus explicitly synthetic local deployment and
  operations runbooks. Frozen DB-state access will provide a capability beyond
  retrieval; exact tool contracts remain open.
- **Confirmed (owner, 2026-11-05):** The RAG system will use English throughout:
  corpus and synthetic documents, pilot/held-out questions and datasets,
  prompts, answers, gold answers/rubrics and model-visible tool descriptions.
  Multilingual or cross-lingual retrieval is not required.
- **Confirmed (owner, 2026-11-05):** The English-only policy also covers the
  entire repository: README files, research/project notes, code, comments,
  docstrings, messages and configuration prose. Only conversation with the
  owner in this chat may remain in Turkish. The existing repository text was
  translated without changing source IDs, paths or experimental scope.
- **Confirmed/implemented (2026-11-02):** At the owner's request, the initial
  official-docs allowlist was prepared for PostgreSQL 18: Using EXPLAIN,
  Multicolumn Indexes, Partial Indexes, and the `pg_stat_replication` section
  of Monitoring Statistics. Stable source IDs and page/section selection are
  in `data/corpus/sources.json`. This is the initial pilot scope; the source
  list alone does not define a content snapshot or the final thesis corpus.
  Actual snapshot progress is recorded in STATUS.
- **Open:** The exact thesis question, final title, full content snapshot and
  final corpus coverage.
- **Confirmed (supervisor guidance):** Draw a method-level design.
  The [initial draft](METHOD_DESIGN.md) exists; the expected format, detail
  level and supervisor feedback remain open.
- **Confirmed (project requirement):** Establish consistent evaluation,
  metrics and result records from the start so results are reproducible.
  Literature work should provide a paper-specific, source-backed comparison
  of methods and limitations. The [initial table](LITERATURE_GAPS.md) needs
  expansion. The [evaluation draft](EVALUATION_PLAN.md) exists; metrics and
  thresholds are not finalized.

## Selected direction and earlier alternatives

1. **Confirmed — Agentic RAG; proposed — adaptive workflow comparison:**
   The current draft evaluates simple, enhanced and Agentic RAG on the same
   questions, then tests whether a router improves the quality/latency/cost
   trade-off. Exact question scope, corpus snapshot, tools, metrics and
   benchmark remain open. Close studies and the experimental framing are
   summarized in [README.md](../README.md).
2. **Earlier alternative — Minimum observability for failure localization:**
   Use an existing tracing platform to identify/localize Agentic RAG failures
   under black-box, retrieval-aware, tool-aware and more complete traces.
   MLflow would provide infrastructure; building an MLflow/RAGAS alternative
   is not the goal.
3. **Earlier alternative — Privacy-preserving RAG over Enron:**
   The supervisor suggested Enron emails and LLM-PBE. This could examine
   reducing PII/private-content leakage to unauthorized users while preserving
   answer utility. The threat model, authorization rules and pipeline position
   of the defense would first need narrowing. Enron is currently **only a
   literature branch**, not the selected retrieval corpus.

Observability and Enron/privacy are not active thesis directions in this repo.

## Implementation and comparison approach

- **Confirmed (owner, 2026-11-06):** Prioritize short, readable, straightforward
  code that the owner can easily review. Follow the
  [Simplicity First rules](../AGENTS.md#simplicity-first) for future changes.
- **Confirmed:** Build **three workflows in one project** with shared
  components: naive RAG, enhanced RAG and Agentic RAG. Share ingestion,
  retrieval, model calls, appropriate tools and measurement infrastructure
  without unnecessary duplication.
- **Proposed:** Naive RAG is a fixed retrieval → answer baseline. Enhanced
  uses improved retrieval and/or predefined conditional tool steps. Agentic
  chooses its next tool/retrieval action dynamically from observations,
  within iteration and cost limits. Define all three operationally and ensure
  fair tool access before the experiment.
- **Proposed:** An intent/source router could route questions to conversation,
  documents, live data or combinations. Tool retrieval/reranking may help if
  a large catalog becomes necessary; it adds unnecessary complexity for one
  preselected tool. Deterministic SQL tools with validated arguments are an
  option for live structured data. These are proposals, not implemented
  features or established thesis contributions.
- **Proposed:** Measure answer quality, evidence use, correct tool selection,
  latency, tokens and API cost on the same question set. Report lookup,
  multi-hop, current-information, document-plus-live-data, tool-dependent,
  ambiguous and unanswerable cases separately. Separate development questions
  from final-test questions. See [ROADMAP.md](ROADMAP.md).
- **Proposed:** Compare a router against always-simple/enhanced/agentic
  baselines and include its own cost and latency. Keep relevant source/tool
  access comparable for enhanced and agentic. Claim preserved quality only
  when a predefined acceptance margin and held-out results support it.
- **Proposed:** Before final testing, define what each metric measures, how
  it is calculated and its question-type breakdown. Connect question/run IDs,
  workflow, model settings and raw outputs to summary tables; include router
  overhead. Document literature limitations with each paper's experimental
  scope and explicit limits rather than as general judgments.
- **Confirmed (owner, 2026-11-01):** Include an LLM-only control to examine
  the effect of prior PostgreSQL knowledge; retain questions it answers
  correctly. Add questions based on synthetic local documents/DB states,
  changed-evidence pairs and insufficient-evidence abstention controls.
  Freeze source snapshots and keep enhanced/agentic tool access comparable.
  This approval does not finalize sample size, rubric or the full protocol.
- The [pilot scope and 20 questions](PILOT_SCOPE.md) define the development
  direction. P01–P06 now form a [source-verified subset](../data/evaluation/dev/README.md)
  with reference answers and pinned snapshot/block/chunk evidence. P07–P20
  remain drafts; no model/retrieval result or verified tool output exists yet.

## Technical choices and open selections

- **Confirmed/implemented (owner, 2026-11-01):** After planning the file
  structure, the owner requested all scaffold files together while preserving
  existing files/folders. `src/rag_workflow_lab/` and configuration/SQL/data/test
  paths were added. CLI/config checks work; functionality is added in small
  steps. The scaffold does not mean RAG, databases or models are running.
- **Implemented (2026-11-02):** `load_sources()` reads and validates the source
  allowlist. Shared `SourceSpec`/`SourceSelection` types and the local
  `check-sources` command exist. The loader accepts selected schema-v1 official
  versioned PostgreSQL HTML records; it performs neither HTTP downloads nor
  parsing. Unit tests use the Python standard library without network access.
- **Implemented (2026-11-02):** Separate `download_source()`/`download-source`
  operations fetch one selected official HTML source. Each call creates a
  unique folder with raw HTML and a portable manifest, preserving old
  snapshots. Source/scope, UTC time, HTTP metadata, size and SHA-256 are kept.
  Redirects are not followed; the first live check used PG-EXPLAIN.
- **Completed (2026-11-05):** The remaining three official pages were downloaded
  with the existing downloader. Saved hashes and HTML titles were verified
  for all four sources; the PG-STATS target section ID exists in its HTML.
  Snapshot IDs are in STATUS; synthetic documents remain unwritten.
- **Implemented (2026-11-05):** The initial parser uses standard-library
  `html.parser` without new dependencies. `parse_html()` and `parse_snapshot()`
  produce heading/paragraph/code/table blocks with source/snapshot, heading
  path and anchor metadata. `parse-source` reads a local snapshot and rejects
  hash/source-definition mismatches. All four sources were verified; PG-STATS
  yields only its selected section. This version targets PostgreSQL DocBook
  HTML; chunking and Markdown support remain separate tasks.
- **Confirmed/implemented (owner, 2026-11-06):** The owner requested the
  measured, structure-aware chunking strategy: 512-token soft target,
  1024-token application ceiling including context/special tokens, intact
  code/tables, no automatic overlap and explicit overflow errors. The
  [implementation](CHUNKING.md) preserves all content blocks and neighbor links;
  all four snapshots produce 49 verified chunks. The counting tokenizer is
  supplied separately. Nomic was a candidate during chunking and was selected
  in the later embedding step below. This implementation establishes no
  retrieval-quality result.
- **Confirmed/Compose configured (2026-11-06):** Local Docker PostgreSQL 18 +
  pgvector 0.8.7 now have a digest-pinned service, loopback port, required local
  password, persistent named volume and extension bootstrap. Startup, vector SQL
  and container-recreation persistence passed in a temporary project. The
  persistent project service uses the owner's `.env`. The Python `check-db`
  command has also verified PostgreSQL 18.6 and pgvector 0.8.7 in a read-only
  transaction. Revision `0001` subsequently created the application tables;
  snapshot/chunk storage is now implemented, with committed import still pending.
  See [POSTGRES_SETUP.md](POSTGRES_SETUP.md).
- **Confirmed (owner, 2026-11-06):** Use raw SQL for application database
  access, without an ORM. Psycopg 3 is the PostgreSQL driver;
  no SQLAlchemy models, ORM sessions or declarative mappings are planned.
  The owner authorized dependency and environment-settings implementation:
  `psycopg[binary]==3.3.8` is now an optional `database` dependency, installed
  in the Git-ignored `.venv`. `load_database_settings()` reads `POSTGRES_*`
  explicitly, validates connection parameters and excludes the password from
  the settings repr. It does not load `.env` or connect to a database;
  `load_settings()` and ingestion commands remain independent of DB credentials.
  `check-db` is now implemented in `cli.py`, calling `store.check_database()`
  for bounded, read-only connectivity/version/extension checks. Psycopg loads
  only when called; output omits credentials and raw driver errors.
  Raw-SQL snapshot/chunk storage is now implemented; vector search remains unimplemented.
- **Confirmed/implemented (owner, 2026-11-06):** Alembic is selected for
  migrations. The optional `migrations` dependencies pin Alembic 1.20.1 and
  SQLAlchemy 2.1.8, installed in `.venv`. SQLAlchemy is used only by
  `migrations/env.py`; application queries remain Psycopg/raw SQL without an ORM.
  Revision files under `migrations/versions/` will contain manually written
  SQL via `op.execute()`. The environment reuses `load_database_settings()`;
  credentials are not stored in `alembic.ini`. Live `current` and temporary
  offline revision checks passed.
- **Applied (owner, 2026-11-07):** Revision
  `migrations/versions/0001_create_retrieval_tables.py` defines the four
  retrieval tables using raw SQL, with `vector(768)` and reversible table DDL.
  Metadata/settings use JSONB; existing source/snapshot/chunk identities are
  retained. The owner explicitly authorized application on 2026-11-07,
  lifting the earlier preparation-only hold. Revision `0001` is applied;
  all four tables, keys and vector dimensions were verified. The tables are
  initially empty. Later import verification used rollback; no corpus rows
  or embeddings have been committed.
- **Implemented (owner, 2026-11-12):** Prepared `save_snapshots()` and
  `save_chunks()` in `store.py` plus `scripts/import_corpus.py`. One connection/
  transaction imports the saved source records and exact chunk inputs/metadata.
  Identical records can be repeated; conflicting existing IDs fail. All four
  snapshots and 49 chunks passed a full DB round trip and repeat check, then
  rollback left every retrieval table empty. Next run the prepared importer
  for a committed import before corpus embedding/indexing.
- **Confirmed, not installed:** LangGraph for the agentic workflow and
  self-hosted MLflow tracing with PostgreSQL as its backend store. PostgreSQL
  may hold both retrieval data and MLflow metadata, but their schema/database
  separation has not been designed.
- **Confirmed/implemented (owner, 2026-11-06):** The owner authorized the
  next embedding step after the Nomic recommendation. The initial pilot uses
  `nomic-ai/nomic-embed-text-v1.5` at revision
  `e9b6763023c676ca8431644204f50c2b100d9aab`, 768-dimensional output, CPU
  float32 and a 1024-token application ceiling. The local adapter uses mean
  pooling, full-vector layer normalization and L2 normalization, with native
  installed code and explicit local loading. One chunk/query pair and an
  offline repeat passed; no retrieval-quality conclusion follows. Model
  weights/reports are Git-ignored. See [EMBEDDING_SETUP.md](EMBEDDING_SETUP.md).
- **Proposed:** Start with a local embedding model and a simple CLI. Establish
  a working retrieval-and-answer baseline before enhanced/agentic behavior.
- **Open:** The full PostgreSQL snapshot/coverage, sandbox data model, precise
  DB tool contracts, generator/LLM provider and exact generator model IDs. The
  owner wants to try local open models and affordable hosted APIs. Small local
  models on a MacBook Air M3 could limit quality, so isolate model effects from
  the workflow comparison. Do not send private corpus content to a hosted API
  without an explicit decision.
- **Hardware (owner, 2026-11-05):** The MacBook Air M3 has 24 GB RAM or more;
  the exact capacity above that threshold was not specified. The
  [embedding plan](EMBEDDING_PLAN.md) proposes one dense model/index to start.
  The English-only decision removed the earlier multilingual rationale for
  BGE-M3. Nomic is now selected and locally tested for the initial pilot;
  generation-model selection and embedding/retrieval quality remain open.
- **Open:** Exact enhanced-workflow steps, router design, corpus count, model
  count and final metric/benchmark protocol. Method, evaluation and literature
  drafts are working documents, not approved findings.

## Where to find the literature

The [main RAG/agent/evaluation list](papers/rag-papers/README.md),
[adaptive RAG branch](papers/adaptive-rag-papers/README.md) and
[Enron/privacy branch](papers/enron-papers/README.md) are separate reading paths.
[Brief Enron notes](papers/enron-papers/enron-notes.md) exist; do not assume
all papers have been read or annotated. These PDFs are research literature,
not the chatbot's retrieval corpus.
