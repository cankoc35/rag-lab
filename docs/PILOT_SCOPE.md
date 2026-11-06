# PostgreSQL pilot — scope and question draft

**Last updated:** 2026-11-06. **Status:** The owner approved PostgreSQL docs
plus synthetic local runbooks, DB-state tools and prior-knowledge controls.
The initial four official documentation sources/scopes are selected in
sources.json; tool contracts and scenario values remain implementation
preparation drafts. This is not a frozen test set or a runnable, fully
verified dataset.

**Verified subset, 2026-11-06:** P01–P06 now have unchanged question text,
source-grounded reference answers and exact snapshot/block/chunk evidence in
[document_questions.json](../data/evaluation/dev/document_questions.json).
The [development-data guide](../data/evaluation/dev/README.md) explains the
annotations. P07–P20 remain drafts; no retrieval/model evaluation has run.

**Language decision (owner, 2026-11-05):** All repository content and RAG
artifacts use English: corpus/synthetic documents, questions/datasets, prompts,
answers and gold answers/rubrics. Multilingual/cross-lingual retrieval is not
required.

## Initial target

A CLI answering PostgreSQL questions with citations. The initial coding
milestone establishes ingestion/retrieval that reads documents and finds
relevant sections. LLM-only and Simple RAG answer runs follow. Enhanced,
LangGraph agent and router stages will share the same components later.

## Source coverage

**Pilot documentation major version:** PostgreSQL 18. Four official source
records are selected in [sources.json](../data/corpus/sources.json) and were
checked against official pages on 2026-11-02. `/docs/18/` pages may change;
source selection alone does not freeze content. Download time, actual content
hash and local file path are recorded in each download's separate manifest.
All four selected pages have saved, hash-verified HTML snapshots. The PG-STATS
target section ID was checked in saved HTML. Snapshot IDs/hashes are in STATUS.
Synthetic sources and the complete pilot corpus are not ready. The HTML parser
is implemented and verified against all four saved sources.

| Source ID | Source | Use |
| --- | --- | --- |
| PG-EXPLAIN | [Using EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html) | Plans, estimated cost, EXPLAIN/ANALYZE distinction |
| PG-MULTI | [Multicolumn Indexes](https://www.postgresql.org/docs/18/indexes-multicolumn.html) | B-tree column order and skip-scan limits |
| PG-PARTIAL | [Partial Indexes](https://www.postgresql.org/docs/18/indexes-partial.html) | Predicate/query compatibility |
| PG-STATS | [Cumulative Statistics — pg_stat_replication](https://www.postgresql.org/docs/18/monitoring-stats.html#MONITORING-PG-STAT-REPLICATION-VIEW) | Only this section, including NULL-lag explanations |
| LOCAL-INVENTORY | Synthetic Atlas environment inventory to be written | Database/schema, replica identities and query catalog |
| LOCAL-POLICY | Synthetic Atlas operations policy to be written | Local thresholds and inspection rules |

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

Keep this document, the evaluation plan and gold answers out of the retrieval
corpus. Ingestion must use an explicit source-file allowlist.

## Synthetic environment and tool draft

- Environment name: **Atlas**, an example using no real user or organizational
  data. Separate corpus documents have not been written.
- Example local policy: for the specified replica, a valid numeric lag of
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
scope. P01–P06 now have verified reference answers and evidence spans mapped
to the saved snapshots and chunks in the JSON subset linked above. The table
below retains the original short answer drafts; the JSON supplies the fuller
verified references. Verify P07–P20 local/tool gold answers after documents
and fixtures are created.

| ID | Type | Draft question | Expected answer / verification needed | Required evidence |
| --- | --- | --- | --- | --- |
| P01 | Direct document | What is the main difference between EXPLAIN and EXPLAIN ANALYZE? | EXPLAIN shows the plan and estimates; ANALYZE executes the query and adds actual measurements. | PG-EXPLAIN |
| P02 | Direct document | Why are filters on the leading columns of a multicolumn B-tree index generally useful? | They can limit the index range scanned; a filter on a later column does not always prevent index use. | PG-MULTI |
| P03 | Direct document | What relationship must the query condition have to a partial index predicate for the index to be usable? | The planner must recognize that the query condition implies the predicate; usability does not guarantee selection. | PG-PARTIAL |
| P04 | Direct document | Can a NULL replay_lag in pg_stat_replication be treated as zero seconds? | No. NULL can also occur on an idle, caught-up system; it is not a numeric lag value or proof of failure. | PG-STATS |
| P05 | Multi-document | With an index on (customer_id, created_at), does filtering only on created_at always require a Seq Scan, and how can we inspect the chosen path? | No. PostgreSQL 18 can use skip scan for suitable data distributions. Inspect the chosen plan with EXPLAIN. | PG-MULTI + PG-EXPLAIN |
| P06 | Multi-document | Is choosing a Seq Scan for a query whose condition matches a partial index necessarily an error? | No. Predicate compatibility determines eligibility; cost and data distribution affect selection. Inspect the plan. | PG-PARTIAL + PG-EXPLAIN |
| P07 | Local document | What are the database and application schema names in the Atlas example environment? | Verify the names and source span after LOCAL-INVENTORY is written. | LOCAL-INVENTORY |
| P08 | Local document | What is the maximum lag allowed by the Atlas replica lag rule? | The draft policy is 5 seconds; verify it against the policy document once written. | LOCAL-POLICY |
| P09 | Local multi-document | Which lag rule applies to the replica listed in the Atlas inventory? | Match the replica identity from the inventory to the correct policy. | LOCAL-INVENTORY + LOCAL-POLICY |
| P10 | DB tool | What indexes currently exist on the Atlas orders table, and in what column order? | Verify against the selected fixture's actual index catalog; names are not fixed yet. | DB index output |
| P11 | DB tool | What is the observed Atlas replica lag, in seconds, in the selected snapshot? | A: 3; B: 12. Verify the output and evidence ID after the fixtures are prepared. | DB observation output |
| P12 | DB tool | Which scan type appears in the selected snapshot's plan for the Atlas customer lookup query? | Determine from an actual plan output; do not assume an Index Scan. | EXPLAIN output |
| P13 | Document + tool | Does the Atlas replica satisfy the lag rule in the policy? | The same question should yield yes in A and no in B; both the policy and the numeric observation are required. | LOCAL-POLICY + DB observation |
| P14 | Document + tool | How do the Atlas customer lookup query's filters align with the existing multicolumn index, and which scan type is selected? | Interpret column order and the actual plan together after the query, index and plan are available. | PG-MULTI + DB query/index/plan outputs |
| P15 | Document + tool | Is the Atlas partial index with predicate billed IS NOT TRUE usable for a query with billed = TRUE? | No, if the fixture actually uses that predicate: the query does not imply the index predicate. | PG-PARTIAL + DB index output |
| P16 | Document + tool | Is the cost in the Atlas query's plain EXPLAIN output an actual duration, and can we measure latency from it? | No. Cost units are not actual milliseconds, and a plain plan supplies no actual duration. Verify the real output. | PG-EXPLAIN + EXPLAIN output |
| P17 | Insufficient evidence | Does the Atlas replica satisfy the lag rule when its observed lag is NULL? | This cannot be determined without a valid numeric observation; NULL must not be treated as zero. | LOCAL-POLICY + PG-STATS + NULL observation fixture |
| P18 | Insufficient evidence | What is the exact root cause of the increase in Atlas replica lag? | A single observation cannot establish an exact cause; identify the additional measurements needed. | Available evidence scope; do not invent a causal diagnosis |
| P19 | Insufficient evidence | What is the approved replica lag limit for the Boreal environment, which is absent from the documents? | The sources do not provide it; do not transfer the Atlas policy to another environment. | Corpus scope and targeted retrieval |
| P20 | Insufficient evidence | Exactly how many milliseconds will an unmeasured new index save on the Atlas query? | An exact gain cannot be established without actual before-and-after measurements. | PG-EXPLAIN + existing plan; no benchmark measurement |

P13 will run in at least two states, an additional execution variant rather
than a new question among the 20 records. Keep all related variants in the
same development group. Do not construct future held-out questions by merely
renaming these questions; keep related scenario families within one split.

## Implementation order and completion criteria

1. **Completed:** A controlled parser for four saved HTML sources preserves
   section text, code, tables, heading paths, source/snapshot IDs and anchors.
   **Next small step:** Produce chunks from these blocks.
2. Write two synthetic documents and add Markdown ingestion. These tasks do
   not require a model or orchestration framework.
3. Choose a local embedding model, configure PostgreSQL + pgvector, and use
   the same model for query/document embeddings. Inspect whether required
   evidence appears in top-k for pilot document questions. The first retrieval
   check does not require generation.
4. Select the generator, add LLM-only/Simple RAG answer runs with citations
   and MLflow traces. Then create DB fixtures/tools, verify tool questions,
   and implement enhanced/agentic workflows.

**Before the pilot is ready:** Verify each record's `question_id`, type,
source state, gold answer/rubric, required source-span/tool evidence IDs and
answerability. Separate gold data from model-visible questions and corpus.
Record model, prompt, corpus, tool and code versions in runs.

**Still open:** Full corpus snapshot, embedding/LLM models, tool schemas,
cost/latency measurement details and the final thesis-test protocol.
