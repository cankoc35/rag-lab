# Session handoff

**Updated:** 2026-11-17. Resume guide for another AI or developer.
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
- Start with one pinned local Nomic embedding model. LangGraph is selected
  but not installed. The owner rejected MLflow on 2026-11-16; use project-owned
  PostgreSQL tracing via Psycopg/raw SQL. [Migration `0002` and writers](TRACING_PLAN.md)
  are applied and verified. The owner authorized application on 2026-11-16,
  superseding the review hold. DB/repository are `0002`; one real P04 trace
  and retrieval span are committed, with no generator/tool execution yet.
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
| Embedding              | Local Nomic; 49 vectors; P05 diagnosis and repeatable six-question 5/10/20 checker | Broader answer evaluation |
| Database               | Revision `0002`; four snapshots, 49 chunks, one index/49 vectors; one committed P04 trace/span | No schema change needed for the current retrieval step |
| Questions              | 20 pilot records; P01–P06 have verified answers/evidence                                          | P07–P20 remain drafts; held-out set is empty                                   |
| Answering / evaluation | Luna Responses API client and locked opt-in smoke; retrieval tracing is verified | API key/live smoke, context/prompt, answer runs, tools, workflows, LLM/tool spans and runners |

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

On 2026-11-14 the service was healthy and `check-db` passed again. All 14 DB
integration tests passed using temporary tables; public counts/fingerprints
were unchanged at `(4, 49, 1, 49)`. Read-only stored-vector self-search returned
its own chunk first. This is a SQL check, not P01–P06 retrieval evaluation.
Record: `outputs/validation/dense-search-2026-11-14.json`.

Later on 2026-11-14, query retrieval passed real local Nomic checks with one
model load and read-only DB access. P01–P06 ran at `limit=5`; annotated chunks
appeared for five questions, while P05 had no annotated evidence in the top
five. P01 repeated with identical vector/results. Public fingerprints/counts
matched the prior SQL check. Report:
`outputs/validation/query-retrieval-2026-11-14.json`. See the
[diagnostic table](../data/evaluation/dev/README.md#first-dense-retrieval-check).
This is a development observation, not a generated-answer or held-out result.

The P05 follow-up found E1/E2/E3 at ranks 17/11/46 among all 49 chunks.
Adding only `multicolumn` to the query moves E1/E2 to 1/2; generic column names
give 2/1. Removing the final inspection request alone did not recover them.
All input hashes/vectors were valid, SQL cosine matched independent Python
calculations within `1e-6`, and public contents were unchanged. These are
exploratory wording probes, not a production rewrite or an internal-cause proof.
Report: `outputs/validation/p05-retrieval-diagnostic-2026-11-14.json`; see the
[diagnostic interpretation](../data/evaluation/dev/README.md#p05-wording-diagnosis).

The owner then approved a repeatable development checker at 5/10/20.
`scripts/check_retrieval.py` passed two locked real-model CLI runs, each using
one model load and read-only SQL. Ranks/cutoff IDs matched across runs and the
previous top-five baseline; all public counts/hashes are unchanged. P05 has
0/3, 0/3 and 2/3 annotated hits; P06 stays at 2/4, with annotation alternatives
still valid. No production cutoff or gold data changed. See the
[checker results](../data/evaluation/dev/README.md#repeatable-retrieval-checker)
and `outputs/validation/check-retrieval-2026-11-14.json`.

On 2026-11-16, the owner explicitly authorized applying tracing revision `0002`
and testing one question, superseding the earlier review hold. The migration
applied, all four tracing DB tests passed in temporary clones, and a real P04
query committed one `ok` trace and one `ok` retrieval span. Fresh connections
verified source/rank/distance payloads and NULL answer/usage/cost. P04-E1/E2
ranked 1/2. Corpus/index fingerprints are unchanged. Trace ID:
`db808e0d-76ed-4148-9996-2a8988cc4ce7`. Record:
`outputs/validation/tracing-schema-0002/applied-2026-11-16.json`.

## Code and local artifacts

The initial generator uses `gpt-6-luna` through OpenAI Responses API with
reasoning `none` and maximum 1000 output tokens. `llm.generate_text()` accepts
a caller-owned SDK client and returns text/status/IDs/usage without DB I/O.
`scripts/llm_smoke.py` and its lock pin SDK `3.51.0`; `--call-api` and an
environment key are mandatory. It sends a fixed short test, with no automatic
retries and a 30-second timeout. On 2026-11-17, 124 unit tests and three real-SDK
mock-transport checks passed offline; the six-question reference checker passed.
No hosted call ran because `OPENAI_API_KEY` is absent. Use the
[README smoke command](../README.md#check-the-luna-api-client), then build
the evidence-context/answer-prompt contract. No LLM DB tracing is connected yet.

The prepared import consists of:

- [store.py](../src/rag_workflow_lab/store.py): `check_database()`,
  `save_snapshots()`, `save_chunks()`, `save_embedding_index()`,
  `save_embeddings()`, `get_embedding_index()` and `search_chunks()`. The save functions accept an existing
  connection; their caller owns the transaction. They preserve exact records
  and reject changed payloads under existing IDs. `search_chunks(connection,
  index_id, query_vector, limit=5)` runs a SELECT scoped to one index, ordered
  by cosine distance then chunk ID. It returns dictionaries with chunk text,
  token count, metadata, source/snapshot IDs, title/URL and distance. Invalid
  dimensions, zero/nonfinite query vectors and nonpositive limits fail;
  empty/unknown indexes return an empty list. It does not connect or commit.
  Embedding writes accept `(chunk_id, EmbeddingResult)` pairs, check index
  model/revision/dimensions and document task, and match input hashes against
  stored `embedding_text`. Vectors use parameterized text-to-vector casting.
- [retrieval.py](../src/rag_workflow_lab/retrieval.py):
  `retrieve(connection, embedder, index_id, question, limit=5)` loads index
  metadata through the store, checks model/revision/dimensions and embedding
  settings, then composes `embed_query(question)` with dense search. Unknown
  indexes/mismatched settings fail before inference. It returns the search
  dictionaries unchanged and reads no gold. The caller loads/reuses the model
  and owns the connection/transaction. Use the separate development checker below.
- [check_retrieval.py](../scripts/check_retrieval.py) and its
  [lockfile](../scripts/check_retrieval.py.lock): explicit `--index-id`, pinned
  reference validation, one cached model load, read-only full-index retrieval
  per raw question and annotated evidence hits at 5/10/20. Fresh JSON reports
  go to `outputs/retrieval/`; progress goes to stderr and stdout gives the path.
  The lock preserves the indexer's 66 package records. It is a development
  diagnostic, not a generator/evaluation runner or a selected new context budget.
  Its `--trace` flag is available now that `0002` is applied. Default operation
  remains read-only. Traced mode opens a
  separate autocommit writer and adds each `trace_id` to its question record.
- [tracing.py](../src/rag_workflow_lab/tracing.py): `start_trace()`, `finish_trace()`,
  `start_span()`, `finish_span()` and `retrieve_with_trace()`. Writers use bound
  raw SQL without owning connections/commits. The wrapper requires a separate
  autocommit writer, records safe chunk/rank/distance payloads, reraises retrieval
  errors after recording error status and aborts on logging failure. A live P04
  trace/span is verified. See [TRACING_PLAN.md](TRACING_PLAN.md) for the exact contract.
- [0002_create_tracing_tables.py](../migrations/versions/0002_create_tracing_tables.py):
  applied upgrade for two tables and their lifecycle/parent constraints.
  Offline previews and verification are in `outputs/validation/tracing-schema-0002/`.
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

The initial Luna client is implemented and checked offline. Set
`OPENAI_API_KEY` locally and run `scripts/llm_smoke.py --call-api` through its
locked uv command in README. Then agree the evidence-context/answer-prompt
contract and connect one P04 answer. See STATUS for the dated price estimate.
[Tracing](TRACING_PLAN.md) is applied and verified for one P04
question, and DB/repository are `0002`. The full P01–P06 `--trace` batch is
available but has not been run; the requested one-question smoke is complete.
The evidence-context/answer-prompt contract and workflow/LLM tracing follow.
The repeatable 5/10/20 checker is implemented and run; its diagnostic coverage
does not select a new production cutoff. Keep raw questions, snapshots, chunks
and the index fixed; review equivalent evidence when judging future answers.
Query retrieval is implemented and the first P01–P06 diagnostic is recorded.
Use the selected index's model/revision/settings. Build the Simple baseline
before the approved Enhanced hybrid/RRF/reranking and fixed tool steps.
Four snapshots, 49 chunks, one index and 49 vectors are
already committed. The selected index is
`nomic-d4a8ebdbce1253c45ea50734d984a14a6258d9f1e7a332fd56964011eb886447`.
Use its stored model/settings; do not recreate the index just for progress output.
The logging edit changes the indexer source hash, so a future indexing run
would produce a different index identity while the existing index retains
its original creation provenance.

Preserve the volume and pinned inputs. Inspect the recorded P01–P06 retrieval
limitation before adding generation. LangGraph, synthetic tools and
the router come in later steps. The existing importer can be repeated as
documented in README; the committed repeat check already passed.

## Checks and resume commands

Run from the repository root. These checks need no database or model:

```sh
PYTHONPATH=src python3.11 -m unittest discover -s tests/unit -v
python3.11 scripts/check_document_questions.py
```

On 2026-11-14, **104 offline unit tests passed**. The preceding storage/retrieval
step passed **15 opt-in DB integration tests**; those were not repeated for the
checker-only change. Two real-model locked checker runs separately passed with
unchanged public data. DB tests use temporary tables and close without committing; the explicit
`RAG_LAB_TEST_DB=1` command is in README. The six-question reference checker
passed during the committed import. It checks artifact integrity, not retrieval or answer quality.
The real-model six-question retrieval diagnostic above is separate. No
generated-answer or held-out RAG evaluation result exists.

On 2026-11-16, **114 offline unit tests passed** for the prepared tracing change.
Four new tracing DB tests skipped at revision `0001`; live tracing is deferred
under the owner's migration hold. Both SQL directions rendered/parsed offline.
A new default checker run without `--trace` preserved ranks/coverage and public
records. Revision `0001` and absent trace tables were independently confirmed.
Record: `outputs/validation/tracing-schema-0002/prepared-2026-11-16.json`.

After the owner authorized application, all four tracing DB tests passed and
one real P04 trace/span was verified in public tables. See the `applied` record
above; the preceding preparation-only observations are historical.

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
