# Session handoff

**Updated:** 2026-11-25. Use [STATUS](STATUS.md) for the current boundary and
[STATUS_HISTORY](STATUS_HISTORY.md) for dated evidence. Scaffolds are not features.

## Read first

Verify `/Users/cankoc/Desktop/rag-workflow-lab`, then read [AGENTS](../AGENTS.md),
[README](../README.md), [PROJECT_CONTEXT](PROJECT_CONTEXT.md), [STATUS](STATUS.md)
and [ROADMAP](ROADMAP.md), in that order. Read METHOD_DESIGN/EVALUATION_PLAN
before experiment changes and LITERATURE_GAPS before novelty claims.

## Resume snapshot — 2026-11-25

This is the current stopping point for a new assistant, including Claude.
The longer preparation records below are historical; use this snapshot and
the current owner decisions in PROJECT_CONTEXT when their older next-step
wording differs. [CLAUDE.md](../CLAUDE.md) is a short entry point to the same rules.

### Current implementation boundary

- **Working:** versioned ingestion/chunking, local Nomic embeddings, raw-SQL
  PostgreSQL/pgvector storage, dense/full-text/RRF retrieval, Simple RAG and
  LLM-only runners, retrieval/LLM tracing, six retrieval metrics at 5/10/20.
- **Current data:** 14 expanded sources, 151 shared-index chunks; dataset
  [v1.8](../data/evaluation/dev/expanded_questions_v1_8.json) has 100 answerable
  questions (50 PostgreSQL, 30 Atlas, 20 combined) and 20 unanswerable. Earlier
  Atlas states/indexes are controls and must remain separate.
- **Selected reranker:** `Qwen/Qwen3-Reranker-4B`, revision
  `22e683669bc0f0bd69640a1354a6d0aebcfeede5`, local MPS/float16, batch-one default,
  [pinned config](../configs/reranker.toml). The owner accepts the wait for a
  one- or two-question school-project demo. The earlier 10-second limit is
  withdrawn; full-set 0.6B/batching experiments are optional. Keep reporting time.
- **Verified 4B result:** all 120 questions/2,400 saved RRF candidate pairs
  completed. Full annotated support @5 improves **82/100 → 92/100**, @10
  **93/100 → 100/100**. Mean reranking **43.69 s/question**, scoring total
  **87 min 23 s**. These are retrieval-support metrics, not Luna answer accuracy;
  the twenty negatives are outside positive means. See [results](QWEN_RERANKER_COMPARISON.md).
- **Live reranked retrieval (added 2026-11-25, offline-tested only):**
  `retrieve_reranked(connection, embedder, index_id, question, score_passage, limit=5)`
  in [retrieval.py](../src/rag_workflow_lab/retrieval.py) calls
  `retrieve_hybrid(..., limit=20)`, scores `" > ".join(metadata["heading_path"]) + "\n\n" + text`
  for each candidate and returns the top `limit` (1–20) with `rrf_rank` and
  `reranker_score`. It has not run against the live DB/model; no workflow calls it.
- **Not built:** the Enhanced answer workflow, a runner that loads Qwen for live
  retrieval, DB tools and frozen fixtures, Agentic graph, router,
  reranker/tool/router spans and shared output validator. Simple has
  completion/nonempty checks; citation validation is planned, grounding/retry
  policy remains open. LangGraph is selected but uninstalled.

### Next small increment

**Proposed:** run the live reranked path once on one development question
(for example P05) and compare its RRF top 20 and reranked order with the saved
full-run report `outputs/reranking/qwen4b-probe-20261125T202218873027Z.json`.
Expect identical candidates; small float16 score differences are possible.
The caller loads the pinned Qwen model/tokenizer once (as in
[reranker_probe.py](../scripts/reranker_probe.py)) and passes the unchanged
native scorer:

```python
from scripts.reranker_smoke import score
from rag_workflow_lab.retrieval import retrieve_reranked

matches = retrieve_reranked(connection, embedder, index_id, question,
                            lambda q, passage: score(model, tokenizer, q, passage, settings))
```

`settings` is the `[reranker]` table of [configs/reranker.toml](../configs/reranker.toml).
The Nomic retrieval lock (`check_retrieval.py.lock`) pins the same torch
`2.10.0`, transformers `5.5.0` and tokenizers `0.22.2` as the reranker lock;
whether one environment can load both models has not been checked. Recheck DB
service state first. After that, add shared Luna generation and a reranker span
for Enhanced in separate increments. `build_answer_input()` currently copies
`distance` into sources; decide then whether Enhanced sources also record
`rrf_rank`/`reranker_score`. Final context token budget is still open; the
initial five-chunk target does not freeze the thesis protocol.

Do not call the complete Enhanced workflow finished before its fixed tool
behavior is implemented. Simple stays dense-only. Do not repeat the 87-minute
benchmark or run paid calls just to resume.

### Focused code and evidence map

| File | Why read it next |
| --- | --- |
| [retrieval.py](../src/rag_workflow_lab/retrieval.py) | Live dense/full-text/RRF and `retrieve_reranked()` (fused top 20 → caller scorer → top `limit`) |
| [test_hybrid_retrieval.py](../tests/unit/test_hybrid_retrieval.py) | RRF tests and reranked-path tests, including passage/order parity with the probe |
| [store.py](../src/rag_workflow_lab/store.py), [llm.py](../src/rag_workflow_lab/llm.py) | SQL results already include chunk text/metadata; existing cited context construction |
| [reranker_smoke.py](../scripts/reranker_smoke.py) | Native `pair_tokens`, `score`, `score_batch`; no silent truncation |
| [reranker_probe.py](../scripts/reranker_probe.py) | Saved-candidate selection, whole-passage assembly, ranking and provenance |
| [simple.py](../src/rag_workflow_lab/workflows/simple.py), [tracing.py](../src/rag_workflow_lab/tracing.py) | Existing workflow and trace ownership to reuse later |
| [enhanced.py](../src/rag_workflow_lab/workflows/enhanced.py) | Still only a scaffold; no callable Enhanced workflow |
| [test_reranker_smoke.py](../tests/unit/test_reranker_smoke.py), [test_reranker_probe.py](../tests/unit/test_reranker_probe.py) | Existing offline scoring/candidate tests |

Saved local evidence, all present at handoff:

- Raw 4B run: `outputs/reranking/qwen4b-probe-20261125T202218873027Z.json`.
- Independent audit: `outputs/validation/qwen4b-full-20261125T202218873027Z.json`.
- RRF input: `outputs/retrieval/hybrid-20261125T133826756751Z.json`.
- Shared index ID and earlier control indexes: STATUS's index list above its
  selected-reranker section. Do not substitute an Atlas-only index.
- Supervisor diagram: [presentation folder](presentations/2026-11-23/README.md),
  updated with selected 4B/full-run results; the older speaking notes are dated.

### Local state and verification boundary

Handoff checkout: `main`, HEAD `11dad36b47dbe225357d37d6596cc012cdf1530e`, with
existing uncommitted documentation/presentation edits, `CLAUDE.md` and the
uncommitted reranked-retrieval code/tests/docs above. Inspect `git status` and
`git diff`; preserve them. Model files under `data/local/` and run reports under
`outputs/` are local/ignored artifacts, not guaranteed by a fresh clone.

This handoff refresh confirmed the pinned 4B model directory and both safetensors
shards exist. The saved full-run SHA-256 matches its audit; recorded runtime-code
hashes match the current files. No weights were reloaded, inference rerun or live
DB/API state checked. Earlier unit-test counts and service checks below are dated
evidence, not newly executed checks. Use [COMMANDS](COMMANDS.md) for existing
offline test/reference commands; verify services before later DB work. No new
Alembic migration is implied by a reranker adapter.

The reranked-retrieval increment (2026-11-25) passed 233 offline unit tests,
Ruff `F` checks and `git diff --check`. `reranker_smoke.py`, `reranker_probe.py`
and `check_retrieval.py` are unchanged, so the saved reports' code hashes still
match. No model, DB or API access occurred in that increment.

## Goal and established decisions

Build a PostgreSQL documentation/sandbox assistant for an Agentic RAG thesis.
The working study compares Simple, Enhanced, Agentic and a later router;
the exact research question and final protocol remain open.

- English repository; Turkish chat. Small, testable steps and simple code.
- Docker PostgreSQL + pgvector; Psycopg raw SQL without ORM; Alembic migrations.
- Local Nomic for embeddings, Luna Responses API for the first generator.
- Selected Qwen3-Reranker-4B, pinned local MPS/float16, batch-one default; latency accepted for the project/demo.
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
ablations. Qwen3-Reranker-4B is selected; exact tools and final budgets remain open. See
[METHOD_DESIGN](METHOD_DESIGN.md#approved-initial-simple-and-enhanced-design).

## Earlier preparation and development records

The owner approved 100 answerable questions (50 PostgreSQL-only, 30 Atlas-only,
20 combined) plus 20 unanswerable and broader topics. The
[source/topic/question matrix](RETRIEVAL_DATASET_PLAN.md) is complete: eight
PostgreSQL scopes, six authored Atlas documents, exact budgets and evidence
requirements. [Version 1.7.0](../data/evaluation/dev/expanded_questions_v1_7.json)
completes all 120 development questions: 50 PostgreSQL-only, 30 Atlas-only,
20 combined answerable and 20 unanswerable. No question-preparation slots remain.
The development measurement step is implemented in `check_retrieval.py`:
schema 4 / `annotated-evidence-v2` implements all six quality metrics at
5/10/20: unique annotated-chunk recall, any/all required-claim coverage,
all-requirements-supported rate, Precision, MRR and nDCG. Retrieval time is
separate. Precision divides by fixed `k`; nDCG uses binary reference gains and
ideal `min(k, reference_count)` normalization. Negative scores stay `null` and
outside positive means. Alternatives remain unjudged. Details are in
[the metric definitions](EVALUATION_PLAN.md#implemented-ranking-metrics--2026-11-25).
The real [expanded comparison](EXPANDED_RETRIEVAL_COMPARISON.md) completed on
2026-11-25: three methods × 120 raw questions, read-only on the exact shared
151-chunk index. Full annotated support at five is dense 80/100, full-text
60/100 and RRF 77/100; RRF reaches 96/100 at twenty. Independent metric and
RRF reconstruction checks passed. A targeted review found equivalent evidence
and overstrict requirements; frozen scores and raw rankings are preserved.
The subsequent [reference review](REFERENCE_REVIEW.md) creates current
[version 1.8.0](../data/evaluation/dev/expanded_questions_v1_8.json), with twelve
source-backed annotation corrections, identical raw questions/source state and
unchanged negatives. All saved rankings were rescored offline. Full support at
five is now 83/65/82 and at twenty 88/95/100 for dense/full-text/RRF; these are
annotation-only score changes. The original scores reproduce exactly. Current
verification: 222 unit tests, eleven reference checks, 232 preserved local
artifacts, no DB/model/API access. The review is not exhaustive pooled judging.
The [local-paper review](RETRIEVAL_METRIC_REVIEW.md) supports retaining that
plan; MAP is optional and no additional metric was adopted. It distinguishes
paper-specific Hits/completeness formulas and stresses shared label review.
Final scoring/held-out settings remain open. No expanded answer generation ran.
The existing PostgreSQL container was started; all seven public-table contents
were unchanged afterward (18 snapshots, 175 chunks, four indexes/224 vectors,
24 traces/37 spans). This service check is dated 2026-11-25, not a guarantee
for the next session. All 213 protected artifacts were preserved; 23 diagnostic
unit tests and the current reference checker passed. Raw report paths, hashes
and local verification/review artifacts are in the comparison document.
The following records describe the earlier preparation stages. The separate
[expansion manifest](../data/corpus/postgres_expanded_v1.json) and
[acquisition config](../configs/corpus_expansion.toml) now exist. Four new HTML
pages were captured, bringing local PostgreSQL snapshots to eight; their IDs
and hashes are in [STATUS](STATUS.md#saved-official-documentation-snapshots).
All eight passed in-memory parsing and hash/source checks; 35 relevant offline
tests passed and 114 existing files are unchanged. No new parsed/chunk files,
question records, DB writes or model calls ran. Capture record:
`outputs/validation/postgres-expanded-v1-capture-20261123T175303Z.json`.
The six-document `atlas-expanded-v1` state and
[manifest](../data/corpus/synthetic/atlas-expanded-v1/sources.json) are now
authored: 4,149 words with the original inventory, lookup SQL and 5-second rule
preserved. New catalog/policies describe intended definitions, not observations.
Temporary ingestion/readback, cross-document checks and 14 Markdown tests
passed; 124 existing files were preserved during authoring. Report:
`outputs/validation/atlas-expanded-v1-authoring-20261123T180121Z.json`.
Persistent parsing is now complete: four added HTML JSON files under
`data/local/parsed/` and six Atlas snapshots/parsed files under
`data/local/markdown/atlas-expanded-v1-hyrbftbg/`. The four original HTML
outputs are reused. Selected totals: 14 sources/638 blocks (454 newly saved).
Read-back/reparse checks and 30 parser/Markdown tests passed; all 131 existing
source/data/code artifacts are unchanged. No new chunks, vectors or DB rows
were created. Exact scope/paths/hashes:
`outputs/validation/corpus-expansion-parse-20261123T181235Z.json`.
An in-memory chunking fit check now covers all 552 content blocks: 151
candidates, maximum 822 tokens, no overflows, all code/tables preserved.
Six Atlas metadata-only candidates and sixteen split follow-up adjacencies
are documented review points; no quality result or algorithm change follows
from this check. All 153 existing artifacts are unchanged. Report:
`outputs/validation/chunking-fit-20261123T182131Z.json`; see [CHUNKING](CHUNKING.md#expanded-corpus-fit-assessment--2026-11-23).
The two expanded chunk runs are now saved: PostgreSQL 113 and Atlas 38, with
the same settings and exact fit-check layout. Read-back preserves all 552
content blocks, 108 code blocks/nine tables; maximum 822 tokens. Original 49
chunks/IDs are identical. The import loader accepts both groups without a DB
connection, 43 offline tests passed and all 153 prior artifacts are unchanged.
No expanded DB records or vectors were written. Report:
`outputs/validation/corpus-expansion-chunk-20261123T182736Z.json`.
The expanded DB import is now committed: 10 new snapshots/102 new chunks,
with the original four PostgreSQL snapshots/49 chunks reused. All fourteen
selected snapshots/151 chunks matched local records on read-back. Old row
hashes, indexes/vectors/traces/spans and 169 local artifacts are unchanged.
Nine importer unit tests/four temporary-table DB tests passed; a repeated
import was accepted and rolled back. Report:
`outputs/validation/corpus-expansion-import-20261123T184700Z.json`.
The shared Nomic index is now committed:
`nomic-b2793fdf4ef7869c0589851fb5ee19da961118e251066311e0219f79d534c3d1`.
It contains exactly those fourteen snapshots/151 chunks, excluding original
Atlas v1/v2 controls. Input hashes, finite normalized 768-dimensional vectors,
index identity and a document-vector self-search passed. Old rows and 185
local artifacts are unchanged; 19 unit/17 DB tests passed. No hosted API call
or migration ran. Verification:
`outputs/validation/corpus-expansion-index-20261123T185609Z.json`.
The separate [expanded reference file](../data/evaluation/dev/expanded_questions.json)
is now verified against the complete shared scope: unchanged P01–P09/P19,
nine answerable plus one unanswerable. Six Atlas evidence records were rebound;
thirteen PostgreSQL records are unchanged. P19 received a fourteen-source absence/
policy-authority review. Bucket/family labels are recorded; all ten remain dev.
The checker supports plural pinned manifests and preserves the singular format.
All four dataset checks and 204 offline unit tests passed. A fresh read-only
DB check accepted the shared index and rejected the three old scopes; all
public rows and 182 protected files are unchanged; the development README was
updated. No retrieval/model call or
DB write ran. Record:
`outputs/validation/expanded-question-references-20261123T190949Z.json`.
The first new batch is complete in cumulative
[expanded_questions_v1_1.json](../data/evaluation/dev/expanded_questions_v1_1.json):
P21–P30 add four PostgreSQL, two Atlas, two combined and two negative records.
All original records, source pins and prior files are preserved. Batch-one totals
were 10 PostgreSQL/5 Atlas/2 combined/3 negative, all dev; 100 records remained.
The checker supports `missing_fact` editorial reviews about documented entities,
with complete-scope and entity-presence checks; it preserves P19's absent-entity
behavior. No automatic semantic absence test is claimed. All five reference
checks, 206 offline unit tests and Ruff passed; 188 protected artifacts are
unchanged. No DB/model/retrieval access ran. Verification:
`outputs/validation/expanded-questions-batch01-20261123T194352Z.json`.
The second batch P31–P40 is now verified in cumulative
[expanded_questions_v1_2.json](../data/evaluation/dev/expanded_questions_v1_2.json):
thirty dev questions, 25 answerable/5 unanswerable (14 PostgreSQL/7 Atlas/4 combined/
5 negative). All twenty inherited records and source pins are unchanged.
P39 lacks a promotion authorization policy; P40 lacks comparative performance
measurements. The existing checker/format handle both; no code changed.
Ten reference-boundary unit tests and all six dataset checks passed; all 191
protected artifacts are unchanged. No DB/model/retrieval access ran. Record:
`outputs/validation/expanded-questions-batch02-20261123T200722Z.json`.
The third batch P41–P50 is verified in cumulative
[expanded_questions_v1_3.json](../data/evaluation/dev/expanded_questions_v1_3.json):
forty dev questions, 33 answerable/7 unanswerable (18 PostgreSQL/9 Atlas/6 combined/
7 negative). All thirty inherited records/source pins and prior files remain.
MIX03 now connects the local NULL-lag decision to PostgreSQL idle behavior;
all 23 topic buckets have records. P49/P50 lack an individual index size and
current role membership respectively, with whole-corpus reviews. Ten reference
unit tests and all seven reference-file checks passed; 192 protected artifacts
are unchanged. Code is unchanged; no DB access or model/retrieval call ran. Record:
`outputs/validation/expanded-questions-batch03-20261123T201630Z.json`.
The fourth batch P51–P60 is verified in cumulative
[expanded_questions_v1_4.json](../data/evaluation/dev/expanded_questions_v1_4.json):
fifty dev questions, 41 answerable/9 unanswerable (22 PostgreSQL/11 Atlas/8 combined/
9 negative). All forty inherited records/source pins and prior files remain.
P59 lacks an event-row retention policy; P60 lacks evidence of the stated lag
event and its cause. P54/P58 share the foreign-key deletion family; related
EXPLAIN, isolation, statistics, lag and vacuum questions retain existing families.
Ten reference unit tests and all eight reference-file checks passed; 193
protected artifacts are unchanged. Code is unchanged; no DB access or model/retrieval call ran.
Record: `outputs/validation/expanded-questions-batch04-20261123T202711Z.json`.
The fifth batch P61–P70 is verified in cumulative
[expanded_questions_v1_5.json](../data/evaluation/dev/expanded_questions_v1_5.json):
sixty dev questions, 50 answerable/10 unanswerable (26 PostgreSQL/14 Atlas/10 combined/
10 negative), halfway toward the preparation target. This batch uses four
PostgreSQL, three Atlas, two combined and one negative record to follow the
remaining budgets. All fifty inherited records/source pins and prior files remain.
P70 lacks CPU allocation; related isolation/query/EXPLAIN/lag families are kept.
Ten reference unit tests and all nine reference-file checks passed; 194 protected
artifacts are unchanged. Code is unchanged; no DB access or model/retrieval call ran.
Record: `outputs/validation/expanded-questions-batch05-20261123T203929Z.json`.
The sixth batch P71–P80 is verified in cumulative
[expanded_questions_v1_6.json](../data/evaluation/dev/expanded_questions_v1_6.json):
seventy dev questions, 58 answerable/12 unanswerable (29 PostgreSQL/17 Atlas/
12 combined/12 negative). This batch adds three PostgreSQL, three Atlas,
two combined and two negative records. All sixty inherited records/source
pins and prior files remain. P77 contains hypothetical lag inputs, not an
imported observation. P79/P80 lack an observed setting and a measured usable
recovery point respectively. All negative buckets now have three records.
Ten reference unit tests and all ten reference-file checks passed; 195 protected
artifacts are unchanged. Code is unchanged; no DB access or model/retrieval call ran.
Record: `outputs/validation/expanded-questions-batch06-20261123T205144Z.json`.
Completion batch P81–P130 is verified in cumulative
[expanded_questions_v1_7.json](../data/evaluation/dev/expanded_questions_v1_7.json):
120 dev questions, 100 answerable/20 unanswerable (50 PostgreSQL/30 Atlas/20 combined/
20 negative). All 23 budgets are met, with five records per negative bucket.
The seventy inherited records and source state are unchanged. There are
252 requirements and 195 evidence records over 134 distinct blocks/73 chunks.
Ten reference unit tests and all eleven reference-file checks passed; all
196 protected files are unchanged. No app code, DB access or model/retrieval
call changed. Record: `outputs/validation/expanded-questions-complete-20261123T211259Z.json`.
Original datasets/indexes remain baselines; reranking is later work.

Four PostgreSQL sources produce 49 chunks; their Nomic index/49 vectors are preserved.
Atlas v1 adds two snapshots/12 chunks in its separate index. The later v2
control adds another two snapshots/12 chunks and an isolated index. Current
retrieval DB totals are 18 snapshots/175 chunks, four indexes/224 vectors and 24 traces/
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
five. See [HYBRID_RETRIEVAL](HYBRID_RETRIEVAL.md). Latest implementation checks:
201 unit/32 DB tests. No API/trace writes ran in that retrieval step.
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
| [check_retrieval.py](../scripts/check_retrieval.py) | Exact scope; all six quality metrics at 5/10/20, ranks, positive means and separate negative/manual-review records; schema 4, dense tracing only |
| [reranker_probe.py](../scripts/reranker_probe.py) | Explicit question/all selection and 4B/0.6B profiles, saved RRF top-20 reranking, per-pair progress/timing and existing metrics; no DB/API |
| [reranker_smoke.py](../scripts/reranker_smoke.py) | Native yes/no pair scoring, token checks and explicit preparation/runtime smoke modes; separate pinned uv environment |
| [check_document_questions.py](../scripts/check_document_questions.py) | Offline pinned-reference checks; single or multiple source manifests, exact evidence and negative-case scope |
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
| Expanded PostgreSQL allowlist / acquisition config | `data/corpus/postgres_expanded_v1.json`, `configs/corpus_expansion.toml`; original four definitions plus four new pages |
| Atlas sources and pinned local allowlist | `data/corpus/synthetic/atlas_inventory.md`, `atlas_operations_policy.md`, `sources.json` |
| Expanded Atlas sources / pinned manifest | `data/corpus/synthetic/atlas-expanded-v1/`: six Markdown files plus `sources.json` |
| Expanded Atlas raw/manifest/parsed run | `data/local/markdown/atlas-expanded-v1-hyrbftbg/<snapshot_id>/`; six snapshots, 134 blocks |
| Expanded PostgreSQL chunks | `data/local/chunks/postgres-expanded-v1-section-blocks-v1/`; eight sources/113 chunks, imported |
| Expanded Atlas chunks | `data/local/chunks/atlas-expanded-v1-section-blocks-v1/`; six sources/38 chunks, imported and embedded in the shared index |
| Atlas raw copies/manifests/parsed blocks | `data/local/markdown/atlas-docs-v1-ssme1pql/<snapshot_id>/` |
| Atlas chunks, block token counts and summary | `data/local/chunks/atlas-docs-v1-section-blocks-v1/` |
| HTML + manifests | `data/local/snapshots/<snapshot_id>/` |
| HTML parsed blocks | `data/local/parsed/<snapshot_id>.json`; eight files, 504 blocks |
| Chunk JSON + summary | `data/local/chunks/pilot-section-blocks-v1/` |
| Model weights | `data/local/models/nomic-ai--nomic-embed-text-v1.5/<revision>/` |
| Six questions + gold evidence | `data/evaluation/dev/document_questions.json` |
| Four Atlas references, including scope-only P19 | `data/evaluation/dev/atlas_questions.json` |
| Ten unchanged questions revalidated against the shared fourteen-source/151-chunk scope | `data/evaluation/dev/expanded_questions.json`; nine answerable + one unanswerable, dev only |
| First new batch, cumulative version 1.1.0 | `data/evaluation/dev/expanded_questions_v1_1.json`; twenty questions, preserved |
| Second new batch, cumulative version 1.2.0 | `data/evaluation/dev/expanded_questions_v1_2.json`; thirty questions, preserved |
| Third new batch, cumulative version 1.3.0 | `data/evaluation/dev/expanded_questions_v1_3.json`; forty questions, preserved |
| Fourth new batch, cumulative version 1.4.0 | `data/evaluation/dev/expanded_questions_v1_4.json`; fifty questions, preserved |
| Fifth new batch, cumulative version 1.5.0 | `data/evaluation/dev/expanded_questions_v1_5.json`; sixty questions, preserved |
| Sixth new batch, cumulative version 1.6.0 | `data/evaluation/dev/expanded_questions_v1_6.json`; seventy questions, preserved |
| Completed cumulative expanded references, version 1.7.0 | `data/evaluation/dev/expanded_questions_v1_7.json`; 120 questions, 100 answerable + 20 unanswerable, dev only |
| Current annotation revision, version 1.8.0 | `data/evaluation/dev/expanded_questions_v1_8.json`; same raw questions/scope, twelve annotation corrections |
| Editorial review | `data/evaluation/dev/reference_review_v1_8.json`; exact accepted spans and requirement changes; [summary](REFERENCE_REVIEW.md) |
| Offline rescoring | `scripts/rescore_retrieval.py`; run as `python -m scripts.rescore_retrieval`; no DB/model |
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
- Shared expanded scope (151): `nomic-b2793fdf4ef7869c0589851fb5ee19da961118e251066311e0219f79d534c3d1`.

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

The owner's **120-question Qwen4B run is complete and verified**: 2,400 pairs,
MPS/float16, **batch size one**, version-1.8 references and unchanged RRF top-20
candidates. Full support @5 is RRF 82/100 → reranked 92/100; @10 93/100 → 100/100.
Mean reranking is 43.69 s/question, 87 min 23 s total scoring. All six metrics
and summaries were independently recomputed with preserved questions/candidates
and matching provenance; no model/DB/API call ran during verification.
Read [the full-set results](QWEN_RERANKER_COMPARISON.md#full-120-question-qwen4b-run).
Report: `outputs/reranking/qwen4b-probe-20261125T202218873027Z.json`;
audit: `outputs/validation/qwen4b-full-20261125T202218873027Z.json`.
**Next:** integrate RRF top-20 → selected Qwen4B → initial top-5 into Enhanced's
document retrieval path. Shared answer generation and reranker spans follow in
separate increments. Do not rerun 4B unnecessarily; the supervisor diagram now
includes the verified result and owner decision.

**Current owner decision:** keep **Qwen3-Reranker-4B** for the school project and
a one- or two-question demo. The owner accepts the measured 43.69-second mean;
the earlier under-10-second gate is withdrawn. Timing remains recorded, not a
model-selection blocker. Full-set 0.6B and batching studies are optional.

Earlier, the owner chose Qwen0.6B for a trial. It is pinned/downloaded under
`configs/reranker_qwen06b.toml`; the native smoke and 2,400 input checks passed.
The paired four-question test averages 5.95 s for 0.6B versus a fresh 27.90 s for
4B, both MPS/float16/batch one. P05 top-five support is 0/3 versus 2/3; P07/P27
stay 2/2 and 3/3. All 227 offline tests and independent metric/input checks passed.
Read [the paired comparison](QWEN_RERANKER_COMPARISON.md) for limits/artifacts.
A batch-four 4B command is also prepared:
`--batch-size 4`, with schema-2 batch metadata and correct left-padding/masks.
All 229 offline tests passed. A native P05 check preserved the full ranking but
took 46.36 seconds versus batch one's 30.85; it does not show a speedup. Report:
`outputs/reranking/qwen4b-probe-20261125T184838008770Z.json`; verification:
`outputs/validation/qwen4b-batch4-20261125T184838008770Z.json`.
The [batch test](COMMANDS.md#run-qwen4b-with-batch-size-four) and full-set 0.6B
comparison remain optional. Scripts already default to selected 4B/batch one;
neither model is integrated into the answer workflow. Preserve both
profiles and all prior results. Ettin remains an untested alternative.

Read the [Qwen4B research review](QWEN_RERANKER_REVIEW.md). Qwen3-Reranker-4B
is the selected project reranker: [setup](QWEN_RERANKER_SETUP.md),
`configs/reranker.toml`, `scripts/reranker_smoke.py` and its separate uv lock.
Pinned tokenizer/config assets are local; all 2,400 saved RRF input pairs fit
without truncation (max 821 / limit 2,048). The pinned pretrained weights are now
downloaded (8.04 GB, ignored by Git); shard hashes match the download metadata.
The MPS/float16 smoke passed: load 18.51 seconds, two short passages 2.99 seconds,
relevant/unrelated scores 0.962953/0.000005104. Runtime report:
`outputs/reranking/qwen4b-20261125T180455418462Z.json`.
The earlier preparation passed 225 unit tests and a tiny random native forward;
this download ran the pretrained smoke without code/config/lock changes or DB/API
access. The subsequent four-question real-candidate probe is now complete:
P05/P07/P27/P19, 80 pairs, 8.18-second load and 110.40-second scoring. Required
claims supported at five are P05 0/3 → 2/3, P07 2/2 → 2/2 and P27 1/3 → 3/3.
P19 remains a separate negative; its high score is not calibrated answerability.
The probe preserves all candidates and original source/rank fields. All 227
offline tests and independent metric/preservation checks passed. Report:
`outputs/reranking/qwen4b-probe-20261125T181229740228Z.json`; audit:
`outputs/validation/qwen4b-probe-20261125T181229740228Z.json`.
No new retrieval, DB access, hosted call or answer generation ran. No prior
code/config/lock, dataset or baseline report changed. The small targeted sample
does not establish general quality. The runner now supports `--all` (120 questions,
2,400 pairs, selection checked offline); `--question-id` remains available for
subsets. This selector change ran no model inference. The full 4B comparison
is now verified above; a smaller-model comparison is not a prerequisite for
Enhanced integration. Preserve both annotation versions,
raw reports and rescores. Relevance review remains non-exhaustive; final
held-out/scoring decisions remain open. No live service was checked during
offline rescoring; recheck service state before any later DB work.

### Earlier verification records

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
Later component proposal: select and implement a reranker as a separate increment.
Preserve all baselines and P09's omission.
Do not infer general accuracy from either small pair.
The documents define no live lag or actual index/plan output; DB fixtures/tools follow later.
Preserve existing questions,
snapshots, chunks, index and `limit=5`. The current context sends all five
whole chunks without truncation; no final numeric context budget is chosen.
Synthetic-source ingestion/tools, Enhanced and Agentic follow the Simple baseline.

## Checks and resume commands

Supervisor materials originally prepared on 2026-11-23 are in
[presentations/2026-11-23/](presentations/2026-11-23/README.md): annotated
pipeline PDF/PNG/SVG and a one-page briefing PDF with editable Markdown.
The **25-November diagram revision** adds the 14-source/151-chunk scope,
dense/full-text/RRF and Qwen3 reranking stages, current/planned workflow and tool
statuses, tracing coverage and six retrieval metrics. It separates offline
evaluation from the live response. Router method remains open; Enhanced and
Agentic workflow composition and DB tools are not built. Shared validation is
partial: Simple's completion/nonempty checks exist; citation checks are planned
and grounding/failure/retry policy is open. The verified 4B full run and the
owner's model selection are now shown. The [renderer](presentations/2026-11-23/render_pipeline.py)
regenerates all three exports. PDF visual/text checks and local links passed;
no model/DB/API work or experiment change ran for this revision. The briefing
PDF/Markdown remain the earlier 23-November snapshot, explicitly dated in the
presentation README.

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
