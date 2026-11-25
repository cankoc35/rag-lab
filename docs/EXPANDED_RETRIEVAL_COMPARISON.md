# Expanded retrieval comparison

This records the original **version-1.7** results. The later
[version-1.8 reference review and offline rescores](REFERENCE_REVIEW.md) preserve
these raw reports and apply corrected annotations to the same saved rankings.

**Measured:** 2026-11-25. All 120 development questions were retrieved with dense,
PostgreSQL full-text and hybrid/RRF: 360 method/question calls. No Luna call,
answer generation, trace write, migration or reindexing occurred.

## Main finding

Dense has the strongest first-five reference scores. RRF finds complete annotated
support for more questions at 10 and 20, but dense retains higher MRR/nDCG at every
cutoff. RRF is not a universal improvement. These are frozen-reference diagnostics,
not answer accuracy or a held-out thesis result.

## Shared setup

- Dataset: `postgresql18-atlas-expanded-dev` / `1.7.0`,
  [120 raw questions](../data/evaluation/dev/expanded_questions_v1_7.json).
- Quality means: 100 answerable questions, weighted equally; 20 unanswerable
  questions retrieved and retained separately, with positive scores `null`.
- Exact common index: 14 pinned snapshots / 151 chunks:
  `nomic-b2793fdf4ef7869c0589851fb5ee19da961118e251066311e0219f79d534c3d1`.
- Dense: local `nomic-ai/nomic-embed-text-v1.5`, revision
  `e9b6763023c676ca8431644204f50c2b100d9aab`, CPU float32, normalized 768 dimensions.
- Full-text: English normalized lexemes, OR matching, `ts_rank_cd` on chunk text.
- RRF: equal weights, rank constant 60, at most 20 candidates per component.
  No query rewrite or reranker. Simple still uses dense with five context chunks.
- Reports: schema 4 / `annotated-evidence-v2`; raw question only enters retrieval.
  Gold is used afterward for scoring. Settings and source hashes are in each report.

## Scores

All values below are percentages. Recall/Precision/nDCG count distinct annotated
chunk IDs; MRR measures the first annotated hit. Claim coverage averages supported
mandatory requirements using their `any`/`all` rules. Full support is the percentage
of questions meeting every annotated requirement. See the
[definitions](EVALUATION_PLAN.md#implemented-ranking-metrics--2026-11-25).

| Metric | Cutoff | Dense | Full-text | RRF |
| --- | ---: | ---: | ---: | ---: |
| Recall | 5 | 88.83 | 73.00 | 86.50 |
| Recall | 10 | 91.17 | 88.67 | 94.17 |
| Recall | 20 | 93.17 | 94.83 | 97.83 |
| Claim coverage | 5 | 88.33 | 70.00 | 84.50 |
| Claim coverage | 10 | 90.67 | 87.00 | 94.00 |
| Claim coverage | 20 | 92.67 | 94.00 | 98.17 |
| Full support | 5 | 80.00 | 60.00 | 77.00 |
| Full support | 10 | 83.00 | 81.00 | 90.00 |
| Full support | 20 | 87.00 | 90.00 | 96.00 |
| Precision | 5 | 25.40 | 21.00 | 24.40 |
| Precision | 10 | 13.10 | 13.10 | 13.80 |
| Precision | 20 | 6.75 | 7.00 | 7.30 |
| MRR | 5 | 85.52 | 55.63 | 78.40 |
| MRR | 10 | 85.77 | 56.80 | 78.75 |
| MRR | 20 | 85.77 | 57.07 | 78.92 |
| nDCG | 5 | 83.00 | 56.19 | 75.69 |
| nDCG | 10 | 83.86 | 61.94 | 78.66 |
| nDCG | 20 | 84.48 | 63.63 | 79.86 |

At five, RRF gains full support on P37/P57 but loses it on P27/P48/P89/P101/P105
compared with dense: a net change from 80 to 77 questions.

| Answerable group | Questions | Dense full support @5 | Full-text @5 | RRF @5 |
| --- | ---: | ---: | ---: | ---: |
| PostgreSQL-only | 50 | 44/50 | 35/50 | 42/50 |
| Atlas-only | 30 | 29/30 | 23/30 | 28/30 |
| Combined | 20 | 7/20 | 2/20 | 7/20 |

Combined questions are the weakest at five, often needing a local definition
and a PostgreSQL rule in different chunks. A larger cutoff improves coverage but
does not select a production context/token budget.

Precision is reference-based. Its mean theoretical ceiling for these annotations
is only 30.4% / 15.2% / 7.6% at 5/10/20 because most questions cite few chunks.
Unannotated passages are unjudged; low reference precision does not establish
that the remaining context is irrelevant.

## Failure and annotation review

A targeted editorial check covered nine positives: all four incomplete RRF@20
cases, the four zero-reference-hit cases shared by dense/RRF@5, and P27/P48
regressions. This is not an exhaustive pooled relevance review.

| Question | Finding |
| --- | --- |
| P05 | Annotated EXPLAIN introduction is outside both component top-20 lists. Maintenance block 14 explicitly supplies an EXPLAIN procedure at RRF rank 18; a valid alternative is omitted from strict scoring. |
| P21 | Explicit Hash equality-only evidence ranks 8/18/10 in dense/full-text/RRF. No equally explicit explanation was found in the inspected first-five passages. |
| P27 | RRF retrieves the index and multicolumn rule, but the exact device-range SQL is rank 9; dense has it at 2. |
| P48 | RRF has partial-index DDL and the general rule at 5. The explicit local false/NULL explanation is rank 8, so strict `all` requirements fail; zero claim coverage does not mean unrelated context. |
| P64 | Alternative RR/Serializable paragraphs support the distinction in RRF top five despite zero annotated hits. Dense alternatives clearly support the Serializable part. |
| P81 | A returned LIMIT example supports total cost and early stopping; it is missing from references. Full startup-cost support is not established by that passage alone. |
| P98 | Wraparound reference is dense rank 19, RRF rank 28: a fusion ordering loss. Other returned freezing passages merit equivalent-evidence review. |
| P108 | Mandatory `jsonb` type is not asked by the raw question. The index/table/column and no-filter statements are already RRF rank 1. Proposed requirement correction only. |
| P116 | Mandatory inspection-boundary reference duplicates the limitation already explicit in returned catalog block 34. Proposed removal from mandatory `all` support only. |

RRF lacks full annotated support at 20 for P05/P98/P108/P116. P05/P116 have a
required reference outside the component candidate union; P98/P108 have it in
the union but below fused rank 20. These are reference-level failure locations,
not necessarily missing semantic answer support.

Four negative examples were inspected separately: P19 (Boreal policy), P125
(backup URI), P127 (observed plan) and P130 (dated causal diagnosis). Their RRF
contexts are related but do not establish the requested facts. No model answer
or abstention was generated or graded.

**No question, reference, algorithm or raw report was changed.** Review notes
record exact source blocks, chunk IDs, method ranks and two unapplied annotation
proposals. Review equivalent evidence consistently across all methods, publish a
new annotation version if accepted, then rescore these saved rankings. No new
embedding or paid call is needed for that rescoring. Reranking remains a later step.

## Timing and verification

| Method | Median retrieval ms | p95 ms |
| --- | ---: | ---: |
| Dense | 36.81 | 52.47 |
| Full-text | 31.29 | 39.01 |
| RRF | 54.53 | 61.07 |

Timing covers all 120 questions, excludes model loading, and includes query
embedding where applicable plus diagnostic ranking fetches. Methods ran
sequentially without controlled warm-up; result lengths also differ. This is
descriptive diagnostic timing, not a controlled production top-five benchmark.

Independent recomputation matched all per-question scores and macro summaries.
All 120 RRF rankings were reconstructed from dense/full-text top-20 lists and
matched component ranks, scores and ordering. Exact index scope and all seven
public-table content fingerprints were unchanged. All 213 protected artifacts,
including sixteen earlier retrieval reports, were preserved. Twenty-three
diagnostic unit tests and the 120-question reference checker passed.

The existing stopped PostgreSQL container was started and left running; no
container recreation or corpus import was needed.

## Local artifacts

Raw reports and validation records are ignored local artifacts; preserve them
with the pinned source files when reproducing this comparison.

| Method | Raw report under `outputs/retrieval/` | SHA-256 |
| --- | --- | --- |
| dense | `dense-20261125T133729034758Z.json` | `4ef78984b03650659c181078438e8209ee6caf5d37cd300f9dc33c9904581700` |
| full-text | `full-text-20261125T133812795420Z.json` | `dbe8b7f49b8b0832035a7cbe10bebdf4f75f10af7ad6b59e09ba49e3d90b10f5` |
| hybrid | `hybrid-20261125T133826756751Z.json` | `edc745860cada8e3fdbd981165d58b8dd7806118791a2823a004a4406fbe4198` |

Dataset SHA-256:
`f03c1802d5da69274cf2397a58ef6077314050fc53955aee924703e041d4decc`.

Git HEAD was `2ca8d84140be90b6f3d592c01516a2df6aacd22a` with local changes;
each raw report pins the actual code/config/protocol hashes. Subsequent progress
updates to this documentation do not change those historical fingerprints.

Files prefixed `expanded-retrieval-comparison-20261125T133609Z`:

- `outputs/validation/`: `-preflight.json`, `-before.json`, `-analysis.json`,
  `-evidence-review.json`, `-postflight.json`, `-verify.py` and `-completion.json`.
- `outputs/retrieval/`: `-per-question.csv` (1,080 method/question/cutoff rows).
