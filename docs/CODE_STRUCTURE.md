# Code structure — implemented and planned components

**Last updated:** 2026-11-17. **Status:** The owner requested the planned
files while preserving existing files and folders; the scaffold now exists.
CLI help/version, config and source-manifest loading/validation work.
Unimplemented modules contain responsibility docstrings, and prompts remain
scaffolds. Raw-SQL Alembic revision `0001` created the four retrieval tables;
`store.py` implements the read-only connection check and raw-SQL snapshot,
chunk, embedding-index and vector save functions, plus dense `search_chunks()`.
`scripts/import_corpus.py`
coordinates snapshot/chunk writes; `scripts/index_corpus.py` now coordinates
local embedding and index/vector writes. `store.get_embedding_index()` reads
index metadata, and `retrieval.retrieve()` composes compatibility checks, local
query embedding and dense search with a caller-supplied model/connection.
PostgreSQL + pgvector Compose and the extension bootstrap are configured and
verified. The source allowlist was
populated with four PostgreSQL 18 records on 2026-11-02. Loading/validation,
shared source/snapshot types, single-source downloading and the offline HTML
parser/`parse-source` command and section-aware chunking are implemented.
The initial local Nomic embedding adapter is also implemented and passed a
document/query runtime check. The full corpus and experimental protocol remain
open. See [HANDOFF.md](HANDOFF.md) for local inputs and P05's retrieval limitation;
the service was healthy on 2026-11-14, with four snapshots, 49 chunks and 49 vectors.

## Core approach

Use one Python package: `src/rag_workflow_lab/`. Share ingestion, embeddings,
storage, retrieval, LLM calls and database tools. Workflow files compose these
components without copying retrieval/model code into each workflow. Build the
first baseline from small Python functions; add the LangGraph dependency when
implementing the agentic workflow.

**Initial workflow design approved, 2026-11-13:** `simple.py` will compose
dense retrieval and one answer call. `enhanced.py` will compose dense/full-text
hybrid retrieval, RRF merge/deduplication and reranking with the same answer
setup, plus relevant tool steps controlled by predefined Python conditions.
Native LLM function calling is not required for that initial Enhanced design.
Agentic details are deferred. Reranker/generator selection, numeric budgets
and exact tool conditions remain open. These are planned module responsibilities;
the implementations are still scaffolds. See
[METHOD_DESIGN.md](METHOD_DESIGN.md#approved-initial-simple-and-enhanced-design).

The tree below was initially a staged file-creation plan. At the owner's later
explicit request, scaffold files were created together; functional implementation
still follows the stages below. `__main__.py` also provides the `python -m`
entry point. Package `__init__.py` files are omitted from the tree for brevity.

## Target file tree

```text
rag-workflow-lab/
├── pyproject.toml                 # Package, required dependencies, CLI entry
├── .env.example                   # Environment example without secret values
├── compose.yaml                   # Local PostgreSQL + pgvector
├── alembic.ini                    # Migration configuration, no credentials
├── migrations/
│   ├── env.py                    # Connection from existing POSTGRES_* settings
│   └── versions/
│       ├── 0001_create_retrieval_tables.py  # Applied raw-SQL schema
│       └── 0002_create_tracing_tables.py   # Applied trace/span schema
├── configs/
│   └── pilot.toml                 # Explicit experiment/model/retrieval settings
├── sql/
│   ├── retrieval/000_extensions.sql  # Docker bootstrap: vector extension
│   ├── retrieval/001_initial.sql  # Preserved comment-only scaffold
│   └── sandbox/001_initial.sql    # Later: example database and fixture tables
├── src/rag_workflow_lab/
│   ├── __init__.py
│   ├── cli.py                    # User commands and component setup
│   ├── config.py                 # Settings loading and validation
│   ├── contracts.py              # Shared data types; no I/O
│   ├── ingestion/
│   │   ├── download.py           # load_sources/download_source; raw HTML/hash
│   │   ├── parse.py              # HTML/synthetic Markdown → source sections
│   │   ├── chunk.py              # Sections → source-linked chunks
│   │   └── pipeline.py           # Parse/chunk; embed/store once indexing exists
│   ├── embeddings.py             # Document/query embedding generation
│   ├── store.py                  # Retrieval DB connection, writes, vector SQL
│   ├── retrieval.py              # Query embedding → scoped chunk search
│   ├── llm.py                    # Selected provider/model calls and usage
│   ├── prompts/
│   │   ├── answer_v1.md          # Cited answer / insufficient-evidence prompt
│   │   └── agent_v1.md           # Later: tools and stopping rules
│   ├── workflows/
│   │   ├── llm_only.py           # Control without sources/tools
│   │   ├── simple.py             # One retrieval → answer
│   │   ├── enhanced.py           # Later: predefined, bounded steps
│   │   ├── agentic.py            # Later: LangGraph state/node/edge flow
│   │   └── router.py             # Last: select and run a suitable workflow
│   ├── tools/
│   │   ├── retrieval.py          # Tool interface to the shared retriever
│   │   └── database.py           # Read-only DB inspection and allowed EXPLAIN
│   ├── tracing.py                # Prepared trace/span writers and retrieval wrapper
│   └── evaluation/
│       ├── dataset.py           # Question/gold loading, ID and split validation
│       ├── runner.py            # Compared runs under fixed configuration
│       ├── records.py           # Per-run metadata and raw outputs
│       └── metrics.py           # Defined measurements and summary calculations
├── data/
│   ├── corpus/
│   │   ├── sources.json          # Allowed sources, version and section scope
│   │   └── synthetic/            # Atlas inventory and operations runbook
│   ├── evaluation/
│   │   ├── dev/                 # Development questions and separate gold records
│   │   └── heldout/             # Separate final test set, prepared later
│   ├── scenarios/               # Synthetic state A/B/... definitions
│   └── local/                   # Git-ignored: raw HTML and processed artifacts
├── outputs/                     # Git-ignored: config, runs, judgments, summaries
├── tests/
│   ├── fixtures/                # Small HTML and synthetic examples
│   ├── unit/                    # Meaningful checks without APIs/databases
│   └── integration/             # Opt-in local DB; hosted/paid runs also opt-in
└── docs/                        # Existing project and research documentation
```

## File responsibilities and boundaries

| Component | Responsibility | Dependency boundary |
| --- | --- | --- |
| `cli.py` | Parse the command, construct components and invoke the relevant pipeline/workflow. | Do not accumulate business logic or SQL here. |
| `config.py` | Validate file/environment settings, corpus/index versions and model settings. | No model download, database or API call during import. Never include secrets in public run configuration. |
| `contracts.py` | Define shared source/section, chunk, retrieved-evidence, answer, tool-result and usage fields. | Simple data types without orchestration or database-driver dependencies. Add types as needed. |
| `ingestion/` | Download/read, clean and split sources, then coordinate indexing steps. | Never scan gold answers, evaluation directories or the entire repository. HTML and Markdown should share a section contract. |
| `embeddings.py` | Generate document/query embeddings with the same model/revision and compatible settings. | No database or workflow decisions; models may expose distinct query/document methods. |
| `store.py` | Execute source/chunk upserts and metadata-filtered vector-search SQL. | No LLM calls. Reject queries with mismatched model/index identity or vector dimensions. |
| `retrieval.py` | Embed questions, search the correct corpus/index scope and return scored evidence. | Does not generate answers; workflows and the retrieval tool share this implementation. |
| `llm.py` and `prompts/` | Provider calls, selected model settings, usage/errors and versioned prompts. | Does not select a retriever or access gold data. One concrete adapter is sufficient initially; avoid a generic provider framework. |
| `workflows/` | Determine the order of source access and model/tool calls. | Do not reimplement shared retrieval/storage. Simple and LLM-only do not require LangGraph. |
| `tools/` | Expose retrieval and validated read-only operations on a separate sandbox. | Cannot open evaluation gold, other states, retrieval storage or trace records. |
| `tracing.py` | Raw-SQL trace/span lifecycle writes and explicit traced retrieval. | Uses a caller-owned writer; the wrapper requires a separate autocommit connection. Migration `0002` and one real P04 trace/span are verified. |
| `evaluation/` | Load separate questions, run workflows, preserve raw outputs and score afterward. | Pass only allowed questions/source access to workflows/models; gold/rubric is evaluation-only. |

`workflows/agentic.py` may hold the initial graph's state and node definitions
together. Split into `workflows/agentic/` if actual complexity warrants it.
Likewise, split `database.py` tools into separate files when needed. There is
no initial need for a provider/plugin registry, generic repository pattern or
a separate class for every operation.

## Data flows

```text
Index preparation:
sources.json → download → parse → chunk → embeddings → store

Simple RAG:
question → retrieval (embeddings + store) → answer prompt → llm → cited answer

Control condition:
question → llm_only → llm → answer

Agentic, later:
question → LangGraph → retrieval / database tools → observations → next step
```

Simple, enhanced and agentic share `retrieval.py`, `embeddings.py`, `llm.py`
and appropriate tools. `tools/retrieval.py` wraps the existing retriever rather
than introducing a new search algorithm. `router.py` executes the selected
workflow; `evaluation/runner.py` runs all arms for offline evaluation. The
router must not access gold labels or other arms' outputs.

## Data and database separation

- Select sources through `data/corpus/sources.json`. Store official HTML
  snapshots under `data/local/` with hashes and manifest metadata. Preserve
  the snapshots or explicit download information for reproducibility; a hash
  alone cannot recover the content.
- Version synthetic corpus documents separately. Chunks retain raw-source
  snapshot, section/anchor and location metadata. Associate chunk identity
  with content and chunking version; re-indexing must not create duplicates.
- Keep `data/evaluation/` and gold files outside the source allowlist. Separate
  development and future held-out sets; scenario-family A/B variants stay in
  one split. Never pass the dataset path to a model or tool.
- Proposed: isolate retrieval, sandbox and trace access through database roles
  and allowed schemas. The initial custom trace tables can use the application
  database; a separate writer connection preserves read-only retrieval.
  Sandbox tools must not access trace/corpus storage. Exact deployment isolation
  remains open. The trace schema/writers are applied and verified;
  see [TRACING_PLAN.md](TRACING_PLAN.md).
- Label synthetic observation states separately from measured DB telemetry.
  The runner binds the state to the tool; the model cannot change states and
  read A/B results together. Keep sandbox setup/evaluation state-loading
  privileges separate from the tool.
- Preserve resolved, redacted configuration, corpus/index/model/prompt/code/
  tool IDs, per-attempt raw run records, separate judgments and derived
  summaries under `outputs/<experiment_id>/`. Never change raw outputs during
  re-scoring. Include router overhead and failures. Final record schema is
  tied to the evaluation protocol.

## Implementation order

| Stage | Components to add | Verification / completion criteria |
| --- | --- | --- |
| 1 — Sources and ingestion | `pyproject.toml`, CLI/config/contracts, `ingestion/`, source allowlist and snapshot manifests; Markdown reading once synthetic documents exist | Correct section/text/code extraction, retained URLs/anchors and controlled repeat runs. Small offline parser/chunk checks cover real HTML structure and code blocks. |
| 2 — Retrieval | `embeddings.py`, `store.py`, `retrieval.py`, retrieval SQL, database Compose and configuration | Inspect expected evidence for pilot document questions; verify corpus/index/model alignment and repeated indexing. Explicitly run embedding/DB checks; no model downloads in default tests. |
| 3 — Answers and control | `llm.py`, answer prompt, `workflows/simple.py`, `workflows/llm_only.py`, `tracing.py`, `evaluation/` | Record cited answers/abstention and LLM-only outputs on the same questions; link raw records to project-owned traces. Model tests are opt-in. |
| 4 — DB tools and enhanced/agentic | `tools/`, sandbox SQL/states, `enhanced.py`, `agentic.py`, agent prompt | Tool questions correctly label real/synthetic states; enhanced and agentic have comparable relevant tool access and loop limits. |
| 5 — Router | `workflows/router.py` and routing config/prompt if needed | Add routing after fixed-workflow comparison works; record decision overhead and errors. |

The RAG checks above are planned verification. Initial scaffold checks with
Python 3.11 passed compilation of 29 files, imports of 28 submodules, CLI
help/config, TOML/JSON metadata and `docker compose config --quiet`.
Compose validation covered an empty service scaffold, not a running database.
The source loader added 9 offline tests and `check-sources`. The downloader
brought the total to 19 and separately downloaded/hash-checked PG-EXPLAIN.
On 2026-11-05, the remaining three sources were downloaded; all four HTML/
manifest pairs were checked for hash, size and title, and the PG-STATS target
section ID exists. That download-only step did not change code or rerun tests.
The parser step on the same day added 16 tests; all 35 offline unit tests
passed. All four real snapshots were parsed through the CLI with network
access blocked; outputs were saved as `data/local/parsed/<snapshot_id>.json`.
These are historical results from the scaffold/parser stages. Tests use
standard-library `unittest`; later embedding and DB checks are described below.
Actual commands are documented in README.

## Current functional boundary

Package/CLI, source allowlist, source loading/validation, single-source
downloading and HTML parsing are ready. All four selected HTML snapshots
are saved and recorded in STATUS. `parse_html(bytes, snapshot)` operates in
memory; `parse_snapshot(manifest_path, source)` reads local HTML/manifest files.
The latter verifies allowlist matching, response metadata, safe local paths,
byte size and SHA-256. `parse-source` prints JSON without changing inputs or
making HTTP requests.

`ParsedDocument` holds source/snapshot IDs, URL, raw hash, parser version and
ordered `ParsedBlock` records. Each block has kind/text, heading path and an
anchor. `TableCell` preserves text, header status, rowspan and colspan.
This version targets PostgreSQL's explicitly closed DocBook HTML; Markdown,
arbitrary web layouts and nested content tables are unsupported.

`chunk_document()` now groups whole content blocks within heading boundaries,
with 512/1024-token defaults, no overlap and explicit overflow errors. `Chunk`
and `TokenizerSpec` retain source-block and tokenizer provenance, exact counted
embedding inputs and neighbor IDs. The counter is supplied by the caller;
the application adds no tokenizer dependency. The standalone
`scripts/chunk_corpus.py` uses an isolated cached tokenizer and verifies all
four sources offline: 49 chunks, all 46 code blocks and the table intact.
The chunking step passed 48 offline unit tests; the embedding step brings the
total to 59. See [CHUNKING.md](CHUNKING.md) for the chunk API and reproduction
command. `embeddings.py` now explicitly loads a pinned, checksummed local
Nomic snapshot and produces normalized document/query vectors, with an
injected backend seam for offline tests. `scripts/embedding_smoke.py` is the
opt-in runtime command; its dependency lockfile and model manifest support
reproducibility. [EMBEDDING_SETUP.md](EMBEDDING_SETUP.md) records its results.
The optional `database` extra now pins Psycopg 3.3.8. `config.py` also provides
explicit `POSTGRES_*` environment loading with validation and password-safe
repr, independently of TOML/ingestion settings. Ten additional offline tests
bring the total to 69. The subsequent `check-db` command in `cli.py` calls
`store.check_database()` for read-only raw-SQL connectivity/version/extension
checks. Eleven fake-driver/CLI tests bring the total to 80; the explicit live
command passed against PostgreSQL 18.6 + pgvector 0.8.7. Corpus-wide
embedding/indexing, vector search, generator calls and LangGraph
remain later stages. Alembic is now installed and configured through
`alembic.ini` and `migrations/env.py`. Manual raw-SQL revisions belong under
`migrations/versions/`. Revision `0001_create_retrieval_tables.py` was applied
on 2026-11-07 and its four empty retrieval tables were verified.

On 2026-11-12, `save_snapshots(connection, snapshots)` and
`save_chunks(connection, chunks)` were added. The standalone importer reads
saved artifacts, validates snapshot/provenance links and owns one transaction.
Matching records can be repeated; conflicting IDs raise an error. All chunk
fields outside dedicated columns are preserved in JSONB metadata. The step
passed 86 offline tests, three opt-in DB tests and a full-corpus round trip
with rollback. The owner subsequently requested execution of the importer;
four snapshots and 49 chunks are now committed, with exact field checks and
an unchanged second-run fingerprint. Corpus embedding/indexing and vector
search remain next steps. Subsequently, `save_embedding_index(connection, index)`
and `save_embeddings(connection, index_id, embeddings)` were added, accepting
index dictionaries and `(chunk_id, EmbeddingResult)` pairs. They reject
conflicting records and mismatched model/revision/dimensions, task or chunk
input hashes. The caller owns the transaction. The step passed 89 offline
tests and eight opt-in DB tests with synthetic vectors; public corpus contents
were unchanged and no production embeddings were stored in that step.

The subsequent `scripts/index_corpus.py` reads all stored chunk inputs,
verifies their token counts with the local Nomic adapter and creates a stable
index identity from sorted chunk/input hashes and model/runtime metadata.
The metadata includes code/model/lock hashes and library versions. The script
owns one DB transaction; repeat runs must reproduce the existing vectors.
Its separate lockfile retains the smoke environment's ML versions and adds
Psycopg. Checks passed: 92 offline tests, 11 opt-in DB tests and two complete
real-Nomic CLI runs with identical results and forced rollback. The owner later
ran committed indexing; one index and 49 vectors match those verified results.
The indexer now emits immediate phase/chunk progress to stderr and final JSON
to stdout (93 offline tests and 11 DB tests passed at that step).

On 2026-11-14, `store.search_chunks(connection, index_id, query_vector, limit=5)`
added one parameterized SELECT for exact cosine ranking within one index.
It returns source-linked dictionaries without committing; equal distances
are ordered by chunk ID. Invalid dimensions, zero/nonfinite vectors and
nonpositive limits are rejected. Checks passed: 96 offline unit tests and
14 opt-in DB tests, with public contents unchanged. Query embedding/search
orchestration in `retrieval.py` followed this SQL-only step.

`retrieve(connection, embedder, index_id, question, limit=5)` is now implemented.
It reads index metadata through the store and checks model/revision/dimensions,
adapter, prefixes, normalization, device/dtype and token budget before inference.
It then forwards raw question text to the existing query adapter and passes
the vector to dense search. Model loading and transaction ownership remain
with the caller. No new framework/dependency or retrieval CLI was added.
Checks passed: 101 offline unit tests, 15 DB tests and a six-question real-model
diagnostic with an identical P01 repeat and unchanged public records. P05 has
no annotated evidence in the top five; see the
[development results](../data/evaluation/dev/README.md#first-dense-retrieval-check).

`scripts/check_retrieval.py` now makes the development check repeatable. It
validates pinned P01–P06 references, reuses one local model, runs read-only
retrieval once per question across the selected index, then records reference
ranks and hits at 5/10/20. Every run writes JSON under `outputs/retrieval/` with
dataset/index/model/runtime/code/lock provenance. It has an explicit `--index-id`
and its own lock preserving existing dependency versions. Checks: 104 offline
unit tests and two complete locked real-model runs with identical ranks/coverage
and unchanged public data. The generator, answer prompt and Simple workflow
follow the first custom retrieval-tracing increment. See the
[checker guide](../data/evaluation/dev/README.md#repeatable-retrieval-checker).

Related plans: [Pilot scope](PILOT_SCOPE.md), [method](METHOD_DESIGN.md),
[evaluation](EVALUATION_PLAN.md) and [roadmap](ROADMAP.md).

On 2026-11-16, migration `0002` and the custom tracing code were prepared,
then applied on the owner's explicit instruction.
`tracing.py` provides start/finish writers plus `retrieve_with_trace()`, with
safe ranked chunk payloads, immutable completion and fail-fast logging. The
checker has opt-in `--trace`, linked question/batch IDs and an independent writer.
114 offline tests passed; SQL rendered/parsed offline and the default real-model
checker preserved baseline results and DB records during preparation. After
application, all four tracing DB tests passed and one real P04 query persisted
one verified `ok` trace/span. DB/repository are `0002`; corpus/index contents
are unchanged. See [TRACING_PLAN.md](TRACING_PLAN.md).

On 2026-11-17, the owner approved the initial Luna client step.
`config.GeneratorSettings` and `[generator]` in `configs/pilot.toml` select
`gpt-6-luna`, reasoning `none` and maximum 1000 output tokens. `llm.generate_text()`
uses a caller-owned OpenAI SDK client and returns text/status/IDs/usage, with
no DB access. `scripts/llm_smoke.py` and its lock pin SDK `3.51.0`; the script
requires `--call-api` and an environment key for one fixed English request.
124 unit tests and three real-SDK mock-transport checks passed offline.
The API key is absent, so no hosted inference is verified. Next: run the
[explicit smoke](../README.md#check-the-luna-api-client), then prepare the
context/answer prompt and Simple workflow with LLM tracing.
