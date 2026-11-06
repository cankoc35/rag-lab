# Code structure — proposal

**Last updated:** 2026-11-05. **Status:** The owner requested the planned
files while preserving existing files and folders; the scaffold now exists.
CLI help/version, config and source-manifest loading/validation work.
Unimplemented modules contain responsibility docstrings; SQL, Compose and
prompts do not yet provide application behavior. The source allowlist was
populated with four PostgreSQL 18 records on 2026-11-02. Loading/validation,
shared source/snapshot types, single-source downloading and the offline HTML
parser/`parse-source` command and section-aware chunking are implemented.
The offline corpus script uses a cached tokenizer; this did not select a model,
freeze the full corpus or finalize the experimental protocol.

## Core approach

Use one Python package: `src/rag_workflow_lab/`. Share ingestion, embeddings,
storage, retrieval, LLM calls and database tools. Workflow files compose these
components without copying retrieval/model code into each workflow. Build the
first baseline from small Python functions; add the LangGraph dependency when
implementing the agentic workflow.

The tree below was initially a staged file-creation plan. At the owner's later
explicit request, scaffold files were created together; functional implementation
still follows the stages below. `__main__.py` also provides the `python -m`
entry point. Package `__init__.py` files are omitted from the tree for brevity.

## Target file tree

```text
rag-workflow-lab/
├── pyproject.toml                 # Package, required dependencies, CLI entry
├── .env.example                   # Environment example without secret values
├── compose.yaml                   # Local PostgreSQL; MLflow when needed
├── configs/
│   └── pilot.toml                 # Explicit experiment/model/retrieval settings
├── sql/
│   ├── retrieval/001_initial.sql  # Source, section/chunk and vector tables
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
│   ├── tracing.py                # MLflow integration and shared span fields
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
| `contracts.py` | Define shared source/section, chunk, retrieved-evidence, answer, tool-result and usage fields. | Simple data types without LangGraph, SQL or MLflow dependencies. Add types as needed. |
| `ingestion/` | Download/read, clean and split sources, then coordinate indexing steps. | Never scan gold answers, evaluation directories or the entire repository. HTML and Markdown should share a section contract. |
| `embeddings.py` | Generate document/query embeddings with the same model/revision and compatible settings. | No database or workflow decisions; models may expose distinct query/document methods. |
| `store.py` | Execute source/chunk upserts and metadata-filtered vector-search SQL. | No LLM calls. Reject queries with mismatched model/index identity or vector dimensions. |
| `retrieval.py` | Embed questions, search the correct corpus/index scope and return scored evidence. | Does not generate answers; workflows and the retrieval tool share this implementation. |
| `llm.py` and `prompts/` | Provider calls, selected model settings, usage/errors and versioned prompts. | Does not select a retriever or access gold data. One concrete adapter is sufficient initially; avoid a generic provider framework. |
| `workflows/` | Determine the order of source access and model/tool calls. | Do not reimplement shared retrieval/storage. Simple and LLM-only do not require LangGraph. |
| `tools/` | Expose retrieval and validated read-only operations on a separate sandbox. | Cannot open evaluation gold, other states or retrieval/MLflow databases. |
| `tracing.py` | Record MLflow traces with shared trace/span fields. | Does not select workflows or hold the sole copy of measurement outputs. |
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
- Proposed: use separate databases/roles for retrieval, sandbox and MLflow
  within one PostgreSQL service. `store.py` uses the retrieval role;
  `tools/database.py` uses a sandbox read-only role. MLflow manages its own
  backend. Final Compose isolation is an implementation decision.
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
| 3 — Answers and control | `llm.py`, answer prompt, `workflows/simple.py`, `workflows/llm_only.py`, `tracing.py`, `evaluation/` | Record cited answers/abstention and LLM-only outputs on the same questions; link raw records to MLflow traces. Model tests are opt-in. |
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
Tests use standard-library `unittest`; RAG/model dependencies are not installed.
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
All 48 offline unit tests pass. See [CHUNKING.md](CHUNKING.md) for the API and
reproduction command. Embeddings, database connections, LLM calls and LangGraph
remain later stages.

Related plans: [Pilot scope](PILOT_SCOPE.md), [method](METHOD_DESIGN.md),
[evaluation](EVALUATION_PLAN.md) and [roadmap](ROADMAP.md).
