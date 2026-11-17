# Current status

**Last updated:** 2026-11-18. This is the current implementation boundary.
Detailed dated records are in [STATUS_HISTORY.md](STATUS_HISTORY.md);
plans are in [ROADMAP](ROADMAP.md), decisions in [PROJECT_CONTEXT](PROJECT_CONTEXT.md),
and code/artifact paths in [HANDOFF](HANDOFF.md).

## Implemented

| Area | Current state |
| --- | --- |
| Sources | Four saved PostgreSQL 18 HTML snapshots; allowlist, downloader and offline parser |
| Synthetic sources | Atlas v1.0: two snapshots/12 chunks committed and independently verified; no Atlas vectors yet |
| Chunking | HTML: 184 parsed blocks → 49 chunks; all content/code/table blocks preserved; target 512 / ceiling 1024; maximum observed 822 tokens |
| Embedding | Pinned local Nomic; normalized 768-dimensional document/query vectors |
| Database | Applied Alembic `0002`; six snapshots, 61 chunks, original index/49 vectors, 14 traces/21 spans |
| Retrieval | Index/model compatibility checks, query embedding and dense cosine search; default `limit=5` |
| Diagnostics | P01–P06 full ranks and annotated hits at 5/10/20; immutable JSON reports |
| Tracing | Retrieval-only diagnostics plus workflow-owned retrieval/LLM spans; exact prompt/output/usage |
| Generator | Luna client, source-linked context, `answer_v1` and Simple workflow; one live P04 answer verified |
| Answer runner | `run_simple_rag.py`: explicit single-question or all-question selection; shared resources/run ID and per-question records |
| Live Simple batch | P01–P06 completed; editorial review: P01/P02/P04/P06 meet recorded requirements, P03/P05 partial |
| LLM-only control | Live P01–P06 completed with one LLM span per question; paired editorial comparison recorded |
| Questions | P01–P06 baseline unchanged; separate P07–P09/P19 Atlas subset verified, including one unanswerable case; P10–P18/P20 drafts |

Nomic revision: `e9b6763023c676ca8431644204f50c2b100d9aab`, CPU float32,
1024-token application limit. Committed index:
`nomic-d4a8ebdbce1253c45ea50734d984a14a6258d9f1e7a332fd56964011eb886447`.
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

## Next small step

Atlas references and DB import are complete. Proposed next small step: add
explicit corpus selection to the indexer and embed the 12 Atlas chunks into
their own index, matching the two-document reference state and preserving the
original PostgreSQL index. Then expose runner dataset selection and test
Atlas retrieval/answers. The current indexer reads every stored chunk (61).
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

- Broader paired evaluation and source-specific/abstention/changed-evidence checks.
- Hybrid/full-text search, RRF, reranker and Enhanced tool conditions.
- Atlas embedding/index selection and runner dataset selection, changed document states, frozen DB fixtures and validated tools.
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
