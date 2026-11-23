# Current status

**Last updated:** 2026-11-23. This is the current implementation boundary.
Detailed dated records are in [STATUS_HISTORY.md](STATUS_HISTORY.md);
plans are in [ROADMAP](ROADMAP.md), decisions in [PROJECT_CONTEXT](PROJECT_CONTEXT.md),
and code/artifact paths in [HANDOFF](HANDOFF.md).

## Implemented

| Area | Current state |
| --- | --- |
| Sources | Four saved PostgreSQL 18 HTML snapshots; allowlist, downloader and offline parser |
| Synthetic sources | Atlas v1 and v2: two snapshots/12 chunks each, in separate verified indexes; lag limit changes 5 → 8 seconds |
| Chunking | HTML: 184 parsed blocks → 49 chunks; all content/code/table blocks preserved; target 512 / ceiling 1024; maximum observed 822 tokens |
| Embedding | Pinned local Nomic; normalized 768-dimensional document/query vectors |
| Database | Applied Alembic `0002`; eight snapshots, 73 chunks, three indexes/73 vectors, 24 traces/37 spans (verified 2026-11-23) |
| Retrieval | Dense, English OR full-text and equal-weight RRF fusion (`k=60`, 20 candidates/method); Simple remains dense with `limit=5` |
| Diagnostics | `--method dense` (default), `full-text` or `hybrid`; exact index scope, ranks/scores/hits at 5/10/20 and immutable reports |
| Tracing | Retrieval-only diagnostics plus workflow-owned retrieval/LLM spans; exact prompt/output/usage |
| Generator | Luna client, source-linked context, `answer_v1` and Simple workflow; one live P04 answer verified |
| Answer runners | Simple/LLM-only support `--dataset`, one/all selection, shared resources/run ID and per-question records; Simple requires exact index scope |
| Live Simple batch | P01–P06 completed; editorial review: P01/P02/P04/P06 meet recorded requirements, P03/P05 partial |
| LLM-only control | Live PostgreSQL and Atlas pairs completed; raw-question-only inputs verified, with one LLM span per question |
| Questions | P01–P06 baseline unchanged; separate P07–P09/P19 Atlas subset verified, including one unanswerable case; P10–P18/P20 drafts |
| Changed evidence | P08 is unchanged across v1/v2; fresh Simple answers follow the source limit, 5 → 8 seconds, with supporting citations |

Nomic revision: `e9b6763023c676ca8431644204f50c2b100d9aab`, CPU float32,
1024-token application limit. Committed indexes:

- PostgreSQL, 49 vectors: `nomic-d4a8ebdbce1253c45ea50734d984a14a6258d9f1e7a332fd56964011eb886447`.
- Atlas, 12 vectors: `nomic-b98238adf1e5b69036fc64a756e3171b7459ad8842e8c3ea280fe9a777ad8ddf`.
- Atlas v2, 12 vectors: `nomic-5710f4359df83e693a0d994cbf59c45d6ebe9b08695f0ff4d9f75ec062825a55`.

Keep pinned questions/snapshots/chunks/index unchanged when comparing workflows.

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

## Next small step

Dense, full-text and initial RRF diagnostics are complete. Proposed next:
choose/pin a reranker and its candidate/context limits, then add a reranking
component and compare it with these baselines. Simple remains dense-only;
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
- Reranker, the complete Enhanced workflow and its tool conditions.
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
`<source_id>.html` plus `manifest.json`. The parser used these saved copies.
PG-EXPLAIN was downloaded on 2026-11-02, the others on 2026-11-05; do not assume
an atomic, simultaneous capture. Synthetic sources are not yet included.

| Source ID | Snapshot directory | Bytes | SHA-256 |
| --- | --- | --- | --- |
| PG-EXPLAIN | `PG-EXPLAIN-20261102T173311Z-yhdhybna` | 70029 | `22b29b578fe330ce2a1eca03dcc6ecfb540eb6211e21cfa4d61d93d55e87bf7e` |
| PG-MULTI | `PG-MULTI-20261105T191707Z-96nc6y0c` | 21135 | `df6631e673511c60f9ea45dab2b5c69ab80ff1a747117af72236006dc59063d1` |
| PG-PARTIAL | `PG-PARTIAL-20261105T191707Z-kmf7w4sp` | 26463 | `ab67b4a1909a9be617038dcea60e34b7d8f898ca9e8b5f0a569e4df389caa18e` |
| PG-STATS | `PG-STATS-20261105T191715Z-zm7b259y` | 290994 | `4b872e1cd30fd40679c000bf3e5efc15d9f1e4d7a003aed877cfe2c09381c45c` |

## Parser outputs

Four example files are under `data/local/parsed/<snapshot_id>.json`, using
the snapshot IDs above. The CLI writes JSON to stdout; these examples were
saved separately during verification and are ignored by Git. Parser version:
`postgresql-html-v1`. There are 184 content blocks, not embedding chunks.

| Source ID | Heading | Paragraph | Code | Table |
| --- | --- | --- | --- | --- |
| PG-EXPLAIN | 4 | 82 | 32 | 0 |
| PG-MULTI | 1 | 12 | 3 | 0 |
| PG-PARTIAL | 1 | 30 | 11 | 0 |
| PG-STATS | 2 | 5 | 0 | 1 |

The second PG-STATS heading is `Note`, nested under its section's heading
path. This parser expects the pilot's explicitly closed DocBook HTML tags;
general web/PDF/Markdown and nested content tables are not supported.

## First steps when returning

Follow the reading order and resume checks in [HANDOFF](HANDOFF.md). Inspect
Git/service state before editing or running DB commands; dated successful
checks do not prove that local services are running in a new session.
