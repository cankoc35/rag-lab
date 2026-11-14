# Session handoff

**Updated:** 2026-11-13. Resume guide for another AI or developer.
Use [STATUS.md](STATUS.md) for dated verification records. Plans and scaffold
files do not imply working features.

## Read first

1. Verify the checkout is `/Users/cankoc/Desktop/rag-workflow-lab`, then read
   [AGENTS.md](../AGENTS.md).
2. Read [README.md](../README.md), [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md),
   [STATUS.md](STATUS.md), and [ROADMAP.md](ROADMAP.md), in that order.
3. Use this guide to locate code and artifacts. Read
   [METHOD_DESIGN.md](METHOD_DESIGN.md) and [EVALUATION_PLAN.md](EVALUATION_PLAN.md)
   before changing the experiment, and [LITERATURE_GAPS.md](LITERATURE_GAPS.md)
   before making novelty claims.

## Goal and established decisions

Build a PostgreSQL documentation and sandbox-database assistant for an Agentic
RAG thesis. The working study compares simple, enhanced and agentic workflows, with an
adaptive router later. The exact thesis question and protocol remain open.

- Repository content and all RAG artifacts are English; chat may be Turkish.
- Take one small, testable step at a time. Follow **Simplicity First** in AGENTS:
  short, readable code without speculative features or unnecessary abstractions.
- Use PostgreSQL + pgvector in Docker, parameterized raw SQL through Psycopg,
  and Alembic migrations. SQLAlchemy is migration infrastructure only; no ORM.
- Start with one pinned local Nomic embedding model. LangGraph and self-hosted
  MLflow are selected but not installed or implemented.
- The approved pilot includes public PostgreSQL docs, synthetic local runbooks,
  frozen sandbox state, an LLM-only control, changed-evidence checks and
  insufficient-evidence cases. Most of these are still preparation work.

## Approved initial workflow decisions

**Owner, 2026-11-13:** Simple = one dense retrieval pass + one answer call.
Enhanced = dense + PostgreSQL full-text retrieval, RRF merge/deduplication,
reranking + the same answer setup. Share corpus/chunks, dense embedding
settings, generator/settings, answer prompt and maximum context token budget.
Both cite evidence and may abstain. Relevant Enhanced tools follow predefined
Python conditions/order; native LLM function calling is not required.

Agentic retains the shared-tool/dynamic-control direction, with detailed design
deferred until that stage. Reranker/generator choices, numeric budgets and exact
tool conditions remain open. Future additions are possible; this is an initial
working design, not a frozen thesis protocol. Development ablations are
dense-only → hybrid-only → hybrid + reranking. See the
[method definitions](METHOD_DESIGN.md#approved-initial-simple-and-enhanced-design).
These decisions do not implement the scaffold workflows.

## Actual stopping point

| Area                   | Implemented / verified                                                                             | Still missing                                                                   |
| ---------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Sources                | Four PostgreSQL 18 HTML snapshots; allowlist, downloader and parser                                | Synthetic runbooks, Markdown ingestion and sandbox fixtures                     |
| Chunking               | 184 parsed blocks become 49 chunks; target 512, ceiling 1024 tokens; intact SQL/tables, no overlap | No new chunking work required for the current four sources                      |
| Embedding              | Local Nomic; 49 committed document vectors match the earlier verification | Query retrieval and retrieval-quality measurement |
| Database               | Revision `0001`; four snapshots, 49 chunks, one index and 49 vectors committed | Vector search |
| Questions              | 20 pilot records; P01–P06 have verified answers/evidence                                          | P07–P20 remain drafts; held-out set is empty                                   |
| Answering / evaluation | Planning documents and module paths                                                                | Generator selection, answer runs, tools, workflows, traces, metrics and runners |

**Database history versus current availability:** Revision `0001` was applied
with explicit owner authorization on 2026-11-07. Catalog checks verified
`source_snapshots`, `chunks`, `embedding_indexes` and `chunk_embeddings`, all
empty, with `vector(768)`. The local record is
`outputs/validation/retrieval-schema-0001/applied-2026-11-07.json`.
On 2026-11-12, the service was healthy, `check-db` passed and revision `0001`
was confirmed. After initial preparation checks with rollback, the owner
requested a committed import. The script committed four snapshots and 49
chunks. Fresh read-only connections verified every stored field; a second
script run left counts and contents unchanged. The owner later ran indexing,
committing one index and 49 vectors. Read-only checks confirmed input hashes,
finite 768-dimensional unit vectors and an exact match to the rollback-tested
vectors. Record: `outputs/validation/corpus-indexing-committed-2026-11-12.json`.
The rollback-only, empty-embedding and stopped-service observations are historical.

## Code and local artifacts

The prepared import consists of:

- [store.py](../src/rag_workflow_lab/store.py): `check_database()`,
  `save_snapshots()`, `save_chunks()`, `save_embedding_index()` and
  `save_embeddings()`. The save functions accept an existing
  connection; their caller owns the transaction. They preserve exact records
  and reject changed payloads under existing IDs. There is no vector search.
  Embedding writes accept `(chunk_id, EmbeddingResult)` pairs, check index
  model/revision/dimensions and document task, and match input hashes against
  stored `embedding_text`. Vectors use parameterized text-to-vector casting.
- [import_corpus.py](../scripts/import_corpus.py): reads saved artifacts from
  the pilot allowlist, checks snapshots/provenance, then saves all records in
  one connection/transaction. It reads no gold data and generates no embeddings.
- [index_corpus.py](../scripts/index_corpus.py) and its
  [lockfile](../scripts/index_corpus.py.lock): embed all chunks in the configured
  retrieval DB using cached local Nomic, then save one index in the caller's
  transaction. Index identity includes sorted chunk/input hashes, model/revision,
  runtime settings, library versions and model/code fingerprints. Tests verified
  two complete real-model runs with rollback; the command commits when run normally.
  It now emits flushed phase/chunk progress to stderr while keeping the final
  JSON on stdout. The current corpus is already indexed; no rerun is needed.
- [config.py](../src/rag_workflow_lab/config.py) and
  [contracts.py](../src/rag_workflow_lab/contracts.py): environment settings and
  source/snapshot/parsed-block/chunk data contracts. These are not ORM entities.
- [0001_create_retrieval_tables.py](../migrations/versions/0001_create_retrieval_tables.py):
  the applied schema. `sql/retrieval/001_initial.sql` is an older comment-only
  scaffold; Alembic revisions are the schema history.
- [chunk_corpus.py](../scripts/chunk_corpus.py): current chunk JSON format.
  [embeddings.py](../src/rag_workflow_lab/embeddings.py) and
  [EMBEDDING_SETUP.md](EMBEDDING_SETUP.md): the existing adapter and runtime setup.

Local inputs already exist on the owner's machine:

| Artifact                                    | Repository-relative path                                          |
| ------------------------------------------- | ----------------------------------------------------------------- |
| Source allowlist                            | `data/corpus/sources.json`                                      |
| Raw HTML and manifests                      | `data/local/snapshots/<snapshot_id>/`                           |
| Parsed blocks                               | `data/local/parsed/<snapshot_id>.json`                          |
| 49 chunks and summary                       | `data/local/chunks/pilot-section-blocks-v1/`                    |
| Model weights                               | `data/local/models/nomic-ai--nomic-embed-text-v1.5/<revision>/` |
| Six development questions and gold evidence | `data/evaluation/dev/document_questions.json`                   |
| Local verification / smoke reports          | `outputs/validation/` and `outputs/embeddings/`               |

`data/local/`, `outputs/`, `.env` and `.venv` are Git-ignored. A fresh clone
will not contain them or the Docker database volume. Preserve existing
snapshots, IDs and hashes: fresh downloads may differ and invalidate pinned
question evidence. Exact snapshot IDs/hashes are in STATUS. Gold answers and
project/paper documents must stay outside ingestion.

The embedding model is `nomic-ai/nomic-embed-text-v1.5`, revision
`e9b6763023c676ca8431644204f50c2b100d9aab`: CPU float32, 768 dimensions,
1024-token application ceiling. Keep the existing `search_document: ` input
and `search_query: ` query conventions and normalization.
Database/migration packages are in `.venv`; the smoke and corpus-indexing scripts
use isolated `uv` environments with separate lockfiles. Setup guides cover installation.

## Next small step

First add dense `search_chunks()` to `store.py`, then compose query embedding
and index-scoped search in `retrieval.py` for P01–P06. Build the Simple baseline
before the approved Enhanced hybrid/RRF/reranking and fixed tool steps.
Four snapshots, 49 chunks, one index and 49 vectors are
already committed. The selected index is
`nomic-d4a8ebdbce1253c45ea50734d984a14a6258d9f1e7a332fd56964011eb886447`.
Use its stored model/settings; do not recreate the index just for progress output.
The logging edit changes the indexer source hash, so a future indexing run
would produce a different index identity while the existing index retains
its original creation provenance.

Preserve the volume and pinned inputs. Inspect P01–P06 retrieval after indexing
and the retriever are implemented. Generation, LangGraph, synthetic tools and
the router come in later steps. The existing importer can be repeated as
documented in README; the committed repeat check already passed.

## Checks and resume commands

Run from the repository root. These checks need no database or model:

```sh
PYTHONPATH=src python3.11 -m unittest discover -s tests/unit -v
python3.11 scripts/check_document_questions.py
```

On 2026-11-12, **93 offline unit tests and 11 opt-in DB integration tests passed**.
The latter use temporary tables and close without committing; the explicit
`RAG_LAB_TEST_DB=1` command is in README. The six-question reference checker
passed during the committed import. It checks artifact integrity, not retrieval or answer quality.
No RAG evaluation result exists.

The embedding-storage check used synthetic vectors in temporary tables and no
model inference. Public counts were `(4, 49, 0, 0)` after that preparation
check, with the corpus unchanged.
Record: `outputs/validation/embedding-store-2026-11-12.json`.

The later real-model check ran the indexing CLI twice with network access
blocked and a forced transaction rollback. All 49 vectors were finite,
768-dimensional, unit-normalized and identical across repeats. Public counts
returned to `(4, 49, 0, 0)` after that check; record:
`outputs/validation/corpus-indexing-2026-11-12.json`. The owner's later committed
run is separately verified at `(4, 49, 1, 49)` in the committed-indexing record.

Inspect the service first; when resuming DB work, start it with its existing volume:

```sh
docker compose ps --all
docker compose up -d --wait postgres
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python -m rag_workflow_lab check-db
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python alembic current
```

Load `.env` explicitly without printing credentials. Inspect `git status`
before editing and preserve existing changes; use the live Git state rather
than an earlier session's commit/status snapshot. The assistant made no commit
or push during the import preparation or execution sessions.

Suggested opening request for a new session:

> Read AGENTS.md, then README.md, docs/PROJECT_CONTEXT.md, docs/STATUS.md,
> docs/ROADMAP.md and docs/HANDOFF.md. Verify the code and local state. Briefly
> explain the implemented boundary, open decisions and next small step before
> changing code. Keep repository text in English and our conversation in Turkish.
