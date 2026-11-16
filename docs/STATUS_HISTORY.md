# Project history

Dated implementation and verification records through 2026-11-17. Later entries
supersede earlier proposals, preparation holds and missing features. These
records do not establish current service health. Use [STATUS.md](STATUS.md) for
the current boundary and next step. Local report paths are Git-ignored.

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

- **2026-11-12, committed corpus import:** On the owner's instruction, ran
  `scripts/import_corpus.py` against the project DB. It committed four snapshots
  and 49 chunks. A fresh read-only connection verified every stored snapshot
  field and every chunk field, including exact embedding inputs and JSONB
  metadata. Counts by source are PG-EXPLAIN 37, PG-MULTI 3, PG-PARTIAL 5 and
  PG-STATS 4. Ran the script again and verified the same counts and content
  fingerprint from another connection. Embedding indexes/vectors remain empty.
  Record: `outputs/validation/corpus-import-committed-2026-11-12.json`.
  The six-question reference checker passed; code hashes matched the previously
  tested version. No code, dependency or schema changes were needed; the
  earlier 86-unit/3-integration-test suite was not repeated for this data-only
  step. No embedding, retrieval or model-answer run occurred.

- **2026-11-12, embedding storage:** Added `save_embedding_index(connection,
  index)` and `save_embeddings(connection, index_id, embeddings)` to `store.py`.
  The latter accepts `(chunk_id, EmbeddingResult)` pairs. Index metadata is
  immutable; document vectors must match the index model/revision/dimensions
  and the stored chunk input SHA-256. Nonfinite JSON values, missing chunks,
  stale hashes and conflicting vectors are rejected. Parameters use raw SQL;
  vector text is cast to `vector` without adding a pgvector adapter dependency.
- **89 offline unit tests and 8 opt-in PostgreSQL tests passed**. New tests
  cover validation, float32 round trips, identical/conflicting repeats, separate
  index scopes and rollback of an index plus earlier vectors after a batch
  failure. Tests use synthetic vectors and temporary tables, with no model
  inference. A read-only check confirmed `(4, 49, 0, 0)` public row counts and
  the same corpus fingerprint as the committed-import report. Record:
  `outputs/validation/embedding-store-2026-11-12.json`. No schema/dependency
  changes or production embedding writes occurred.

- **2026-11-12, corpus indexing script:** Added `scripts/index_corpus.py` and
  its dependency lockfile. It reads all chunk rows from the configured retrieval
  DB, preserves exact embedding inputs/counts and creates a deterministic index
  ID from sorted chunk/input hashes, model/revision and runtime settings.
  Metadata records prefixes, normalization, device/dtype, budget, library
  versions, model-manifest/lock hashes and code hashes. Index metadata and vectors
  share one transaction. The script loads only cached local model assets;
  the lockfile retains all existing smoke-environment versions and adds Psycopg,
  its binary package and the Windows-only timezone dependency.
- **92 offline unit tests and 11 opt-in DB tests passed**. New checks cover
  order-independent identity, changed inputs/configuration, DB-driven indexing,
  identical repeats, empty corpus and token-count mismatch. A separate check
  called the complete CLI twice with real local Nomic inference and blocked
  Python network access, inside a forced-rollback transaction. Both runs
  produced the same index ID and all 49 stored float32 vectors. Input hashes,
  768 finite values and unit norms were verified for every vector. Public
  counts returned to `(4, 49, 0, 0)`. Record:
  `outputs/validation/corpus-indexing-2026-11-12.json`. No committed indexing,
  retrieval or generation occurred; application dependencies/migrations were unchanged.

- **2026-11-12, committed indexing and progress visibility:** The owner ran
  the indexing command, then reported a blank terminal while it was working.
  Initial inspection found an active Python process; the later check confirmed
  it had finished with public counts `(4, 49, 1, 49)`. All committed vector/input
  hashes, dimensions and norms passed read-only validation. The index and
  vector fingerprint match the earlier real-model rollback verification.
  Record: `outputs/validation/corpus-indexing-committed-2026-11-12.json`.
- Added flushed stderr messages before model loading, for each chunk, before
  saving and after commit. Stdout remains the final JSON result. **93 offline
  unit tests and 11 opt-in DB tests passed**, including a new CLI test that
  checks progress appears before model loading and leaves stdout parseable.
  These tests used fake inference/temporary tables; no committed re-indexing
  was performed. The existing index retains its original code provenance;
  the logging edit changes the source hash for future index identities.

- **2026-11-13, initial fixed-workflow design approved:** The owner accepted
  Simple = dense retrieval + one answer call; Enhanced = dense/full-text hybrid
  retrieval + RRF merge/deduplication + reranking + the same answer setup.
  Shared controls include corpus/chunks, dense embedding configuration,
  generator/settings, answer prompt and maximum context token budget. Relevant
  Enhanced tool steps will be predefined in Python, without a model-directed
  loop or a requirement for native LLM function calling. Agentic keeps the
  shared-tool/dynamic-control direction, with detailed design deferred.
- Recorded development ablations (dense-only → hybrid-only → hybrid + reranking)
  and the scope for later additions. Reranker/generator models, candidate/context
  limits, fusion parameters and exact tool conditions remain open. Updated
  method/evaluation/context/roadmap/handoff/public-entry/code-structure notes.
  This was documentation-only: no code, DB, corpus or dependency changes and
  no new model/evaluation run. The next implementation step remains dense
  `search_chunks()` followed by query retrieval; hybrid/reranking come after
  that baseline. The DB counts above were last checked on 2026-11-12.

- **2026-11-14, dense SQL search:** Added `search_chunks(connection, index_id,
  query_vector, limit=5)` to `store.py`. It runs one parameterized SELECT,
  filters by index, sorts by cosine distance then chunk ID, and returns chunk
  text/token count, source/snapshot IDs, title/URL, metadata and distance.
  Empty/unknown indexes return no matches; wrong dimensions, zero/nonfinite
  query vectors and nonpositive limits fail. It neither connects nor commits.
- **96 offline unit tests and 14 opt-in PostgreSQL integration tests passed**.
  The three new DB tests cover cosine ranking versus vector magnitude, limits,
  source metadata, index isolation/bound parameters and transaction ownership.
  Before/after checks confirmed all public records unchanged, including the
  existing index/49 vectors. A separate read-only stored-vector self-search
  passed. No model inference, schema/dependency change, re-indexing or P01–P06
  evaluation occurred. `retrieval.py` remains a scaffold; composing query
  embedding and this search function is the next small step.

- **2026-11-14, query retrieval:** Added `store.get_embedding_index()` and
  `retrieve(connection, embedder, index_id, question, limit=5)` in `retrieval.py`.
  Before inference, it checks model/revision/dimensions and adapter/prefix/
  normalization/device/dtype/token-budget settings against the selected index.
  It then calls the existing query adapter and dense search. The caller loads/
  reuses the model and owns the connection/transaction; no gold data is read.
- **101 offline unit tests and 15 opt-in DB tests passed**. The pinned dataset
  reference checker also passed. A separate opt-in real-Nomic run loaded the
  model once, retrieved P01–P06 at five results, and repeated P01 with identical
  vectors/results. All public record hashes/counts matched the prior SQL check.
  The [development diagnostic](../data/evaluation/dev/README.md#first-dense-retrieval-check)
  records annotated-evidence ranks: P01/P02/P03/P04/P06 have reference hits;
  P05 has none in the top five. This is an observed retrieval limitation, not
  a failed SQL test or a correctness grade. Next inspect P05's ranking.
  No corpus/gold changes, re-indexing, migration, new dependency, generation,
  hosted API call or held-out evaluation occurred. The retrieval CLI,
  generator/model selection and final evaluation protocol remain future work.

- **2026-11-14, P05 diagnosis:** Retrieved all 49 ranks for the unchanged P05
  and three exploratory wording probes. Original E1/E2/E3 rank at 17/11/46.
  Adding only `multicolumn` moves E1/E2 to 1/2; replacing concrete column names
  with first/second-column names gives 2/1. Removing the final EXPLAIN-path
  request alone gives 16/11/49. These observations show dense-ranking wording
  sensitivity, not an established internal model mechanism or a selected fix.
- All 49 vectors/evidence chunks are present; input hashes, dimensions and norms
  passed. SQL distances matched independent Python cosine calculations within
  `1e-6`, and the original query vector/top five matched the prior report.
  Public contents remained unchanged under read-only access. No application,
  corpus/gold, index, dependency or schema changes occurred. Tests were not
  repeated for this diagnostic-only session. Results and limits are in the
  [development guide](../data/evaluation/dev/README.md#p05-wording-diagnosis)
  and `outputs/validation/p05-retrieval-diagnostic-2026-11-14.json`.

- **2026-11-14, repeatable retrieval checker:** Added
  `scripts/check_retrieval.py` and its dependency lockfile, preserving all 66
  existing indexer package records. The owner approved checking the original
  P01–P06 at 5/10/20 as development diagnostics. The script validates pinned
  references, loads the local model once, opens a read-only connection and
  obtains full ranks once per question. It records annotated evidence ranks/
  cutoff IDs and ranked source/chunk metadata with version/hash provenance in
  a fresh `outputs/retrieval/dense-<UTC timestamp>.json`. It prints progress.
- **104 offline unit tests passed**, including cutoff-boundary, missing-
  evidence, raw-question-isolation and empty-index checks. `--help` and locked
  dependency validation passed. Two actual locked CLI runs produced identical
  ranks/coverage in distinct reports and matched the previous top-five baseline.
  All public row counts/hashes remained unchanged at `(4, 49, 1, 49)`. P05 has
  0/3, 0/3 and 2/3 annotated hits at 5/10/20; P06 stays at 2/4, with evidence
  alternatives still applicable. These are annotation counts, not answer grades.
  The production cutoff, corpus/gold, index, schema and generator are unchanged.
  Report: `outputs/validation/check-retrieval-2026-11-14.json`. Earlier DB tests
  were not repeated; the new checker was verified through real read-only CLI runs.

- **2026-11-16, tracing direction changed:** The owner explicitly rejected
  MLflow and requested handling logging in the project. Updated current stack,
  roadmap, handoff and code responsibilities to use project-owned PostgreSQL
  tracing via Psycopg/raw SQL. Added [TRACING_PLAN.md](TRACING_PLAN.md) with a
  proposed two-table question-trace/operation-span structure, safe payloads,
  ID relationships and a staged retrieval-first implementation sequence.
  This supersedes the earlier MLflow selection; the schema proposal is not
  approved DDL or implemented logging. No migration, dependency, DB/model run,
  corpus/gold change or runtime behavior change occurred. Prior verification
  results remain dated evidence; no live service check was run in this session.

- **2026-11-16, tracing code/migration prepared only:** On the owner's request,
  prepared raw-SQL revision `0002_create_tracing_tables.py` for `traces` and
  `spans`, four lifecycle writers and `retrieve_with_trace()` in `tracing.py`.
  The wrapper logs safe retrieval inputs, ranked source/chunk references and
  success/error through a separate autocommit writer. Completed records cannot
  be overwritten. Unknown usage/cost stay NULL; logging failures abort instead
  of silently losing observations. Prompt/usage/tool fields exist, but those
  workflows are not implemented. The checker now has opt-in `--trace`, with
  per-question trace IDs linked to its batch ID and independent JSON report.
- **114 offline unit tests passed**. Upgrade and downgrade rendered offline
  and parsed with pglast 8.7. Four new tracing DB tests were discovered and
  skipped because `0002` is not applied; no live tracing DDL/DML ran. A full
  default locked checker run without `--trace` matched prior ranks/coverage and
  preserved all public records at `(4, 49, 1, 49)`. Read-only checks confirmed
  DB revision `0001` and absent `traces`/`spans`. Repository head is `0002`.
  Verification: `outputs/validation/tracing-schema-0002/prepared-2026-11-16.json`.
  SQL previews are in the same directory. **Stop for owner review before
  applying migration or running `--trace`.** No dependency/model/corpus/gold
  changes, generation or hosted API calls occurred.

- **2026-11-16, tracing migration applied and one question tested:** The owner
  explicitly requested applying `0002`, lifting the prior review hold. Verified
  unchanged prepared-file hashes and baseline data, then ran `alembic upgrade 0002`.
  DB revision is `0002`; `traces`/`spans`, their columns and constraints exist.
  All four new tracing DB tests passed in temporary table clones, including
  parent-trace isolation and logging surviving retrieval transaction rollback.
- Ran only P04 with real local Nomic and `retrieve_with_trace()` at five results.
  A fresh read-only connection confirmed one `ok` trace and one `ok` span,
  exact query/source payloads, chunk ranks/distances and NULL answer/usage/cost.
  P04-E1 and P04-E2 ranked 1 and 2. Trace ID:
  `db808e0d-76ed-4148-9996-2a8988cc4ce7`. Corpus/index row counts and fingerprints
  are unchanged at `(4, 49, 1, 49)`; only the authorized tracing tables/records
  and revision metadata changed. No generated answer or hosted API call occurred.
  Record: `outputs/validation/tracing-schema-0002/applied-2026-11-16.json`.
  The full six-question traced checker batch has not run; the one-question
  verification satisfies this step. Generator/context/prompt work is next.

## Luna client preparation — 2026-11-17

- `GeneratorSettings` and `[generator]` config select Luna without loading
  the SDK or making network calls. `llm.generate_text()` makes one Responses
  API call and returns text, completion status, provider IDs and usage.
- `scripts/llm_smoke.py` and its lock pin OpenAI `3.51.0`. The SDK is installed
  locally and the locked script environment is prepared. An explicit
  `--call-api` and `OPENAI_API_KEY` are required. The client uses Standard
  processing, `store=False`, a 30-second timeout and zero automatic retries.
- All **124 offline unit tests passed**, including ten new generator/smoke
  tests. The six-question reference checker passed. Real-SDK mock-transport
  checks passed for completed, incomplete and HTTP 429 responses, with one
  intercepted request per case and socket networking blocked.
- A live call was not possible: the API key is absent. No hosted inference,
  DB writes, migration or LLM trace occurred. The smoke script reads no corpus. Record:
  `outputs/validation/luna-client-2026-11-17.json`.
- Next: set the key locally and run the documented opt-in smoke. Then prepare
  the source-linked context/answer prompt and connect one P04 answer.
