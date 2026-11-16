# PostgreSQL tracing — applied retrieval logging

**Updated:** 2026-11-16. **Status:** The owner explicitly authorized applying
migration `0002` and testing one question, superseding the earlier review hold.
Database and repository revisions are `0002`. `traces` and `spans` exist;
one real P04 retrieval trace/span is committed and independently verified.
MLflow is not used. Generator and tool instrumentation remain future work.

## Implementation files

- [0002_create_tracing_tables.py](../migrations/versions/0002_create_tracing_tables.py): raw-SQL upgrade/downgrade.
- [tracing.py](../src/rag_workflow_lab/tracing.py): four writer functions and traced retrieval.
- [check_retrieval.py](../scripts/check_retrieval.py): optional `--trace` integration.
- [Unit tests](../tests/unit/test_tracing.py) and [post-migration DB tests](../tests/integration/test_tracing_store.py).

Offline SQL previews are saved locally as
`outputs/validation/tracing-schema-0002/upgrade.sql` and `downgrade.sql`.
The upgrade was applied through Alembic; the downgrade remains an offline preview.

## Tables

| Table | Columns |
| --- | --- |
| `traces` | `trace_id UUID` primary key; optional `run_id`/`question_id`; `workflow`, `question`; `started_at`/`finished_at`; `status`; optional `final_answer`; `configuration JSONB`; optional `error JSONB` |
| `spans` | `span_id UUID` primary key; `trace_id`; optional `parent_span_id`; `kind`, `name`; `started_at`/`finished_at`; `status`; `inputs JSONB`; optional `outputs`, `usage`, `cost`, `error` JSONB |

Every question attempt has a new UUID. Dataset `question_id` stays stable across
attempts; the checker's `run_id` identifies the batch containing six traces.
An index on `(run_id, started_at)` supports batch inspection. Spans reference
their trace; a composite parent foreign key requires the parent to belong to
the same trace. A span cannot parent itself.

Status is `running`, `ok` or `error`. Running records have no finish timestamp;
completed records have one. Times use `clock_timestamp()`. Duration can be
calculated from finish minus start. No extension or existing corpus-table
change is required. Downgrade drops spans, then traces; it does not drop corpus
tables or pgvector.

## Writer and retrieval behavior

`start_trace()`, `finish_trace()`, `start_span()` and `finish_span()` use an
existing connection and parameterized raw SQL. They do not connect or commit.
Finish operations only update `running` records; repeated completion or a
missing ID raises `ValueError`. Unknown outputs/usage/cost/errors stay SQL NULL,
not zero or JSON null. JSON serialization rejects nonfinite numbers.

`retrieve_with_trace(reader, writer, embedder, index_id, question, ...)` returns
`(matches, trace_id)`. It requires a separate autocommit writer so a retrieval
rollback does not erase observations. It records one complete `dense_retrieval`
trace and one retrieval span, preserving the existing search results. Inputs
include raw question, index, requested limit and exact prefixed-query hash.
Configuration includes safe embedding/retrieval settings and caller-supplied
dataset/index/code provenance. Outputs contain ordered chunk/source/snapshot
IDs, URLs/titles, token counts and cosine distances. Whole documents, connection
objects and credentials are not serialized.

Retrieval exceptions finish both records as `error` and are re-raised. Stored
error details contain exception type and a fixed safe message, not raw driver
messages. Logging failures abort the diagnostic call; they are not silently
ignored. A writer failure can leave a partial `running` record for inspection.
There is no automatic logging retry or background queue.

The wrapper completes a retrieval-only trace. Future answer workflows should
own their question trace and reuse the four writers for retrieval/context/LLM/
tool spans, rather than appending operations to this completed diagnostic trace.
Inputs/outputs JSONB can hold exact prompt/messages and actual tool arguments/
results; usage/cost fields are ready but no LLM/tool instrumentation exists yet.
Distinguish retrieved candidates from excerpts actually sent to a future LLM.
Preserve reported usage and estimated-cost basis; aggregate individual calls
without double-counting nested spans or token subcategories.

## Checker modes

The existing command without `--trace` still uses read-only SQL and writes only
its JSON report. No trace connection or DB records are created. JSON has
`read_only: true`, `retrieval_read_only: true`, `tracing_enabled: false`.

With `0002` applied, append `--trace` to the locked
checker command in [README](../README.md#run-the-scaffold). The checker opens
a second autocommit connection and links each question record's `trace_id` to
the same batch `run_id` in JSON and PostgreSQL. Retrieval stays read-only;
the overall report has `read_only: false`, `retrieval_read_only: true` and
`tracing_enabled: true`. Cutoff coverage/gold comparisons remain outside tracing.

## Verification and remaining work

- During preparation, 114 offline unit tests passed, including lifecycle, safe payloads, NULL usage,
  writer separation, logging failure and checker trace-link checks.
- Both directions rendered with Alembic `--sql` using a synthetic password and
  parsed with pglast 8.7. This checks SQL syntax, not live constraint execution.
- The preparation check without tracing preserved prior ranks and all corpus
  fingerprints/counts at `(4, 49, 1, 49)`.
- On the owner's instruction, `alembic upgrade 0002` applied the reviewed DDL.
  Four tracing DB tests then passed using session-local table clones, checking
  round trips, parent isolation, immutable completion and retrieval rollback.
- One real cached-Nomic query, P04, ran through `retrieve_with_trace()` at
  `limit=5`. A fresh read-only connection confirmed one `ok` trace and one `ok`
  span, exact input/output payloads and matching ranks/distances. Annotated
  P04-E1/E2 chunks are ranked 1/2. Usage, cost and final answer remain SQL NULL
  because this was retrieval only. The corpus/index fingerprints are unchanged.
- The full six-question `--trace` checker batch has not been executed yet.
  The Luna client is checked offline; its live smoke, context/prompt and LLM
  instrumentation follow. See [STATUS](STATUS.md) for the current boundary.

Application/test record: `outputs/validation/tracing-schema-0002/applied-2026-11-16.json`.
Trace ID: `db808e0d-76ed-4148-9996-2a8988cc4ce7`.
Earlier preparation evidence remains in `prepared-2026-11-16.json` in that directory.
JSON experiment records remain available independently of any UI, and all
trace records stay outside corpus ingestion and sandbox-tool access.
