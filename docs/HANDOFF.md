# Session handoff

**Updated:** 2026-11-17. Use [STATUS](STATUS.md) for the current boundary and
[STATUS_HISTORY](STATUS_HISTORY.md) for dated evidence. Scaffolds are not features.

## Read first

Verify `/Users/cankoc/Desktop/rag-workflow-lab`, then read [AGENTS](../AGENTS.md),
[README](../README.md), [PROJECT_CONTEXT](PROJECT_CONTEXT.md), [STATUS](STATUS.md)
and [ROADMAP](ROADMAP.md), in that order. Read METHOD_DESIGN/EVALUATION_PLAN
before experiment changes and LITERATURE_GAPS before novelty claims.

## Goal and established decisions

Build a PostgreSQL documentation/sandbox assistant for an Agentic RAG thesis.
The working study compares Simple, Enhanced, Agentic and a later router;
the exact research question and final protocol remain open.

- English repository; Turkish chat. Small, testable steps and simple code.
- Docker PostgreSQL + pgvector; Psycopg raw SQL without ORM; Alembic migrations.
- Local Nomic for embeddings, Luna Responses API for the first generator.
- Project-owned PostgreSQL tracing; MLflow rejected. LangGraph selected but uninstalled.
- Public docs + synthetic runbooks/frozen DB state; LLM-only, changed-evidence
  and insufficient-evidence controls. Keep development and held-out data separate.

## Approved initial workflow decisions

Simple = dense retrieval + one answer call. Enhanced = dense/full-text search,
RRF merge/deduplication, reranking + the same answer setup; relevant tools
follow fixed Python conditions. Share corpus/chunks, embedding and generator
settings, answer prompt and maximum context budget. Both cite evidence/may
abstain. Agentic tool access should be comparable; its dynamic control details
are deferred. Dense-only → hybrid-only → hybrid + reranking are development
ablations. Exact tools, reranker and final budgets remain open. See
[METHOD_DESIGN](METHOD_DESIGN.md#approved-initial-simple-and-enhanced-design).

## Actual stopping point

Four saved sources produce 49 chunks; one Nomic index/49 vectors are committed.
Dense retrieval and the P01–P06 checker work. P05's evidence ranks 17/11/46
show wording sensitivity; review the [diagnostic](../data/evaluation/dev/README.md#p05-wording-diagnosis).
Revision `0002` and retrieval tracing are applied; one real P04 trace/span is
verified. The full traced six-question batch has not run.

The Luna client and locked opt-in smoke passed offline checks. No hosted
response is verified; the API key was absent at setup. Context/answer prompt,
full workflows, tools, LLM spans and final evaluation remain unimplemented.
P07–P20 are drafts; the held-out set is empty. See STATUS for live-check dates
and counts; never infer current service health from this paragraph.

## Code and local artifacts

| File | Responsibility |
| --- | --- |
| [config.py](../src/rag_workflow_lab/config.py) | TOML paths/model settings and explicit `POSTGRES_*` environment loading; no service initialization |
| [contracts.py](../src/rag_workflow_lab/contracts.py) | Source/snapshot/block/chunk contracts, not ORM entities |
| [ingestion/](../src/rag_workflow_lab/ingestion/) | Allowlist, immutable HTML download, scoped parsing and whole-block chunking |
| [embeddings.py](../src/rag_workflow_lab/embeddings.py) | Pinned checksummed Nomic loading, exact task inputs, normalized vectors |
| [store.py](../src/rag_workflow_lab/store.py) | Read-only DB check, immutable writes, index metadata and dense SQL search |
| [retrieval.py](../src/rag_workflow_lab/retrieval.py) | Check index/model compatibility, embed raw question, search; no gold data |
| [tracing.py](../src/rag_workflow_lab/tracing.py) | Lifecycle writers and retrieval wrapper; independent autocommit writer |
| [llm.py](../src/rag_workflow_lab/llm.py) | One Responses API call through a caller-owned client; text/status/IDs/usage, no DB I/O |
| [import_corpus.py](../scripts/import_corpus.py) | Validate snapshots/chunks and commit one corpus transaction |
| [index_corpus.py](../scripts/index_corpus.py) | Embed all stored chunks and commit index/vectors; flushed progress |
| [check_retrieval.py](../scripts/check_retrieval.py) | Full ranks and annotated hits at 5/10/20; optional `--trace` |
| [llm_smoke.py](../scripts/llm_smoke.py) | Explicit `--call-api`; one fixed English test, no corpus/DB access |
| [migrations/versions/](../migrations/versions/) | Applied raw-SQL `0001` retrieval and `0002` trace/span schemas |

Store/search/retrieval functions accept existing connections; callers own
transactions. Identical stored records are accepted and conflicting IDs fail.
Dense SQL sorts by cosine distance then chunk ID and preserves citation fields.
Tracing records safe ranked references, not duplicate full chunk texts. Logging
failure aborts; finished observations cannot be overwritten and unknown
usage/cost stays NULL. The current wrapper finishes a retrieval-only trace;
a future answer workflow must own its root trace through the LLM step.
See [TRACING_PLAN](TRACING_PLAN.md). `sql/retrieval/001_initial.sql` is only an
old comment scaffold; Alembic revisions are authoritative.

| Local artifact | Path |
| --- | --- |
| Source allowlist | `data/corpus/sources.json` |
| HTML + manifests | `data/local/snapshots/<snapshot_id>/` |
| Parsed blocks | `data/local/parsed/<snapshot_id>.json` |
| Chunk JSON + summary | `data/local/chunks/pilot-section-blocks-v1/` |
| Model weights | `data/local/models/nomic-ai--nomic-embed-text-v1.5/<revision>/` |
| Six questions + gold evidence | `data/evaluation/dev/document_questions.json` |
| Local verification reports | `outputs/validation/`, `outputs/embeddings/`, `outputs/retrieval/` |

Git ignores `.env`, `.venv`, `data/local/` and `outputs/`; a fresh clone lacks
these and the Docker volume. Preserve snapshot IDs/hashes in STATUS and keep
gold/project/paper documents outside ingestion. Fresh downloads may differ.

Nomic: revision `e9b6763023c676ca8431644204f50c2b100d9aab`, CPU float32,
768 dimensions, 1024-token application ceiling. Preserve exact task prefixes
and normalization. Existing index:
`nomic-d4a8ebdbce1253c45ea50734d984a14a6258d9f1e7a332fd56964011eb886447`.
Index identity includes code/runtime fingerprints; do not re-index merely
because progress text or surrounding code changed.

Luna: `gpt-6-luna`, reasoning `none`, maximum 1000 output tokens; SDK `3.51.0`.
DB/migration/generation dependencies are installed in `.venv`; model and API
scripts also have separate locked uv environments. Bootstrap guides are linked
from README. The app loads `.env` only when explicitly requested through uv.

## Next small step

Set `OPENAI_API_KEY` locally and run the [Luna smoke](../README.md#check-the-luna-api-client).
Then prepare source-linked context/answer prompt and one P04 answer with
retrieval/LLM spans under the same trace. Preserve questions, snapshots, chunks,
index and `limit=5`; the cutoff sweep did not choose a new context budget.
Synthetic sources/tools, Enhanced and Agentic follow the Simple baseline.

## Checks and resume commands

From the repository root:

```sh
PYTHONPATH=src python3.11 -m unittest discover -s tests/unit -v
python3.11 scripts/check_document_questions.py
docker compose ps --all
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python -m rag_workflow_lab check-db
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python alembic current
```

Start the existing service with `docker compose up -d --wait postgres` if
needed, preserving its volume. The [README](../README.md#verification) has
opt-in DB tests and [retrieval commands](../README.md#retrieval-diagnostic).
On 2026-11-17, 124 unit tests and 19 DB tests passed; public counts/hashes are
checked in the review record. Paid API calls are not part of ordinary tests.
Inspect Git before edits and load credentials without printing them.
