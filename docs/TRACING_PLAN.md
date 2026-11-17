# PostgreSQL tracing — retrieval and Simple answers

**Updated:** 2026-11-17. **Status:** The owner explicitly authorized applying
migration `0002` and testing one question, superseding the earlier review hold.
Database and repository revisions are `0002`. `traces` and `spans` exist;
one retrieval-only P04 trace and a later Simple P04 trace with retrieval/LLM
spans are independently verified. MLflow is not used. Tool instrumentation
remains future work.

## Implementation files

- [0002_create_tracing_tables.py](../migrations/versions/0002_create_tracing_tables.py): raw-SQL upgrade/downgrade.
- [tracing.py](../src/rag_workflow_lab/tracing.py): four writer functions and traced retrieval.
- [check_retrieval.py](../scripts/check_retrieval.py): optional `--trace` integration.
- [simple.py](../src/rag_workflow_lab/workflows/simple.py): owns the question trace through retrieval and one LLM call.
- [run_simple_rag.py](../scripts/run_simple_rag.py): opt-in single/batch answers, per-question traces linked by a shared run ID.
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

Standalone calls complete a retrieval-only trace. Supplying `trace_id` leaves
that existing trace open for its workflow owner, including on retrieval errors.
Simple starts its own `simple` trace and records retrieval followed by one LLM
span. The latter's inputs contain exact instructions/input, source-label map,
generator settings and request policy. Outputs retain response/model IDs,
completion status, text and incomplete reason; usage keeps the provider's full
payload. A partial/empty reply marks the span and root `error` while preserving
returned text/usage. Provider exceptions use sanitized messages without retries.

The current context sends all five retrieved chunks, whole and untruncated;
no separate context span or final numeric token budget is introduced. Source
labels S1–S5 are runtime citations, distinct from gold E1/E2 annotations.
Gold stays outside the workflow/model input. Unknown cost stays SQL NULL;
the P04 validation report records a separate token-price estimate with its
basis. Cache-write/read counts are subsets of input, not extra tokens to add
to totals. No tool spans are claimed.

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
- On 2026-11-17, Simple P04 added one `ok` trace with `ok` retrieval/LLM spans.
  A fresh read-only check confirmed full prompt/chunk text, valid S1/S2 mapping,
  answer/usage and unchanged corpus/older records. Public totals: two traces,
  three spans. Both mandatory requirements and optional guidance passed
  post-run editorial review. This is not a benchmark or prior-knowledge control.
  Trace: `0a5c1437-8383-4702-b9a7-e676a24ddbee`; report and validation use
  `simple-P04-20261117T172725743636Z.json` under `outputs/answers/` and
  `outputs/validation/` respectively.
- 135 offline unit tests and 20 local DB integration tests passed, including
  completed/incomplete Simple trace round trips in temporary tables.
- The owner then ran the full P01–P06 Simple answer batch:
  `simple-20261117T183619008413Z`. A fresh read-only check verified six new
  completed traces and 12 spans, exact inputs/full chunk text, response IDs,
  answers and usage. Public totals are eight traces/15 spans, with unchanged
  corpus and older records. Validation and a separate `-review.json` record
  are under `outputs/validation/`; raw answers are under `outputs/answers/`.
  Editorial review found P03/P05 partial; a trace's `ok` status indicates
  successful execution, not semantic correctness.
- The separate full-ranking six-question `check_retrieval.py --trace` batch
  has not run. LLM-only uses one `llm_only` trace and one LLM span
  per question; `inputs.prompt` is the raw question and `inputs.sources` is
  empty. The DB connection is solely a trace writer. Completed/incomplete
  round trips passed in temporary tables. The later live P01–P06 control added
  six traces/six LLM spans, independently verified against raw inputs,
  prompt/settings, answers and usage. Public totals then reached 14 traces/21
  spans; older rows and corpus/index fingerprints were unchanged. Cost remains
  NULL. See the [paired comparison](LLM_ONLY_COMPARISON.md).
  Tool spans remain future work. See [STATUS](STATUS.md).

Application/test record: `outputs/validation/tracing-schema-0002/applied-2026-11-16.json`.
Trace ID: `db808e0d-76ed-4148-9996-2a8988cc4ce7`.
Earlier preparation evidence remains in `prepared-2026-11-16.json` in that directory.
JSON experiment records remain available independently of any UI, and all
trace records stay outside corpus ingestion and sandbox-tool access.
