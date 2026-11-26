# Current status

**Last updated:** 2026-11-25. This is the current implementation boundary.
Detailed dated records are in [STATUS_HISTORY.md](STATUS_HISTORY.md);
plans are in [ROADMAP](ROADMAP.md), decisions in [PROJECT_CONTEXT](PROJECT_CONTEXT.md),
and code/artifact paths in [HANDOFF](HANDOFF.md).

**Assistant handoff refreshed, 2026-11-25:** [CLAUDE.md](../CLAUDE.md) points to
the repository rules; [HANDOFF's resume snapshot](HANDOFF.md#resume-snapshot--2026-11-25)
records the selected 4B model, completed run, exact evidence/code paths, local
artifact caveats and next live-retrieval increment. Its report/runtime-code hash
checks passed without inference, DB/API access or a repeated benchmark. No
application code or experiment setting changed for this handoff. Documentation
links and `git diff --check` passed; application tests were not repeated.

## Implemented

| Area | Current state |
| --- | --- |
| Sources | Eight PostgreSQL 18 HTML snapshots/113 chunks imported; original four sources preserved |
| Synthetic sources | Atlas v1/v2 preserved separately; six expanded Atlas snapshots/38 chunks embedded in the shared index |
| Parsing | Selected expansion scope: eight PostgreSQL + six Atlas sources, 638 blocks; four original HTML outputs reused |
| Chunking | Expanded scope: 552 content blocks → 151 saved chunks (113 PostgreSQL/38 Atlas); target 512 / ceiling 1024; maximum 822; original 49 unchanged |
| Embedding | Pinned local Nomic; normalized 768-dimensional vectors; shared fourteen-snapshot index has 151 vectors |
| Database | Applied Alembic `0002`; 18 snapshots, 175 chunks, four indexes/224 vectors, 24 traces/37 spans (read-only verification 2026-11-25) |
| Retrieval | Dense, English OR full-text and equal-weight RRF fusion (`k=60`, 20 candidates/method); live `retrieve_reranked()` scores the fused top 20 and returns the top five (offline-tested, not yet run live); Simple remains dense with `limit=5` |
| Reranker runtime | Selected Qwen4B: 120 questions/2,400 pairs verified, batch one, 43.69 s/question; full support @5 improves 82/100 to 92/100. Latency accepted; live retrieval function added, Enhanced answer workflow pending |
| Diagnostics | Schema 4 / `annotated-evidence-v2`: all six quality metrics at 5/10/20, answerable-only means, separate negatives and manual-review candidates; elapsed time retained |
| Expanded comparison | Same saved dense/full-text/RRF rankings rescored with v1.8 references; full support @5: 83/65/82 of 100; @20: 88/95/100. Original v1.7 scores preserved; relevance review is not exhaustive |
| Tracing | Retrieval-only diagnostics plus workflow-owned retrieval/LLM spans; exact prompt/output/usage |
| Generator | Luna client, source-linked context, `answer_v1` and Simple workflow; one live P04 answer verified |
| Answer runners | Simple/LLM-only support `--dataset`, one/all selection, shared resources/run ID and per-question records; Simple requires exact index scope |
| Live Simple batch | P01–P06 completed; editorial review: P01/P02/P04/P06 meet recorded requirements, P03/P05 partial |
| LLM-only control | Live PostgreSQL and Atlas pairs completed; raw-question-only inputs verified, with one LLM span per question |
| Questions | Expanded dev version 1.8.0 refines twelve annotations; same 120 raw questions, groups, source pins and twenty negative records; all prior versions preserved |
| Changed evidence | P08 is unchanged across v1/v2; fresh Simple answers follow the source limit, 5 → 8 seconds, with supporting citations |

Nomic revision: `e9b6763023c676ca8431644204f50c2b100d9aab`, CPU float32,
1024-token application limit. Committed indexes:

- PostgreSQL, 49 vectors: `nomic-d4a8ebdbce1253c45ea50734d984a14a6258d9f1e7a332fd56964011eb886447`.
- Atlas, 12 vectors: `nomic-b98238adf1e5b69036fc64a756e3171b7459ad8842e8c3ea280fe9a777ad8ddf`.
- Atlas v2, 12 vectors: `nomic-5710f4359df83e693a0d994cbf59c45d6ebe9b08695f0ff4d9f75ec062825a55`.
- Expanded shared scope, 151 vectors: `nomic-b2793fdf4ef7869c0589851fb5ee19da961118e251066311e0219f79d534c3d1`.

Keep pinned questions/snapshots/chunks/index unchanged when comparing workflows.

## Selected reranker — owner decision, 2026-11-25

Use **Qwen3-Reranker-4B** for the school project and a one- or two-question demo.
The owner accepts its measured runtime and withdraws the earlier under-10-second
requirement. Keep recording latency and quality; full 0.6B testing and further
batch-size experiments are optional. The pinned 4B config and batch-one default
already match this choice; no runtime/configuration change is needed.

The live RRF top-20 → Qwen4B → initial top-5 retrieval function is now added;
see the next section. Shared generation and reranker tracing follow in separate
increments; tools and the complete Enhanced workflow are still pending.
Core design/status/setup documents and the supervisor SVG/PNG/PDF now reflect
the choice and verified full run. Documentation links, SVG/PDF text and visual
layout were checked; no application tests, inference or DB/API calls ran.

## Live reranked retrieval function — 2026-11-25

`retrieve_reranked()` in [retrieval.py](../src/rag_workflow_lab/retrieval.py)
explicitly requests `retrieve_hybrid(..., limit=20)`, builds each passage from
the SQL match's stored `metadata.heading_path` and whole `text` (heading path
joined by ` > `, a blank line, then the chunk body), scores it with a
caller-supplied `score_passage(question, passage)` and returns the top `limit`
(default 5, allowed 1–20). Each result keeps the RRF match fields plus `rrf_rank`
and `reranker_score`; equal scores keep RRF order. No Nomic prefix, gold data or
truncation enters scoring. The caller loads Qwen once and wraps the unchanged
native `score()` from [reranker_smoke.py](../scripts/reranker_smoke.py), so the
`src` package needs no torch import and the saved-report code hashes still match.
All 151 shared-scope chunk files have a nonempty `heading_path`.

Verification: **233 offline unit tests passed** (4 new), Ruff `F` checks and
`git diff --check` passed. One new test confirms the live passages and ordering
match the saved-candidate probe's `rerank()` for the same chunks. No model,
DB, API or benchmark run occurred; the function has not yet run against the
live DB/model, and no workflow calls it yet.

## Full Qwen4B run verified — 2026-11-25

The owner's saved run is complete: **120 unique questions, 2,400 scored pairs**,
dataset v1.8, unchanged saved RRF top-20 lists and **batch size one**. Offline
checks independently reproduced all six metrics and summaries, verified raw
question/candidate/source preservation and provenance hashes, and confirmed
the timing totals. No model inference, DB/API access or application code change
was needed for this verification.

Full annotated support @5 rises **82/100 → 92/100**, and @10 **93/100 → 100/100**;
@20 stays 100/100. Mean reranking is **43.69 s/question**, scoring total
**87 min 23 s**, plus a 6.58-second load. This improves evidence ranking; the owner
now accepts this wait for the project/demo. Twenty negatives are outside
positive means; no generated answers were evaluated. Details and all six
top-five scores: [Qwen comparison](QWEN_RERANKER_COMPARISON.md#full-120-question-qwen4b-run).
Raw report: `outputs/reranking/qwen4b-probe-20261125T202218873027Z.json`;
audit: `outputs/validation/qwen4b-full-20261125T202218873027Z.json`.
Qwen4B is selected; full-set 0.6B testing is optional. Enhanced integration is next.

## Supervisor diagram revision — 2026-11-25

Updated the existing [presentation diagram](presentations/2026-11-23/README.md)
in SVG/PNG/PDF, with a small renderer for later edits. It now shows the 14-source,
151-chunk scope, dense Simple path, Enhanced's dense/full-text → RRF → top-20
→ Qwen3 reranker components, planned tools/Agentic/router, and shared generation
and validation statuses. Tracing coverage and all six retrieval metrics at
5/10/20 are explained separately from the live response path. The earlier
23-November speaking notes remain unchanged and are marked as historical.

The diagram now includes the verified 120-question 4B result and the owner's
selection, with live workflow integration still marked partial. PDF rendering, visual review,
required labels, text bounds and local links were checked. No application code,
model inference, API/DB access, benchmark input or report changed; application
tests were not repeated for this presentation-only update.

## Retrieval findings and limits

The initial dense check found annotated evidence in the top five for five
questions. P05's E1/E2/E3 ranks are 17/11/46; adding `multicolumn` in an
exploratory probe moved E1/E2 to 1/2. SQL distances and stored inputs passed
independent checks. This shows wording sensitivity, not a selected rewrite policy.

The repeatable checker matched prior ranks in two real-model runs. P05 has
0/3, 0/3 and 2/3 annotated hits at 5/10/20; P06 has 2/4 at each cutoff, with
valid evidence alternatives. These are annotation counts, not answer grades
or a held-out result; the sweep did not select a new production context budget.
See the [development results](../data/evaluation/dev/README.md#repeatable-retrieval-checker).

The owner authorized migration `0002` on 2026-11-16. A real P04 check committed
one `ok` trace and retrieval span; E1/E2 ranked 1/2 and answer/usage/cost stayed
NULL. Trace ID: `db808e0d-76ed-4148-9996-2a8988cc4ce7`. The full six-question
traced retrieval-diagnostic batch is available but has not run.
Details: [TRACING_PLAN](TRACING_PLAN.md).

## Latest verification — 2026-11-17

- **159 offline unit tests passed**, including 13 new LLM-only isolation/runner tests.
- **21 local PostgreSQL integration tests passed**, using temporary tables and
  synthetic vectors. `check-db` confirmed read-only PostgreSQL 18.6 + pgvector
  0.8.7; Alembic reported `0002 (head)`. Service health was checked this date,
  not inferred from older records.
- Ruff's unused/undefined-name checks and installed-dependency compatibility
  checks passed. The CLI refinement matched the prior version in 11 cases,
  including outputs, error codes and mocked side effects.
- Earlier this date, three real-SDK mock-transport checks covered completed,
  incomplete and HTTP 429 replies without network access or retries.
- On the owner's explicit request, one live Luna smoke passed: `completed`,
  answer `Luna API smoke test passed.`, 27 input / 11 output tokens, zero
  reasoning tokens and 5.26 seconds. The key was moved from `.env.example`
  to the ignored `.env`; the tracked template is blank. Report:
  `outputs/llm/luna-smoke-20261117T170826Z.json`. Estimated Standard token cost:
  $0.0000082 before taxes/extra services. This is connectivity verification,
  not a RAG answer; no corpus was sent and no DB/LLM trace was written.
- The later P04 Simple run completed with five whole chunks and one Luna call.
  Both mandatory requirements and optional monitoring guidance passed a
  post-run editorial check; S1/S2 map to P04-E1/E2. Gold was not sent to Luna.
  Usage: 2,207 input / 81 output / 2,288 total, zero reasoning tokens;
  2,204 input tokens were 30-minute cache writes, zero cache reads.
  Retrieval took 0.719 s and generation 4.125 s; workflow total 4.854 s
  excludes model loading. Estimated Standard cost including cache writes:
  **$0.0003163**, not an invoice. DB cost remains NULL.
  Trace: `0a5c1437-8383-4702-b9a7-e676a24ddbee`.
  Report: `outputs/answers/simple-P04-20261117T172725743636Z.json`;
  independent checks: `outputs/validation/simple-P04-20261117T172725743636Z.json`.
  A fresh read-only connection verified exact prompt/chunk text, label mapping,
  answer/usage and both completed spans. Public totals are now two traces/three
  spans; corpus/index and the older trace/span fingerprints are unchanged.
- Generalized and renamed the P04 script/lock to `run_simple_rag.py` and its
  matching lockfile. `--question-id` and `--all` are mutually exclusive and
  required; invalid IDs fail before model loading or DB/API client creation.
  The runner loads Nomic once, reuses connections/client, shares one batch
  `run_id` and saves per-question trace/source/answer/usage/duration records
  in a schema-version-2 JSON report. Incomplete replies remain visible and
  produce exit code 2; provider/DB exceptions stop the batch without retries.
  The runner preparation used mocks and offline checks only; it made no API
  calls or DB writes. The earlier 20 DB integration checks were not repeated
  because the workflow/store/tracing implementation is unchanged.
- Added [COMMANDS.md](COMMANDS.md) with copyable commands, short descriptions,
  supported options and output locations. CLI help was checked locally;
  documentation preparation made no model calls or DB writes.
- On the owner's instruction, the live six-question Simple batch completed:
  `simple-20261117T183619008413Z`. Six Luna requests returned `completed`;
  a fresh read-only check verified six distinct traces and 12 retrieval/LLM
  spans, exact prompts/full chunk texts, responses and usage. Public totals
  are eight traces/15 spans; corpus/index and older records are unchanged.
  Post-run editorial review found P01/P02/P04/P06 meet recorded requirements;
  P03 omits the eligibility-versus-selection distinction despite retrieving
  its evidence at S3. P05 misses the multicolumn evidence, acknowledges that
  gap and answers the plan-inspection part; it remains partial. This is not
  an automated grade or a held-out accuracy result.
  Usage: 15,328 input / 457 output / 15,785 total; zero reasoning/cache reads,
  15,310 30-minute cache-write tokens. Batch workflow time: 19.262 s, excluding
  model loading. Estimated Standard token cost: $0.00214405, not an invoice;
  DB cost remains NULL. Report: `outputs/answers/simple-20261117T183619008413Z.json`.
  Integrity checks and editorial review are the same basename under
  `outputs/validation/`, with `-review.json` for the latter. No code or prompt
  changed; unit/DB tests were not repeated for this execution-only step.
- Prepared `workflows.llm_only`, `llm_only_v1` and locked `run_llm_only.py`.
  The control uses the same Luna/settings with a concise own-knowledge prompt,
  an explicit PostgreSQL 18 task label and unchanged raw questions. No source
  excerpts, answer hints, tools or prior responses enter generation. The sole
  DB connection writes traces; it reads no corpus/index tables or source files.
  Question selection is now shared through `evaluation.dataset.select_questions()`;
  existing Simple behavior and its prompt are preserved. SDK/database dependency
  versions match Simple; the control's environment has no ML packages. Unit
  tests and temporary-table DB round trips passed, including incomplete replies.
  All six public-table fingerprints are unchanged, including eight traces/15
  spans. Record: `outputs/validation/llm-only-prepared-20261117T190852Z.json`.
  No hosted LLM-only call ran during preparation. See
  [COMMANDS](COMMANDS.md#llm-only-control).
- The owner then requested the live LLM-only batch and comparison. All six
  calls completed in `llm-only-20261117T191359474642Z`. A fresh read-only
  check confirmed unchanged raw questions and generator settings, one LLM
  span/trace per question, exact prompt/output/usage and empty sources with
  retrieval disabled. Six traces/six spans were added: totals 14 traces/21
  spans. Corpus/index, older records and the Simple raw report are unchanged.
  Same-requirement editorial comparison: Simple meets P01/P02/P04/P06;
  LLM-only meets P01/P05/P06. Simple is more complete on P02/P04, LLM-only on
  P05, both partial on P03. These are completeness observations, not general
  accuracy rates or proof of training-data membership. LLM-only used 523
  input / 621 output / 1,144 total tokens; zero reasoning/cache tokens.
  Workflow batch time was 19.031 s; estimated Standard token cost $0.0003628.
  Compare Simple's 19.262 s excluding model loading and $0.00214405 estimate.
  The sample/prompt differences prevent a pure causal or latency conclusion.
  See [LLM_ONLY_COMPARISON](LLM_ONLY_COMPARISON.md) and
  `outputs/comparisons/simple-vs-llm-only-20261117T191359474642Z.json`.
  No application code, prompt or dataset changed; tests were not repeated
  for this execution/documentation-only step.

The review shortened repeated orientation prose and moved chronological
records intact to [history](STATUS_HISTORY.md). Source IDs, corpus artifacts,
embedding/index behavior, migrations and dataset annotations are unchanged.
Generated `.egg-info` metadata is ignored and no longer tracked; its files
remain on disk. All six public-table counts/fingerprints matched before and
after the review.
See `outputs/validation/refine-2026-11-17.json` for the final review checks;
older evidence paths are listed in the history.

## Atlas synthetic sources — 2026-11-17

Created two English corpus documents in `data/corpus/synthetic/`:
[inventory](../data/corpus/synthetic/atlas_inventory.md) (`LOCAL-INVENTORY`)
and [operations policy](../data/corpus/synthetic/atlas_operations_policy.md)
(`LOCAL-POLICY`), with 630 and 668 whitespace-separated words respectively.
Both use version 1.0 and document state `atlas-docs-v1`.
The inventory defines a fictional 120-table, 10.0 GB database, its important
tables, replica identity and customer lookup query. The policy retains the
5-second inclusive lag criterion and unknown outcome for missing/invalid data.
All values are synthetic; no live lag, index definitions or measured plans
were added. Document structure, storage totals, source references, protected-file
hashes and local links were checked. No runtime code, manifest, dataset or DB
changed, and no API call or ingestion ran. At that point, P07–P20 were still drafts.
Validation record: `outputs/validation/atlas-docs-v1-authored-20261117.json`.

## Markdown ingestion — 2026-11-18

Added the separate pinned [Markdown manifest](../data/corpus/synthetic/sources.json),
scoped `ingestion/markdown.py` reader and `ingest-markdown` CLI command. It
validates local source boundaries and hashes before writes, then preserves
raw copies and source/state/version/hash metadata in new snapshot folders.
Parsed output reuses `ParsedDocument`/`ParsedBlock`, including heading paths,
table cells, intact SQL and one-based source-line anchors. Lists/inline markup
remain text; this is not a general Markdown implementation. No dependency added.

Ran the command on both Atlas files. Output:
`data/local/markdown/atlas-docs-v1-ssme1pql/`.
Inventory: `LOCAL-INVENTORY-246a17e09e73d871`, 19 blocks
(6 headings, 11 paragraphs, 1 table, 1 code).
Policy: `LOCAL-POLICY-d7124ea3bb39455d`, 18 blocks
(6 headings, 11 paragraphs, 1 table).

**168 offline unit tests passed**, including nine new Markdown tests. Existing
P01–P06 reference checks, changed-file Ruff checks and whitespace checks passed.
Independent read-back verified source bytes/hashes and parsed metadata; all
24 protected source/evaluation/HTML artifact hashes stayed unchanged. Record:
`outputs/validation/markdown-ingestion-20261118.json`.
No token measurement, chunking, embedding, DB access or API call ran. The
HTML manifest/contracts/parser and existing 49 chunks/index are unchanged.
DB integration tests were not repeated; this change has no DB code.

## Atlas token measurement and chunking — 2026-11-18

The existing chunk runner now accepts `--markdown-run` with the separate Atlas
allowlist. A snapshot reader verifies pinned metadata/bytes and saved blocks
by reparsing the immutable copies. The chunking algorithm and settings are
unchanged: `section-blocks-v1`, 512 target / 1024 ceiling, no overlap/truncation.
Per-content-block body/contextual counts are saved alongside the chunks.

Output: `data/local/chunks/atlas-docs-v1-section-blocks-v1/`.

| Source | Content blocks | Chunks | Chunk token range | Largest contextual block |
| --- | ---: | ---: | ---: | ---: |
| LOCAL-INVENTORY | 13 | 6 | 60–268 | 113 |
| LOCAL-POLICY | 12 | 6 | 59–204 | 103 |

All 25 content blocks, one SQL block and two tables are preserved exactly once;
12 headings remain as context/heading records. Total complete chunk inputs:
1,861 tokens. No chunk exceeds the target. The cached pinned Nomic tokenizer
ran locally; no embedding model was loaded.

**173 offline unit tests passed**, including five new snapshot-reader tests.
Independent read-back reproduced all Atlas chunks/counts. A temporary HTML
regression run reproduced all 49 original chunks and heading records exactly;
P01–P06 reference checks and changed-file Ruff/whitespace checks passed.
All 35 protected source/evaluation/snapshot/old-chunk/core-algorithm hashes
were unchanged. Record: `outputs/validation/atlas-chunking-20261118.json`.
No DB/API access occurred; DB tests were not repeated.

## Atlas reference dataset — 2026-11-18

Added [atlas_questions.json](../data/evaluation/dev/atlas_questions.json),
`atlas-document-dev` / `1.0.0`: P07–P09 are answerable and P19 is unanswerable
within the complete pinned two-document Atlas state. The original PostgreSQL
six-question file/hash and answer-runner defaults are unchanged. P19's raw
question drops the draft clause that disclosed document absence; its ID/scope
remain unchanged. P07–P09 wording is unchanged.

Eight requirements and six positive evidence records reference five blocks/
four chunks. P09 records complementary inventory/policy support; P19 has no
positive answer evidence and instead binds a complete corpus-scope review.
The existing checker now handles Markdown source records and `any`/`all`/
`corpus_scope` references. It checks integrity; semantic support and absence
were reviewed against the complete saved documents.

Both dataset checks, **178 offline unit tests**, changed-file Ruff and
whitespace checks passed. Five new unit tests cover bad references/spans,
negative-case scope, state/hash mismatches and gold isolation without local
corpus fixtures. All 64 protected file hashes were unchanged. Record:
`outputs/validation/atlas-questions-v1-20261118.json`.
Runtime workflows, corpus/chunk files and DB state were unchanged. No API call ran.
At that point, Atlas import/indexing and runner selection were unimplemented;
these are reference annotations, not generated-answer results.

## Atlas database import — 2026-11-18

Added explicit Markdown inputs to `import_corpus.py`, reusing the pinned
snapshot reader. It verifies snapshot provenance, complete ordered block
coverage, intact table/SQL blocks and rendered text before opening a DB
connection. `save_snapshots()` uses local `captured_at` as the acquisition
timestamp in the legacy `downloaded_at` column. No schema change was needed;
repository/database head remains `0002`. HTML defaults are preserved.

The owner authorized the committed import. Fresh checks confirmed the Docker
service healthy, PostgreSQL 18.6/pgvector 0.8.7 and revision `0002`. Imported
two Atlas snapshots and 12 chunks in one transaction, then repeated the same
command. A fresh read-only connection verified both snapshot records and all
12 chunk payloads against their files. Repeat-import row counts and full
logical row fingerprints were identical.

Public totals: six snapshots, 61 chunks, one index/49 vectors and 14 traces/21
spans. Atlas has six inventory chunks, six policy chunks and zero embeddings.
All old snapshot/chunk/index/vector/trace/span rows retained their fingerprints;
all 35 protected source/dataset/artifact hashes were unchanged.
**181 offline unit tests and 22 DB integration tests passed**, including local
timestamp/immutability checks. Both dataset reference checks, changed-file
Ruff and whitespace checks passed. DB tests used temporary tables/rollback.
Record: `outputs/validation/atlas-import-20261118.json`, with separate before/
first-import records in the same directory. No real model inference or API call ran.

## Atlas embedding index — 2026-11-18

Added repeatable `--source-id` selection to `index_corpus.py`. It uses a
parameterized source/snapshot join, rejects any requested source without
chunks before inference/writes, and records sorted unique source IDs in index
settings. Omitting the flag retains the all-stored-chunks behavior.

The owner-authorized offline Nomic run selected `LOCAL-INVENTORY` and
`LOCAL-POLICY`: exactly 12 artifact-matched chunks, 1,861 input tokens.
It committed one separate index with 12 normalized 768-dimensional vectors.
Independent read-back verified exact membership/input hashes, finite vectors,
norms and reproducible index identity/code/lock/model-manifest fingerprints.
All older rows, including the PostgreSQL index/49 vectors, retained their
logical fingerprints. Totals: six snapshots, 61 chunks, two indexes/61 vectors,
14 traces/21 spans. Revision remains `0002`; no hosted API call ran.

**181 offline unit tests and 24 DB integration tests passed**, including
source isolation, missing-source rejection, repeatability and preservation of
other indexes. Ruff passed. Validation:
`outputs/validation/atlas-index-20261118.json`, with a separate before record.

## Atlas retrieval diagnostic — 2026-11-18

Added `--dataset` to `check_retrieval.py`, retaining the PostgreSQL default.
Before model loading it verifies exact index membership, snapshots, stored
inputs and hashes against the complete pinned dataset scope. Wrong Atlas/PG
pairing was rejected in a live read-only check. Reports use schema version 2;
unanswerable P19 retains its ranking with positive evidence scoring marked N/A.
Only unchanged question text enters the query embedder; gold does not guide search.

The offline Atlas run `dense-20261118T202158580023Z` checked all four questions:
P07 E1 rank 1; P08 E1/E2 rank 1 (one chunk); P09 E1/E2/E3 ranks 1/3/2.
All six positive annotations are present in the top three. P19 returns the
Atlas lag rule first and its Atlas-only scope third; these do not establish a
Boreal limit. No answer or abstention was generated or graded. The 12-chunk/
three-answerable-question check does not establish general retrieval quality
or improvement over LLM-only. No settings, rewriting or filtering were tuned.

Independent read-back verified ranks/cutoffs, all 12 memberships/source fields,
query/code hashes and unchanged fingerprints for all six public tables plus
31 pinned files. DB totals remain six snapshots/61 chunks, two indexes/61
vectors and 14 traces/21 spans; no trace, migration or paid call ran.
**184 unit tests, 24 DB integration tests and Ruff passed.**
Report: `outputs/retrieval/dense-20261118T202158580023Z.json`.
Validation: `outputs/validation/atlas-retrieval-20261118.json`.
See the [Atlas results](../data/evaluation/dev/README.md#atlas-retrieval-diagnostic--2026-11-18).

## Atlas paired answer check — 2026-11-18

Both answer runners now accept `--dataset`, preserving the PostgreSQL default.
Simple reuses the diagnostic's complete pinned index-scope check before model
loading or trace/API clients. LLM-only reads only question JSON and passes only
raw text to generation. Reports/configuration record dataset path/hash;
the prompts, model/settings and workflow behavior are unchanged.

The owner-authorized pair made eight independent completed Luna calls, first
LLM-only then Simple using the Atlas-only index/top five. Editorial review
against the pinned requirements found P07/P08 complete with supported citations;
P09 gives the correct replica/rule/inclusive limit but omits the explicit
`reporting` role (R1 partial). LLM-only honestly abstains on all three answerable
questions. Both appropriately abstain on P19; Simple mentions five seconds only
as an Atlas limit and rejects transfer to Boreal. No numeric Boreal limit was invented.

This shows practical access to source-specific facts in this pair, not general
accuracy or a pure causal retrieval estimate. One generation per arm, different
fixed prompts and the 12-chunk development scope remain limitations.
Simple used 6,772 input/186 output tokens; LLM-only 321/118. No price estimate
was added; DB cost remains NULL. See the [comparison](LLM_ONLY_COMPARISON.md#atlas-source-specific-comparison--2026-11-18).

Fresh read-back verified exact prompts/full source text, output/usage/settings,
eight new traces and 12 spans. Older rows, 39 protected files and 42 prior reports
retained their fingerprints. Totals: six snapshots/61 chunks, two indexes/61
vectors, 22 traces/33 spans; revision remains `0002`.
**187 unit tests, 24 DB integration tests and Ruff passed.**
Runs: `simple-20261118T203140812238Z`, `llm-only-20261118T203122477461Z`.
Records: `outputs/comparisons/atlas-simple-vs-llm-only-20261118.json` and
`outputs/validation/atlas-paired-20261118.json`; raw reports are in `outputs/answers/`.

## Supervisor discussion materials — 2026-11-23

Prepared the [presentation package](presentations/2026-11-23/README.md):
one-page pipeline PDF, slide PNG, editable SVG and a one-page briefing PDF
with Markdown source. The chart separates source preparation, question-time
routing, cross-cutting tracing and offline experiments, with explicit
DONE / NOT BUILT / PARTIAL / OPEN notes. It shows the current direct Simple
path and the proposed router selecting one workflow; router method is undecided.
The response is an output, not an extra model call after a RAG workflow.

Checked current code/design and the saved Atlas comparison. Experimental
results remain the 2026-11-18 development records. Both PDFs were rendered
and visually inspected; page counts, text and local links were checked.
This was an artifact/documentation update: no application code, corpus,
dataset, model experiment, migration or service state changed. Application
tests were not repeated for presentation-only work.

The owner then requested a clearer C section, an unambiguous tracing status
and an output-validation box. Revised the PDF/PNG/SVG in place: C now explains
the separate thesis evaluation process in four numbered steps, with an example
and an explicit definition of "offline". The partial-coverage label is integrated
into the tracing heading. RAG outputs now pass through a depicted shared
validation stage before Response. Its completion/nonempty checks exist in
Simple; citation checks are planned and grounding/failure/retry policy remains
open. No new validator or extra LLM call was implemented. The revised page was
rendered and visually checked; application/source files and the briefing PDF/
Markdown are unchanged. The next implementation step below remains a proposal.

## Direct LLM terminal command — 2026-11-23

Added a copyable free-form question/answer block to
[COMMANDS](COMMANDS.md#ask-the-llm-directly). It reuses the existing client and
configured generator, prints plain answer text and requires no corpus, dataset
or DB. It makes one explicitly invoked paid request and saves no project trace
or report. Syntax and mock-client checks passed without a real API call.
No application code, dependency, prompt file or experiment default changed.

## Atlas changed-evidence control — 2026-11-23

Completed the owner-authorized one-question source-change check. Separate Atlas
v2 documents change only the lag limit as a domain fact, from 5 to 8 seconds;
version metadata and references are updated consistently. Existing documents,
datasets, prompts, indexes and raw results remain preserved, including P09's
earlier reporting-role omission. The v2 dataset pins only the unchanged P08.

The existing ingestion/chunking/import pipeline produced two new snapshots and
12 chunks, all below 512 tokens. The import was repeated successfully.
The indexer now supports mutually exclusive, repeatable `--snapshot-id` and
`--source-id` filters. Exact snapshots keep v1/v2 separate; a source filter
includes all versions. No schema change was needed.

Two fresh Luna calls with identical question, `answer_v1`, generator settings
and top-five dense workflow answered **5 seconds inclusive** for v1 and
**8 seconds inclusive** for v2, each citing its own first-ranked policy chunk.
A fresh read-only check verified both complete prompts, source text, responses,
usage, two new traces/four spans and unchanged older DB rows/artifacts.
Both wrong-state index/dataset pairings were rejected before calls.

**188 offline unit and 26 DB integration tests passed**, including exact
same-source snapshot isolation, missing-selection rejection and unchanged
default/source selection behavior. All three reference checks, Ruff and
whitespace checks passed. Usage: 3,457 input / 60 output tokens; two paid
calls, no new LLM-only run or price estimate. One development pair does not
establish general accuracy or universal grounding.

See [CHANGED_EVIDENCE_CHECK](CHANGED_EVIDENCE_CHECK.md) for commands, trace IDs,
source versions and limits. Local records:
`outputs/comparisons/atlas-changed-evidence-20261123.json` and
`outputs/validation/atlas-changed-evidence-20261123.json`.

## Full-text retrieval component — 2026-11-23

Added `store.search_chunks_full_text()` using parameterized SQL, exact selected
index membership, English lexemes and `ts_rank_cd`. Results retain citation
metadata and expose `text_score` descending with deterministic chunk-ID ties.
The generic OR query policy uses only the unchanged raw question. No migration,
new dependency, embedding update or Simple workflow change was needed.

The existing diagnostic now accepts `--method full-text`; it uses the DB only,
without a cached model or ML runtime. Dense remains the default with its
existing optional tracing. Full-text diagnostics are read-only and untraced;
the unsupported `--trace` combination is rejected before service access.

The initial plain AND policy returned no candidates for all eleven question/
state observations. Those reports are preserved. OR was then selected on
development data and compared with dense on the same pinned datasets/indexes.
P05 E1/E2 rank 3/2 with full-text versus 17/11 with dense; top-five annotation
coverage is 2/3 versus 0/3. E3 remains low. Other top-five annotation counts
match dense, although some ranks worsen. P19 returns related Atlas text,
without establishing a Boreal limit. No answer/abstention quality was measured.

**193 offline unit tests and 31 DB integration tests passed**, including
stemming/OR matching, ranking/ties/limits, source-version isolation, quoted
input, transaction ownership and a CLI path without model dependencies. All
three reference checks passed; live rankings/scores were independently checked.
All DB rows/counts and 69 protected source/dataset/artifact/report file hashes
are unchanged. No API call or trace write occurred. Migration remains `0002`.
See [FULL_TEXT_RETRIEVAL](FULL_TEXT_RETRIEVAL.md) and the local records
`outputs/comparisons/dense-vs-full-text-20261123.json` and
`outputs/validation/full-text-retrieval-20261123.json`.

## Equal-weight RRF component — 2026-11-23

The owner approved equal method weights. Added `reciprocal_rank_fusion()` and
`retrieve_hybrid()` in `retrieval.py`: one index, unchanged raw question,
at most 20 candidates per method, `k=60`, rank-based summation and chunk-ID
deduplication. These development defaults were recorded before live runs and
were not tuned afterward. Results retain citation fields, both component
ranks/scores and `rrf_score`; missing component values are NULL.

The diagnostic now accepts `--method hybrid` using the cached Nomic runtime,
read-only SQL and the same exact dataset/index scope checks. It returns the
bounded union for cutoff analysis. Simple's dense function, full-text SQL,
prompts, corpus, indexes and older reports remain unchanged. Hybrid diagnostics
are untraced; the complete Enhanced answer workflow is not implemented yet.

Three real-model diagnostics covered PostgreSQL, Atlas v1 and the v2 P08
variant. P05 RRF evidence ranks are E1=9, E2=4, E3=absent from the candidate
union: 1/3 at five versus dense 0/3 and full-text 2/3; at ten RRF has 2/3.
Other top-five counts match the prior methods. This mixed result was retained;
RRF does not guarantee an improvement. No answer quality was measured.

**201 offline unit tests and 32 DB integration tests passed**, including
known score calculations, equal weights, missing/overlapping candidates,
tie order, citation preservation and index-isolated live SQL integration.
All three reference checks passed. Independent reconstruction from the preserved
component reports verified every union, score and component rank for all eleven
question/state observations. All DB rows/counts and 79 protected source/data/
artifact/report hashes are unchanged. No API call, trace write or migration ran.
See [HYBRID_RETRIEVAL](HYBRID_RETRIEVAL.md),
`outputs/comparisons/dense-full-text-rrf-20261123.json` and
`outputs/validation/rrf-retrieval-20261123.json`.

A subsequent read-only coverage audit reconfirmed all three dataset/index
scopes and the live 8/73/3/73 snapshot/chunk/index/vector counts. Existing
three-method results cover all ten verified unique questions plus P08 v2,
not all twenty pilot drafts. P10–P18/P20 need fixture/scope/reference work;
the sandbox tool module remains a scaffold. No inference or API call was
repeated. Audit: `outputs/comparisons/pilot-retrieval-coverage-20261123.json`.

## Retrieval dataset allocation — 2026-11-23

The owner approved 50 PostgreSQL-only, 30 Atlas-only and 20 combined answerable
questions, plus 20 unanswerable, and broader topics. Completed the
[source/topic/question matrix](RETRIEVAL_DATASET_PLAN.md): eight PostgreSQL
scopes (four existing/four new), six planned Atlas documents, combined evidence
requirements and four groups of five unanswerable cases. Existing IDs map to
their budgets; the verified set remains nine plus one, leaving 110 new records.
The plan preserves old states and specifies one shared expanded comparison
corpus. No source snapshot, corpus/question file, embedding, DB or API run was
created. Matrix totals, retained question IDs and local documentation links
were checked; this documentation step needs no application test run.

## PostgreSQL expansion capture — 2026-11-23

Added [postgres_expanded_v1.json](../data/corpus/postgres_expanded_v1.json)
with the four unchanged original source definitions plus Index Types,
Transaction Isolation, Routine Vacuuming and Constraints. The minimal
[corpus_expansion.toml](../configs/corpus_expansion.toml) reuses the downloader
without changing Python code or model settings. Only the four new pages were
downloaded, totaling 187,826 bytes. Their immutable HTML/manifest pairs and
hashes are listed below. The original config/manifest and all 114 protected
source, dataset, code and local artifact files are unchanged.

All eight selected snapshots passed byte/hash/source checks and parsing in
memory, including the new pages' expected subsection headings. Parsed results
were not persisted; chunking, embeddings, DB writes and model calls did not
run. **35 offline source/download/parser tests passed.** Capture/preservation
record: `outputs/validation/postgres-expanded-v1-capture-20261123T175303Z.json`.
The retrieval DB and ten verified questions were not modified by this step.

## Expanded Atlas authoring — 2026-11-23

Created six English documents and their [hash-pinned manifest](../data/corpus/synthetic/atlas-expanded-v1/sources.json)
under `data/corpus/synthetic/atlas-expanded-v1/`: inventory, operations policy,
query/index catalog, backup, maintenance and access. The 4,149-word corpus
retains the baseline inventory, original lookup SQL and 5-second lag rule.
The catalog adds three query patterns in total, four declared secondary indexes
and selected constraints; policies cover recovery targets, approvals and roles.
These are synthetic definitions and rules, not executed DDL or observations.

All six sources passed hash/metadata checks and temporary ingestion/readback,
producing 134 blocks in temporary storage only. Query IDs, parameter slots,
cross-references and preserved facts were checked; **14 Markdown tests passed**.
All 124 protected existing files remain unchanged, including Atlas v1/v2,
datasets and model/code/config artifacts. Report:
`outputs/validation/atlas-expanded-v1-authoring-20261123T180121Z.json`.
No persistent snapshots/chunks, new questions, DB writes or model calls ran.

## Expanded source parsing — 2026-11-23

Saved four new PostgreSQL parser JSON files in `data/local/parsed/` and
persistently ingested the six Atlas sources into
`data/local/markdown/atlas-expanded-v1-hyrbftbg/`. Each Atlas folder contains
the exact Markdown copy, snapshot manifest and `parsed.json`. The original
four PostgreSQL parser outputs were verified and reused unchanged.

The ten new documents contain 454 blocks. The complete selected scope has
14 sources/638 blocks: 86 headings, 435 paragraphs, 108 code blocks and nine
tables. These are parser blocks, not chunks. Saved records match re-parsed
sources exactly; all twelve Atlas SQL fences retain their text. All 131
protected existing files are unchanged, including source manifests, old
snapshots/chunks, datasets and code. **30 HTML/Markdown tests passed.**
No code change, download, tokenizer/model call or DB write ran. Scope,
snapshot/parsed paths and hashes are pinned in
`outputs/validation/corpus-expansion-parse-20261123T181235Z.json`.

## Expanded chunking fit assessment — 2026-11-23

An offline in-memory check of all 552 non-heading blocks produced 151 candidate
chunks: 113 PostgreSQL and 38 Atlas. The maximum complete input is 822 tokens;
none exceeds 1024, and all 108 code blocks/nine tables remain intact. Added
PostgreSQL/Atlas maxima are 508/380. The original 49-chunk baseline counts and
tokenizer/settings match. Six metadata-only Atlas candidates and sixteen
split code/table-following-paragraph adjacencies are review points, not
measured retrieval failures. See [CHUNKING](CHUNKING.md#expanded-corpus-fit-assessment--2026-11-23).
All 153 protected artifacts are unchanged. Report:
`outputs/validation/chunking-fit-20261123T182131Z.json`. No chunk files, vectors,
DB records or algorithm changes were made; no embedding/LLM inference ran.

## Expanded persistent chunks — 2026-11-23

Saved `data/local/chunks/postgres-expanded-v1-section-blocks-v1/` (113 chunks)
and `data/local/chunks/atlas-expanded-v1-section-blocks-v1/` (38 chunks).
Each source JSON contains chunks, heading records and block token counts;
each run has a settings/provenance summary. The 151-chunk layout exactly
matches the in-memory fit check. All 552 content blocks, 108 code blocks and
nine tables remain intact; complete inputs stay within 1024 tokens (max 822).
The original 49 chunks/IDs/heading records are identical to the baseline.

Independent read-back checked token counts, serialization, source hashes,
heading boundaries and neighbor links. Both groups passed the existing import
loader without a DB connection. **43 offline chunk/parser/Markdown tests passed.**
All 153 protected existing artifacts are unchanged. No code, chunking settings,
source text, model calls or DB records changed. Report:
`outputs/validation/corpus-expansion-chunk-20261123T182736Z.json`.
The metadata-only chunks and split follow-up review points are retained;
this is structural verification, not a retrieval-quality result.

## Expanded corpus DB import — 2026-11-23

Verified live PostgreSQL 18.6/pgvector 0.8.7, then committed both expanded
source groups with the existing importer. Added **10 snapshots and 102 chunks**;
the original four PostgreSQL snapshots/49 chunks were reused. DB totals are
now **18 snapshots/175 chunks**. The selected fourteen-source corpus contains
151 chunks; the other 24 chunks belong to preserved Atlas v1/v2 controls.

Read-back matched all fourteen selected snapshots and 151 chunks to local
records, including exact text, embedding inputs, metadata and acquisition
times. Every pre-existing row hash is unchanged. The three embedding indexes,
73 vectors, 24 traces, 37 spans and Alembic `0002` are preserved. A repeat
import was accepted and rolled back as an idempotency check.

**Nine offline importer tests and four DB integration tests passed.** The DB
tests use temporary tables/rollback. All 169 protected local artifacts remain
unchanged. No migration, model call or new vector ran. Record:
`outputs/validation/corpus-expansion-import-20261123T184700Z.json`.

## Expanded shared embedding index — 2026-11-23

Created the shared index listed above with the pinned local Nomic model,
CPU float32, 768 dimensions and unchanged normalization/token settings.
It contains exactly the fourteen selected snapshots/151 chunks (113 PostgreSQL,
38 expanded Atlas); original Atlas v1/v2 controls are excluded. DB totals are
now four indexes/224 vectors. The eighteen snapshots/175 chunks are unchanged.

Read-back verified every input SHA-256, finite 768-dimensional vector and L2
norm (0.99999982–1.00000020). Reconstructed index identity/settings match the
stored record. A document-vector self-search passed; this is a storage/search
smoke, not question-level retrieval quality. Repeated identical saves were
accepted and rolled back without rerunning inference.

**19 offline unit tests and 17 temporary-table DB tests passed.** All old row
hashes, three original indexes/73 vectors, traces/spans/schema and 185 protected
local artifacts are unchanged. Ten local model files passed checksum checks.
No hosted API call or migration ran. Indexer output and verification:
`outputs/validation/corpus-expansion-index-20261123T185609Z-result.json` and
`outputs/validation/corpus-expansion-index-20261123T185609Z.json`.

## Expanded question references — 2026-11-23

Created [expanded_questions.json](../data/evaluation/dev/expanded_questions.json),
version 1.0.0: the same P01–P09/P19 text, expected answers and requirements,
now pinned to all fourteen sources/151 chunks. The six Atlas evidence records
use expanded-state snapshots/chunks; all thirteen PostgreSQL evidence records
are unchanged. There are 21 requirements and 19 evidence records over fourteen
blocks/thirteen chunks. Topic buckets, related scenario families and explicit
answerability labels are recorded; all ten remain development material.

P19 was rechecked over all 638 blocks and 151 embedding inputs. Boreal is
absent; the Atlas policy remains local to Atlas and no selected source supplies
an approved Boreal limit. This combines a recorded scope/authority review with
an absence scan, not a general semantic proof. The reference checker now accepts
multiple pinned source manifests while preserving the original single-manifest format.

**204 offline unit tests and all four dataset reference checks passed.**
A fresh read-only DB check accepted the shared 151-vector index and rejected
all three smaller original indexes for this dataset. All public row hashes
and 182 protected artifacts are unchanged; the development README was updated.
No retrieval, embedding, hosted API
call or DB write ran. Verification:
`outputs/validation/expanded-question-references-20261123T190949Z.json`.

## First new question batch — 2026-11-23

Created cumulative [expanded_questions_v1_1.json](../data/evaluation/dev/expanded_questions_v1_1.json),
version 1.1.0. The original ten records and complete fourteen-source/151-chunk
state are unchanged; the earlier file is preserved. New P21–P30 add four
PostgreSQL-only, two Atlas-only, two combined and two unanswerable questions.
They cover all four added PostgreSQL scopes and the Atlas query catalog,
backup, maintenance and access policies. P29 asks for an unspecified table
row count; P30 asks for a backup outcome without a matching observation.

At this milestone there were **20 unique development questions: 17 answerable + 3 unanswerable**
(10 PostgreSQL-only, 5 Atlas-only, 2 combined, 3 negative). The cumulative
annotations have 44 requirements and 36 evidence records over 29 blocks/
23 chunks. Related VACUUM questions P23/P28 share a scenario family. P10–P18/P20
remain separate drafts, not automatically verified by reaching twenty records.

The checker now accepts an explicit `missing_fact` editorial review for a
documented entity, while preserving P19's default absent-entity check. It
checks complete scope, entity presence and missing-fact metadata; it does not
infer semantic unanswerability. Negative records still have no positive evidence.

**206 offline unit tests, all five dataset reference checks and Ruff's unused/
undefined-name checks passed.** All 188 protected source/data/code artifacts
are unchanged; gold is excluded from runtime question selection. No DB access,
retrieval, embedding or hosted API call ran. Record:
`outputs/validation/expanded-questions-batch01-20261123T194352Z.json`.

## Second new question batch — 2026-11-23

Created cumulative [expanded_questions_v1_2.json](../data/evaluation/dev/expanded_questions_v1_2.json),
version 1.2.0. P31–P40 add four PostgreSQL-only, two Atlas-only, two combined
and two unanswerable questions. They cover EXPLAIN units, unresolved partial-index
parameters, lag interpretation, UNIQUE/NULL semantics, unbilled-query filters,
retry limits, approved plan inspection and reporting-export isolation.
P39 asks for an unspecified emergency promotion decision-maker; P40 asks for
an unmeasured index-versus-Seq-Scan execution-time change. All four negative
categories now have records, with whole-corpus reviews rather than retrieval-miss labels.

At this milestone there were **30 unique development questions: 25 answerable + 5 unanswerable**
(14 PostgreSQL-only, 7 Atlas-only, 4 combined, 5 negative). The cumulative
annotations have 67 requirements and 53 evidence records over 41 blocks/
30 chunks. Related EXPLAIN, partial-index, lag and isolation questions retain
existing scenario families. All twenty inherited records and the complete
fourteen-source/151-chunk state are identical to version 1.1.0; prior files remain.

**10 reference-boundary unit tests and all six dataset reference checks passed.**
All 191 protected source/data/code artifacts are unchanged; no application code
or dependency changed. Gold stays outside runtime question selection. No DB
access, retrieval, embedding or hosted API call ran. Verification:
`outputs/validation/expanded-questions-batch02-20261123T200722Z.json`.

## Third new question batch — 2026-11-23

Created cumulative [expanded_questions_v1_3.json](../data/evaluation/dev/expanded_questions_v1_3.json),
version 1.3.0. P41–P50 add four PostgreSQL-only, two Atlas-only, two combined
and two unanswerable questions. Topics include multicolumn GIN, BRIN summaries,
sequence counters, ANALYZE, Atlas storage accounting and backup retention.
P47 connects the local NULL-lag decision to PostgreSQL idle-standby behavior;
P48 applies the partial-index implication rule to the declared unbilled index.
P49 asks for an unspecified individual index size; P50 asks for an unobserved
current membership list. Both have full-corpus missing-fact reviews.

At this milestone there were **40 unique development questions: 33 answerable + 7 unanswerable**
(18 PostgreSQL-only, 9 Atlas-only, 6 combined, 7 negative). The cumulative
annotations have 87 requirements and 66 evidence records over 50 blocks/
37 chunks. All 23 planned topic buckets, including all five combined buckets,
now have at least one record; their target budgets remain incomplete.
Related lag/partial-index questions retain their existing scenario families.
All thirty inherited records and the fourteen-source/151-chunk state are
identical to version 1.2.0; prior files remain unchanged.

**10 reference-boundary unit tests and all seven reference-file checks passed.**
All 192 protected source/data/code artifacts are unchanged. Application code and
dependencies are unchanged. No DB access, retrieval, embedding or hosted API call ran.
Gold remains outside ingestion and runtime question selection. Verification:
`outputs/validation/expanded-questions-batch03-20261123T201630Z.json`.

## Fourth new question batch — 2026-11-23

Created cumulative [expanded_questions_v1_4.json](../data/evaluation/dev/expanded_questions_v1_4.json),
version 1.4.0. P51–P60 add four PostgreSQL-only, two Atlas-only, two combined
and two unanswerable questions. Topics include EXPLAIN loops/averages,
Read Uncommitted, partition-parent statistics, foreign-key delete actions,
lag-observation validity and intended reporting-table access.
P57 connects the approved routine command to PostgreSQL space behavior;
P58 applies the NO ACTION default to the declared device/customer relationship.
P59 lacks an event-row retention policy; P60 lacks evidence of the stated lag
spike and its cause. Both have full-corpus missing-fact reviews.

At this milestone there were **50 unique development questions: 41 answerable + 9 unanswerable**
(22 PostgreSQL-only, 11 Atlas-only, 8 combined, 9 negative). The cumulative
annotations have 109 requirements and 82 evidence records over 61 blocks/
42 chunks. Related EXPLAIN, isolation, statistics, lag and vacuum questions
retain existing families; P54/P58 share the new foreign-key deletion family.
All forty inherited records and the fourteen-source/151-chunk state are
identical to version 1.3.0; prior files remain unchanged.

**10 reference-boundary unit tests and all eight reference-file checks passed.**
All 193 protected source/data/code artifacts are unchanged. Application code
and dependencies are unchanged. No DB access, retrieval, embedding or hosted
API call ran; gold stays outside ingestion and runtime question selection.
Verification: `outputs/validation/expanded-questions-batch04-20261123T202711Z.json`.

## Fifth new question batch — 2026-11-23

Created cumulative [expanded_questions_v1_5.json](../data/evaluation/dev/expanded_questions_v1_5.json),
version 1.5.0. P61–P70 add four PostgreSQL-only, three Atlas-only, two combined
and one unanswerable question, following the remaining source-group budgets.
Topics include partial uniqueness, lag stages, GIN components, serialization,
query time bounds/ties, backup coverage and maintenance prerequisites.
P68 connects unbilled-query filters to plan-node row estimates; P69 connects
conditional asynchronous replay-lag semantics to the local criterion's limits.
P70 lacks a documented CPU-core allocation for the named primary server.

At this milestone there were **60 unique development questions: 50 answerable + 10 unanswerable**
(26 PostgreSQL-only, 14 Atlas-only, 10 combined, 10 negative), halfway toward
the approved 120-record preparation target. The cumulative annotations have
132 requirements and 98 evidence records over 71 blocks/48 chunks.
Related isolation, query-range, EXPLAIN and lag questions retain existing
families. All fifty inherited records and the fourteen-source/151-chunk state
are identical to version 1.4.0; prior files remain unchanged.

**10 reference-boundary unit tests and all nine reference-file checks passed.**
All 194 protected source/data/code artifacts are unchanged. Application code
and dependencies are unchanged. No DB access, retrieval, embedding or hosted
API call ran; gold stays outside ingestion and runtime question selection.
Verification: `outputs/validation/expanded-questions-batch05-20261123T203929Z.json`.

## Sixth new question batch — 2026-11-23

Created cumulative [expanded_questions_v1_6.json](../data/evaluation/dev/expanded_questions_v1_6.json),
version 1.6.0. P71–P80 add three PostgreSQL-only, three Atlas-only, two combined
and two unanswerable questions. Topics include buffer counters, later-column
B-tree conditions, LIKE patterns/locales, selective inventory totals,
maintenance-window boundaries and access-record escalation.
P77 applies the local rule to explicitly hypothetical write/replay lag inputs;
P78 connects capacity approval to temporary VACUUM FULL rewrite space.
P79 lacks a matching autovacuum-setting observation; P80 lacks the usable
archive recovery point needed to quantify the incident's data-loss window.

There are **70 unique development questions: 58 answerable + 12 unanswerable**
(29 PostgreSQL-only, 17 Atlas-only, 12 combined, 12 negative). The cumulative
annotations have 152 requirements and 109 evidence records over 76 blocks/
51 chunks. All four negative buckets now contain three records each.
Related EXPLAIN, multicolumn, lag and vacuum families are retained. All sixty
inherited records and the fourteen-source/151-chunk state are identical to
version 1.5.0; prior files remain unchanged. P77's numeric inputs are raw
question data, not measured or imported observations.

**10 reference-boundary unit tests and all ten reference-file checks passed.**
All 195 protected source/data/code artifacts are unchanged. Application code
and dependencies are unchanged. No DB access, retrieval, embedding or hosted
API call ran; gold stays outside ingestion and runtime question selection.
Verification: `outputs/validation/expanded-questions-batch06-20261123T205144Z.json`.

## Completed 120-question development set — 2026-11-24

Created cumulative [expanded_questions_v1_7.json](../data/evaluation/dev/expanded_questions_v1_7.json),
version 1.7.0. P81–P130 complete the remaining fifty records: 21 PostgreSQL-only,
13 Atlas-only, eight combined and eight unanswerable. New topics include GiST/BRIN
design, predicate locks, visibility maps, freezing, primary/exclusion constraints,
and Atlas query, restore, maintenance and access boundaries. Combined questions
require both source groups; negative cases distinguish missing policies,
resource attributes, observations and unsupported quantitative/causal conclusions.

The completed distribution is **50 PostgreSQL-only + 30 Atlas-only + 20 combined
answerable questions, plus 20 unanswerable** (five in each negative bucket).
All 23 topic budgets are met. The 120 unique records contain 252 requirements
and 195 positive evidence records over 134 distinct blocks/73 chunks.
All seventy inherited records, fourteen-source/151-chunk pins and prior files
are unchanged. Gold remains outside ingestion and runtime question selection.
All 120 remain development material; this does not freeze the thesis test set.

**10 reference-boundary unit tests and all eleven reference-file checks passed.**
The 196 protected source/data/code files are unchanged. Counts, source-group
support, parent pins, raw-question-only selection and negative scope/context
reviews passed offline checks. No DB access, retrieval, embedding or hosted API
call ran. Reference integrity is not a model-quality result. Verification:
`outputs/validation/expanded-questions-complete-20261123T211259Z.json`.

## Expanded retrieval measurements — 2026-11-24

[check_retrieval.py](../scripts/check_retrieval.py) now implements
[`annotated-evidence-v1`](EVALUATION_PLAN.md#expanded-development-measurements--2026-11-24).
Schema-3 reports count each annotated chunk once and compute available claim
support using `any`/`all` rules at 5/10/20. Summary means give each answerable
question equal weight; the all-requirements-supported rate is also recorded.
Unanswerable questions retain their missing-fact review and full ranking with
`null` positive coverage. They cannot be graded for abstention without answers.

Unannotated returned chunks are listed separately with `not_reviewed` status.
They are not automatically wrong or accepted as sufficient; manual review and
versioned reference additions remain separate from raw reports. Old evidence-ID
fields remain for inspection. Question type, bucket/family and measurement/doc
hash provenance support later grouped review. Retrieval SQL, fusion settings,
model, questions, source scope and Simple's five-chunk context are unchanged.

**18 diagnostic unit tests and all eleven reference-file checks passed.**
Offline compatibility checks exercised all 120 records through each of the
three mocked retrieval paths (360 simulated question calls), including the
100-positive/20-negative split and raw-question-only inputs. These are test
fixtures, not measured retrieval runs. All 211 protected files, including
sixteen previous retrieval reports, are unchanged. No model loaded, DB connection
opened or hosted API called. Verification:
`outputs/validation/retrieval-measurements-20261123T215752Z.json`.

## Metric extension recorded for the next session — 2026-11-24

The owner agreed to [six quality metric types](EVALUATION_PLAN.md#agreed-metric-extension--2026-11-24)
at 5/10/20: recall, requirement coverage, all-requirements-supported rate,
Precision, MRR and nDCG. Retrieval elapsed time is tracked separately.
At that stopping point only the first three quality metrics were implemented;
Precision/MRR/nDCG were pending. Saving the plan changed no code, dataset, DB
or model. Measurement version/schema at that point were `annotated-evidence-v1`/3.

## Literature check of retrieval metrics — 2026-11-24

The [metric review](RETRIEVAL_METRIC_REVIEW.md) screens all 47 local PDFs
(44 distinct byte hashes) and checks the relevant evaluation sections in eight
papers. Five rendered pages verify core definitions/tables. The recommendation
is to retain the agreed six quality metrics plus time. MAP@K is optional;
Hits@K/completeness terminology varies, and our reference-based claim coverage
is not RAGChecker's semantic entailment evaluator. Label sufficiency, grouped
results and consistent alternative-evidence review remain important.
No new metric was adopted or implemented; no model/DB run occurred.

## Precision, MRR and nDCG implemented — 2026-11-25

[check_retrieval.py](../scripts/check_retrieval.py) now includes the three
additional metrics under `annotated-evidence-v2` / schema 4. All six quality
metrics are implemented at 5/10/20, giving 18 summary scores per method plus
separate retrieval time. Precision always divides by the fixed cutoff; each
question's reciprocal rank uses its first reference hit within that cutoff.
Binary-reference nDCG uses log2 discounting and an ideal ranking of
`min(k, unique_reference_count)` chunks. Definitions are in the
[evaluation plan](EVALUATION_PLAN.md#implemented-ranking-metrics--2026-11-25).

The original measurements and retrieval behavior are unchanged. Duplicate
references count once, empty positive results score zero, negative scores are
`null`, and only answerable questions enter quality means. Missing reference
annotations still need consistent semantic review. Schema-3 and older reports
remain preserved; there is no model, dependency, migration or dataset change.

**23 diagnostic unit tests and all eleven reference-file checks passed.**
All 120 records passed each of the three mocked retrieval paths (360 simulated
question calls), including strict JSON serialization, raw-question-only inputs,
six summary fields/18 cutoff scores, hand-calculated metrics and negative
exclusion. These are implementation checks, not measured retrieval results.
All 262 protected artifacts, including sixteen previous retrieval reports,
are unchanged. No DB access, model loading or hosted API call ran.
Verification: `outputs/validation/retrieval-ranking-metrics-20261125T113908Z.json`.

## Expanded retrieval comparison completed — 2026-11-25

All three methods retrieved the same 120 raw questions from the exact shared
fourteen-snapshot/151-chunk index: 360 method/question calls. All six metrics
at 5/10/20 and timing are recorded. Dense has the strongest first-five
reference scores; RRF reaches full annotated support for 96/100 at twenty.
Twenty negatives retain rankings and `null` positive scores. No answer or
abstention was generated or graded. See the
[measured comparison](EXPANDED_RETRIEVAL_COMPARISON.md) for tables, raw report
hashes, group breakdowns, timing limits and targeted evidence reviews.

Independent raw-ranking recomputation matched all scores; all 120 fused
rankings matched reconstruction from component top-20 lists. The existing
stopped PostgreSQL container was started. Exact index scope and all seven
public-table content fingerprints were unchanged afterward; no migration,
import, reindexing, trace write or hosted API call ran. All 213 protected
artifacts, including sixteen earlier retrieval reports, were preserved.
Twenty-three diagnostic unit tests and the 120-question reference checker passed.

Targeted review covered nine positives and four negative contexts. Valid
alternative passages and overstrict P108/P116 requirements limit interpretation
of strict scores. No frozen question/reference or raw report changed.
Audit prefix: `outputs/validation/expanded-retrieval-comparison-20261125T133609Z-`.

## Reference review and offline rescoring — 2026-11-25

[Version 1.8.0](../data/evaluation/dev/expanded_questions_v1_8.json) keeps all
120 raw questions, source state, group/family labels and twenty negative records.
The alignment screen covered all 120 records; twelve received targeted corrections:
P05/P48/P64/P81/P85/P91/P98/P101/P108/P116/P119/P122. Ten evidence records were
added, three removed; there are now 251 requirements and 202 evidence records
over 135 blocks/73 distinct chunks. The other 108 complete question records
are identical. Exact rationale and accepted spans are in the
[editorial change record](../data/evaluation/dev/reference_review_v1_8.json).

The new offline [rescorer](../scripts/rescore_retrieval.py) validates the pinned
parent and unchanged queries/scope, reuses `measure_evidence` and the extracted
shared `summarize` function, and preserves rankings/query hashes/original timings.
All three methods were rescored: full support at five is 83/65/82 of 100 and
at twenty 88/95/100 for dense/full-text/RRF. The original scores reproduce exactly;
independent revised calculations pass. No retrieval quality changed through this
annotation-only operation. See [REFERENCE_REVIEW](REFERENCE_REVIEW.md) for limits.

**222 offline unit tests and eleven reference-file checks passed.** All 232
protected local artifacts and all 360 rankings/query hashes/timings are unchanged.
No DB access, model/API call, retrieval, embedding, migration or reindexing ran.
This is a single-editor development review informed by earlier results, not
exhaustive pooled relevance judging or a held-out benchmark. Other unannotated
passages remain unjudged. Audit:
`outputs/validation/reference-review-20261125T140656Z-verification.json`.

## Qwen3-Reranker-4B research — 2026-11-25

The [source-backed model review](QWEN_RERANKER_REVIEW.md) compares Qwen's
published results with a separate English MTEB reranker evaluation. Both support
4B as a quality-oriented candidate; the latter directly includes ModernBERT.
These are external results, not PostgreSQL/Atlas measurements. Local model-file
sizes make a small-batch M3/24-GB trial plausible, but latency and total memory
are unmeasured. Runtime/template/quantization compatibility must be checked.
No model, dependency, index, dataset or experiment setting changed; no model
download, inference, DB access or paid call ran. Selection remains open.

## Qwen4B preparation — 2026-11-25

The owner requested preparing Qwen3-Reranker-4B. The separate
[config](../configs/reranker.toml) pins revision
`22e683669bc0f0bd69640a1354a6d0aebcfeede5`, MPS/float16 and a 2,048-token
application limit. The [smoke script](../scripts/reranker_smoke.py) has a separate
uv lock and uses native Transformers scoring with the pinned model's own template.
Nomic settings, environment locks and indexes are unchanged.

Tokenizer/config preparation completed: all 120 saved RRF questions × 20 candidates
fit without truncation, maximum 821 tokens. MPS availability is confirmed.
All 225 offline unit tests passed; a tiny random native Qwen3 forward also checked
the scoring API and oversized-input rejection. All 194 protected prior files
were preserved. No pretrained weights, DB access, hosted call or new retrieval ran.
The approximately 8-GB weight download/local smoke is an explicit separate mode.
See [setup and limits](QWEN_RERANKER_SETUP.md); report:
`outputs/reranking/qwen4b-20261125T152717058435Z.json`.

## Qwen4B weight download and local runtime — 2026-11-25

The owner authorized the download. Both pinned safetensors shards are local
under ignored `data/local/models/`, totaling 8.04 GB; their SHA-256 hashes match
the download metadata. The existing smoke passed on MPS/float16: loading took
18.51 seconds and scoring two short passages took 2.99 seconds. The relevant
EXPLAIN passage scored 0.962953 versus 0.000005104 for the unrelated passage.
Report: `outputs/reranking/qwen4b-20261125T180455418462Z.json`.
This is a runtime check, not a retrieval-quality result. No code/config/lock,
dataset or prior report changed; no DB access or hosted model call occurred.

## Qwen4B real-candidate probe — 2026-11-25

The new [probe runner](../scripts/reranker_probe.py) reuses the native smoke scorer
and existing metrics with a separate lockfile containing the same dependencies.
It reranked P05/P07/P27/P19's unchanged RRF top-20 lists: 80 pairs, MPS/float16,
one model load. Loading took 8.18 seconds; scoring totaled 110.40 seconds.
At five, supported required claims changed from 0/3 to 2/3 for P05, stayed 2/2
for P07, and changed from 1/3 to 3/3 for P27. P19 remains unscored as a negative;
its high top score (0.906653) is not evidence that Boreal's limit is known.
This targeted three-positive/one-negative check establishes feasibility, not
general quality. No references, baseline ranks, model settings or existing code
changed; no new retrieval, DB access, embedding or hosted call occurred.

All 227 offline unit tests passed. Independent checks verified candidate/source
preservation, all six metric summaries, negative exclusion and unchanged
recall/claim coverage at twenty. Results and limits are in
[Qwen setup](QWEN_RERANKER_SETUP.md#saved-candidate-probe--2026-11-25).
Report: `outputs/reranking/qwen4b-probe-20261125T181229740228Z.json`.
Audit: `outputs/validation/qwen4b-probe-20261125T181229740228Z.json`.

## Earlier reranker latency requirement — 2026-11-25, superseded

The owner initially required reranking below 10 seconds per question, preferably
much less. This requirement was later withdrawn when 4B was selected above.
The measured Qwen4B top-20 latency missed that earlier requirement. The
[source-backed shortlist](RERANKER_LATENCY_REVIEW.md) proposes Ettin 68M as the
first smaller-model probe, with Ettin 150M/GTE ModernBERT/Qwen 0.6B alternatives.
At that research step no smaller model was installed or locally verified.
The owner subsequently chose Qwen0.6B; measured results follow below.
Preserve Qwen4B results as a quality reference.

## Qwen0.6B preparation and paired comparison — 2026-11-25

The owner chose Qwen3-Reranker-0.6B for the next trial. Its separate
[profile](../configs/reranker_qwen06b.toml) pins revision
`e61197ed45024b0ed8a2d74b80b4d909f1255473`; weights are local (1.19 GB),
with a verified download hash. Smoke and all 2,400 token-fit checks passed.
Shared scripts now accept `--config`; the original 4B profile/default and
all dependency locks remain unchanged. The native scorer is unchanged.

Both models scored the same P05/P07/P27/P19 top-20 lists using MPS/float16,
batch size one and the same code. Fresh 4B rankings reproduce the historical
probe. Mean question time is 27.90 s for 4B versus 5.95 s for 0.6B (4.69x faster).
0.6B's observed range is 5.11–6.86 s, below the 10-second budget. P05 support
at five falls from 2/3 to 0/3; P07/P27 stay 2/2 and 3/3. Mean claim coverage
is 0.8889/0.6667 and nDCG@5 0.7380/0.6176 for 4B/0.6B over three positives.
Both still score related P19 text highly; no answerability threshold is selected.
This targeted sample is not general accuracy or a future latency guarantee.

All 227 offline tests passed. Independent checks verified all six metric
summaries, preserved candidates/sources, identical input token sequences and
model/code/lock hashes. No DB, embedding, new retrieval or hosted call ran.
See [comparison and report paths](QWEN_RERANKER_COMPARISON.md).

## Qwen4B batch-size-four command — 2026-11-25

The owner requested a runnable batch-size-four script. The probe now accepts
`--batch-size` (default 1), using left padding, attention masks and per-sequence
position IDs for batched native yes/no scoring. Inputs stay whole and all
candidates keep individual scores. New reports use schema 2, record batch size
and leave per-pair times null when only batch/question latency was measured.

All 229 offline unit tests passed. One native P05 check scored all 20 candidates
in five forwards, preserving the complete batch-one ranking and quality metrics;
maximum score difference was 0.003842. It took **46.36 seconds**, versus the
previous batch-one P05's 30.85 seconds. This check shows no speed gain and does
not establish general batch performance. No four-question/full-set batch-four
benchmark ran. Report: `outputs/reranking/qwen4b-probe-20261125T184838008770Z.json`.
Audit: `outputs/validation/qwen4b-batch4-20261125T184838008770Z.json`.

## Next small step

**Proposed:** run `retrieve_reranked()` once live on one development question
(for example P05) with the pinned Qwen4B profile, the shared 151-chunk index and
the existing Nomic environment, and compare its RRF top 20 and reranked order with
the saved full-run report. Then add shared Luna generation and a reranker span
for Enhanced in separate increments. Full-set 0.6B and additional batching
comparisons are optional. Both profiles, candidate/evidence state and prior
reports are preserved.

The probe runner now accepts `--all` for the configured 120 questions, or
repeatable `--question-id` for a subset. The all-question selection was checked
offline (120 questions/2,400 pairs); that command-preparation step did not start model inference.
See [the command](COMMANDS.md#probe-qwen4b-on-saved-rrf-candidates).

The full 120-question Qwen4B comparison is now verified above: RRF top-20 →
rerank → top-5, using the same version-1.8 references and unchanged dense/RRF
baselines. Actual scoring took 87 min 23 s; the earlier small-probe projection
is superseded by this observation. Peak memory was not measured. Keep baselines
immutable; final scoring, held-out allocation and thesis settings remain open.

Dense, full-text, RRF and full-set Qwen4B diagnostics are complete. Reranker
workflow integration remains component work. Simple remains dense-only;
the Enhanced answer workflow and fixed tools follow separately. Final thesis
budgets remain open. Preserve both Atlas states, their results and P09's
explicit-role omission; no prompt was tuned to these results.
Keep all six public questions and both
raw baselines, including LLM-only-correct questions, P03's shared omission and
P05's retrieval gap. Keep gold outside generation; final scoring remains open.
Initial settings: `gpt-6-luna`, reasoning `none`, maximum 1000 output tokens;
OpenAI SDK `3.51.0`. Paid runs require `--call-api`, Standard processing,
`store=False`, a 30-second timeout and zero retries. The Simple runner writes
traces; the connectivity-only smoke does not. Current context is all five
whole chunks; a final numeric context token budget has not been selected.

The 2026-11-17 price check was $0.10 / million input and $0.50 / million output
tokens: 4,000 uncached input + 1,000 billed output would cost $0.0009 before
extra services/taxes. This is an estimate, not observed usage. Recheck
[official pricing](https://developers.openai.com/api/docs/models/gpt-6-luna) before budgeting.

Build Simple before Enhanced's hybrid/RRF/reranking and fixed tools.

## Not yet completed

- Broader paired evaluation and additional source-specific/abstention/changed-evidence cases.
- A live check of `retrieve_reranked()`, the complete Enhanced workflow and its tool conditions.
- Additional changed document states, frozen DB fixtures and validated tools.
- Agentic workflow, LangGraph installation and adaptive router.
- Verified P10–P18/P20 answers, a held-out test set, rubric/judges, metrics,
  quality margin, final model/settings choices, sample size and result runner.
- Supervisor review of the method design and a complete literature review.

The working study and controls are approved directions, not a frozen protocol
or evidence that Agentic RAG is better. Earlier observability/Enron proposals
are background. Detailed decisions live in PROJECT_CONTEXT and METHOD_DESIGN.

## Saved official-documentation snapshots

Each directory is under `data/local/snapshots/` and contains
`<source_id>.html` plus `manifest.json`. The original PG-EXPLAIN capture is
from 2026-11-02, the other three baseline pages from 2026-11-05; the four
expansion pages were captured on 2026-11-23. This is not an atomic capture.
The table covers HTML only; Atlas snapshots are recorded separately above.
All eight have persisted parser outputs and 113 imported/embedded chunks in
the shared index. The original four-source/49-chunk index remains separate.

| Source ID | Snapshot directory | Bytes | SHA-256 |
| --- | --- | --- | --- |
| PG-EXPLAIN | `PG-EXPLAIN-20261102T173311Z-yhdhybna` | 70029 | `22b29b578fe330ce2a1eca03dcc6ecfb540eb6211e21cfa4d61d93d55e87bf7e` |
| PG-MULTI | `PG-MULTI-20261105T191707Z-96nc6y0c` | 21135 | `df6631e673511c60f9ea45dab2b5c69ab80ff1a747117af72236006dc59063d1` |
| PG-PARTIAL | `PG-PARTIAL-20261105T191707Z-kmf7w4sp` | 26463 | `ab67b4a1909a9be617038dcea60e34b7d8f898ca9e8b5f0a569e4df389caa18e` |
| PG-STATS | `PG-STATS-20261105T191715Z-zm7b259y` | 290994 | `4b872e1cd30fd40679c000bf3e5efc15d9f1e4d7a003aed877cfe2c09381c45c` |
| PG-INDEX-TYPES | `PG-INDEX-TYPES-20261123T175401Z-9bwzmjkd` | 26162 | `174f2b0501e2f98edf2df8440a51a9de5c188526db9f0277d1e675e8d685df42` |
| PG-ISOLATION | `PG-ISOLATION-20261123T175402Z-2_17hssf` | 47604 | `1553516d656d3d557aa4c6fc0d7b93cb8c00cb5ea87352355701feb620999670` |
| PG-VACUUM | `PG-VACUUM-20261123T175402Z-lwwvgshl` | 67459 | `f8a8eca1e310b50426d903e4150a1c1a0d805ca08919454a99fdaeada258219a` |
| PG-CONSTRAINTS | `PG-CONSTRAINTS-20261123T175403Z-5w4qbo7f` | 46601 | `520904acbfd1aabb32798983b2a17aab0b70831d9a55ea4f55a76ac1f0449667` |

## Parser outputs

Eight files are under `data/local/parsed/<snapshot_id>.json`, using the
snapshot IDs above. The CLI writes JSON to stdout; saved outputs are ignored
by Git. Parser version: `postgresql-html-v1`. The eight HTML sources contain
504 blocks, including 48 headings; the original four account for 184 blocks.

| Source ID | Heading | Paragraph | Code | Table |
| --- | --- | --- | --- | --- |
| PG-EXPLAIN | 4 | 82 | 32 | 0 |
| PG-MULTI | 1 | 12 | 3 | 0 |
| PG-PARTIAL | 1 | 30 | 11 | 0 |
| PG-STATS | 2 | 5 | 0 | 1 |
| PG-INDEX-TYPES | 7 | 18 | 8 | 0 |
| PG-ISOLATION | 6 | 57 | 7 | 1 |
| PG-VACUUM | 17 | 78 | 6 | 0 |
| PG-CONSTRAINTS | 10 | 76 | 29 | 0 |

The second PG-STATS heading is `Note`, nested under its section's heading
path. This parser expects the pilot's explicitly closed DocBook HTML tags;
general web/PDF/Markdown and nested content tables are not supported.

### Expanded Atlas parser outputs

Run: `data/local/markdown/atlas-expanded-v1-hyrbftbg/`. Parser version:
`atlas-markdown-v1`. The six sources add 134 blocks, including 38 headings;
their raw copies, manifests and parsed records are beside each other.
Together with PostgreSQL, the selected scope has 638 blocks/552 non-heading
content blocks. Original Atlas v1/v2 controls are outside this expanded scope.

| Source ID | Snapshot directory within the run | Blocks |
| --- | --- | ---: |
| LOCAL-INVENTORY | `LOCAL-INVENTORY-fe15d4078bde0d46` | 22 |
| LOCAL-POLICY | `LOCAL-POLICY-cb95d1ffabe529d7` | 20 |
| LOCAL-QUERY-CATALOG | `LOCAL-QUERY-CATALOG-5040c4097f291207` | 36 |
| LOCAL-BACKUP | `LOCAL-BACKUP-680206816dba1b08` | 18 |
| LOCAL-MAINTENANCE | `LOCAL-MAINTENANCE-913bdddf1eb94c40` | 21 |
| LOCAL-ACCESS | `LOCAL-ACCESS-8206771d2a7ea5a3` | 17 |

## First steps when returning

Follow the reading order and resume checks in [HANDOFF](HANDOFF.md). Inspect
Git/service state before editing or running DB commands; dated successful
checks do not prove that local services are running in a new session.
