# Code structure — implemented and planned components

**Updated:** 2026-11-17. This guide maps module boundaries and planned files.
A file's existence does not imply implemented behavior. Use [STATUS](STATUS.md)
for progress and [HANDOFF](HANDOFF.md) for artifacts/resume commands.

## Core approach

Use one Python package: `src/rag_workflow_lab/`. Share ingestion, embeddings,
storage, retrieval, LLM calls and database tools. Workflow files compose these
components without copying retrieval/model code into each workflow. Build the
first baseline from small Python functions; add the LangGraph dependency when
implementing the agentic workflow.

**Initial workflow design approved, 2026-11-13:** `simple.py` composes
dense retrieval and one answer call. `enhanced.py` will compose dense/full-text
hybrid retrieval, RRF merge/deduplication and reranking with the same answer
setup, plus relevant tool steps controlled by predefined Python conditions.
Native LLM function calling is not required for that initial Enhanced design.
Agentic details are deferred. Reranker/final generator settings, numeric budgets
and exact tool conditions remain open. Simple has one verified live P04 run;
the remaining workflows are scaffolds. See
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

These are completion criteria, not claims that the workflows exist. Tests
use standard-library `unittest`; paid calls and DB/model checks are opt-in.
Commands are in [README](../README.md#verification), dated results in
[history](STATUS_HISTORY.md).

## Current functional boundary

Source loading/downloading/parsing, section-aware chunking, local Nomic,
immutable raw-SQL storage and dense query retrieval are implemented. Four
snapshots produce 49 chunks and one index/49 vectors. The repeatable checker
records P01–P06 ranks/annotated hits; retrieval tracing is applied and verified.

`llm.build_answer_input()` labels whole retrieved chunks S1–S5 and excludes
gold. `workflows.simple.answer_question()` combines retrieval and one
`llm.generate_text()` call using `answer_v1`; the workflow owns one trace with
retrieval and LLM spans. `scripts/run_simple_rag.py` and its lock provide an
explicit opt-in single-question or batch runner. It reuses model/connections,
shares a batch run ID and preserves per-question JSON records. The former P04
smoke script was renamed and generalized; the live batch is pending. One live answer passed
editorial review; broader answer evaluation and other workflows remain open.
Tools, full evaluation and LangGraph remain scaffolds.
See [chunking](CHUNKING.md), [embedding setup](EMBEDDING_SETUP.md),
[DB setup](POSTGRES_SETUP.md) and [tracing](TRACING_PLAN.md) for contracts.
