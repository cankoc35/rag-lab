# Current status

**Last updated:** 2026-11-12

**Stage:** Section-aware chunking is implemented. The four PostgreSQL snapshots
produce 49 verified chunks. P01–P06 have source-verified reference answers and
chunk evidence. Local Nomic document/query embeddings work. PostgreSQL +
pgvector Compose and the Psycopg driver/environment settings are implemented.
The `check-db` command passed against local PostgreSQL 18.6 + pgvector 0.8.7
with a verified read-only transaction. Alembic is installed and configured;
revision `0001` is applied and the four empty retrieval tables are verified.
Raw-SQL snapshot/chunk storage and the import script are implemented and
verified with rollback. Committed corpus import, indexing and retrieval remain
next stages.
**Confirmed:** According to the owner, the supervisor liked the Agentic RAG
subject; the project will continue in this direction.
**Proposed:** Compare three RAG workflows and an adaptive router. The precise
thesis question and experimental protocol remain open.
**Owner approval, 2026-11-01:** The initial pilot uses PostgreSQL docs,
synthetic local runbooks and frozen DB state. Include LLM-only, source-specific,
changed-evidence and abstention controls.
**Owner decision, 2026-11-05:** The entire repository and RAG system use
English, including documentation, code text, corpus, questions/datasets,
prompts, answers and evaluation content. Only chat with the owner may use
Turkish. Multilingual support is not required.
**Owner decision, 2026-11-06:** Application database access will use
parameterized raw SQL without an ORM. Psycopg 3.3.8 and environment settings
are available and the read-only connection check works. Snapshot/chunk storage
is now implemented; vector search remains pending. Alembic revision `0001` is applied.
**Owner instruction, 2026-11-07:** Apply the prepared migration; this superseded
the earlier preparation-only hold. Application and catalog checks passed.

**Current runtime check, 2026-11-12:** The project PostgreSQL service is healthy.
`check-db` passed with PostgreSQL 18.6, pgvector 0.8.7 and a read-only transaction;
revision `0001` is applied. Full-corpus import verification was rolled back.
All four retrieval tables were verified empty afterward. This supersedes the
stopped-service observation from 2026-11-08.
The [session handoff](HANDOFF.md) gives the reading order, code/artifact map
and resume commands for another AI or developer.

## Completed work (chronological history)

Entries below describe each step at its recorded date. Later entries supersede
earlier proposals, missing features and preparation-only holds.

- The repository purpose, three possible thesis directions and proposed
  implementation sequence are documented in [README.md](../README.md) and
  [ROADMAP.md](ROADMAP.md).
- The shared-component approach and choices of PostgreSQL + pgvector,
  LangGraph and self-hosted MLflow are recorded. PostgreSQL Compose is now
  configured and temporarily verified; LangGraph and MLflow remain future work.
- `docs/papers/` contains main RAG, adaptive RAG and Enron/privacy reading
  branches, plus brief Enron notes. These are not the retrieval corpus or a benchmark.
- A Git repository and `.gitignore` exist; a baseline commit is now present
  (`e301eaa` at the start of the embedding session).
- The repository/folder name is `rag-workflow-lab`; the thesis title remains open.
- The proposed three-workflow/router research question and close literature
  were added to [README.md](../README.md). This is not an experimental result.
- The supervisor-requested [initial method-level design](METHOD_DESIGN.md)
  exists but has not been reviewed by the supervisor.
- The [initial literature comparison](LITERATURE_GAPS.md) covers five primary
  sources; a comprehensive literature review is not complete.
- The [evaluation draft](EVALUATION_PLAN.md) proposes metrics and per-run
  record fields; thresholds and the final protocol remain undecided.
- Owner-approved corpus direction and prior-knowledge controls are recorded
  in README, PROJECT_CONTEXT, ROADMAP, method and evaluation documents.
- The [pilot scope and 20 development question drafts](PILOT_SCOPE.md) exist.
  The required official PostgreSQL pages were inspected; not all gold answers
  have been verified against saved source spans/tool outputs. This is not a runnable dataset.
- At the owner's request to plan before coding, the [code structure proposal](CODE_STRUCTURE.md)
  defined shared components, workflow/tool/evaluation boundaries, corpus/gold
  separation and staged implementation.
- The owner subsequently requested all scaffold files: 45 were added under
  `src/rag_workflow_lab/`, package/config/env/compose, SQL, prompts and data/tests.
  Existing files/folders were preserved. CLI help/version and TOML config
  checks worked; the other modules initially contained responsibility docstrings.
- Python 3.11 checks passed for compilation of 29 Python files, importing 28
  submodules, CLI help/config, package TOML and source-list JSON.
  `docker compose config --quiet` passed for an empty service scaffold;
  this did not start DB/MLflow. No model/API test was run.
- **2026-11-02:** `data/corpus/sources.json` was populated with four official
  PostgreSQL 18 sources. Each record has source ID, title, URL, format, major
  version and selection scope. The first three select the page body; PG-STATS
  selects only the `pg_stat_replication` HTML section. URLs and the section ID
  were checked. `selected` denotes source selection; separate records track snapshots.
- The source JSON was checked for four unique IDs/URLs, required fields,
  PostgreSQL 18 paths and page/section scope. Local links and code fences
  passed validation in six updated Markdown documents.
- **2026-11-02:** `load_sources()` was added to `ingestion/download.py`.
  It validates a selected schema-v1 manifest and returns shared immutable
  `SourceSpec`/`SourceSelection` records. Missing/malformed fields, duplicate
  IDs/URLs, inconsistent documentation versions and invalid section selections
  produce clear `SourceManifestError` messages. The loader supports only
  official versioned PostgreSQL HTML; Markdown support is future work.
- `check-sources --config configs/pilot.toml` validates the allowlist locally
  without changing its JSON or downloading content. Nine offline unit tests
  and CLI checks against the four real source records passed. No new runtime
  or test dependency was added.
- **2026-11-02:** `download_source()` and the explicit network command
  `download-source --source-id ... --timeout ...` were added. Each download
  writes raw HTML and `manifest.json` to a new directory, preserving earlier
  snapshots. HTTP/timeout, incomplete/non-HTML responses and write errors
  are handled; redirects are not followed.
- **19 offline unit tests passed** (9 source-loader + 10 downloader).
  Simulated HTTP tests cover preservation on repeated downloads, SHA-256,
  metadata, cleanup after failures and selecting one source through the CLI.
- A separate live check initially downloaded **only PG-EXPLAIN**: HTTP 200,
  70,029 bytes, HTML title Using EXPLAIN. The saved file's hash matched its
  manifest. Snapshot: `data/local/snapshots/PG-EXPLAIN-20261102T173311Z-yhdhybna/`.
  SHA-256: `22b29b578fe330ce2a1eca03dcc6ecfb540eb6211e21cfa4d61d93d55e87bf7e`.
  Raw HTML and its manifest are ignored by Git.
- **2026-11-05:** The existing CLI downloaded PG-MULTI, PG-PARTIAL and PG-STATS,
  each with HTTP 200 and a separate HTML/manifest pair. PG-STATS failed once
  because the connection was reset, then succeeded on retry. The original
  PG-EXPLAIN HTML/manifest and `data/corpus/sources.json` were byte-for-byte
  unchanged. No code or dependencies were added in that download step.
- Disk SHA-256/size values matched all four manifests. Source definitions,
  PostgreSQL 18 HTML titles and PG-STATS section ID
  `MONITORING-PG-STAT-REPLICATION-VIEW` were verified. Exactly four snapshots
  and eight files existed, with no partial files; all were Git-ignored.
  Unit tests were not repeated for this download-only step; the 19-test result
  above came from the earlier downloader implementation.
- **2026-11-05, parser:** `parse_html()` and `parse_snapshot()` were implemented
  in `ingestion/parse.py`; `ParsedDocument`, `ParsedBlock`, `TableCell` and
  the `parse-source` CLI were added. The standard library is used without new
  dependencies. Navigation/footer/TOC/scripts/styles are removed; heading
  paths, SQL indentation, table cells/headers/spans and source/snapshot/anchor
  metadata are retained. Source-allowlist matching, size and SHA-256 are
  checked; missing or overlapping section selections produce errors.
- A small synthetic DocBook fixture added **16 parser tests; 35 offline unit
  tests passed in total**. All four real snapshots were parsed through the CLI
  with network access blocked; hashes of all preexisting data files were
  unchanged. PG-STATS contains only its selected section, one 21-row table
  including the header, and following NULL-lag notes, with no neighboring-section anchors.
- **2026-11-05, chunking research:** Official tool documentation was reviewed
  for technical documents containing SQL/code and tables. The source-backed
  comparison and project proposal are in [CHUNKING_RESEARCH.md](CHUNKING_RESEARCH.md).
  Structure-based grouping, tokenizer budgets, SQL/code integrity, repeated
  table headers, AST and parent-child approaches were distinguished. Ready-made
  splitters may divide oversized blocks. Chunker, model/tokenizer and overflow
  policy remain open; no code/dependency changes or new test run occurred in this research step.
- **2026-11-05, embedding research:** The owner reaffirmed pgvector and reported
  M3 RAM of 24 GB or more. Three multilingual local candidates were checked;
  [EMBEDDING_PLAN.md](EMBEDDING_PLAN.md) initially proposed one dense BGE-M3
  model with `vector(1024)`. No model was selected/downloaded, no dependency/DB
  was installed and no model benchmark was run.
- **2026-11-05, English system scope:** The owner confirmed an English RAG
  system. All 20 question and expected-answer drafts were translated, preserving
  IDs, scope and scenario values. Language was removed from the open decisions.
  The earlier multilingual embedding rationale was removed; Nomic Embed Text
  v1.5 and BGE Base English v1.5 were added as candidates. There was no final
  model selection, installation or new model test.
- **2026-11-05, English repository:** The owner extended the policy to every
  repository file, including project/research documentation and Python text.
  Remaining non-English project prose and reading notes were translated.
  The Unicode source-loader test now uses an English title with an em dash,
  preserving its Unicode round-trip coverage. Paths, source IDs, original
  research PDFs and raw/parsed corpus artifacts were preserved.
- Translation verification passed: **35 offline unit tests**, all 18 Markdown
  files' local-link/code-fence checks, and a repository-text scan for remaining
  Turkish characters/common words. All existing link targets, pilot question
  records and snapshot-table data rows were preserved. All 125 preexisting
  files remain; 12 Markdown files and one test example changed. All 47 PDF
  hashes and all data-artifact hashes are unchanged. Application Python files
  were already English and remain byte-for-byte unchanged. `AGENTS.md` now
  records the English-only repository policy and Turkish chat exception.
- **2026-11-05, block token measurement:** All 184 parsed blocks were measured
  locally with the Nomic Embed Text v1.5 tokenizer at pinned revision
  `e9b6763023c676ca8431644204f50c2b100d9aab` and `tokenizers==0.22.2`.
  [TOKEN_COUNTS.md](TOKEN_COUNTS.md) records the method and results; the
  [standalone script](../scripts/measure_block_tokens.py) saves per-block
  counts, source/snapshot identifiers and input/tokenizer/script hashes.
  With headings, document prefix and special tokens, the maximum code block
  is 658 tokens and the table is 811. Three blocks exceed 512; none exceeds
  1,024. All 552 counts matched a local-only `BertTokenizerFast` cross-check;
  an untruncated 9,002-token probe and all 35 existing offline tests passed.
  Only tokenizer metadata was downloaded, with no model weights, corpus
  upload or embedding/DB run. The candidate is not a final model selection;
  chunk budgets and overflow policy remain open.
- **2026-11-06, chunking:** At the owner's request, `chunk_document()` was
  implemented with a 512-token soft target and 1024-token application ceiling,
  counting complete inputs with headings, prefix and special tokens. Whole
  paragraphs, SQL/code and tables are preserved. Adjacent paragraph + code/table
  pairs stay together when they fit; this is a structural heuristic, not
  semantic classification. Heading boundaries are respected, overlap is zero,
  and oversized individual blocks raise an explicit error without partial output.
- Shared immutable `Chunk` and `TokenizerSpec` contracts now record source
  blocks/positions, anchors, source/snapshot hashes, tokenizer configuration,
  versioned deterministic IDs, exact embedding inputs/counts and neighbor links.
  The core uses an injected counter without adding application dependencies.
  The [chunking guide](CHUNKING.md) describes the implementation and API.
- **48 offline unit tests passed**, including 13 new chunking tests. The
  optional `scripts/chunk_corpus.py` ran against all four saved snapshots
  using the pinned cached Nomic tokenizer with network connections blocked.
  It produced **49 chunks**: PG-EXPLAIN 37, PG-MULTI 3, PG-PARTIAL 5 and
  PG-STATS 4. All 176 content blocks (46 code blocks, 129 paragraphs, one table)
  occur unchanged exactly once; eight headings are indexed metadata/context.
  Four chunks exceed the soft target; the maximum is **822 tokens**, and none
  exceeds 1024. Repeated calls, whole-input counts, heading boundaries,
  neighbor links and the retained NULL-lag note were verified. All raw/parsed
  input hashes remain unchanged. Output: `data/local/chunks/pilot-section-blocks-v1/`.
  No model weights, embeddings, DB operation or retrieval evaluation were involved;
  the embedding model remains undecided.
- **2026-11-06, document-question evidence:** At the owner's request,
  [document_questions.json](../data/evaluation/dev/document_questions.json)
  was created as development dataset `postgresql18-document-dev` version
  `1.0.0`. P01–P06 retain their question text and now have English reference
  answers reviewed against the saved sources, claim-to-evidence annotations,
  exact quote spans and pinned source/snapshot/block/chunk references.
  **13 evidence records** reference **9 distinct blocks/chunks** across all
  four sources. Evidence alternatives and optional guidance avoid treating
  every reference passage as mandatory. The records do not fix the final
  grading rubric or prove irreducible multi-document reasoning.
- The read-only standard-library `scripts/check_document_questions.py`
  verified file hashes, source/chunk/block identities, spans, anchors and
  claim references. Nine negative checks rejected stale hashes, unknown
  chunks/claims, wrong block positions/snapshots, altered spans, duplicate
  question IDs and a non-development split. All **17 pinned input files**
  remained unchanged, and all **48 existing offline unit tests passed**.
  Details are in the [development-data guide](../data/evaluation/dev/README.md);
  the local check record is `outputs/validation/document-questions-v1.json`.
  P07–P20 remain drafts. No retrieval, embedding, model-answer or metric run
  occurred; the application dataset loader/evaluation runner remain scaffolds.
- **2026-11-06, local embedding smoke:** The owner authorized the next step
  after the Nomic recommendation. The initial pilot now selects
  `nomic-ai/nomic-embed-text-v1.5` at revision
  `e9b6763023c676ca8431644204f50c2b100d9aab`, CPU float32, 768 dimensions
  and a 1024-token application ceiling. `embeddings.py` explicitly loads a
  checksummed local safetensors snapshot with native Transformers NomicBERT;
  it performs no download or ML import on module import. Document inputs keep
  their existing prefix; raw query inputs receive their query prefix once.
  Complete-token checks reject overflow or forward-tokenization changes.
  Mean pooling is followed by full-vector layer normalization and L2 normalization.
- Model assets (10 files, 547,886,235 bytes) are cached under
  `data/local/models/nomic-ai--nomic-embed-text-v1.5/<revision>/`, with a
  SHA-256/size manifest. Optional dependency pins and a smoke-script lockfile
  record Sentence Transformers 5.3.0, Transformers 5.5.0, PyTorch 2.10.0
  and Tokenizers 0.22.2. Downloads are explicit; inference is local-only.
- `scripts/embedding_smoke.py` produced a 768-dimensional vector for one
  **822-token PG-STATS chunk** and one **25-token P04 query**. Both vectors
  were finite and unit-normalized. All **49 chunk token counts matched** the
  runtime tokenizer; those 49 chunks were not all embedded. A fully offline
  repeat produced identical vectors on this device; oversized-query rejection
  and full-forward token IDs passed. Reports are under
  `outputs/embeddings/nomic-smoke-v1/` and `nomic-smoke-offline-v1/`.
  **59 offline unit tests passed**, including 11 new adapter/config checks
  with fake inference and no model dependencies. The source snapshots, parsed
  blocks, chunk files and development-question references remain unchanged.
  See [EMBEDDING_SETUP.md](EMBEDDING_SETUP.md). No ranking, retrieval score,
  generator answer or DB operation was performed.
- **2026-11-06, Compose setup:** At the owner's request, `compose.yaml` now
  defines PostgreSQL 18 + pgvector 0.8.7 using a pinned multi-architecture
  image digest. It binds only to `127.0.0.1`, requires a nonempty local
  password, mounts a named volume at the PG18 data location and uses a TCP
  healthcheck. `.env.example` now lists the database settings with a blank
  password; no real credentials were added. A read-only `000_extensions.sql`
  bootstrap enables `vector` on a new empty volume. The application migration
  scaffold remains unchanged, with no chunk tables created yet.
- Compose schema validation and missing-password rejection passed. A separate
  temporary Compose project reached **healthy** status with PostgreSQL 18 and
  pgvector 0.8.7; a vector cosine-distance SQL expression worked, and a test
  row survived container recreation with the same volume. The temporary
  project and its test volume were removed afterward. The persistent project
  service is started explicitly using the owner's `.env`. Details are in
  [POSTGRES_SETUP.md](POSTGRES_SETUP.md); the local report is
  `outputs/validation/compose-20261106T180311247594Z.json`. Python code was
  unchanged and unit tests were not repeated in this step; live Compose/SQL
  checks provided the relevant verification. No application corpus data,
  embeddings or evaluation records were imported.
- **2026-11-06, database-access decision:** The owner requested raw SQL and
  no ORM. Current application code and dependency declarations contain no
  SQLAlchemy, Alembic or Psycopg integration; `store.py` remains a scaffold.
  The raw-SQL requirement and planned Psycopg 3 driver are now documented.
  Alembic remains a proposal: its SQLAlchemy infrastructure does not require
  ORM models, and migrations can execute raw SQL. No dependencies, application
  schema, database data or Python code changed in this documentation step.
  The owner's preceding terminal screenshot showed the persistent project
  service running with healthy status; that startup was owner-reported.
- **2026-11-06, database dependency and environment settings:** The owner
  requested only the first two parts of the proposed connection step.
  `pyproject.toml` now pins `psycopg[binary]==3.3.8` in the optional `database`
  extra. It was installed in the Git-ignored project `.venv` with
  `psycopg-binary==3.3.8` and `typing-extensions==4.16.0`; importing the driver
  confirmed its binary implementation. SQLAlchemy and Alembic are absent.
  No model packages were installed into this environment.
- `DatabaseSettings` and `load_database_settings()` now read `POSTGRES_HOST`,
  `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` and
  `POSTGRES_CONNECT_TIMEOUT`. Local defaults match Compose; the password is
  required. Ports/timeouts and blank/NUL-containing values are validated.
  Password punctuation and whitespace are preserved in separate connection
  keyword arguments; errors do not echo input values and repr omits the password.
  The loader does not read files, import Psycopg or open a connection.
  Ingestion/TOML settings and existing CLI output remain independent.
- **69 offline unit tests passed**, including 10 new database-settings tests
  covering defaults, overrides, invalid values, explicit-environment isolation,
  password handling and existing CLI compatibility. Driver import was checked
  separately. Real Psycopg conninfo parsing preserved special-character
  credentials without connecting, and `uv run --env-file` was verified with
  a temporary synthetic file. Installed dependencies passed `uv pip check`;
  updated documentation links/fences and dependency declarations passed checks.
  The local `.env` was not read or modified. Application queries,
  a DB-check command, migrations and table creation were outside these first
  two parts; no database connection or corpus indexing was performed.
- **2026-11-06, explicit DB check:** At the owner's request, `cli.py` now
  exposes `check-db`, loading only the environment-based database settings.
  `store.check_database()` imports Psycopg on invocation, opens a read-only
  transaction and runs `SELECT 1`, a server-version/read-only-state query and
  a parameterized query for the installed `vector` extension version.
  Each statement has a five-second timeout; connection timeout comes from
  settings. Connection/cursor contexts clean up on success or failure.
- Success prints JSON containing `status`, `postgresql_version`,
  `pgvector_version` and `read_only`. Missing settings/driver/extension and DB
  failures produce a nonzero exit. Output omits credentials and raw driver
  errors. Existing ingestion commands still require no driver or DB settings.
- **80 offline unit tests passed**, including 11 new fake-driver/CLI tests for
  successful checks, read-only verification, malformed/missing results,
  missing extensions/dependencies, context cleanup and safe error output.
  The explicit live command, using the local `.env` without printing its
  contents, returned **PostgreSQL 18.6**, **pgvector 0.8.7**, `status: ok` and
  `read_only: true` against `rag-workflow-lab-postgres-1`. No schema/data
  mutations, migration setup, corpus indexing or model calls were performed.

- **2026-11-06, coding style:** Added the owner's Simplicity First rules to
  [AGENTS.md](../AGENTS.md#simplicity-first): minimal, readable code without
  speculative features or unnecessary complexity. Application code is unchanged;
  the next task remains migration tooling and the initial raw-SQL schema.

- **2026-11-06, retrieval schema proposal:** Proposed four tables:
  `source_snapshots`, `chunks`, `embedding_indexes` and `chunk_embeddings`.
  Preserve existing snapshot/chunk IDs; keep citation/chunking metadata with
  chunks, corpus membership fingerprint and model/settings with the embedding
  index, and one vector per `(index_id, chunk_id)`. Start with `vector(768)`
  and exact search. This is a proposal, not an approved or applied schema;
  migration tooling remains undecided.

- **2026-11-06, Alembic setup:** The owner selected and requested Alembic
  installation/configuration. The optional `migrations` dependencies pin
  Alembic 1.20.1 and SQLAlchemy 2.1.8; both are installed in `.venv` alongside
  Mako 1.4.3 and MarkupSafe 3.0.4. `alembic.ini`, a 30-line `migrations/env.py`,
  a small raw-SQL revision template and an empty `migrations/versions/` now exist.
  Existing `POSTGRES_*` settings supply the connection through a SQLAlchemy
  URL object, without storing credentials in configuration files. SQLAlchemy
  is limited to migration connections; no application ORM is introduced.
- The template generated a valid temporary revision, and its raw-SQL
  upgrade/downgrade rendered offline without connecting or exposing the
  synthetic password. Temporary files were removed. Installed packages passed
  `uv pip check`, and all **80 offline unit tests passed**. `alembic heads`
  and `history` confirm an empty revision graph. Live `alembic current`
  connected successfully; before/after checks found the same **zero public
  tables**. No revision was applied, and no existing SQL scaffold was changed.
  The next task is the first raw-SQL revision for the proposed retrieval schema.

- **2026-11-06, initial migration prepared only:** Created raw-SQL revision
  `0001_create_retrieval_tables.py` for `source_snapshots`, `chunks`,
  `embedding_indexes` and `chunk_embeddings`. It declares primary/foreign keys,
  positive token counts, 768-dimensional index metadata and `vector(768)`.
  Chunk metadata/settings use JSONB. The composite embedding primary key is
  `(index_id, chunk_id)`. Upgrade enables `vector` if absent; downgrade drops
  tables in reverse dependency order and keeps the shared extension.
- Both directions rendered with Alembic `--sql` while DB/network connection
  functions were blocked, using a synthetic environment without reading `.env`.
  pglast 8.7 parsed both generated scripts successfully in an isolated temporary
  tool environment; it was not added as a project dependency. All **80 offline
  unit tests passed**. SQL previews are under
  `outputs/validation/retrieval-schema-0001/`. No migration was sent to any DB;
  catalog/constraint execution checks remain deferred under the owner's hold.

- **2026-11-07, migration applied:** On the owner's explicit instruction,
  `alembic upgrade 0001` applied the prepared revision to the running project
  PostgreSQL service. Read-only catalog checks confirmed database revision
  `0001`, all four retrieval tables, `vector(768)`, four primary keys, three
  foreign keys and two CHECK constraints. The embedding primary key is
  `(index_id, chunk_id)`, and pgvector remains 0.8.7. All four tables contain
  zero rows; no corpus records, embeddings or model outputs were imported.
  Local verification record:
  `outputs/validation/retrieval-schema-0001/applied-2026-11-07.json`.
  Migration/application code was unchanged. Unit tests were not repeated;
  this step verified the applied schema against PostgreSQL itself.

- **2026-11-08, session handoff:** Reviewed the implementation and local
  artifacts and added [HANDOFF.md](HANDOFF.md). Updated orientation, code,
  pilot, embedding and database guides to distinguish implemented features
  from scaffolds and to agree on the next task: raw-SQL snapshot/chunk import.
  No application code, dependencies, corpus inputs or database contents changed.
  The six-question reference checker passed again: six questions, four sources,
  13 evidence records and nine referenced chunks/blocks. This is an integrity
  check, not a retrieval or answer-quality evaluation. The stopped container and
  unsuccessful connection check are recorded above. Unit tests and model
  inference were not rerun for this documentation-only session.
  Local-link/heading-anchor and code-fence checks passed across all 14 updated
  Markdown files (137 local links); `git diff --check` passed.

- **2026-11-12, snapshot/chunk import prepared:** Added `save_snapshots()` and
  `save_chunks()` to `store.py` and `scripts/import_corpus.py`. The script uses
  the pilot allowlist, saved snapshot checks and chunk-provenance checks;
  file loading completes before a DB connection is opened. Both save functions
  share the script's transaction. Identical records are accepted; an existing
  ID with different contents fails instead of overwriting data. Chunk text,
  exact embedding input, token counts and all remaining metadata are preserved.
- **86 offline unit tests and 3 opt-in PostgreSQL integration tests passed**.
  The integration tests use temporary tables, verifying round trips, repeat
  imports, conflicting payloads and whole-transaction rollback. A separate
  verification imported all four real snapshots and 49 chunks twice in one
  transaction, checked every stored field, then rolled back. Before and after
  counts were `(0, 0, 0, 0)` for snapshots, chunks, embedding indexes and vectors.
  Record: `outputs/validation/corpus-import-2026-11-12.json`. The six-question
  reference checker also passed with its pinned inputs unchanged. No committed
  import, model inference, new migration or dependency change occurred.

### Saved official-documentation snapshots

Each directory is under `data/local/snapshots/` and contains
`<source_id>.html` plus `manifest.json`. The parser used these saved copies.
PG-EXPLAIN was downloaded on 2026-11-02, the others on 2026-11-05; do not assume
an atomic, simultaneous capture. Synthetic sources are not yet included.

| Source ID | Snapshot directory | Bytes | SHA-256 |
| --- | --- | --- | --- |
| PG-EXPLAIN | `PG-EXPLAIN-20261102T173311Z-yhdhybna` | 70029 | `22b29b578fe330ce2a1eca03dcc6ecfb540eb6211e21cfa4d61d93d55e87bf7e` |
| PG-MULTI | `PG-MULTI-20261105T191707Z-96nc6y0c` | 21135 | `df6631e673511c60f9ea45dab2b5c69ab80ff1a747117af72236006dc59063d1` |
| PG-PARTIAL | `PG-PARTIAL-20261105T191707Z-kmf7w4sp` | 26463 | `ab67b4a1909a9be617038dcea60e34b7d8f898ca9e8b5f0a569e4df389caa18e` |
| PG-STATS | `PG-STATS-20261105T191715Z-zm7b259y` | 290994 | `4b872e1cd30fd40679c000bf3e5efc15d9f1e4d7a003aed877cfe2c09381c45c` |

### Parser outputs

Four example files are under `data/local/parsed/<snapshot_id>.json`, using
the snapshot IDs above. The CLI writes JSON to stdout; these examples were
saved separately during verification and are ignored by Git. Parser version:
`postgresql-html-v1`. There are 184 content blocks, not embedding chunks.

| Source ID | Heading | Paragraph | Code | Table |
| --- | --- | --- | --- | --- |
| PG-EXPLAIN | 4 | 82 | 32 | 0 |
| PG-MULTI | 1 | 12 | 3 | 0 |
| PG-PARTIAL | 1 | 30 | 11 | 0 |
| PG-STATS | 2 | 5 | 0 | 1 |

The second PG-STATS heading is `Note`, nested under its section's heading
path. This parser expects the pilot's explicitly closed DocBook HTML tags;
general web/PDF/Markdown and nested content tables are not supported.

## Not yet completed

- The exact thesis question/protocol, final corpus coverage, tool contracts
  and generator model are undecided. Nomic is selected for the initial embedding
  pilot. The initial documentation allowlist
  is PostgreSQL 18; the full corpus snapshot is not frozen.
- All four official HTML/manifest pairs are ready. Synthetic documents and
  DB fixtures remain unwritten. HTML is parsed and chunked; a local embedding
  adapter works, while corpus-wide embedding/indexing and retrieval are not implemented.
  P01–P06 have verified document answers/evidence; P07–P20 still need their
  answers verified against synthetic documents, saved sources or tool outputs.
- Supervisor feedback on the method draft, expected format and detail level
  has not been obtained.
- Beyond source loading, downloads, HTML parsing, chunking and local embedding,
  retrieval, generator LLM, tracing, tools, workflows and evaluation runners are
  not implemented. PostgreSQL Compose and the Python connection check work,
  and the retrieval tables and snapshot/chunk storage exist. The committed
  corpus import and vector search are pending;
  MLflow is not configured. No generator or
  RAG/evaluation run has been executed.
- There is no finalized three-workflow protocol or frozen test set; no
  performance result or thesis finding can be claimed.
- Metric definitions and the consistent result-record schema remain open.
  The literature table covers only the initial five studies.
- Router design and precise DB tool contracts remain open. Preserving quality
  or reducing cost has not been demonstrated.

## Open decisions and considerations

- How should the exact thesis question and experimental scope express the
  supervisor-supported Agentic RAG direction?
- The initial corpus is PostgreSQL docs plus synthetic local runbooks.
  The first four documentation sources/scopes are selected; the complete
  snapshot, final coverage and read-only DB tool contracts remain open.
- How should naive/enhanced/agentic boundaries and tool access be defined
  fairly? How should local and hosted model effects be measured separately?

## Latest assessment: corpus and tools

- **Confirmed:** The pilot uses PostgreSQL documentation and synthetic local
  runbooks. Save one major version's HTML with timestamps/hashes. The initial
  allowlist is PostgreSQL 18; its official
  [documentation](https://www.postgresql.org/docs/18/index.html) includes SQL,
  indexes, concurrency and performance.
- **Confirmed:** The assistant explains documentation and inspects an example
  PostgreSQL database. Non-retrieval tool candidates include reading schema/
  index information and obtaining a bounded sandbox
  [EXPLAIN plan](https://www.postgresql.org/docs/18/using-explain.html).
  This supports document-only and document-plus-DB-state questions. Freeze DB
  state for experiments and provide comparable relevant tool access to enhanced
  and agentic workflows.
- **Implemented HTML parser:** Python standard-library `html.parser`.
  **Implemented embedding:** The pinned local Nomic adapter described above.
  **Database-access decision:** Parameterized raw SQL without an ORM;
  Psycopg 3.3.8 is installed locally and environment settings are implemented;
  pgvector-python remains an optional adapter proposal. `check-db` has passed
  on the local service. Alembic revision `0001` is applied and verified;
  snapshot/chunk storage is prepared; committed import and vector search remain pending.
  Add the chosen LangGraph orchestration after a baseline built from simple
  Python functions; use MLflow to trace initial end-to-end runs.
  [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview),
  [Sentence Transformers](https://www.sbert.net/docs/sentence_transformer/usage/usage.html)
  and [MLflow LangGraph tracing](https://mlflow.org/docs/latest/genai/tracing/integrations/listing/langgraph/)
  capabilities were checked against official documentation. Embedding dependencies
  are available in the isolated smoke environment; LangGraph and MLflow remain uninstalled.
- **Approved evaluation direction:** Include a retrieval-free LLM-only control
  to examine prior PostgreSQL knowledge. Details are in the
  [evaluation plan](EVALUATION_PLAN.md#candidate-controls-for-prior-knowledge--postgresql-corpus-option):
  synthetic local runbooks/DB states, changed-evidence sensitivity and
  insufficient-evidence abstention. Retain LLM-only-correct questions. This
  approval does not finalize the whole protocol; sample size/rubric remain
  open and there are no model runs or a runnable evaluation dataset.
- **Next concrete task:** Run the prepared `scripts/import_corpus.py` for a
  committed import of the saved four snapshots and 49 chunks, then verify DB
  records and repeat-run counts. The current code has only been exercised with
  rollback, so the tables remain empty.
  `sql/retrieval/001_initial.sql` is still a comment-only scaffold, not an
  applied migration. Then embed/index the
  [49 verified chunks](CHUNKING.md) with the selected Nomic adapter. Use P01–P06
  for the first retrieval checks afterward. Generator selection and retrieval
  quality remain open; the smoke check establishes local execution only.

## First steps when returning

1. Revision `0001` is applied and the retrieval tables are empty. Run the
   prepared raw-SQL snapshot/chunk importer, then embed/index the corpus with
   the pinned Nomic adapter. Keep P01–P06 reference answers outside ingestion;
   use them to inspect retrieval. P07–P20 remain drafts, and the held-out
   thesis test set is still separate and unprepared.
2. Write synthetic runbooks and add Markdown ingestion. Keep gold answers and
   this plan out of the corpus.
3. Check retrieval on pilot document questions using the selected local
   embedding model and PostgreSQL + pgvector. Generator selection, LLM-only/Simple
   RAG answer runs and MLflow traces come afterward.
4. Create DB fixtures/tools, verify their gold answers, then implement enhanced
   and agentic workflows. Supervisor/method feedback and literature work may
   proceed in parallel; the final thesis protocol remains open.

Read this document with [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) and
[ROADMAP.md](ROADMAP.md) for orientation. After meaningful work, record actual
progress and the next concrete action here.
