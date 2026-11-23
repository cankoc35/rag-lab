# Session handoff

**Updated:** 2026-11-23. Use [STATUS](STATUS.md) for the current boundary and
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

Four PostgreSQL sources produce 49 chunks; their Nomic index/49 vectors are preserved.
Atlas v1 adds two snapshots/12 chunks in its separate index. The later v2
control adds another two snapshots/12 chunks and an isolated index. Current
totals are eight snapshots/73 chunks, three indexes/73 vectors and 24 traces/
37 spans, verified on 2026-11-23. Existing rows and baselines are preserved.
The unchanged P08 returns 5 seconds inclusive for v1 and 8 seconds inclusive
for v2 with the same workflow/settings. See [CHANGED_EVIDENCE_CHECK](CHANGED_EVIDENCE_CHECK.md).
The next full-text component is also complete: `store.search_chunks_full_text`
uses English OR matching within an exact selected index. The diagnostic has
`--method full-text`, needs no cached model and is read-only/untraced. Dense is
still its default. P05's annotated top-five count is 2/3 versus dense 0/3;
this is not answer quality. No DB row or artifact was overwritten. See
[FULL_TEXT_RETRIEVAL](FULL_TEXT_RETRIEVAL.md) for the initial AND failure,
final OR results and records. Equal-weight RRF is now implemented too:
`retrieval.reciprocal_rank_fusion()` and `retrieve_hybrid()` use `k=60` and
20 candidates per method; `--method hybrid` saves component ranks and RRF
scores. P05 has 1/3 annotations at five and 2/3 at ten, trailing full-text at
five. See [HYBRID_RETRIEVAL](HYBRID_RETRIEVAL.md). Latest checks: 201 unit/32 DB
tests; next is reranker selection and implementation. No API/trace writes ran.
Dense retrieval and the P01–P06 checker work. P05's evidence ranks 17/11/46
show wording sensitivity; review the [diagnostic](../data/evaluation/dev/README.md#p05-wording-diagnosis).
The checker now accepts `--dataset` and validates exact index scope before
model loading. The Atlas check found all six positive annotations in the top
three across P07–P09. P19 returned Atlas policy text, not a Boreal answer.
The later live answer pair found P07/P08 complete and P09 partial (explicit
reporting role omitted) in Simple; LLM-only honestly abstained on all three.
Both appropriately abstained on P19. See the
[Atlas diagnostic](../data/evaluation/dev/README.md#atlas-retrieval-diagnostic--2026-11-18).
Revision `0002` and retrieval tracing are applied; one real P04 trace/span is
verified. The separate full-ranking traced retrieval-diagnostic batch has not run.

The Luna client and one full Simple P04 answer passed live checks on 2026-11-17;
credentials are in the ignored `.env`, with a blank tracked template. Simple
assembles source-linked whole chunks, uses `answer_v1` and records retrieval
and LLM spans under one trace. P04 passed editorial requirements/citation review;
this is not a benchmark or a prior-knowledge control. Enhanced, tools
and final evaluation remain unimplemented.
The P04 script/lock are now `run_simple_rag.py` and its matching lockfile.
The runner accepts one question ID or all pinned questions. Its first live
six-question batch completed and was independently checked: six new traces,
12 spans, full prompt/source/response/usage persistence and unchanged corpus.
Editorial review: P01/P02/P04/P06 meet recorded requirements; P03/P05 are partial.
P03 omits a distinction available in S3; P05 lacks multicolumn evidence and
acknowledges that gap while answering the EXPLAIN part. The final judging
protocol remains open.
The LLM-only implementation uses `llm_only_v1` to permit prior
knowledge for PostgreSQL 18, using the unchanged raw question and no source
text/tools/history. It records one trace/LLM span per question. Its live
P01–P06 batch then completed: `llm-only-20261117T191359474642Z`. Independent
checks confirmed input isolation and exact persisted records. Editorial
comparison: Simple more complete on P02/P04, LLM-only on P05, both partial
on P03; requirement-complete counts are four versus three, not general accuracy.
P07–P09/P19 now have a separate verified Atlas subset; P10–P18/P20 remain
drafts and the held-out set is empty. See STATUS for live-check dates
and counts; never infer current service health from this paragraph.

Two synthetic Atlas Markdown sources are now authored, version 1.0/state
`atlas-docs-v1`. They contain inventory facts and the local lag policy, with
no live observations or gold questions. They now have a separate pinned manifest
and offline snapshot/parser command. The first run produced 37 blocks under
`data/local/markdown/atlas-docs-v1-ssme1pql/`. Its 25 content blocks now form
12 local chunks in `data/local/chunks/atlas-docs-v1-section-blocks-v1/`,
with complete inputs between 59 and 268 tokens. Both snapshots and all 12
chunks are in the DB and embedded in an Atlas-only index.
The HTML-only manifest and existing source artifacts are unchanged.

## Code and local artifacts

| File | Responsibility |
| --- | --- |
| [config.py](../src/rag_workflow_lab/config.py) | TOML paths/model settings and explicit `POSTGRES_*` environment loading; no service initialization |
| [contracts.py](../src/rag_workflow_lab/contracts.py) | Source/snapshot/block/chunk contracts, not ORM entities |
| [ingestion/](../src/rag_workflow_lab/ingestion/) | Allowlist, immutable HTML download, scoped parsing and whole-block chunking |
| [ingestion/markdown.py](../src/rag_workflow_lab/ingestion/markdown.py) | Explicit local allowlist, immutable Markdown copies, scoped block parsing; no model/DB/network |
| [embeddings.py](../src/rag_workflow_lab/embeddings.py) | Pinned checksummed Nomic loading, exact task inputs, normalized vectors |
| [store.py](../src/rag_workflow_lab/store.py) | Read-only DB check, immutable writes, index metadata and dense/full-text SQL search |
| [retrieval.py](../src/rag_workflow_lab/retrieval.py) | Dense compatibility/query orchestration plus equal-weight RRF and bounded hybrid retrieval; no gold data |
| [tracing.py](../src/rag_workflow_lab/tracing.py) | Lifecycle writers and retrieval wrapper; independent autocommit writer |
| [llm.py](../src/rag_workflow_lab/llm.py) | Whole-chunk JSON context/labels and one Responses API call; no DB I/O or gold |
| [workflows/simple.py](../src/rag_workflow_lab/workflows/simple.py) | Dense top-five retrieval, `answer_v1`, one answer call and workflow-owned trace |
| [workflows/llm_only.py](../src/rag_workflow_lab/workflows/llm_only.py) | Own-knowledge answer, raw question only, one trace/LLM span; DB used solely for logging |
| [evaluation/dataset.py](../src/rag_workflow_lab/evaluation/dataset.py) | Shared selection that retains only question IDs/text and excludes gold from workflows |
| [import_corpus.py](../scripts/import_corpus.py) | Validate snapshots/chunks and commit one corpus transaction |
| [index_corpus.py](../scripts/index_corpus.py) | Embed stored chunks; repeatable source or exact snapshot selection, one index transaction, flushed progress |
| [check_retrieval.py](../scripts/check_retrieval.py) | `--dataset`, `--method dense/full-text/hybrid`, exact index scope, component/fused ranks and hits at 5/10/20; `--trace` for dense only |
| [llm_smoke.py](../scripts/llm_smoke.py) | Explicit `--call-api`; one fixed English test, no corpus/DB access |
| [run_simple_rag.py](../scripts/run_simple_rag.py) | `--dataset`, exact pinned index scope, explicit `--call-api` and one/all selection; shared resources/run ID, per-question records |
| [run_llm_only.py](../scripts/run_llm_only.py) | Same dataset/selection/paid-call flags without an index; question JSON only, one trace writer, no embedding/corpus reads |
| [migrations/versions/](../migrations/versions/) | Applied raw-SQL `0001` retrieval and `0002` trace/span schemas |

Store/search/retrieval functions accept existing connections; callers own
transactions. Identical stored records are accepted and conflicting IDs fail.
Dense SQL sorts by cosine distance then chunk ID and preserves citation fields.
The retrieval span records ranked references; the LLM span stores exact
instructions/input including chunk texts, source-label mapping and response/usage.
Logging failure aborts; finished observations cannot be overwritten and unknown
usage/cost stays NULL. `retrieve_with_trace(..., trace_id=...)` leaves the supplied
trace open for its workflow owner; standalone calls still finish their own root.
See [TRACING_PLAN](TRACING_PLAN.md). `sql/retrieval/001_initial.sql` is only an
old comment scaffold; Alembic revisions are authoritative.

| Local artifact | Path |
| --- | --- |
| Source allowlist | `data/corpus/sources.json` |
| Atlas sources and pinned local allowlist | `data/corpus/synthetic/atlas_inventory.md`, `atlas_operations_policy.md`, `sources.json` |
| Atlas raw copies/manifests/parsed blocks | `data/local/markdown/atlas-docs-v1-ssme1pql/<snapshot_id>/` |
| Atlas chunks, block token counts and summary | `data/local/chunks/atlas-docs-v1-section-blocks-v1/` |
| HTML + manifests | `data/local/snapshots/<snapshot_id>/` |
| Parsed blocks | `data/local/parsed/<snapshot_id>.json` |
| Chunk JSON + summary | `data/local/chunks/pilot-section-blocks-v1/` |
| Model weights | `data/local/models/nomic-ai--nomic-embed-text-v1.5/<revision>/` |
| Six questions + gold evidence | `data/evaluation/dev/document_questions.json` |
| Four Atlas references, including scope-only P19 | `data/evaluation/dev/atlas_questions.json` |
| Atlas v2 source copies/manifest | `data/corpus/synthetic/atlas-docs-v2/` |
| Atlas v2 snapshots and chunks | `data/local/markdown/atlas-docs-v2-3jvgwbl6/`, `data/local/chunks/atlas-docs-v2-section-blocks-v1/` |
| Unchanged P08 with v2 references and pair metadata | `data/evaluation/dev/atlas_changed_evidence_v2.json` |
| Local reports | `outputs/validation/`, `outputs/embeddings/`, `outputs/retrieval/`, `outputs/llm/`, `outputs/answers/` |

Git ignores `.env`, `.venv`, `data/local/` and `outputs/`; a fresh clone lacks
these and the Docker volume. Preserve snapshot IDs/hashes in STATUS and keep
gold/project/paper documents outside ingestion. Fresh downloads may differ.

Nomic: revision `e9b6763023c676ca8431644204f50c2b100d9aab`, CPU float32,
768 dimensions, 1024-token application ceiling. Preserve exact task prefixes
and normalization. Existing indexes:

- PostgreSQL (49): `nomic-d4a8ebdbce1253c45ea50734d984a14a6258d9f1e7a332fd56964011eb886447`.
- Atlas (12): `nomic-b98238adf1e5b69036fc64a756e3171b7459ad8842e8c3ea280fe9a777ad8ddf`.
- Atlas v2 (12): `nomic-5710f4359df83e693a0d994cbf59c45d6ebe9b08695f0ff4d9f75ec062825a55`.

The indexer accepts mutually exclusive `--source-id` or `--snapshot-id`, both
repeatable. Source IDs include all versions; select exact snapshots for v1/v2.
The runner's exact dataset/index scope check rejects mixed or wrong states.

Index identity includes code/runtime fingerprints; do not re-index merely
because progress text or surrounding code changed.

Luna: `gpt-6-luna`, reasoning `none`, maximum 1000 output tokens; SDK `3.51.0`.
DB/migration/generation dependencies are installed in `.venv`; model and API
scripts also have separate locked uv environments. Bootstrap guides are linked
from README. The app loads `.env` only when explicitly requested through uv.

## Next small step

One P04 Simple run is complete: trace `0a5c1437-8383-4702-b9a7-e676a24ddbee`,
report `outputs/answers/simple-P04-20261117T172725743636Z.json`; independent
checks use the same filename under `outputs/validation/`. Public totals are
two traces/three spans; corpus remains `(4, 49, 1, 49)`.
The later batch is `simple-20261117T183619008413Z`, with report under
`outputs/answers/`, integrity checks under `outputs/validation/` and a separate
`-review.json` editorial record. Public totals then reached eight traces/15 spans.
The later LLM-only batch added six traces/six spans, bringing totals to
14 traces/21 spans. Its raw report is under `outputs/answers/`; validation uses
the same basename under `outputs/validation/`. Paired answers, requirement
notes and calculations are in
`outputs/comparisons/simple-vs-llm-only-20261117T191359474642Z.json` and
[LLM_ONLY_COMPARISON](LLM_ONLY_COMPARISON.md).
Markdown ingestion passed 168 unit tests, including nine new tests; P01–P06
reference checks and read-back artifact/hash checks passed. Validation record:
`outputs/validation/markdown-ingestion-20261118.json`. No DB/API work occurred.
The later Atlas chunking step passed 173 unit tests and independent artifact
checks; a temporary HTML run reproduced the original 49 chunks exactly.
Record: `outputs/validation/atlas-chunking-20261118.json`.
The separate `atlas-document-dev` / `1.0.0` subset is now reference-verified:
three answerable records and one unanswerable P19, eight requirements/six
positive evidence records. P19 has no positive chunk and omits the draft's
answer-disclosing clause. Both reference checks and 178 unit tests passed;
the original six-question dataset/runtime defaults and corpus artifacts are
unchanged. Record: `outputs/validation/atlas-questions-v1-20261118.json`.
The owner then authorized Atlas import. The importer now accepts explicit
Markdown inputs. Two snapshots/12 chunks were committed, repeated without
duplicates and field-verified from a fresh read-only connection. Public totals
are six snapshots/61 chunks, one original index/49 vectors, 14 traces/21 spans.
All older row fingerprints and source/dataset/artifact hashes are preserved.
The local capture time maps to the legacy `downloaded_at` acquisition column;
no migration was required. All 181 unit/22 DB tests and both reference checks
passed. Record: `outputs/validation/atlas-import-20261118.json`.
The subsequent owner-authorized offline run used the new repeatable
`--source-id LOCAL-INVENTORY --source-id LOCAL-POLICY` filter. It committed
12 normalized 768-dimensional vectors in a separate Atlas index. Read-back
verified exact artifact membership/input hashes, norms and index provenance;
all older row fingerprints are unchanged. Totals: six snapshots/61 chunks,
two indexes/61 vectors, 14 traces/21 spans. All 181 unit/24 DB tests and Ruff
passed. Record: `outputs/validation/atlas-index-20261118.json`.
At that stage, source flags selected Atlas v1. With multiple versions now
stored, use exact snapshot IDs for state-specific indexing. The subsequent
`--dataset data/evaluation/dev/atlas_questions.json`
diagnostic checked all four unchanged questions in the Atlas-only index.
P07 E1 ranks 1, P08 E1/E2 rank 1, P09 E1/E2/E3 rank 1/3/2. P19 has no
positive evidence score and returns Atlas policy passages; no Boreal answer
is established. Read-only report: `outputs/retrieval/dense-20261118T202158580023Z.json`;
validation: `outputs/validation/atlas-retrieval-20261118.json`. All public rows
and 31 pinned file hashes are unchanged; 184 unit/24 DB tests and Ruff passed.
The later owner-authorized pair added `--dataset` support to both runners,
preserving their defaults/prompts/settings and reusing the diagnostic's scope
check for Simple before model/trace/API work. LLM-only ran first, followed by
Simple: eight completed paid calls. Runs `llm-only-20261118T203122477461Z` and
`simple-20261118T203140812238Z` have raw reports in `outputs/answers/`.
Editorial review: Simple P07/P08 complete, P09 core facts correct but explicit
reporting role omitted; LLM-only honestly abstains on all three. Both abstain
on P19 without inventing a Boreal limit. Review/raw pairs:
`outputs/comparisons/atlas-simple-vs-llm-only-20261118.json`;
integrity: `outputs/validation/atlas-paired-20261118.json`.
Read-back verified exact prompts, source text, outputs/usage/settings and
eight new traces/12 spans. All older rows, 39 protected files and 42 reports
are preserved. Totals: six snapshots/61 chunks, two indexes/61 vectors,
22 traces/33 spans, migration `0002`. All 187 unit/24 DB tests and Ruff passed.
The subsequent owner-authorized source-change step is complete. Separate v2
sources consistently change the limit to 8 seconds; P08 text, shared workflow,
prompt and generator settings are unchanged. Two fresh calls follow the
5 → 8 change with inclusive boundaries and supporting S1 citations. New traces:
`d3a20767-0fdb-414f-9962-585268ed48ad` (v1),
`a626e4f2-8c08-4ec6-8603-3828eb0ad73c` (v2).
Raw reports: `outputs/answers/simple-20261123T115533976548Z.json` and
`outputs/answers/simple-20261123T115600036150Z.json`.
Comparison: `outputs/comparisons/atlas-changed-evidence-20261123.json`;
read-back/preservation record: `outputs/validation/atlas-changed-evidence-20261123.json`.
All 188 unit/26 DB tests, three reference checks and Ruff passed. No migration
was needed; older rows, gold datasets and raw outputs are unchanged.
The full-text component subsequently passed its recorded checks, without API
calls, trace writes or public-table changes. Its comparison is
`outputs/comparisons/dense-vs-full-text-20261123.json`; preservation/rank checks
are in `outputs/validation/full-text-retrieval-20261123.json`.
The subsequent equal-weight RRF check is complete, with no parameter tuning
after the mixed result. New reports under `outputs/retrieval/`:
`hybrid-20261123T164729411936Z.json` (PostgreSQL),
`hybrid-20261123T164729409769Z.json` (Atlas v1) and
`hybrid-20261123T164729410070Z.json` (Atlas v2).
Comparison: `outputs/comparisons/dense-full-text-rrf-20261123.json`;
independent score/union/preservation record: `outputs/validation/rrf-retrieval-20261123.json`.
All public rows and 79 protected source/data/artifact/report files are unchanged.
Next proposal: select and implement a reranker as a separate increment.
Preserve all baselines and P09's omission.
Do not infer general accuracy from either small pair.
The documents define no live lag or actual index/plan output; DB fixtures/tools follow later.
Preserve existing questions,
snapshots, chunks, index and `limit=5`. The current context sends all five
whole chunks without truncation; no final numeric context budget is chosen.
Synthetic-source ingestion/tools, Enhanced and Agentic follow the Simple baseline.

## Checks and resume commands

Supervisor materials prepared on 2026-11-23 are in
[presentations/2026-11-23/](presentations/2026-11-23/README.md): annotated
pipeline PDF/PNG/SVG and a one-page briefing PDF with editable Markdown.
Code/design were inspected; the results summarized remain the 2026-11-18
development checks. Router, Enhanced, Agentic and sandbox tools are still
scaffolds. Router method remains open, not implicitly selected as an LLM.
No application code, corpus, dataset, experiment or service state changed
while preparing these materials.
The chart was subsequently revised at the owner's request: C explains the
separate thesis evaluation process, tracing's partial status is in its heading,
and a shared Output validation box precedes Response. Only completion/nonempty
checks currently exist; citation checks are planned and grounding/failure/retry
behavior is open. The diagram change did not implement a validator or alter
the experiment. The briefing PDF/Markdown remain unchanged.

The [command reference](COMMANDS.md) lists runnable commands, short descriptions
and supported options. Update it when commands or their options change.
Its [direct LLM section](COMMANDS.md#ask-the-llm-directly) has a free-form
question/answer snippet using the existing client, without dataset/retrieval/
DB access or saved traces. It was checked with a mock, not a paid call.

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
On 2026-11-17, 159 unit tests and 21 DB tests passed, including LLM-only
request isolation and temporary-table trace checks. These tests preceded the
live control and were not repeated for execution/documentation-only work.
The later live batch made six explicit paid calls and added six traces/12 spans;
corpus/older trace hashes are preserved in its verification record. No code
changed for that run, so tests were not repeated. Paid calls are not ordinary tests.
Inspect Git before edits and load credentials without printing them.
