# Session handoff

**Updated:** 2026-11-12. Resume guide for another AI or developer.
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

## Actual stopping point

| Area                   | Implemented / verified                                                                             | Still missing                                                                   |
| ---------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Sources                | Four PostgreSQL 18 HTML snapshots; allowlist, downloader and parser                                | Synthetic runbooks, Markdown ingestion and sandbox fixtures                     |
| Chunking               | 184 parsed blocks become 49 chunks; target 512, ceiling 1024 tokens; intact SQL/tables, no overlap | No new chunking work required for the current four sources                      |
| Embedding              | Local Nomic adapter; one chunk and one query embedded, with an identical offline repeat            | Corpus-wide embedding and indexing; no retrieval-quality result                 |
| Database               | Compose, Psycopg settings, `check-db`, revision `0001`, raw-SQL snapshot/chunk storage and import script | Committed corpus import and vector search |
| Questions              | 20 pilot records; P01–P06 have verified answers/evidence                                          | P07–P20 remain drafts; held-out set is empty                                   |
| Answering / evaluation | Planning documents and module paths                                                                | Generator selection, answer runs, tools, workflows, traces, metrics and runners |

**Database history versus current availability:** Revision `0001` was applied
with explicit owner authorization on 2026-11-07. Catalog checks verified
`source_snapshots`, `chunks`, `embedding_indexes` and `chunk_embeddings`, all
empty, with `vector(768)`. The local record is
`outputs/validation/retrieval-schema-0001/applied-2026-11-07.json`.
On 2026-11-12, the service was healthy, `check-db` passed and revision `0001`
was confirmed. The full four-snapshot/49-chunk import passed a round trip and
repeat-run check, then was rolled back. All four tables remain empty.
Record: `outputs/validation/corpus-import-2026-11-12.json`. The earlier stopped
service observation from 2026-11-08 is historical, not the current check.

## Code and local artifacts

The prepared import consists of:

- [store.py](../src/rag_workflow_lab/store.py): `check_database()`,
  `save_snapshots()` and `save_chunks()`. The save functions accept an existing
  connection; their caller owns the transaction. They preserve exact records
  and reject changed payloads under existing IDs. There is no vector search.
- [import_corpus.py](../scripts/import_corpus.py): reads saved artifacts from
  the pilot allowlist, checks snapshots/provenance, then saves all records in
  one connection/transaction. It reads no gold data and generates no embeddings.
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
Database/migration packages are in `.venv`; ML dependencies use the isolated
`embedding_smoke.py` environment and lockfile. Setup guides cover installation.

## Next small step

Run the prepared importer for a **committed** import of the four saved
snapshot manifests and 49 existing chunks. Preparation/testing is complete,
but no corpus import has been committed. The command is documented in README:

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python scripts/import_corpus.py
```

Inspect service/revision before running and verify four snapshots and 49 chunks
afterward. Identical repeats must leave the same contents and counts. Preserve
the volume and pinned inputs. Then implement corpus embedding/indexing and
inspect P01–P06 retrieval. Generation, LangGraph, synthetic tools and the router
come in later steps.

## Checks and resume commands

Run from the repository root. These checks need no database or model:

```sh
PYTHONPATH=src python3.11 -m unittest discover -s tests/unit -v
python3.11 scripts/check_document_questions.py
```

On 2026-11-12, **86 offline unit tests and 3 opt-in DB integration tests passed**.
The latter use temporary tables and close without committing; the explicit
`RAG_LAB_TEST_DB=1` command is in README. The six-question reference checker
also passed. It checks artifact integrity, not retrieval or answer quality.
No RAG evaluation result exists.

Inspect the service first; when resuming DB work, start it with its existing volume:

```sh
docker compose ps --all
docker compose up -d --wait postgres
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python -m rag_workflow_lab check-db
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python alembic current
```

Load `.env` explicitly without printing credentials. Inspect `git status`
before editing. The checkout was clean at the start of the 2026-11-12 import
preparation (HEAD `481e8b6`); this session's code/tests/docs are uncommitted.
Preserve existing changes. No commit or push was made in this session.

Suggested opening request for a new session:

> Read AGENTS.md, then README.md, docs/PROJECT_CONTEXT.md, docs/STATUS.md,
> docs/ROADMAP.md and docs/HANDOFF.md. Verify the code and local state. Briefly
> explain the implemented boundary, open decisions and next small step before
> changing code. Keep repository text in English and our conversation in Turkish.
