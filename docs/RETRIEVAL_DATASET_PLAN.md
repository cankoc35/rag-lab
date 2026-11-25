# Retrieval dataset expansion

**Updated:** 2026-11-25. **Status:** Expanded corpus indexed; all 120 development questions compared with dense/full-text/RRF using six quality metrics.
The owner approved 100 answerable questions split 50 PostgreSQL-only,
30 Atlas-only and 20 combined, plus 20 unanswerable questions, and broader
topic coverage. Eight PostgreSQL scopes have pinned HTML snapshots and six
expanded Atlas Markdown documents have a hash-pinned manifest. All fourteen
sources have saved parser outputs and 151 verified chunks in the shared Nomic
index. A separate [reference file](../data/evaluation/dev/expanded_questions.json)
revalidates the unchanged ten questions against that whole scope. Cumulative
[version 1.7.0](../data/evaluation/dev/expanded_questions_v1_7.json) completes
all 120 records, including the remaining fifty P81–P130. The seventy inherited
records, source state and prior versions are preserved. All 23 topic budgets
are complete. All 120 are development material. The expanded retrieval
comparison and the version-1.8 targeted reference revision/offline rescoring are
complete. Further relevance review and the final held-out/scoring protocol remain open.

## Counts and scope

| Group | Target | Currently verified | Questions remaining |
| --- | ---: | --- | ---: |
| PostgreSQL-only | 50 | 50; completion IDs P81–P101 | 0 |
| Atlas-only | 30 | 30; completion IDs P102–P114 | 0 |
| Combined PostgreSQL + Atlas | 20 | 20; completion IDs P115–P122 | 0 |
| Unanswerable | 20 | 20; completion IDs P123–P130 | 0 |
| **Total** | **120** | **120** | **0** |

Each question counts once under its primary topic, even when it needs several
sources. PostgreSQL-only and Atlas-only questions can use multiple documents
within their source group. Combined questions must require both groups.
P08 v2 is a related state variant, not an additional independent question.
P10–P18/P20 remain separate tool/scope drafts; they are not ready records
automatically counted toward this document-retrieval set.

## PostgreSQL source and question matrix

Keep PostgreSQL **18**. Retain the four existing pinned source scopes and add
four selected pages. Save full HTML snapshots; parsing selects the document
body with all subsections, examples and tables, excluding navigation/footer.
Do not crawl linked pages. All eight scopes will enter the comparison corpus, not only
gold passages. The [expansion manifest](../data/corpus/postgres_expanded_v1.json)
now defines all eight sources; [its config](../configs/corpus_expansion.toml)
is for source acquisition only. The original manifest/config remain unchanged.

| Bucket | Source ID and official page | Questions | Required topic/evidence coverage | Source status / verified questions |
| --- | --- | ---: | --- | --- |
| PG01 | PG-EXPLAIN: [Using EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html) | 8 | Plan nodes, estimates versus actual measurements, cost units, rows/loops and scan choices | Verified; P01, P06, P31, P51, P71, P81, P82, P83 |
| PG02 | PG-MULTI: [Multicolumn Indexes](https://www.postgresql.org/docs/18/indexes-multicolumn.html) | 7 | Column order, equality/range filters, skip-scan conditions and limits | Verified; P02, P05, P41, P72, P84, P85, P86 |
| PG03 | PG-PARTIAL: [Partial Indexes](https://www.postgresql.org/docs/18/indexes-partial.html) | 6 | Predicate implication, planner recognition, parameters, eligibility versus selection | Verified; P03, P32, P61, P87, P88, P89 |
| PG04 | PG-STATS: [pg_stat_replication](https://www.postgresql.org/docs/18/monitoring-stats.html#MONITORING-PG-STAT-REPLICATION-VIEW) | 5 | Field meanings, lag interpretation and NULL/idle-state caveats | Verified; P04, P33, P62, P90, P91 |
| PG05 | PG-INDEX-TYPES: [Index Types](https://www.postgresql.org/docs/18/indexes-types.html) | 5 | Index methods and supported query patterns; compare methods using documented conditions | Verified; P21, P42, P63, P73, P92 |
| PG06 | PG-ISOLATION: [Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html) | 7 | Isolation levels, visibility, anomalies, sequence caveats and retry requirements | Verified; P22, P43, P52, P64, P93, P94, P95 |
| PG07 | PG-VACUUM: [Routine Vacuuming](https://www.postgresql.org/docs/18/routine-vacuuming.html) | 7 | Reuse versus disk return, VACUUM/FULL, statistics, visibility, wraparound and autovacuum | Verified; P23, P44, P53, P96, P97, P98, P99 |
| PG08 | PG-CONSTRAINTS: [Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html) | 5 | CHECK/NULL, NOT NULL, unique/primary keys, foreign keys and exclusion constraints | Verified; P24, P34, P54, P100, P101 |
| **Total** | | **50** | | |

P05 still needs PG-EXPLAIN as well as PG-MULTI; P06 still needs PG-PARTIAL
as well as PG-EXPLAIN. Their bucket assignment does not remove evidence.
The four new pages were captured on 2026-11-23. Their bytes, hashes and
snapshot IDs are recorded in [STATUS](STATUS.md#saved-official-documentation-snapshots).
All eight scopes now have persisted parser JSON under `data/local/parsed/`;
the original four files were reused unchanged. The capture record binds the
four reused and four new snapshots; this is not a simultaneous capture.
All eight HTML sources and their 113 chunks are imported. The original
49 chunks/IDs remain unchanged; all 113 belong to the shared embedding index.

## Atlas source and question matrix

Six English Markdown documents now exist under
`data/corpus/synthetic/atlas-expanded-v1/`, with document state
`atlas-expanded-v1`. This state extends Atlas v1, preserving its database,
schema, table/storage inventory, replica identities, customer lookup SQL and
5-second inclusive lag rule. Atlas v2's 8-second policy remains a separate
changed-evidence control. Existing files and snapshots are preserved.

All additional deployment facts, index definitions, roles, schedules and
targets are authored synthetic facts. They are not observations from a running
DB. The [manifest](../data/corpus/synthetic/atlas-expanded-v1/sources.json)
pins all six files, their versions and SHA-256 hashes. Inventory/policy use
version 1.1; the four new documents use 1.0. Their persistent snapshot/parsed
run is `data/local/markdown/atlas-expanded-v1-hyrbftbg/`, with 134 blocks.
Its 38 chunks are saved under
`data/local/chunks/atlas-expanded-v1-section-blocks-v1/` and imported with the
six snapshots. All 38 are now embedded in the fourteen-snapshot shared index;
see [STATUS](STATUS.md#expanded-shared-embedding-index--2026-11-23) for its ID.

| Bucket | Source ID / filename | Questions | Required document content | Source status / verified questions |
| --- | --- | ---: | --- | --- |
| AT01 | LOCAL-INVENTORY / `atlas_inventory.md` | 5 | Identity, application scope, table purposes/storage and primary/reporting-replica relationships | Verified; P07, P45, P74, P102, P103 |
| AT02 | LOCAL-POLICY / `atlas_operations_policy.md` | 5 | Rule scope, threshold/units, observation validity, unknown outcomes and escalation requirements | Verified; P08, P09, P55, P104, P105 |
| AT03 | LOCAL-QUERY-CATALOG / `atlas_query_catalog.md` | 5 | Exact SQL and parameter meanings for lookup, event-range and unbilled-order queries; declared synthetic indexes, predicates and relevant table constraints | Verified; P35, P65, P106, P107, P108 |
| AT04 | LOCAL-BACKUP / `atlas_backup_policy.md` | 5 | Backup coverage, schedule, retention, recovery objectives and restore-verification procedure; outcomes remain unmeasured | Verified; P25, P46, P66, P109, P110 |
| AT05 | LOCAL-MAINTENANCE / `atlas_maintenance_policy.md` | 5 | Maintenance window, approvals, VACUUM/FULL restrictions, evidence requirements and transaction/retry policy | Verified; P36, P67, P75, P111, P112 |
| AT06 | LOCAL-ACCESS / `atlas_access_policy.md` | 5 | Named role responsibilities, intended access, approval/review and escalation; distinguish policy from actual grants | Verified; P26, P56, P76, P113, P114 |
| **Total** | | **30** | | |

P09 requires both inventory and operations-policy evidence. Keep the original
customer lookup SQL identical wherever repeated; make the query catalog the
authority for new query/index definitions. Cross-references must identify the
same document state. Do not invent measured plans, performance gains, backup
successes or live replication history. Author coherent procedures and facts
first, then derive distinct questions from them.

## Combined question matrix

The counts below add 20 questions; they do not add another 20 to either source
table. The local fact must change the answer or required reasoning. Merely
adding the word "Atlas" to a generic PostgreSQL question is insufficient.

| Bucket | Questions | Atlas evidence | PostgreSQL evidence | Required connection | Verified IDs |
| --- | ---: | --- | --- | --- | --- |
| MIX01 | 5 | LOCAL-QUERY-CATALOG | PG-MULTI, PG-PARTIAL, PG-INDEX-TYPES | Interpret the declared query filters, index order/method and predicate compatibility | P27, P48, P115, P116, P117 |
| MIX02 | 4 | LOCAL-QUERY-CATALOG, LOCAL-POLICY, LOCAL-MAINTENANCE | PG-EXPLAIN | Relate a named workload and local inspection/approval rule to estimates, execution and measurement limits | P37, P68, P118, P119 |
| MIX03 | 3 | LOCAL-INVENTORY, LOCAL-POLICY | PG-STATS | Combine reporting-replica identity/local validity rules with PostgreSQL lag and NULL semantics | P47, P69, P77 |
| MIX04 | 4 | LOCAL-MAINTENANCE | PG-VACUUM | Apply local windows/approval rules to documented space, concurrency and statistics behavior | P28, P57, P78, P120 |
| MIX05 | 4 | LOCAL-MAINTENANCE, LOCAL-QUERY-CATALOG | PG-ISOLATION, PG-CONSTRAINTS | Relate documented Atlas transaction/integrity requirements to isolation behavior and declared constraints | P38, P58, P121, P122 |
| **Total** | **20** | | | | |

Require only the listed sources needed by each particular question, not
every source in its bucket. These questions assess documented rules and SQL,
not actual runtime plans, grants or observations. For example, index eligibility
can be answerable without knowing which scan a running planner selected.
P27 now covers MIX01 (the device-range query and B-tree rule); P28 covers MIX04
(local VACUUM FULL authorization and engine locking behavior).
P37 covers MIX02 (approved initial inspection versus ANALYZE execution);
P38 covers MIX05 (reporting-export profile and PostgreSQL snapshot semantics).
P47 adds MIX03 (local NULL-lag outcome and PostgreSQL idle-standby behavior);
P48 adds MIX01 (the declared partial predicate versus a billed = TRUE query).
All five combined buckets now have records; this does not establish retrieval quality.
P57 adds MIX04 (the approved routine command and normal space-reuse behavior);
P58 adds MIX05 (the declared device/customer foreign key and NO ACTION default).
P68 adds MIX02 (plan-node emitted rows and the unbilled-query predicates);
P69 adds MIX03 (conditional asynchronous visibility delay and local health limits).
P77 completes MIX03's three-record budget by applying the replay-lag rule to
explicit hypothetical inputs and distinguishing write/replay milestones.
P78 adds MIX04 (temporary rewrite space and the local capacity-assessment prerequisite).

## Unanswerable question matrix

Answerability is relative to the complete frozen corpus and permitted
capabilities. For this comparison, evidence access is document retrieval only.
Review absence after all selected sources have been captured and parsed.

| Bucket | Questions | Missing evidence | Example request / review requirement | Verified IDs |
| --- | ---: | --- | --- | --- |
| NEG01 | 5 | Undocumented environment, component or policy | Retain P19's Boreal limit request; verify no approved value exists anywhere in the expanded scope | P19, P39, P59, P123, P124 |
| NEG02 | 5 | Unspecified attribute of a documented entity | Exact table row count or individual index size; ensure it cannot be derived from other provided values | P29, P49, P70, P125, P126 |
| NEG03 | 5 | Matching runtime/historical observation | Lag at a time, actual query plan or backup result; a documented identity, query or schedule supplies no observation | P30, P50, P79, P127, P128 |
| NEG04 | 5 | Measurements supporting a precise conclusion | Exact lag root cause or exact index speedup; related rules/estimates do not establish the requested conclusion | P40, P60, P80, P129, P130 |
| **Total** | **20** | | | |

Use distinct situations, not five renamed copies of the same missing fact.
Questions must sound like normal requests and must not disclose that the
answer is missing. Avoid wording shortcuts such as using "exactly" only in
negative questions. Related passages can be present, but must not establish
the requested fact. An explicitly refuted premise is answerable by correcting
it; a documented "unknown" outcome can also be a complete answer to a rule
question. Neither automatically makes a question unanswerable.

NEG03 is capability-limited: future DB tools could supply missing observations.
Label and report it separately when tools are introduced. Negative questions
have no positive-answer recall denominator. Returning related chunks is not
an abstention failure; answer generation must be evaluated separately for
unsupported claims and acknowledgement of missing evidence.
P29 now covers NEG02 (device-event row count); P30 covers NEG03 (a dated
backup run outcome). Both document a missing fact about an entity present in
the corpus, with complete-scope editorial reviews. Entity absence alone cannot
validate these cases; useful policy/schema passages do not establish the requested fact.
P39 adds NEG01 for an unspecified emergency-promotion decision-maker of a
documented replica. P40 adds NEG04 for an unmeasured index-versus-Seq-Scan
execution-time change. All four negative categories now have records; this
coverage does not establish answer-level abstention quality.
P49 adds NEG02 for an individual GIN index size that cannot be derived from a
table total; P50 adds NEG03 for current reporting-role memberships, which the
intended access policy does not observe. Both retain complete-corpus reviews.
P59 adds NEG01 for the unspecified live-event row-retention policy; backup/audit
retention does not define it. P60 adds NEG04 for a lag-spike causal diagnosis
without a matching event or diagnostic measurements. Neither invents an observation.
P70 adds NEG02 for the primary server's unspecified CPU allocation. Logical
identity, storage totals and generic CPU-cost parameters do not establish a core count.
P79 adds NEG03 for a dated autovacuum setting without a matching inspection;
P80 adds NEG04 for a data-loss window without a measured usable recovery point.
Completion records P123–P130 add two cases per bucket: key-rotation/timeout
policy, repository URI/physical table mapping, actual plan/drill outcome, and
reclaimable-space/causal conclusions. All four buckets now contain five records.
Each missing fact was reviewed against all fourteen sources; related policy or
schema passages remain useful but insufficient context, outside positive evidence.

## Question and evidence requirements

- Give each question one primary bucket, a scenario-family identifier and an
  answerability label tied to the exact corpus state. Preserve existing P IDs.
- For positives, verify the expected answer and every required claim against
  exact source/snapshot/block/chunk references. Record acceptable alternative
  evidence. Preserve SQL/table blocks during chunking.
- For negatives, record the requested missing fact, whole-corpus absence
  review and any useful but insufficient passages. Do not treat a retrieval
  miss as evidence that no answer exists.
- Mix direct lookup, conditional reasoning, SQL/identifier interpretation and
  evidence across documents. Use natural wording; do not select questions
  because one retrieval method already wins on them.
- Count unique evidence chunks and required claims explicitly; duplicate
  annotations for one chunk must not inflate coverage. Development formulas
  are versioned as [annotated-evidence-v1](EVALUATION_PLAN.md#expanded-development-measurements--2026-11-24).
  Final thesis scoring and semantic judgment rules remain open.
- Keep gold answers, this plan and project documents outside ingestion. Use
  only allowlisted source files, including their non-answer passages.
- Existing verified questions, pilot drafts and their scenario families remain
  development material. Keep related paraphrases/state variants in the same
  split. All 120 prepared records are dev. Final held-out family selection
  remains open; tuning on this set requires a separate held-out thesis set.

## Preparation order and completion checks

1. **Complete:** four new PostgreSQL 18 pages captured with the separate
   expansion manifest; the four original pinned scopes are reused unchanged.
2. **Complete:** six-document Atlas state authored and hash-pinned; baseline
   facts, cross-references and query/index definitions checked. Fourteen
   Markdown tests and temporary ingestion/readback passed.
3. **Complete:** four new HTML parser outputs and six Atlas snapshot/parsed
   outputs saved; original four HTML outputs reused. The selected scope has
   14 sources/638 blocks. Saved blocks match reparsed sources exactly.
4. **Complete:** 113 PostgreSQL and 38 Atlas chunks saved in separate local
   runs, preserving the original 49 chunks/IDs. The layout matches the fit
   check; all content blocks and token limits passed read-back verification.
5. **Complete:** both groups imported and read back. Added ten snapshots and
   102 chunks; the selected scope is fourteen snapshots/151 chunks. All old
   records and indexes are preserved; repeated import passed with rollback.
6. **Complete:** all fourteen exact snapshots/151 chunks embedded with the
   pinned local Nomic model into one shared index, preserving all old indexes.
   Every method will search this same index for every expanded-set question; gold
   categories must not route questions to a smaller source-specific index.
7. **Complete:** the unchanged ten questions have a separate expanded-scope
   reference file with bucket/family/answerability labels. Six Atlas evidence
   records are rebound; thirteen PostgreSQL records are unchanged. P19 received
   a new fourteen-source absence/policy-authority review. Original files are preserved.
8. **Complete:** first new batch P21–P30 verified in cumulative version 1.1.0:
   four PostgreSQL, two Atlas, two combined and two negative cases. All inherited
   records/source pins and prior files are unchanged. All twenty are dev;
   P23/P28 share the VACUUM space/locking family. No retrieval/model comparison ran.
9. **Complete:** second new batch P31–P40 verified in cumulative version 1.2.0:
   four PostgreSQL, two Atlas, two combined and two negative cases. Thirty dev
   records total; all twenty inherited records/source pins and prior files are
   unchanged. Related EXPLAIN, partial-index, lag and isolation variants retain
   existing families. No application code or retrieval/model comparison changed.
10. **Complete:** third new batch P41–P50 verified in cumulative version 1.3.0:
   four PostgreSQL, two Atlas, two combined and two negative cases. Forty dev
   records total; all thirty inherited records/source pins and prior files are
   unchanged. All 23 topic buckets have at least one record. No application code
   changed and no retrieval/model comparison ran.
11. **Complete:** fourth new batch P51–P60 verified in cumulative version 1.4.0:
   four PostgreSQL, two Atlas, two combined and two negative cases. Fifty dev
   records total; all forty inherited records/source pins and prior files are
   unchanged. Related families are retained and P54/P58 share the foreign-key
   deletion family. No application code changed or retrieval/model comparison ran.
12. **Complete:** fifth new batch P61–P70 verified in cumulative version 1.5.0:
   four PostgreSQL, three Atlas, two combined and one negative case, following
   remaining group budgets. Sixty dev records total (50 answerable/10 unanswerable);
   all fifty inherited records/source pins and prior files are unchanged.
   No application code changed or retrieval/model comparison ran.
13. **Complete:** sixth new batch P71–P80 verified in cumulative version 1.6.0:
   three PostgreSQL, three Atlas, two combined and two negative cases. Seventy
   dev records total (58 answerable/12 unanswerable); all sixty inherited
   records/source pins and prior files are unchanged. P77's given lag values
   remain hypothetical question inputs, not measured or imported observations.
   No application code changed or retrieval/model comparison ran.
14. **Complete:** remaining fifty records P81–P130 verified in cumulative
   version 1.7.0: 21 PostgreSQL, 13 Atlas, eight combined and eight negative.
   All 120 unique development questions and every topic budget are complete;
   all seventy inherited records/source pins and prior files are unchanged.
   The 252 requirements/195 evidence records reference 134 blocks/73 chunks.
   Ten unit tests, eleven reference-file checks and preservation of 196 protected
   artifacts passed. No application code, DB access or retrieval/model call changed.
15. **Complete:** implement `annotated-evidence-v1`: unique annotated-chunk
   recall, any/all required-claim coverage, question means over positives only,
   separate negative records and unannotated candidates for manual review.
   Schema-3 reports retain raw ranks and provenance. No model/DB run was needed.
   Final held-out selection/scoring remain open.
16. **Complete:** implement/version/test the
   [Precision/MRR/nDCG extension](EVALUATION_PLAN.md#implemented-ranking-metrics--2026-11-25)
   as `annotated-evidence-v2` / schema 4: six quality metric types at 5/10/20,
   plus timing separately. Twenty-three diagnostic tests and all-120-record
   fixture checks through each method passed. No actual retrieval run occurred.
17. **Complete:** compare dense, full-text and RRF on all 120 raw questions and
   the exact shared index, preserving per-question ranks and six metrics at
   5/10/20. Independent scoring/RRF checks passed; DB tables and protected files
   are unchanged. No Luna call ran. See the
   [comparison](EXPANDED_RETRIEVAL_COMPARISON.md).
18. **Complete:** screen all 120 records and apply twelve source-backed annotation
   corrections in version 1.8.0. Rescore all three saved rankings with common labels;
   preserve version 1.7, sources, raw questions and negatives. See the
   [review limits and results](REFERENCE_REVIEW.md). Judging remains non-exhaustive.
19. **Next:** select/pin a reranker and input handling, then evaluate RRF top-20 →
   rerank → top-5 against dense/RRF top-5 on the same version-1.8 references.

**Completed:** allocation, source preparation, parsing, chunking, import, indexing
and all 120 expanded-scope development questions, plus versioned development
diagnostic measurements and the first three-method retrieval comparison.
**Still to do:** reranking, further relevance review and separate final
held-out/scoring decisions. Existing source/config, corpus and
dataset files are preserved. The question-preparation session was offline; it made no DB,
retrieval, embedding, migration or hosted API call.
