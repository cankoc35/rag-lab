# Reference review and offline rescoring

**Completed:** 2026-11-25. Development annotations are now version **1.8.0**.
The same saved dense/full-text/RRF rankings were rescored. Score changes come
from annotation corrections; there was no new retrieval or model execution.

## What changed

All 120 raw-question/requirement records were screened for alignment. Twelve
questions received targeted source-backed changes. The 120 IDs, raw English
questions, group/family labels, fourteen-source/151-chunk state and all twenty
negative records remain identical. The other 108 complete question records
are unchanged. Version 1.7.0 and all raw reports are preserved.

New references: [expanded_questions_v1_8.json](../data/evaluation/dev/expanded_questions_v1_8.json).
The [editorial change record](../data/evaluation/dev/reference_review_v1_8.json)
lists exact blocks, chunk IDs, reasons and before/after requirement definitions.

| Question | Correction |
| --- | --- |
| P05 | Accept two independently sufficient EXPLAIN-inspection passages for R3; keep the multicolumn/cost requirements. |
| P48 | Remove the redundant dependency on a different query's billing-state explanation; retain exact index DDL and PostgreSQL predicate implication. |
| P64 | Accept equivalent RR and Serializable passages while preserving separate stable-view, monitoring/guarantee and retry requirements. |
| P81 | Accept the documented LIMIT explanation for completion cost and early stopping; do not credit it as the complete startup definition. |
| P85 | Move unrequested contextual comparison to optional guidance; retain the exact raw-question requirement and source evidence. |
| P91 | Move unrequested contextual comparison to optional guidance; retain the exact raw-question requirement and source evidence. |
| P98 | Accept the explicit forced-autovacuum/unfrozen-XID-age paragraph as alternative wraparound-protection evidence; retain the static-table requirement. |
| P101 | The explicit automatic-index-creation paragraph suffices; the GiST syntax example is optional corroboration rather than an extra mandatory prerequisite. |
| P108 | Remove the unasked jsonb-type prerequisite and narrow R2 to the requested filter question; preserve index identity and exact no-filter evidence. |
| P116 | Remove redundant mandatory inspection-boundary evidence; retain the PostgreSQL GIN mechanism and local index/no-filter limitations. |
| P119 | Apply the same total-cost/early-stop evidence equivalence used for P81 to this combined question. |
| P122 | Separate the compound guarantee requirement into two necessary claims and apply the same equivalent RR/Serializable passages as P64. |

Ten source-span records were added and three redundant/unasked records removed:
202 evidence records over 135 distinct blocks / 73 distinct chunks globally.
The requirement count is now 251: two unasked comparisons became optional and
one compound requirement was split into two necessary claims. The existing
`any`/`all` schema and six metric formulas are unchanged. Optional guidance
references still belong to the annotated-chunk set, as in the original metric;
only mandatory requirements determine claim coverage and full support.

## Results

Full support means all mandatory annotated requirements have evidence among
the first k chunks, averaged over the 100 answerable questions.

| Method | @5 before → after | @10 before → after | @20 before → after |
| --- | ---: | ---: | ---: |
| Dense | 80 → 83 | 83 → 87 | 87 → 88 |
| Full-text | 60 → 65 | 81 → 85 | 90 → 95 |
| RRF | 77 → 82 | 90 → 93 | 96 → 100 |

All revised quality scores below are percentages; full-support counts above
also equal percentages because the positive denominator is 100.

| Metric | k | Dense | Full-text | RRF |
| --- | ---: | ---: | ---: | ---: |
| Recall | 5 | 90.33 | 73.47 | 88.62 |
| Recall | 10 | 92.77 | 89.40 | 94.75 |
| Recall | 20 | 94.17 | 96.02 | 98.55 |
| Claim coverage | 5 | 91.17 | 73.00 | 88.67 |
| Claim coverage | 10 | 93.83 | 89.50 | 95.83 |
| Claim coverage | 20 | 94.17 | 96.83 | 100.00 |
| Precision | 5 | 26.00 | 21.80 | 25.40 |
| Precision | 10 | 13.60 | 13.70 | 14.30 |
| Precision | 20 | 7.00 | 7.40 | 7.65 |
| MRR | 5 | 86.22 | 57.22 | 80.40 |
| MRR | 10 | 86.44 | 58.38 | 80.61 |
| MRR | 20 | 86.44 | 58.66 | 80.68 |
| nDCG | 5 | 83.97 | 57.20 | 77.71 |
| nDCG | 10 | 84.95 | 63.13 | 80.25 |
| nDCG | 20 | 85.44 | 65.00 | 81.55 |

Dense remains slightly ahead in full support at five (83 versus RRF 82). RRF
has greater required-evidence coverage at ten/twenty. Its 100/100 at twenty
is complete support under these revised development annotations, not measured
LLM answer accuracy. No answer or abstention was generated or graded.

Scores can decrease too: P05 full-text reference recall@5 falls from 2/3 to
2/5 because two valid alternative reference chunks enlarge its denominator.
The frozen raw ranking is identical. Across individual metric/cutoff entries,
46 scores decreased. Complete required support does not require retrieving
every interchangeable reference passage.

## Review boundaries

This is a single-editor development review informed by observed diagnostics.
It is not blinded, independent, exhaustive pooled relevance judging or a
held-out thesis evaluation. Unannotated candidates still remain unjudged.

- P21 retains its explicit Hash paragraph; no equivalent first-five explanation was accepted.
- P27 still needs the exact device-range SQL; the index definition cannot replace its filters.
- P81 still needs a complete startup-cost explanation; the LIMIT example supports only its second requirement.
- P98 insert-only/visibility passages were not accepted as universal substitutes for static-table and wraparound requirements.
- P64/P122 share equivalent isolation evidence; P81/P119 share equivalent cost evidence. All methods use the same labels.
- Final rubric, held-out allocation and candidate/context budgets remain open. Qwen4B was subsequently selected; see [current context](PROJECT_CONTEXT.md).

## Reproduce and inspect

Run from the repository root; this needs the saved files and existing Python
environment, with no DB, embedding model or API access:

```sh
PYTHONPATH=src .venv/bin/python -m scripts.rescore_retrieval \
  --dataset data/evaluation/dev/expanded_questions_v1_8.json \
  --report outputs/retrieval/dense-20261125T133729034758Z.json
```

Replace the report argument with the original full-text or hybrid report to
rescore that method. New reports use `report_type=retrieval_annotation_rescore`,
schema 1, and the unchanged `annotated-evidence-v2` measurements. They pin the
original report hash and revised dataset hash; rankings, query hashes and original
elapsed times are retained. Timing was not measured again.

| Method | Saved rescore report under `outputs/retrieval/` |
| --- | --- |
| dense | `dense-rescore-20261125T144825088536Z.json` |
| full-text | `full-text-rescore-20261125T144825081590Z.json` |
| hybrid | `hybrid-rescore-20261125T144825073382Z.json` |

Parent SHA-256: `f03c1802d5da69274cf2397a58ef6077314050fc53955aee924703e041d4decc`.
Revised SHA-256: `78d93eb0166eab9d32164ae849863150771b386c95b7cf7f79788b3d4da8b527`.

**Verification:** 222 offline unit tests and eleven reference-file checks passed.
All 360 raw rankings, query hashes and timings were unchanged. Original scores
were reproduced exactly; revised scores and summaries were independently
recomputed. All 232 protected local artifacts were preserved. No DB access,
API call, new retrieval, embedding, migration or reindexing occurred.

Local audit: `outputs/validation/reference-review-20261125T140656Z-verification.json`.
Original comparison: [version-1.7 results](EXPANDED_RETRIEVAL_COMPARISON.md).

Next: choose a reranker and its input-token handling, then evaluate the proposed
RRF top-20 → rerank → top-5 path against RRF top-5 and dense top-5 on these
same version-1.8 development annotations. Do not change the existing baselines.
