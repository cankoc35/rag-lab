# Project context

This file helps a new session understand **why** the project exists and
**which decisions** guide it. Read [STATUS.md](STATUS.md) for current progress
and the next task, [ROADMAP.md](ROADMAP.md) for stages, and
[README.md](../README.md) for a brief overview. The
[session handoff](HANDOFF.md) maps the current code, local artifacts and resume
checks. Last updated: **2026-11-17**.

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
- **Approved initial design (owner, 2026-11-13):** Simple uses one dense
  retrieval pass and one final-answer call, without hybrid search, reranking
  or sandbox tools. Enhanced uses dense + PostgreSQL full-text retrieval,
  RRF merge/deduplication, reranking and the same final-answer setup. Both share
  corpus/chunks, dense embedding settings, generator/settings, answer prompt
  and maximum context token budget. Both cite evidence and may abstain.
- **Approved control principle (owner, 2026-11-13):** Enhanced's relevant
  sandbox tool steps follow predefined Python conditions/order; native LLM
  function calling is not required and no model-directed loop is planned in
  this first version. Agentic will have comparable relevant tool access and
  dynamic model decisions, but its detailed design is deferred until that
  stage. Exact tools/conditions still need definition. The earlier runbook/
  frozen-DB-state plans remain active.
- **Approved development approach (owner, 2026-11-13):** Measure dense-only,
  hybrid-only and hybrid-plus-reranking variants to separate component effects.
  These are ablations, not extra main workflows. This is an extensible initial
  design; reranker/generator choices, numeric budgets and the final thesis
  protocol remain open. No workflows are implemented by this decision. Details
  are in [METHOD_DESIGN.md](METHOD_DESIGN.md#approved-initial-simple-and-enhanced-design).
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
  remain drafts. A first six-question dense-retrieval diagnostic now exists;
  no generator result or verified sandbox-tool output exists yet.

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
  snapshot/chunk storage is implemented and four snapshots/49 chunks are imported.
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
  Raw-SQL storage, dense SQL search and query embedding/search orchestration
  are now implemented.
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
  initially empty. The later committed corpus import and indexing populated
  all four tables.
- **Implemented (owner, 2026-11-12):** Prepared `save_snapshots()` and
  `save_chunks()` in `store.py` plus `scripts/import_corpus.py`. One connection/
  transaction imports the saved source records and exact chunk inputs/metadata.
  Identical records can be repeated; conflicting existing IDs fail. All four
  snapshots and 49 chunks passed a full DB round trip and repeat check, then
  rollback left every retrieval table empty at that preparation step.
- **Imported (owner, 2026-11-12):** The owner requested execution of the
  prepared script. It committed four snapshots and 49 chunks. Independent
  read-only checks verified every stored field against the saved artifacts;
  a second committed run left counts and contents unchanged. Corpus
  indexing had not yet been implemented at that import step; retrieval remains pending.
- **Implemented (owner, 2026-11-12):** `save_embedding_index()` and
  `save_embeddings()` now provide raw-SQL storage for index metadata and
  `(chunk_id, EmbeddingResult)` pairs. They share the caller's transaction,
  accept identical repeats and reject changed records. Vector writes check
  model/revision/dimensions, document task and the hash of the stored chunk's
  exact embedding input. Tests use synthetic vectors in temporary tables;
  public counts remain four snapshots, 49 chunks and zero indexes/vectors.
  Corpus indexing was the next step after these storage functions.
- **Implemented (owner, 2026-11-12):** `scripts/index_corpus.py` reads all stored
  corpus chunks, creates an index identity from exact inputs/model/runtime
  metadata, generates document vectors and saves everything in one transaction.
  Its lockfile preserves existing ML dependency versions and adds Psycopg.
  Two complete CLI runs with real cached Nomic inference, blocked network and
  forced rollback produced identical index IDs and all 49 vectors. Public
  counts remained `(4, 49, 0, 0)` after that preparation check.
- **Indexed (owner, 2026-11-12):** The owner ran the indexing command; a
  subsequent read-only check confirmed one committed index and 49 vectors,
  matching the prior verified vectors and exact chunk inputs. The process had
  finished by the second inspection. Added immediate stderr phase/chunk progress
  after the owner reported a blank terminal. The index keeps its creation
  provenance; no re-indexing was needed. Retrieval remains unimplemented and
  no retrieval-quality result has been established.
- **Implemented (owner, 2026-11-14):** `store.search_chunks()` accepts a raw
  query vector and index ID, runs a parameterized cosine-distance SELECT and
  returns source-linked chunk dictionaries. The caller owns the connection/
  transaction. SQL behavior passed temporary-table tests and read-only stored-
  vector self-search; public contents are unchanged. Query-model orchestration
  in `retrieval.py` and P01–P06 checks were still pending at that SQL-only step.
- **Implemented/checked (owner, 2026-11-14):** `retrieval.retrieve()` validates
  the selected index's model/revision/dimensions and embedding settings before
  calling `embed_query()` and dense search. The caller reuses one loaded model.
  The first real-Nomic P01–P06 diagnostic found annotated chunks in the top five
  for five questions; P05 had no reference hit. This is a development finding,
  not an answer-quality grade. DB contents and gold data are unchanged.
  Follow-up full ranks (17/11/46) and exploratory wording probes show strong
  sensitivity: adding `multicolumn` raises the two multicolumn references to
  1/2. SQL distance and data checks passed. These findings motivate a controlled
  development comparison; no query-rewriting policy or other fix is selected.
- **Approved/implemented (owner, 2026-11-14):** A repeatable P01–P06 retrieval
  checker now reports full ranks and annotated evidence hits at 5/10/20 using
  the same original questions/model/index. These are development diagnostics;
  the application's five-result baseline and final context budget remain
  separate. Two locked real-model runs matched with unchanged public data.
  The next task is initial generator selection and an evidence-context/prompt
  contract, not adopting a cutoff from annotation counts alone.
- **Confirmed, not installed:** LangGraph for the agentic workflow.
- **Owner decision, 2026-11-16:** Do not use MLflow. Use a small project-owned
  PostgreSQL tracing layer with Psycopg/parameterized raw SQL. The earlier
  MLflow selection is superseded. Raw-SQL migration `0002`, lifecycle writers
  and opt-in checker integration are implemented in [TRACING_PLAN.md](TRACING_PLAN.md).
  After review, the owner explicitly authorized applying it and testing one
  question. Revision `0002` is applied; four tracing DB tests and a committed
  real P04 trace/span passed verification. Corpus/index contents are unchanged.
  Generator/provider and context/prompt work are next. LLM/tool instrumentation
  remains future work; the JSONB payload/usage/cost fields are prepared for it.
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
- **Owner decision, 2026-11-17:** Use an inexpensive paid hosted API for the
  initial generator. The owner subsequently authorized the first Luna client
  step: OpenAI Responses API, `gpt-6-luna`, reasoning `none`, maximum 1000
  output tokens. SDK `3.51.0`, `llm.generate_text()` and a locked opt-in smoke
  script are implemented. Offline checks passed; a live call awaits the API
  key. This is not a measured quality result or a final thesis model selection.
  Keep generator settings shared across workflow comparisons; local models
  may be evaluated later.
- **Open:** The full PostgreSQL snapshot/coverage, sandbox data model, precise
  DB tool contracts and final experimental generator settings.
  Do not send private corpus content to a hosted API without an explicit decision.
- **Hardware (owner, 2026-11-05):** The MacBook Air M3 has 24 GB RAM or more;
  the exact capacity above that threshold was not specified. The
  [embedding plan](EMBEDDING_PLAN.md) proposes one dense model/index to start.
  The English-only decision removed the earlier multilingual rationale for
  BGE-M3. Nomic is now selected and locally tested for the initial pilot;
  generation-model selection and embedding/retrieval quality remain open.
- **Open:** Enhanced tool conditions, reranker/generator choices, candidate/
  context budgets, detailed Agentic and router design, final corpus/model
  count and metric/benchmark protocol. Method, evaluation and literature
  drafts are working documents, not approved findings.

## Where to find the literature

The [main RAG/agent/evaluation list](papers/rag-papers/README.md),
[adaptive RAG branch](papers/adaptive-rag-papers/README.md) and
[Enron/privacy branch](papers/enron-papers/README.md) are separate reading paths.
[Brief Enron notes](papers/enron-papers/enron-notes.md) exist; do not assume
all papers have been read or annotated. These PDFs are research literature,
not the chatbot's retrieval corpus.
