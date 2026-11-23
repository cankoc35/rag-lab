# PostgreSQL pilot — scope and question draft

**Last updated:** 2026-11-24. **Status:** The owner approved PostgreSQL docs
plus synthetic local runbooks, DB-state tools and prior-knowledge controls.
The initial four official documentation sources/scopes are selected in
sources.json; tool contracts and scenario values remain implementation
preparation drafts. This is not a frozen test set or a runnable, fully
verified dataset.

**Verified subset, 2026-11-06:** P01–P06 now have unchanged question text,
source-grounded reference answers and exact snapshot/block/chunk evidence in
[document_questions.json](../data/evaluation/dev/document_questions.json).
The [development-data guide](../data/evaluation/dev/README.md) explains the
annotations and later retrieval diagnostics. P07–P09/P19 now have a separate
[verified Atlas subset](../data/evaluation/dev/atlas_questions.json), dated
2026-11-18. P10–P18/P20 remain drafts. One Simple
P04 answer passed post-run editorial review on 2026-11-17. A later P01–P06
batch completed; editorial review found P03/P05 partial and the other four
meeting recorded requirements. Held-out evaluation has not run.

**Coverage audit, 2026-11-23:** Dense, full-text and equal-weight RRF have now
been compared on the initial ten verified unique questions, plus the P08 Atlas v2
state variant (eleven question/state observations). At that audit the retrieval DB had
eight snapshots/73 chunks and three indexes/73 vectors: PostgreSQL 49,
Atlas v1 12 and Atlas v2 12. These contain all chunks in the selected source
scopes, not only annotated answer passages. P10–P18/P20 are still unverified
drafts; most require index/observation/plan fixtures and tool outputs that do
not exist yet. P18/P20 also need a verified insufficient-evidence scope.
Existing embeddings alone do not make all twenty records evaluation-ready.
See the [three-method results](HYBRID_RETRIEVAL.md) and local audit
`outputs/comparisons/pilot-retrieval-coverage-20261123.json`.

**Language decision (owner, 2026-11-05):** All repository content and RAG
artifacts use English: corpus/synthetic documents, questions/datasets, prompts,
answers and gold answers/rubrics. Multilingual/cross-lingual retrieval is not
required.

## Requested retrieval expansion target — 2026-11-23

The owner approved **100 answerable questions: 50 PostgreSQL-only, 30
Atlas-only and 20 combined**, plus **20 unanswerable questions**, and broader
topic coverage. The completed [source/topic/question matrix](RETRIEVAL_DATASET_PLAN.md)
allocates eight PostgreSQL scopes, six Atlas documents and four negative-case
groups. It specifies source URLs, planned IDs/files and required evidence.

The expanded development set now completes all 100 answerable plus 20
unanswerable questions. The original ten are retained and revalidated. P08 v2
is a related state variant. P10–P18/P20 remain separate tool/scope drafts.
Completing these document questions does not complete those tool drafts or
determine the final thesis sample size.

Four new PostgreSQL 18 pages are now captured with a separate
[expansion manifest](../data/corpus/postgres_expanded_v1.json), retaining the
original four pinned sources. See [snapshot IDs/hashes](STATUS.md#saved-official-documentation-snapshots).
The six expanded Atlas documents and their
[manifest](../data/corpus/synthetic/atlas-expanded-v1/sources.json) are authored
and persistently parsed. The selected fourteen sources have 638 saved parser
blocks and 151 saved/imported chunks in the verified shared Nomic index.
The unchanged ten questions now have a separate [expanded-scope reference file](../data/evaluation/dev/expanded_questions.json),
including Atlas evidence rebinding and P19's full-corpus absence review.
The first new batch P21–P30 is in cumulative
[version 1.1.0](../data/evaluation/dev/expanded_questions_v1_1.json), preserving
all inherited records/source pins. These twenty dev records do not complete
the original P01–P20 draft: P10–P18/P20 still need separate verification.
The second batch P31–P40 is now verified in cumulative
[version 1.2.0](../data/evaluation/dev/expanded_questions_v1_2.json): thirty dev
records, with all twenty earlier records and source pins preserved.
The third batch P41–P50 is verified in cumulative
[version 1.3.0](../data/evaluation/dev/expanded_questions_v1_3.json): forty dev
records, with all thirty earlier records/source pins preserved.
The fourth batch P51–P60 is verified in cumulative
[version 1.4.0](../data/evaluation/dev/expanded_questions_v1_4.json): fifty dev
records, with all forty earlier records/source pins preserved.
The fifth batch P61–P70 is verified in cumulative
[version 1.5.0](../data/evaluation/dev/expanded_questions_v1_5.json): sixty dev
records, with all fifty earlier records/source pins preserved.
The sixth batch P71–P80 is verified in cumulative
[version 1.6.0](../data/evaluation/dev/expanded_questions_v1_6.json): seventy dev
records, with all sixty earlier records/source pins preserved.
Completion batch P81–P130 is verified in cumulative
[version 1.7.0](../data/evaluation/dev/expanded_questions_v1_7.json): 120 dev
records, 100 answerable/20 unanswerable, with all seventy earlier records and
source pins preserved. Every approved topic budget is complete. Next review
the development retrieval diagnostic definitions before an expanded comparison.
New question-level retrieval/answer runs, final held-out selection and scoring
remain open. Original indexes and results are preserved.

## Initial target

A CLI answering PostgreSQL questions with citations. The initial coding
milestone establishes ingestion/retrieval that reads documents and finds
relevant sections. The first Simple and LLM-only P01–P06 batches are
[compared](LLM_ONLY_COMPARISON.md); broader controls follow. Enhanced,
LangGraph agent and router stages will share the same components later.

## Source coverage

**Pilot documentation major version:** PostgreSQL 18. Four official source
records are selected in [sources.json](../data/corpus/sources.json) and were
checked against official pages on 2026-11-02. `/docs/18/` pages may change;
source selection alone does not freeze content. Download time, actual content
hash and local file path are recorded in each download's separate manifest.
All four selected pages have saved, hash-verified HTML snapshots. The PG-STATS
target section ID was checked in saved HTML. Snapshot IDs/hashes are in STATUS.
Two Atlas Markdown sources now have pinned local snapshots, parsed blocks
and 12 verified chunks, now imported and embedded in a separate Atlas-only index.
An additional Atlas v2 state now changes the lag policy from 5 to 8 seconds;
its separate two snapshots/12 chunks are indexed. DB fixtures remain.
The HTML parser is implemented and verified
against all four saved HTML sources.

| Source ID | Source | Use |
| --- | --- | --- |
| PG-EXPLAIN | [Using EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html) | Plans, estimated cost, EXPLAIN/ANALYZE distinction |
| PG-MULTI | [Multicolumn Indexes](https://www.postgresql.org/docs/18/indexes-multicolumn.html) | B-tree column order and skip-scan limits |
| PG-PARTIAL | [Partial Indexes](https://www.postgresql.org/docs/18/indexes-partial.html) | Predicate/query compatibility |
| PG-STATS | [Cumulative Statistics — pg_stat_replication](https://www.postgresql.org/docs/18/monitoring-stats.html#MONITORING-PG-STAT-REPLICATION-VIEW) | Only this section, including NULL-lag explanations |
| LOCAL-INVENTORY | [Atlas inventory v1.0](../data/corpus/synthetic/atlas_inventory.md), snapshot/parsed Markdown | Database/schema, replica identities and query catalog |
| LOCAL-POLICY | [Atlas operations policy v1.0](../data/corpus/synthetic/atlas_operations_policy.md), snapshot/parsed Markdown | Local threshold and inspection rules |

In `sources.json`, `schema_version: 1` is the file-format version;
`postgresql_version: "18"` is the documentation major version.
`status: "selected"` means the source list is ready, not that the corpus is
downloaded or frozen. `load_sources()` requires this status and rejects
others. The first three records use `selection.mode: page` for the document
body, excluding navigation/footer. PG-STATS uses `selection.mode: sections`
with verified ID `MONITORING-PG-STAT-REPLICATION-VIEW`; its complete subtree,
including the table and subsequent NULL-lag notes, is retained. The downloader
saves the full HTML page; the parser extracts only the selected section.
Links are not crawled for new pages. Source loading/validation, single-source
downloading and scope-aware parsing are implemented. Example JSON outputs
under `data/local/parsed/` contain heading/paragraph/code/table blocks with
source/snapshot, heading path and anchor metadata; these are not chunks or embeddings.

Each `download-source` call creates raw HTML and `manifest.json` under
`data/local/snapshots/<snapshot_id>/`. The manifest's `snapshot.local_path` is
relative to its own directory. Source definition/scope, HTTP URL/status/type/
charset, UTC download time, byte size and SHA-256 are recorded. Earlier
snapshots are not overwritten. A single-page snapshot does not freeze the
entire corpus. Redirects, HTTP errors, timeouts and incomplete responses fail.

Record each source's URL/path, version, acquisition time and content hash.
Retain heading paths, section anchors, code blocks and tables during ingestion.
Start with required subsections; include all evidence needed by pilot questions
within the snapshot scope.

Atlas uses a separate [local Markdown manifest](../data/corpus/synthetic/sources.json)
with pinned hashes, document versions/state and filenames. `ingest-markdown`
copies/parses only those files; it does not extend or weaken the HTML allowlist.
See [COMMANDS](COMMANDS.md#corpus-preparation-and-embedding-tools).

Keep this document, the evaluation plan and gold answers out of the retrieval
corpus. Ingestion must use an explicit source-file allowlist.

## Synthetic environment and tool draft

- Environment name: **Atlas**, an example using no real user or organizational
  data. Two corpus documents now use version 1.0/state `atlas-docs-v1`.
  The inventory defines database `atlas_telemetry`, schema `atlas_app`, 120
  application tables and 10.0 GB. Its reporting replica is `atlas-replica-01`.
- Authored local policy `ATLAS-REPORTING-LAG`: for the specified replica, a valid numeric lag of
  **at most 5 seconds** satisfies only the lag criterion. NULL, missing or
  invalid observations make the outcome unknown. This is neither a PostgreSQL
  default nor a claim that the whole system is healthy or failover-ready.
- Paired states: A has 3 seconds, B has 12 seconds; other relevant conditions
  remain fixed. Sources are bound to the same state across workflows. These
  are proposed fixture values, not measurements already obtained from a DB.
- First tool candidate: `inspect_database`, a read-only interface with bounded
  operations returning schema, index or observation records. Alternative
  subtool boundaries can be clarified during implementation.
- Later tool candidate: `explain_query(query_id)`, applying
  `EXPLAIN (FORMAT JSON)` to an allowlisted SELECT in the query catalog.
  Arbitrary SQL and `EXPLAIN ANALYZE` are unnecessary for the first pilot.
  This tool is not implemented.
- Replica observations may initially come from synthetic fixtures or an
  example monitoring table. Do not present these as measured replication
  telemetry. Physical replication is not a prerequisite for the first baseline.
- Bind `source_state_id` through the runner. The model must not access other
  snapshots, gold labels or complete fixture files. Retain the document and
  tool-result IDs actually used in each answer.

## 20 development/pilot question records

Questions and expected-answer drafts are in English, the confirmed experiment
language. The earlier drafts were translated while preserving IDs and scenario
scope. P01–P06 and P07–P09/P19 have verified references in separate JSON
subsets linked above. The table includes those finalized records and the
remaining drafts; JSON supplies the fuller references. P19's final raw wording
omits the draft clause disclosing that the environment is absent from the
documents. Verify P10–P18/P20 against the eventual sources/tool fixtures.

| ID | Type | Draft question | Expected answer / verification needed | Required evidence |
| --- | --- | --- | --- | --- |
| P01 | Direct document | What is the main difference between EXPLAIN and EXPLAIN ANALYZE? | EXPLAIN shows the plan and estimates; ANALYZE executes the query and adds actual measurements. | PG-EXPLAIN |
| P02 | Direct document | Why are filters on the leading columns of a multicolumn B-tree index generally useful? | They can limit the index range scanned; a filter on a later column does not always prevent index use. | PG-MULTI |
| P03 | Direct document | What relationship must the query condition have to a partial index predicate for the index to be usable? | The planner must recognize that the query condition implies the predicate; usability does not guarantee selection. | PG-PARTIAL |
| P04 | Direct document | Can a NULL replay_lag in pg_stat_replication be treated as zero seconds? | No. NULL can also occur on an idle, caught-up system; it is not a numeric lag value or proof of failure. | PG-STATS |
| P05 | Multi-document | With an index on (customer_id, created_at), does filtering only on created_at always require a Seq Scan, and how can we inspect the chosen path? | No. PostgreSQL 18 can use skip scan for suitable data distributions. Inspect the chosen plan with EXPLAIN. | PG-MULTI + PG-EXPLAIN |
| P06 | Multi-document | Is choosing a Seq Scan for a query whose condition matches a partial index necessarily an error? | No. Predicate compatibility determines eligibility; cost and data distribution affect selection. Inspect the plan. | PG-PARTIAL + PG-EXPLAIN |
| P07 | Local document | What are the database and application schema names in the Atlas example environment? | Verified: atlas_telemetry / atlas_app, inventory block 7. | LOCAL-INVENTORY |
| P08 | Local document | What is the maximum lag allowed by the Atlas replica lag rule? | Verified: 5 seconds inclusive, policy blocks 7/9. | LOCAL-POLICY |
| P09 | Local multi-document | Which lag rule applies to the replica listed in the Atlas inventory? | Verified: reporting replica atlas-replica-01 maps to ATLAS-REPORTING-LAG, 5 seconds inclusive. | LOCAL-INVENTORY + LOCAL-POLICY |
| P10 | DB tool | What indexes currently exist on the Atlas orders table, and in what column order? | Verify against the selected fixture's actual index catalog; names are not fixed yet. | DB index output |
| P11 | DB tool | What is the observed Atlas replica lag, in seconds, in the selected snapshot? | A: 3; B: 12. Verify the output and evidence ID after the fixtures are prepared. | DB observation output |
| P12 | DB tool | Which scan type appears in the selected snapshot's plan for the Atlas customer lookup query? | Determine from an actual plan output; do not assume an Index Scan. | EXPLAIN output |
| P13 | Document + tool | Does the Atlas replica satisfy the lag rule in the policy? | The same question should yield yes in A and no in B; both the policy and the numeric observation are required. | LOCAL-POLICY + DB observation |
| P14 | Document + tool | How do the Atlas customer lookup query's filters align with the existing multicolumn index, and which scan type is selected? | Interpret column order and the actual plan together after the query, index and plan are available. | PG-MULTI + DB query/index/plan outputs |
| P15 | Document + tool | Is the Atlas partial index with predicate billed IS NOT TRUE usable for a query with billed = TRUE? | No, if the fixture actually uses that predicate: the query does not imply the index predicate. | PG-PARTIAL + DB index output |
| P16 | Document + tool | Is the cost in the Atlas query's plain EXPLAIN output an actual duration, and can we measure latency from it? | No. Cost units are not actual milliseconds, and a plain plan supplies no actual duration. Verify the real output. | PG-EXPLAIN + EXPLAIN output |
| P17 | Insufficient evidence | Does the Atlas replica satisfy the lag rule when its observed lag is NULL? | This cannot be determined without a valid numeric observation; NULL must not be treated as zero. | LOCAL-POLICY + PG-STATS + NULL observation fixture |
| P18 | Insufficient evidence | What is the exact root cause of the increase in Atlas replica lag? | A single observation cannot establish an exact cause; identify the additional measurements needed. | Available evidence scope; do not invent a causal diagnosis |
| P19 | Insufficient evidence | What is the approved replica lag limit for the Boreal environment? | Verified unanswerable within the complete pinned Atlas scope; do not transfer the Atlas rule. No positive answer chunk. | Corpus-scope absence review |
| P20 | Insufficient evidence | Exactly how many milliseconds will an unmeasured new index save on the Atlas query? | An exact gain cannot be established without actual before-and-after measurements. | PG-EXPLAIN + existing plan; no benchmark measurement |

P13 will run in at least two states, an additional execution variant rather
than a new question among the 20 records. Keep all related variants in the
same development group. Do not construct future held-out questions by merely
renaming these questions; keep related scenario families within one split.

## Implementation order and completion criteria

1. **Completed:** A controlled parser for four saved HTML sources preserves
   section text, code, tables, heading paths, source/snapshot IDs and anchors.
   Section-aware chunking produced 49 verified chunks. Nomic is selected and
   its local adapter works; PostgreSQL + pgvector and retrieval revision `0001`
   are set up. See [HANDOFF.md](HANDOFF.md) for runtime state and local inputs.
2. **Import completed:** Four snapshots and 49 chunks are committed, field-verified
   and unchanged after a second import. The indexing script passed two complete
   real-Nomic runs with rollback, followed by the owner's committed run.
   One index and 49 vectors are verified. Dense query retrieval and its first
   P01–P06 diagnostic, P05 wording diagnosis and repeatable 5/10/20 checker now
   exist. Trace/span code and migration `0002` are applied and verified with
   one real P04 trace/span. The Luna client passed offline checks and one live
   smoke. Simple context/`answer_v1` and one P04 answer with retrieval/LLM spans
   are verified. The later P01–P06 batch completed with P03/P05 partial in
   editorial review. The later LLM-only batch completed on the unchanged
   questions/settings. Simple was more complete on P02/P04, LLM-only on P05,
   and both were partial on P03. Preserve both raw baselines.
   The cutoff sweep alone does not choose a production context budget. See the
   [development results](../data/evaluation/dev/README.md#repeatable-retrieval-checker).
3. **Atlas references complete:** The 12 local chunks support verified
   P07–P09 references; P19 has a complete two-document absence review and no
   positive evidence. The four-question file is separate from the unchanged
   six-question baseline. The first Atlas retrieval diagnostic is now complete;
   the later Atlas answer pair is complete, with P09's reporting-role omission retained.
4. **Atlas import/index complete:** Two snapshots/12 chunks were committed and
   repeated without duplicates. A later source-filtered run committed a
   separate Atlas index/12 vectors, preserving the PostgreSQL index/49 vectors.
   The diagnostic now supports dataset selection and exact index scope checks;
   all positive annotations rank in the top three. Both answer runners now
   select datasets; the first pair found two complete Simple answers/one partial
   P09 and three honest LLM-only abstentions on answerable questions. Both
   appropriately abstained on P19. The subsequent changed-evidence control
   and dense/full-text/RRF development diagnostics are complete; sandbox
   fixture/tool questions remain drafts.
5. Broaden answer/control checks and project-owned traces. Then create DB
   fixtures/tools, verify tool questions and implement enhanced/agentic workflows.

**Before the pilot is ready:** Verify each record's `question_id`, type,
source state, gold answer/rubric, required source-span/tool evidence IDs and
answerability. Separate gold data from model-visible questions and corpus.
Record model, prompt, corpus, tool and code versions in runs.

**Still open:** Full corpus snapshot, generator/LLM models, tool schemas,
cost/latency measurement details and the final thesis-test protocol.
