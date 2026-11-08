# Session handoff

**Updated:** 2026-11-08. Resume guide for another AI or developer.
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
| Database               | Compose, Psycopg settings, read-only `check-db`, applied revision `0001`                       | Snapshot/chunk import and vector-search operations                              |
| Questions              | 20 pilot records; P01–P06 have verified answers/evidence                                          | P07–P20 remain drafts; held-out set is empty                                   |
| Answering / evaluation | Planning documents and module paths                                                                | Generator selection, answer runs, tools, workflows, traces, metrics and runners |

**Database history versus current availability:** Revision `0001` was applied
with explicit owner authorization on 2026-11-07. Catalog checks verified
`source_snapshots`, `chunks`, `embedding_indexes` and `chunk_embeddings`, all
empty, with `vector(768)`. The local record is
`outputs/validation/retrieval-schema-0001/applied-2026-11-07.json`.
On 2026-11-08, `docker compose ps --all` reported the project container as
`exited`; `check-db` failed with exit code 2. The service was not started during
this documentation session, so revision and row counts were not rechecked.
Do not treat the old verification record as a live health check.

## Code and local artifacts

Read these before implementing the import:

- [store.py](../src/rag_workflow_lab/store.py): currently only the DB health
  check; there are no corpus writes or vector searches.
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

## Next small implementation step

Implement minimal Psycopg/raw-SQL store operations and an explicit import entry
point for the **four saved snapshot manifests and 49 existing chunks**.
Preserve source/snapshot/chunk IDs, exact `embedding_text`, token counts and
citation/chunking/tokenizer metadata. Verify stored contents and repeat-run
behavior without duplicating records. This step does not require a new schema.

Before the live import, start the existing Compose service and inspect its
revision and contents. Preserve the volume and pinned inputs. Then embed/index
all chunks and inspect P01–P06 retrieval. Generation, LangGraph, synthetic tools
and the router come in later steps.

## Checks and resume commands

Run from the repository root. These checks need no database or model:

```sh
PYTHONPATH=src python3.11 -m unittest discover -s tests/unit -v
python3.11 scripts/check_document_questions.py
```

Last recorded unit result: **80 passed** during earlier code/migration
preparation work; not rerun for this documentation-only update. The six-question
reference checker passed again on 2026-11-08. It checks artifact integrity,
not retrieval or answer quality. No RAG evaluation result exists.

Inspect the service first; when resuming DB work, start it with its existing volume:

```sh
docker compose ps --all
docker compose up -d --wait postgres
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python -m rag_workflow_lab check-db
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python alembic current
```

Load `.env` explicitly without printing credentials. Inspect `git status`
before editing: the checkout has accumulated uncommitted work and new files;
HEAD is `e301eaa`. Preserve those changes. No commit or push was made in this
handoff session.

Suggested opening request for a new session:

> Read AGENTS.md, then README.md, docs/PROJECT_CONTEXT.md, docs/STATUS.md,
> docs/ROADMAP.md and docs/HANDOFF.md. Verify the code and local state. Briefly
> explain the implemented boundary, open decisions and next small step before
> changing code. Keep repository text in English and our conversation in Turkish.
