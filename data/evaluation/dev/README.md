# Development question subsets

**Version:** `postgresql18-document-dev` / `1.0.0`, verified on 2026-11-06.
[document_questions.json](document_questions.json) contains P01–P06 from the
[pilot draft](../../../docs/PILOT_SCOPE.md), with unchanged question text and
source-verified English reference answers. The separate
[atlas_questions.json](atlas_questions.json), `atlas-document-dev` / `1.0.0`,
contains P07–P09/P19 verified on 2026-11-18. There are ten annotated records
across the two subsets; P10–P18/P20 remain drafts. This is development data,
not the held-out thesis test set. The original six-question file is unchanged.
The separate [expanded_questions.json](expanded_questions.json) revalidates
these same ten questions against the expanded shared corpus; it adds no new
unique questions. Cumulative [version 1.7.0](expanded_questions_v1_7.json)
preserves all earlier records and completes the approved target:
**120 unique development questions, 100 answerable + 20 unanswerable**.
All topic budgets are met; this is not a held-out thesis set or a quality result.

## Current annotations — version 1.8.0, 2026-11-25

Use [expanded_questions_v1_8.json](expanded_questions_v1_8.json) for the current
annotations. All 120 raw questions, source pins, groups/families and twenty negative
records are identical to version 1.7. An alignment screen covered all records;
twelve received source-backed corrections. The other 108 complete question
records are unchanged. There are now 251 requirements and 202 evidence records
over 135 blocks/73 distinct chunks. Exact changes and accepted passages are in
[reference_review_v1_8.json](reference_review_v1_8.json).

All three saved rankings were rescored offline. Full support at five is
dense 83/100, full-text 65/100 and RRF 82/100; at twenty it is 88/95/100.
The [review report](../../../docs/REFERENCE_REVIEW.md) preserves old/new scores,
raw/rescore paths and limitations. This single-editor development review is not
exhaustive pooled judging. Other unannotated contexts remain unjudged; final
held-out/scoring decisions remain open. No new retrieval, DB access or model call
ran. All 222 unit tests and eleven reference checks passed; old files are preserved.

## Completed cumulative file — 2026-11-24

The original [expanded_questions_v1_7.json](expanded_questions_v1_7.json) completes
all 120 questions. Dataset ID is `postgresql18-atlas-expanded-dev`, version `1.7.0`.
Use version 1.8 above for current refined annotations.
P81–P130 add 21 PostgreSQL-only, 13 Atlas-only, eight combined and eight
unanswerable records. All seventy inherited records and the fourteen-source/
151-chunk state are identical to version 1.6.0, whose file remains hash-pinned
as the parent. All prior files are preserved.

| Group | Completed total | New IDs |
| --- | ---: | --- |
| PostgreSQL-only answerable | 50 | P81–P101 |
| Atlas-only answerable | 30 | P102–P114 |
| PostgreSQL + Atlas answerable | 20 | P115–P122 |
| Unanswerable | 20 | P123–P130 |
| **Total** | **120** | **50 new records** |

The [topic matrix](../../../docs/RETRIEVAL_DATASET_PLAN.md) maps all records to
their 23 completed budgets. New coverage includes GiST/BRIN design, predicate
locks, MVCC/visibility/freezing, temporary tables, primary/exclusion constraints,
and local query, restore, maintenance and access requirements. Combined cases
connect exact local facts to PostgreSQL rules; related scenarios retain family
labels. The eight new negative cases cover missing key-rotation/timeout policy,
repository URI/physical table mapping, a chosen plan/drill outcome, reclaimable
space and a query-plan causal diagnosis. Each retains no positive answer evidence
and a complete-scope editorial review. Useful but insufficient context is listed
separately in the validation report.

There are 252 requirements and 195 positive evidence records over 134 distinct
blocks/73 chunks. These are annotations, not independent retrieval hits or a
frozen grading rubric. Alternative sufficient evidence remains acceptable.
Ten reference unit tests and all eleven reference-file checks passed;
196 protected source/data/code files are unchanged. Runtime selection exposes
only IDs/raw questions; no DB, retrieval, embedding or hosted API call ran.
Record: `outputs/validation/expanded-questions-complete-20261123T211259Z.json`.

Question preparation is complete. The diagnostic now uses schema 4 and
`annotated-evidence-v2`: all six quality metrics at 5/10/20, means over answerable
questions only, and separate negative records. Unannotated results remain
candidates for manual review, not automatic
errors. Definitions and review instructions are in the
[evaluation plan](../../../docs/EVALUATION_PLAN.md#expanded-development-measurements--2026-11-24).
The original v1 step passed eighteen diagnostic unit tests and all eleven reference-file checks;
all 120 questions also passed offline compatibility checks through each mocked
retrieval path. These fixtures do not measure real retrieval quality.
No dataset/source files, DB records or previous reports changed.
Verification: `outputs/validation/retrieval-measurements-20261123T215752Z.json`.

The [Precision/MRR/nDCG extension](../../../docs/EVALUATION_PLAN.md#implemented-ranking-metrics--2026-11-25)
was completed on 2026-11-25: 23 diagnostic tests and eleven reference-file
checks passed, with all 120 questions checked through each mocked method.
Fixed-k Precision, truncated reciprocal rank and binary nDCG join the original
three metrics. No real retrieval/answer run occurred. Validation:
`outputs/validation/retrieval-ranking-metrics-20261125T113908Z.json`.

## Expanded retrieval comparison — 2026-11-25

Dense/full-text/RRF each retrieved these same 120 raw questions from the exact
shared 151-chunk index. Full annotated support at five is 80/60/77 of the 100
answerable questions; at twenty it is 87/90/96. All six metrics and raw rankings
are preserved in the [comparison](../../../docs/EXPANDED_RETRIEVAL_COMPARISON.md).
Twenty negatives have no positive score or answer/abstention grade.

Independent scoring and RRF reconstruction passed. A targeted editorial review
found equivalent passages and overstrict P108/P116 requirements; frozen version
1.7.0 and all raw scores remain unchanged. The subsequent version-1.8 review
and common offline rescoring are recorded above.
No Luna call or DB write ran. Final scoring and a separate held-out thesis set
remain open.

## Sixth new batch — 2026-11-23

`expanded_questions_v1_6.json` preserves the first seventy questions. Dataset ID remains
`postgresql18-atlas-expanded-dev`; version is `1.6.0`. Its source state and all
sixty inherited records are identical to version 1.5.0, whose file is preserved
and hash-pinned as this version's parent. The shared scope stays fourteen
sources/151 chunks; reference answers remain outside ingestion and generation.

| New ID | Bucket | Verified topic |
| --- | --- | --- |
| P71 | PG01 | Non-distinct buffer counts including child-node activity |
| P72 | PG02 | Later-column index checks versus scan-span reduction |
| P73 | PG05 | Constant anchored LIKE patterns and locale/operator-class caveat |
| P74 | AT01 | Selective inventory and the unlisted-table/storage remainder |
| P75 | AT05 | Routine maintenance window and exclusive end boundary |
| P76 | AT06 | Access-record fields and out-of-scope grant escalation |
| P77 | MIX03 | Given write/replay lag values and the local replay-lag threshold |
| P78 | MIX04 | Capacity approval and temporary rewrite disk space |
| P79 | NEG03 | Autovacuum setting without a dated inspection |
| P80 | NEG04 | Actual data-loss window without a usable recovery point |

This batch has three PostgreSQL, three Atlas, two combined and two negative
records. The cumulative groups are 29 PostgreSQL-only, 17 Atlas-only, 12 combined
and 12 unanswerable. There are 152 requirements and 109 positive evidence records
over 76 distinct blocks/51 chunks. Each negative bucket has three records;
MIX03's three-record budget is complete. Related EXPLAIN, multicolumn, lag
and vacuum families are retained. All seventy are dev; 50 records remain.

P77 gives hypothetical values in the raw question (2 seconds write lag,
6 seconds replay lag); the source supplies the required replay-lag field and
inclusive 5-second threshold. No observation was imported or claimed as measured.
P79/P80 use full-corpus missing-fact reviews; defaults, intended settings,
schedules and recovery objectives do not supply the missing observations.
Ten reference unit tests and all ten reference-file checks passed; 195 protected
artifacts are unchanged. No code changed; no DB access, retrieval/embedding
or hosted API call ran. Record:
`outputs/validation/expanded-questions-batch06-20261123T205144Z.json`.

## Fifth new batch — 2026-11-23

`expanded_questions_v1_5.json` preserves the first sixty questions. Dataset ID is
`postgresql18-atlas-expanded-dev`; version is `1.5.0`. Its source state and all
fifty inherited records are identical to version 1.4.0, whose file is preserved
and hash-pinned as this version's parent. The shared scope stays fourteen
sources/151 chunks; reference answers remain outside ingestion and generation.

| New ID | Bucket | Verified topic |
| --- | --- | --- |
| P61 | PG03 | Unique partial indexes and predicate-limited enforcement |
| P62 | PG04 | Standby write, flush and replay lag milestones |
| P63 | PG05 | GIN component entries and membership queries |
| P64 | PG06 | Snapshot stability versus serializable guarantees |
| P65 | AT03 | Device-range bounds and unspecified timestamp tie-breaks |
| P66 | AT04 | Database archive coverage versus cluster rebuild/PITR |
| P67 | AT05 | Required backup/restore records and age-assessment time |
| P68 | MIX02 | Plan-node emitted rows and unbilled-query filters |
| P69 | MIX03 | Conditional asynchronous replay lag and local health limits |
| P70 | NEG02 | Undocumented primary-server CPU allocation |

This batch has four PostgreSQL, three Atlas, two combined and one negative
record to follow the remaining group budgets. The cumulative groups are 26
PostgreSQL-only, 14 Atlas-only, 10 combined and 10 unanswerable. There are 132
requirements and 98 positive evidence records over 71 distinct blocks/48 chunks.
Related isolation, query-range, EXPLAIN and lag questions retain their existing
families. All sixty are dev; 60 records remain toward the approved target.

P70 uses a full-corpus missing-attribute review: a logical primary identifier,
storage allocation and generic CPU-cost parameters do not establish allocated
cores. It keeps empty positive answer evidence. Ten reference unit tests and
all nine reference-file checks passed; 194 protected artifacts are unchanged.
No application code changed; no DB access, retrieval/embedding or hosted API call ran.
Record: `outputs/validation/expanded-questions-batch05-20261123T203929Z.json`.

## Fourth new batch — 2026-11-23

`expanded_questions_v1_4.json` preserves the first fifty questions. Dataset ID is
`postgresql18-atlas-expanded-dev`; version is `1.4.0`. Its source state and all
forty inherited records are identical to version 1.3.0, whose file is preserved
and hash-pinned as this version's parent. The shared scope stays fourteen
sources/151 chunks; reference answers remain outside ingestion and generation.

| New ID | Bucket | Verified topic |
| --- | --- | --- |
| P51 | PG01 | EXPLAIN loops, per-execution averages and node total time |
| P52 | PG06 | Read Uncommitted mapping and dirty-read prevention |
| P53 | PG07 | Manual ANALYZE for partition-parent statistics |
| P54 | PG08 | Default NO ACTION versus deferred checks and RESTRICT |
| P55 | AT02 | Lag-observation identity, units and numeric validity |
| P56 | AT06 | Intended reporting-table scope versus actual privileges |
| P57 | MIX04 | Approved routine VACUUM command and space-return limits |
| P58 | MIX05 | Atlas device/customer foreign key and default delete action |
| P59 | NEG01 | Unspecified event-row retention period |
| P60 | NEG04 | Lag-event cause without matching event/diagnostic evidence |

The cumulative groups are 22 PostgreSQL-only, 11 Atlas-only, 8 combined and 9
unanswerable. There are 109 requirements and 82 positive evidence records over
61 distinct blocks/42 chunks. P51/P52/P53/P55/P57 retain related EXPLAIN,
isolation, statistics, lag-policy and vacuum families. P54/P58 share the new
foreign-key deletion family. All fifty are dev; 70 records remain toward the target.

P59/P60 use full-corpus `missing_fact` reviews. Backup/audit retention cannot
establish live-event row retention, and a threshold cannot establish an observed
lag event or its cause. Both keep empty positive answer evidence. Ten reference
unit tests and all eight reference-file checks passed; 193 protected artifacts
are unchanged. No application code changed; no DB access, retrieval/embedding
or hosted API call ran. Record:
`outputs/validation/expanded-questions-batch04-20261123T202711Z.json`.

## Third new batch — 2026-11-23

`expanded_questions_v1_3.json` preserves the first forty questions. Dataset ID is
`postgresql18-atlas-expanded-dev`; version is `1.3.0`. Its source state and all
thirty inherited records are identical to version 1.2.0, whose file is preserved
and hash-pinned as this version's parent. The shared scope remains fourteen
sources/151 chunks; reference answers stay outside ingestion and generation.

| New ID | Bucket | Verified topic |
| --- | --- | --- |
| P41 | PG02 | Multicolumn GIN conditions on non-leading columns |
| P42 | PG05 | BRIN block-range summaries and physical-order correlation |
| P43 | PG06 | Sequence counters: visibility and abort behavior |
| P44 | PG07 | ANALYZE statistics collection and VACUUM combination |
| P45 | AT01 | Table footprints and database-size accounting boundaries |
| P46 | AT04 | Successful backup generations and failed-run retention |
| P47 | MIX03 | Atlas NULL-lag outcome plus PostgreSQL idle-standby behavior |
| P48 | MIX01 | Atlas unbilled-index predicate versus a billed = TRUE query |
| P49 | NEG02 | Unspecified individual GIN index size |
| P50 | NEG03 | Unobserved current reporting-role membership |

The cumulative groups are 18 PostgreSQL-only, 9 Atlas-only, 6 combined and 7
unanswerable. There are 87 requirements and 66 positive evidence records over
50 distinct blocks/37 chunks. All 23 topic buckets now have at least one record,
including all five combined buckets; this is allocation coverage, not a retrieval
quality result. P47 retains P04/P33's lag family and P48 retains the existing
partial-index family. All forty are dev; 80 records remain toward the target.

P49/P50 use the existing full-corpus `missing_fact` reviews: a table footprint
cannot determine an individual index size, and intended role duties cannot
identify observed members. Positive answer evidence remains empty for both.
Ten reference-boundary unit tests and all seven reference-file checks passed;
192 protected artifacts are unchanged. No application code changed; no DB
access, retrieval/embedding or hosted API call ran. Record:
`outputs/validation/expanded-questions-batch03-20261123T201630Z.json`.

## Second new batch — 2026-11-23

`expanded_questions_v1_2.json` preserves the first thirty questions. Dataset ID is
`postgresql18-atlas-expanded-dev`; version is `1.2.0`. Its source state and all
twenty inherited records are identical to version 1.1.0, whose file is preserved
and hash-pinned as this version's parent. The shared scope remains fourteen
sources/151 chunks; none of the questions or reference answers enters ingestion.

| New ID | Bucket | Verified topic |
| --- | --- | --- |
| P31 | PG01 | EXPLAIN cost units versus actual-time milliseconds |
| P32 | PG03 | Unresolved parameter and partial-index predicate implication |
| P33 | PG04 | Measured replication lag versus predicted catch-up time |
| P34 | PG08 | Default UNIQUE/NULL behavior and NULLS NOT DISTINCT |
| P35 | AT03 | Unbilled queue states and timestamp parameter |
| P36 | AT05 | SQLSTATE 40001 retry action and attempt limit |
| P37 | MIX02 | Atlas inspection/benchmark approval plus ANALYZE execution |
| P38 | MIX05 | Atlas export profile plus PostgreSQL snapshot semantics |
| P39 | NEG01 | Unspecified emergency promotion decision-maker |
| P40 | NEG04 | Unmeasured index-versus-Seq-Scan percentage time change |

The cumulative groups are 14 PostgreSQL-only, 7 Atlas-only, 4 combined and 5
unanswerable. There are 67 requirements and 53 positive evidence records over
41 distinct blocks/30 chunks. P31/P37 share P01's EXPLAIN family; P32 shares
P03/P06's partial-index family, P33 shares P04's lag family, and P38 shares
P22's snapshot family. All thirty remain development data, not independent
held-out observations. There are 90 records left toward the approved target.

P39/P40 use the existing `missing_fact` format, with full-corpus context scans
and editorial reviews. The missing promotion policy and performance measurements
are not inferred from empty search results. Positive answer evidence remains empty.
Ten reference-boundary unit tests and all six dataset checks passed; 191
protected source/data/code artifacts are unchanged. No code change, DB access,
retrieval/embedding or hosted API call ran. Record:
`outputs/validation/expanded-questions-batch02-20261123T200722Z.json`.

## First new batch — 2026-11-23

`expanded_questions_v1_1.json` preserves the first twenty questions. Dataset ID is
`postgresql18-atlas-expanded-dev`; version is `1.1.0`. Its fourteen-source/
151-chunk state and all inherited records are identical to version 1.0.0.
The previous file is preserved and hash-pinned as this version's parent.

| New ID | Bucket | Verified topic |
| --- | --- | --- |
| P21 | PG05 | Hash indexes: equality-only comparisons |
| P22 | PG06 | Read Committed snapshots across successive SELECTs |
| P23 | PG07 | Ordinary VACUUM versus FULL: disk return and locking |
| P24 | PG08 | CHECK/NULL behavior and NOT NULL |
| P25 | AT04 | Atlas RPO/RTO values and timing boundaries |
| P26 | AT06 | Temporary access approvals and expiry |
| P27 | MIX01 | Atlas device-range SQL/index plus PostgreSQL's multicolumn rule |
| P28 | MIX04 | Atlas VACUUM FULL authorization plus engine locking behavior |
| P29 | NEG02 | Unspecified Atlas device-event row count |
| P30 | NEG03 | Backup success without a matching run observation |

The cumulative split is 10 PostgreSQL-only, 5 Atlas-only, 2 combined and 3
unanswerable. There are 44 requirements and 36 positive evidence records over
29 distinct blocks/23 chunks. P23/P28 share a scenario family; all twenty are
development data. P10–P18/P20 remain separate drafts with reserved IDs.

P29/P30 use `unanswerability.review_method: missing_fact`, a present target
entity, an explicit `missing_fact` and a full-corpus editorial review. They keep
empty positive evidence and `corpus_scope` requirements. The checker verifies
scope, entity presence and review metadata; it cannot prove a fact's semantic
absence. P19 retains its default `absent_entity` check. Schedules/schema/footprints
can be relevant context without answering an outcome or row-count question.

All five reference checks, 206 offline unit tests and Ruff passed. All 188
protected artifacts are unchanged. No DB access, retrieval/embedding or hosted
API call ran. Record:
`outputs/validation/expanded-questions-batch01-20261123T194352Z.json`.
The shared index ID below also applies to version 1.1.0 because its complete
source/chunk state is unchanged. No method comparison has run for this version.

## Initial expanded shared-corpus references — 2026-11-23

`postgresql18-atlas-expanded-dev` / `1.0.0` contains unchanged P01–P09/P19
question text, expected answers and requirements: nine answerable questions
and one unanswerable case. Its scope is all eight PostgreSQL sources and six
Atlas sources in `atlas-expanded-v1`, including non-answer passages: fourteen
snapshots, 638 parsed blocks and 151 chunks.

The thirteen PostgreSQL evidence records are unchanged. Six Atlas records now
point to expanded-state snapshots/chunks and updated document-state mentions.
The combined annotations have 21 requirements and 19 evidence records over
fourteen distinct blocks/thirteen chunks. `primary_bucket` follows the
[allocation plan](../../../docs/RETRIEVAL_DATASET_PLAN.md); `scenario_family_id`
keeps related concepts together for later splitting. All ten are development data.

P19 received a new absence and policy-authority review across the entire scope:
no selected source supplies Boreal's approved lag limit. Both source manifests
are pinned in `source_state.sources_manifests`; original single-manifest files
remain valid. Gold remains outside ingestion and generation.

The matching shared index is
`nomic-b2793fdf4ef7869c0589851fb5ee19da961118e251066311e0219f79d534c3d1`.
A read-only check accepted its exact 151-chunk/input scope and rejected all
three original smaller indexes for this file. All four reference checks and
204 offline unit tests passed; old artifacts and DB rows are unchanged.
No retrieval comparison or model call ran in this reference-preparation step.
Record: `outputs/validation/expanded-question-references-20261123T190949Z.json`.

## Contents

| Question | Reference answer topic | Source blocks used |
| --- | --- | --- |
| P01 | EXPLAIN estimates versus ANALYZE execution/measurements | PG-EXPLAIN 76 |
| P02 | Leading-column constraints and B-tree scan ranges | PG-MULTI 9 |
| P03 | Recognized predicate implication versus index selection | PG-PARTIAL 27, 33 |
| P04 | Raw NULL lag, idle standbys and monitoring presentation | PG-STATS 5, 8 |
| P05 | Conditional B-tree index/skip-scan use and plan inspection | PG-MULTI 9, 10; PG-EXPLAIN 2 |
| P06 | Partial-index eligibility versus a reasonable Seq Scan | PG-PARTIAL 27, 33; PG-EXPLAIN 112, 2 |

There are **13 evidence records**, referencing **9 distinct source blocks and
9 distinct chunks** across all four saved sources. Block positions are
one-based in the original parsed documents. Each evidence record includes
source/snapshot/chunk IDs, a block hash, heading path, anchor/citation URL and
an exact text span. Span offsets are zero-based Unicode character positions
in the original block text, with an exclusive end; they are not byte offsets.

`source_state` pins the source allowlist and each snapshot manifest, raw HTML,
parsed JSON and chunk JSON by repository-relative path and SHA-256. The
chunker settings, serialization version and candidate tokenizer identity are
also recorded. The pinned artifacts are local and Git-ignored; a checkout
without them can read the annotations but cannot verify their references.

## How to interpret the annotations

- `expected_answer` is a source-grounded paraphrase, not a string that future
  answers must reproduce verbatim.
- `answer_requirements` decomposes reference-answer claims and their source
  support. It is not a finalized grading rubric. Within one entry,
  `supporting_evidence_ids` are alternatives (`any`), not a demand to retrieve
  every listed passage. `optional_guidance` is additional explanation.
- Reference evidence is not exhaustive. An equivalent sufficient passage or
  chunk must remain acceptable in any later evaluation. The combination note
  explains complementary versus overlapping evidence for each question.
- P04 keeps raw NULL distinct from a measured zero. The source allows a
  monitoring presentation policy; the record does not forbid displaying zero.
- P05 keeps its original broad wording, but the skip-scan explanation is
  explicitly conditional on B-tree. It predicts no plan for an actual table.
- P06 retains the draft's `multi_document` label, but PG-PARTIAL contains
  overlapping support. Its label does not establish irreducible multi-hop
  reasoning or a need to retrieve two different documents for every valid answer.

Only the `question` belongs in the model-visible query. Gold answers, evidence
and these notes stay in the evaluation directory, outside the corpus allowlist
and ingestion. Keep future held-out questions separate. If snapshots, parser,
chunker, tokenizer or chunk settings change, revalidate and version the
evidence mapping before comparing runs.

## Offline verification

From the repository root, using Python 3.11+:

```sh
python3.11 scripts/check_document_questions.py
python3.11 scripts/check_document_questions.py --dataset data/evaluation/dev/atlas_questions.json
python3.11 scripts/check_document_questions.py --dataset data/evaluation/dev/expanded_questions.json
python3.11 scripts/check_document_questions.py --dataset data/evaluation/dev/expanded_questions_v1_1.json
python3.11 scripts/check_document_questions.py --dataset data/evaluation/dev/expanded_questions_v1_2.json
python3.11 scripts/check_document_questions.py --dataset data/evaluation/dev/expanded_questions_v1_3.json
python3.11 scripts/check_document_questions.py --dataset data/evaluation/dev/expanded_questions_v1_4.json
python3.11 scripts/check_document_questions.py --dataset data/evaluation/dev/expanded_questions_v1_5.json
python3.11 scripts/check_document_questions.py --dataset data/evaluation/dev/expanded_questions_v1_6.json
```

The read-only checker verifies file hashes, source/snapshot/chunk identities,
block contents and positions, exact text spans, anchors, neighbor links and
claim-to-evidence references. It requires the saved local artifacts but no
model, tokenizer package, database or network access. It does not decide
whether an answer is semantically supported; that support was reviewed against
the saved source passages when the dataset was authored.

## Atlas source-specific subset — 2026-11-18

The Atlas subset binds exactly two complete documents in `atlas-docs-v1` to
their saved Markdown snapshots and 12 local chunks. Its source state pins nine
files: the local allowlist plus raw/manifest/parsed/chunk records for each source.

| Question | Reference | Answerability | Selected blocks |
| --- | --- | --- | --- |
| P07 | Database `atlas_telemetry`, application schema `atlas_app` | Answerable | Inventory 7 |
| P08 | Maximum lag 5 seconds, inclusive | Answerable | Policy 7, 9 |
| P09 | Reporting replica `atlas-replica-01` → `ATLAS-REPORTING-LAG`, 5 seconds inclusive | Answerable | Inventory 14 + policy 4, 7 |
| P19 | No approved Boreal lag limit in this corpus | Unanswerable | Complete two-document scope review; no positive answer evidence |

There are eight answer requirements and six positive evidence records over
five blocks/four chunks. `support_mode: any` lists alternative selected support;
`all` combines complementary records for P09. This does not establish that
two documents are irreducibly necessary for every equivalent valid answer.

P19 uses `answerability: unanswerable`, empty `evidence`, and `corpus_scope`
requirements with no positive evidence IDs. Its `unanswerability` record names
the target entity, complete checked source scope and editorial review. The
checker verifies that the declared absent entity is not in those sources;
this supplements the review and is not a general semantic answerability test.
Correct abstention does not require an empty retrieval result: related Atlas
passages can be returned without answering the Boreal question.

The original P19 draft disclosed the answer with "which is absent from the
documents". Its finalized raw question omits that clause, retaining the ID and
scenario. Questions P07–P09 retain their draft text. Gold and revision notes
stay outside generation; the shared selector emits only question ID/text.
Changing or expanding the two-document scope requires revalidating absence.

Both dataset checks and all 178 offline unit tests passed, including five new
reference-boundary/gold-isolation tests; 64 protected files remained unchanged.
Record: `outputs/validation/atlas-questions-v1-20261118.json`.
The two Atlas snapshots/12 chunks were subsequently imported and verified;
Atlas now has its own verified Nomic index/12 vectors; the original PostgreSQL
index/49 vectors is preserved. The first Atlas retrieval run is recorded below.
The paid answer runners now accept `--dataset`, preserving P01–P06 by default;
their first Atlas pair is recorded in the
[comparison](../../../docs/LLM_ONLY_COMPARISON.md#atlas-source-specific-comparison--2026-11-18).
Dataset `verification` counters describe annotation creation;
later execution records are separate and do not rewrite the pinned JSON.

## Atlas retrieval diagnostic — 2026-11-18

`check_retrieval.py --dataset data/evaluation/dev/atlas_questions.json` now
supports the separate Atlas dataset; omission preserves P01–P06. Before model
loading, it checks the selected index against every pinned chunk, snapshot and
exact embedding input/hash. A PostgreSQL-index/Atlas-dataset mismatch was
rejected in a live read-only check. Only unchanged raw questions reach retrieval;
gold is used afterward to inspect ranks, never to guide search.

Run: `dense-20261118T202158580023Z`, Atlas-only index/12 vectors, pinned local
Nomic settings, no query rewriting, hybrid search or reranking.

| Question | Annotated evidence ranks | Result in the first five |
| --- | --- | --- |
| P07 | E1: 1 | Database/schema names present in the first chunk |
| P08 | E1/E2: 1/1, the same chunk | 5-second inclusive limit present in the first chunk |
| P09 | E1/E2/E3: 1/3/2 | Replica identity, policy scope and rule all present |
| P19 | N/A: no positive answer evidence | Atlas lag criterion ranks first; it does not approve a Boreal limit |

All six positive evidence annotations across the three answerable questions
appear in the top three and therefore at 5/10/20. These are annotation hits,
not six distinct chunks or four correct generated answers. The index has only
12 chunks; cutoffs 10/20 expose most/all of it. Three answerable development
questions do not establish general retrieval quality or answer improvement.

P19 returns related Atlas passages, with policy scope at rank 3 explaining that
the threshold is local to Atlas. Correct abstention must be checked in generation;
the retriever does not detect unanswerability. No similarity threshold was tuned.
P07 also returns a metadata-only chunk at rank 4; no filtering was introduced.

The read-only run wrote a local report and no traces or answers. Independent
read-back recomputed ranks/hits, checked all 12 ranked memberships/source fields,
unchanged raw-question hashes and code provenance. All six public-table
fingerprints and 31 pinned source/dataset/artifact hashes stayed unchanged.
All 184 unit/24 DB integration tests and Ruff passed.

Records: `outputs/retrieval/dense-20261118T202158580023Z.json` and
`outputs/validation/atlas-retrieval-20261118.json`, with a separate before record.
The subsequent live pair found Simple P07/P08 complete and P09 partial because
the reporting role was not explicit; LLM-only honestly abstained on the three
answerable questions. Both appropriately abstained on P19. All eight calls
completed; corpus/index and older records were preserved. See the
[Atlas answer review](../../../docs/LLM_ONLY_COMPARISON.md#atlas-source-specific-comparison--2026-11-18).
The later [changed-evidence control](../../../docs/CHANGED_EVIDENCE_CHECK.md)
is complete, as recorded below.

## Atlas changed-evidence control — 2026-11-23

[atlas_changed_evidence_v2.json](atlas_changed_evidence_v2.json) pins the two
Atlas v2 sources and the unchanged P08 question. Its expected maximum is
8 seconds inclusive, paired with v1's 5-second requirement. Both variants
belong to the same development scenario; they are not additional held-out
questions. Existing JSON datasets and earlier reviews are unchanged.

Both new Simple answers follow their corresponding source version and cite
the first-ranked policy passage. The pair uses the same prompt/settings and
five-chunk dense path. This is one source-change diagnostic, not general
accuracy or proof of universal grounding. See the linked check for frozen
review requirements, commands, trace IDs and persistence verification.

Check references offline:

```sh
python3.11 scripts/check_document_questions.py --dataset data/evaluation/dev/atlas_changed_evidence_v2.json
```

## Full-text development diagnostic — 2026-11-23

The same pinned questions/indexes were checked with index-scoped PostgreSQL
full-text retrieval. Plain AND returned no candidates; the recorded final
development policy uses English normalized lexemes with OR and `ts_rank_cd`.
Neither stage rewrites questions or passes gold into search.

P05 E1/E2 have full-text ranks 3/2 versus dense 17/11: 2/3 annotated records
at five results versus 0/3. E3 stays low at 43 versus 46. Other top-five counts
match, with some rank regressions. This does not imply an answer-quality gain.
Atlas v1/v2 scopes remain separate; P19's related Atlas matches establish no
Boreal limit. No new answer/abstention or LLM call was made.

See [FULL_TEXT_RETRIEVAL](../../../docs/FULL_TEXT_RETRIEVAL.md) for every
question's counts, raw report IDs, the preserved AND check and limitations.
Existing dataset JSON files and earlier results are unchanged. The later
[RRF check](../../../docs/HYBRID_RETRIEVAL.md) uses equal weights, `k=60` and
20 candidates per method. P05 has 1/3 annotations at five and 2/3 at ten;
full-text alone has 2/3 at five. E3 lies outside both candidate windows.
All other top-five counts match. This mixed result was retained without
parameter retuning; no answer-quality improvement is claimed. Reranking is
the next proposed component.

## Historical PostgreSQL verification

Initial verification passed, including nine rejection checks for stale hashes,
unknown chunks, wrong block positions, changed span text/offsets, unknown claim
references, duplicate question IDs, wrong snapshots and a non-development split.
All **17 pinned input files** remained unchanged. All **48 existing offline
unit tests** also passed. The local verification record is
`outputs/validation/document-questions-v1.json`.

No retrieval/model-answer run was performed when this dataset was verified;
its `verification` counters describe that creation step. The evaluation runner, scoring
metrics and final thesis protocol remain unimplemented or open. The
[local Nomic adapter](../../../docs/EMBEDDING_SETUP.md) has since passed a
document/query runtime check. PostgreSQL + pgvector and the four retrieval
tables now exist. Four snapshots and 49 chunks are imported and field-verified;
the indexing script has passed full real-model repeat checks with rollback.
The owner's subsequent indexing run committed one index and 49 verified vectors.
The first dense retrieval diagnostic is recorded below. See the
[session handoff](../../../docs/HANDOFF.md) for current state and local inputs.

## First dense retrieval check

On 2026-11-14, the real cached Nomic model was loaded once and P01–P06 were
passed to `retrieval.retrieve()` as raw question text, with `limit=5`, against
the existing 49-vector index. Gold answers/requirements/evidence were used only
after retrieval to inspect annotated chunk IDs, never as model/search input.

| Question | Ranks of annotated evidence chunks within the top five |
| --- | --- |
| P01 | E1: 5 |
| P02 | E1: 2 |
| P03 | E1: 1; E2: 3 |
| P04 | E1: 1; E2: 2 |
| P05 | No annotated evidence chunk in the top five |
| P06 | E1: 1; E3: 2; E2/E4 outside the top five |

These are annotation-ID diagnostics, not correctness grades. Evidence
alternatives remain valid, and unannotated sufficient passages may exist.
P05 retrieved EXPLAIN/partial-index passages but no multicolumn-index passage;
the follow-up diagnosis below inspected its full ranking. Do not
change gold questions/evidence to hide this miss. The five-result limit is a
development starting point, not a finalized experimental context budget.

The first query/vector repeated identically. Python network calls were blocked,
DB access was read-only, and all public-record fingerprints/counts were unchanged.
The local report, `outputs/validation/query-retrieval-2026-11-14.json`, records
dataset/source/index IDs, model/runtime settings, code/config/lock hashes,
query hashes/token counts, retrieved passages/distances and annotated evidence
ranks. No generated answers, judge calls or held-out evaluation were run.

## P05 wording diagnosis

A read-only follow-up on 2026-11-14 retrieved all 49 ranks with the same
model/index. All annotated chunks exist, input hashes match, and all stored
vectors are finite and normalized. SQL cosine distances agreed with an
independent Python calculation within `1e-6`. The original query vector and
top five matched the earlier run exactly.

| Development probe | E1 rank: leading columns | E2 rank: skip scan | E3 rank: EXPLAIN introduction |
| --- | --- | --- | --- |
| Original P05 | 17 | 11 | 46 |
| Remove only the final question about inspecting the chosen path | 16 | 11 | 49 |
| Add only `multicolumn` before `index` | 1 | 2 | 47 |
| Replace `customer_id` / `created_at` with `first_column` / `second_column` | 2 | 1 | 40 |

The observed failure is dense ranking at the five-result cutoff, not missing
data or an incorrect SQL distance calculation. The wording probes show strong
sensitivity to an explicit concept label and column-name wording. They suggest
weak matching between this concrete schema example and generic multicolumn
documentation; they do not identify the model's exact internal mechanism.
Removing the second request alone did not recover the multicolumn evidence.

The generic EXPLAIN annotation remains low even when multicolumn passages rise;
other EXPLAIN passages may provide equivalent evidence and need separate review.
The four probes are exploratory development observations, not new gold records,
an implemented query-rewriting policy or a final quality benchmark. Gold, corpus,
index and application code are unchanged. Before choosing a change, compare a
bounded retrieval variant against the original baseline across P01–P06.
Report: `outputs/validation/p05-retrieval-diagnostic-2026-11-14.json`.

## Repeatable retrieval checker

[scripts/check_retrieval.py](../../../scripts/check_retrieval.py) implements the
owner-approved development check at 5/10/20. Use the locked offline command in
[README](../../../README.md#run-the-scaffold), selecting the existing index
explicitly with `--index-id`. The script validates pinned references, loads the
cached Nomic model once and uses a read-only DB connection. Each original
question is retrieved once over the full selected index; cutoff membership is
computed afterward. Gold/reference text is never passed to retrieval.

Every run writes a distinct `outputs/retrieval/dense-<UTC timestamp>.json` with
dataset/index/model/runtime/code/lock provenance, query input hashes and latency,
full ranked chunk/source/snapshot IDs, URLs/distances/token counts, annotated
evidence ranks and the evidence IDs found at each cutoff. A `null` evidence rank
means its chunk was not returned from the selected index. Console progress
prints annotated hit counts; the denominator is the number of evidence records,
not a requirement count, correctness score or number of mandatory passages.

Two locked CLI runs on 2026-11-14 produced identical ranks and evidence hits:

| Question | Annotated hits at 5 | At 10 | At 20 |
| --- | --- | --- | --- |
| P01 | 1/1 | 1/1 | 1/1 |
| P02 | 1/1 | 1/1 | 1/1 |
| P03 | 2/2 | 2/2 | 2/2 |
| P04 | 2/2 | 2/2 | 2/2 |
| P05 | 0/3 | 0/3 | 2/3 |
| P06 | 2/4 | 2/4 | 2/4 |

P05's E1/E2/E3 ranks remain 17/11/46; P06's E1/E2/E3/E4 ranks are 1/32/2/27.
P06's evidence annotations contain alternatives, so 2/4 is not a half-correct
answer. Review passages and requirement alternatives separately. Increasing
the cutoff to 20 recovers two P05 reference chunks but does not establish
answer completeness or justify a production context-budget change. The
application's `limit=5` baseline, questions, corpus and index are unchanged.

The runs preserved all public table counts/fingerprints at `(4, 49, 1, 49)`;
104 offline unit tests passed at that retrieval-only step; it produced no
generated answers or final-test results. A later P04 answer check is described below.
Reports:

- `outputs/retrieval/dense-20261114T152432906864Z.json`
- `outputs/retrieval/dense-20261114T152436396465Z.json`
- Verification: `outputs/validation/check-retrieval-2026-11-14.json`

## First persisted question trace

After owner authorization, tracing migration `0002` was applied on 2026-11-16
and P04 alone was run with real cached Nomic at five results. It committed one
`ok` question trace and one `ok` retrieval span, with annotated P04-E1/E2 chunks
ranked 1/2. A fresh connection verified the saved inputs, ordered chunk metadata
and distances against the actual retrieval result. Answer/usage/cost are NULL
because no generator or tool ran. Corpus/index fingerprints remain unchanged.

Trace ID: `db808e0d-76ed-4148-9996-2a8988cc4ce7`.
Record: `outputs/validation/tracing-schema-0002/applied-2026-11-16.json`.
The four tracing DB tests also passed in temporary table clones. The complete
six-question `--trace` checker batch has not run; these results describe only
the requested one-question smoke. See [TRACING_PLAN.md](../../../docs/TRACING_PLAN.md).

## First Simple answer check — 2026-11-17

P04 ran through dense top-five retrieval, whole-chunk context and one Luna
answer call using `answer_v1`. Only the raw question and retrieved public
evidence entered generation. Runtime labels S1/S2 map to P04-E1/E2; they are
not gold annotation IDs shown to the model. Post-run editorial review found
P04-R1/R2 and the optional monitoring guidance satisfied. This is one
development check, not an automated grade, a held-out result or proof that
retrieval caused correctness; the LLM-only control had not run at that point.

Trace: `0a5c1437-8383-4702-b9a7-e676a24ddbee`. Raw answer/usage:
`outputs/answers/simple-P04-20261117T172725743636Z.json`. Independent persisted
record checks and editorial review use the same name under `outputs/validation/`.
The five-chunk baseline, questions, gold, snapshots and index are unchanged.
The [single/batch runner](../../../README.md#run-simple-rag) subsequently ran
P01–P06 as recorded below, followed by the LLM-only control.

## First Simple answer batch

On 2026-11-17 the owner requested the live P01–P06 batch. Six calls to Luna
completed using the unchanged questions, sources, index, top-five retrieval,
generator settings and `answer_v1`. Each question received its own trace;
all six share `run_id` **`simple-20261117T183619008413Z`**.

| Question | Post-run editorial finding | Evidence / limitation |
| --- | --- | --- |
| P01 | Meets recorded requirements | Estimated versus actual execution, including query execution by EXPLAIN ANALYZE; cites S4/S5. |
| P02 | Meets recorded requirements | Leading equalities/first inequality narrow the scanned range; later-column filters are not categorically excluded; cites S2. |
| P03 | Partial | Correct implication direction/planner recognition, but does not explicitly separate eligibility from selection. Supporting P03-E2 was retrieved at S3, so this omission is in the answer. |
| P04 | Meets recorded requirements | Distinguishes NULL from measured zero, explains idle caught-up/absent-tracking cases and monitoring presentation; cites S1/S2. |
| P05 | Partial; explicit evidence gap | No PG-MULTI chunk in the five retrieved sources. Acknowledges missing composite-index evidence and answers plan inspection with alternative EXPLAIN evidence; no supported missing-leading-column/skip-scan explanation. The opening "No" is stronger than the evidence establishes. |
| P06 | Meets recorded requirements | Distinguishes eligibility from cost-based choice; common-value example; cites S1/S2. |

This was one non-blind editorial review against existing development
requirements, not an automated grade or a frozen final judging protocol.
Valid citation labels alone do not establish semantic support. P03 needs
better answer completeness despite retrieved evidence; P05 retains the known
retrieval coverage gap. Preserve both observations when comparing controls.

The batch took 19.262 s excluding model loading: 15,328 input / 457 output /
15,785 total tokens, zero reasoning/cache reads and 15,310 30-minute cache-write
tokens. Estimated Standard token cost: $0.00214405 before taxes/other services;
rates and calculation basis are in the validation record. DB cost remains NULL.

- Raw outputs: `outputs/answers/simple-20261117T183619008413Z.json`.
- Independent DB/provenance checks: `outputs/validation/simple-20261117T183619008413Z.json`.
- Per-question editorial notes: `outputs/validation/simple-20261117T183619008413Z-review.json`.

A fresh read-only connection verified six traces/12 spans, exact full-text
context, source mappings, responses and usage. Public totals are eight
traces/15 spans; corpus and older observations retain their fingerprints.
No implementation, prompt or gold changed during that batch execution.
The [LLM-only control](../../../README.md#run-the-llm-only-control) later ran
on these same questions/settings, as recorded below.
It uses the shared question selector, without reading source artifacts or
passing gold to generation. The separate prompt allows prior knowledge and
supplies the PostgreSQL 18 task label; no per-question hints are added.
Dedicated insufficient/changed-
evidence checks and held-out evaluation remain open; this batch does not
establish retrieval's contribution or general accuracy.

## First paired LLM-only comparison — 2026-11-17

All six calls completed in `llm-only-20261117T191359474642Z`. A fresh read-only
check verified one trace/LLM span per question, exact raw-question inputs,
prompt/settings, answers and usage, with no supplied documents/tools/history.
The prior corpus/index, trace rows and Simple report were unchanged.

Against the same recorded requirements, Simple meets P01/P02/P04/P06 and
LLM-only meets P01/P05/P06. Both are partial on P03. Simple is more complete
on P02/P04; LLM-only supplies the PostgreSQL 18 skip-scan explanation that
Simple's P05 retrieval missed. Keep every question, including LLM-only-correct
cases. This is one non-blind development comparison with intentionally
different instruction policies, not an accuracy estimate or proof of memorization.

LLM-only used 523 input / 621 output / 1,144 total tokens in 19.031 s. Its
estimated Standard token cost was $0.0003628. Full findings, pricing basis and
limitations are in [LLM_ONLY_COMPARISON](../../../docs/LLM_ONLY_COMPARISON.md).

- Raw answers: `outputs/answers/llm-only-20261117T191359474642Z.json`.
- Independent checks: `outputs/validation/llm-only-20261117T191359474642Z.json`.
- Paired answers/requirement notes: `outputs/comparisons/simple-vs-llm-only-20261117T191359474642Z.json`.
