# Luna evidence sufficiency: development checks

**Verified:** 2026-11-26. An initial three-question sample, eight selected
hard negatives and twelve sufficient-context positives, one live response each,
on saved Qwen4B top-five whole passages
from dataset v1.8. No new retrieval,
reranking, DB writes or final-answer generation occurred.

Settings: `gpt-6-luna`, reasoning `none`, maximum 1,000 output tokens,
`sufficiency_v1`, strict JSON, no gold answers or scores in the checker input.
The previously expired API key was replaced by the owner; the retry succeeded.

## Initial three-question results

| Question | Baseline | 0.95 gate | Luna assessment | After quote validation | Request time | Input / output tokens |
| --- | --- | --- | --- | --- | --- | --- |
| P07: Atlas database/schema names | Allow | Allow | sufficient | Allow | 4.73 s | 1,937 / 74 |
| P05: second-column filter and plan inspection | Allow | Allow | sufficient | Allow after offline revalidation | 3.23 s | 2,273 / 253 |
| P19: approved Boreal lag limit | Allow | Block | insufficient | Block after offline revalidation | 2.03 s | 1,758 / 136 |

P07 quotes S1's two explicit names. P05 cites conditional B-tree skip scan,
planner cost considerations and an EXPLAIN ANALYZE example; it does not invent
an observed Atlas plan. P19 identifies the missing Boreal-specific policy and
does not transfer Atlas's five-second limit. Assistant editorial review agrees
with these three evidence decisions; this is not a generated-answer grade.

Total reported usage: **5,968 input + 463 output = 6,431 tokens**, including
5,959 reported cache-write input tokens and zero cache hits. Total request time
was **10.00 seconds**, excluding retrieval/reranking/model loading. Billing was
not queried and no dollar estimate is inferred from token counts.

## Quote-validation repair

The original P07 report passed. P05/P19 returned completed, structurally valid
model responses but failed the original character-exact substring check:
Luna replaced source line breaks with spaces inside otherwise matching quotes.
These were operational validation errors, not model abstentions.

`whitespace_v1` now collapses whitespace for quote comparison only. It preserves
source text and raw model quotes, still checks the cited source, and rejects
changed words, numbers and punctuation. It checks attribution, not entailment.
The prompt and model settings are unchanged. Two regression tests cover the
formatting case and substantive quote changes; **254 offline tests passed**.

All three original responses were replayed through the updated checker offline,
with identical question, context, instructions, prompt and raw response asserted.
No additional hosted request was made after this repair. Original reports remain
unchanged; the replay records both the original and corrected validation decisions.

P05's saved annotation coverage remains 2/3 at five. Its S4 EXPLAIN ANALYZE
example is an unannotated alternative-support candidate, not an accepted new
reference. No dataset or benchmark metric was changed for this sample.

## Gate-passing hard negatives — 2026-11-26

The owner authorized all eight v1.8 unanswerable questions whose saved maximum
Qwen score is at least 0.95. Selection and expected blocking behavior were saved
before the calls. The same model/settings, prompt and `whitespace_v1` validator
were used without modification. Each question retained exactly the same five
chunks; neither scores nor gold labels entered the model input.

| Question | Missing fact | Maximum Qwen score | Luna decision |
| --- | --- | --- | --- |
| P30 | Actual backup-job success | 0.974043 | insufficient |
| P39 | Emergency promotion approver | 0.983085 | insufficient |
| P40 | Comparable measured execution times | 0.974821 | insufficient |
| P79 | Observed autovacuum setting at the requested time | 0.963780 | insufficient |
| P80 | Latest usable archive and snapshot time | 0.994358 | insufficient |
| P126 | Physical relfilenode identifier | 0.989347 | insufficient |
| P128 | Dated restore-drill verification results | 0.998812 | insufficient |
| P129 | Reclaimable table space measurement | 0.991875 | insufficient |

Baseline and threshold both allow all eight; the checker blocks all eight.
All responses completed, all quote/schema checks passed and no operational
errors occurred. Assistant editorial review of all selected passages agrees
with each identified evidence gap. Five quotes needed whitespace tolerance;
the existing repair worked directly in the live path without further changes.

Total request time: **19.20 seconds**; mean **2.40 seconds**, range **1.79–3.52**.
Reported usage: **15,815 input + 1,183 output = 16,998 tokens**, including 15,791
cache-write input tokens and zero cache hits. No final answers were generated;
no DB/model reranking or additional verification API calls were needed. Billing
was not queried.

## Sufficient-context positives — 2026-11-26

The owner authorized twelve answerable questions: four PostgreSQL-only, four
Atlas-only and four combined. Selection favored topic diversity and full
annotated top-five coverage. Assistant editorial review confirmed the actual
passages support every requested part before any model call. Selection, source
pins, support labels and expected decisions were frozen in a preflight report;
gold answers and editorial judgments stayed outside model inputs.

| Group | Questions | Model sufficient | Original runtime allows | Quote errors |
| --- | --- | --- | --- | --- |
| PostgreSQL | P42, P93, P99, P100 | 4 | 4 | 0 |
| Atlas | P36, P46, P56, P107 | 4 | 3 | 1 |
| Combined | P37, P48, P77, P122 | 4 | 3 | 1 |

Luna assessed all twelve contexts as `sufficient`; none returned `partial` or
`insufficient`. The original runtime permitted ten and blocked two as operational errors:

- **P36:** two S1 quotes omit Markdown bold markers around otherwise matching
  wording, including `**entire transaction**` and the retry limit.
- **P122:** an S3 quote starts with `This` while the source substring starts
  with lowercase `this` after `However,`. The words otherwise match.

The `whitespace_v1` validator used for these calls rejected both. Format-tolerant
comparisons were diagnostic only during that sample; no broader normalization was installed and neither error
was relabeled as a successful pass. All twelve provider responses completed.
After P36 stopped the first batch, the remaining seven independent questions
ran under the same fixed settings; P122 was last. No question was retried and
no prompt, runtime policy or source was changed during the sample.

The model made no evidence-insufficiency rejection in this sample, but the
workflow still blocked two sufficient contexts because of quote formatting.
Both outcomes must be reported; twelve `sufficient` model responses do not
mean twelve successful workflow results. Assistant editorial review agrees
that the selected contexts remain sufficient, including P77's hypothetical
lag values supplied in the question.

Total request time: **32.64 seconds**; mean **2.72 seconds**, range **1.98–4.66**.
Reported usage: **29,091 input + 1,734 output = 30,825 tokens**, including 29,055
cache-write input tokens and zero cache hits. No final answers, new retrieval,
reranking or DB access occurred. Application code was unchanged; ordinary unit
tests were not repeated. Frozen inputs/code, response/quote validation, report
hashes, group counts and usage sums were independently checked offline.

## Offline quote alignment repair — 2026-11-26

The owner authorized repairing P36/P122 using saved responses. The new
`source_span_v2` validator first tries literal and whitespace-tolerant matching.
If those fail, a limited search view ignores `**` markers and permits a model's
capitalized first letter to match a lowercase source letter. All remaining
letters, words, numbers and punctuation remain case-sensitive and exact. The
recovery must identify one unique span with word boundaries in the cited source;
ambiguous matches, altered facts and quotes belonging to another source fail.
This is not general Markdown rendering or unrestricted lowercasing of SQL.

`assessment` and the raw model response remain unchanged. New
`verified_evidence` contains the actual source substrings, preserving original
Markdown, casing and whitespace. Quote attribution does not prove entailment.

All **23 existing responses** were replayed through `assess_evidence()` offline,
with identical question/context, instructions, prompt, raw response and parsed
assessment asserted. All **61 verified quotes** are literal substrings of their
cited original text. Compared with the preceding reviews, only P36/P122 change:

| Cohort | Records | Current allows | Current evidence blocks | Validation errors |
| --- | --- | --- | --- | --- |
| Initial sample | 3 | 2 | 1 | 0 |
| Selected negative gate passes | 8 | 0 | 8 | 0 |
| Sufficient-context positives | 12 | 12 | 0 | 0 |

Original reports, including the two runtime failures, are preserved. This is a
subsequent validation repair, not a new model-quality experiment or rewritten
live result. No API call, model inference, DB access or reranking occurred.
**261 offline unit tests passed**, including changed numbers/negation, wrong
sources, ambiguous recovery, word-prefix removal and case changes inside SQL
values/quoted identifiers. Prompt/schema/model settings remain unchanged.

## Interpretation and next step

The initial three decisions equal the score gate's. The follow-up demonstrates
additional rejection of these eight selected negative gate passes. It does not
estimate overall accuracy: the sample was selected using known negative labels and several synthetic
policies explicitly state that observations are missing. There is one response
per question and no held-out or final-answer result.

The positive follow-up exposed quote-format failures; the subsequent versioned
offline repair resolves the two recorded cases without changing model decisions
or negative blocking. Broader/held-out evaluation is still needed. Next add
Enhanced's shared answer-generation path, honoring an explicit evidence mode;
reranker/checker DB spans follow separately. No default policy is selected.

## Local evidence

- P07: `outputs/evidence/evidence-sufficiency-20261126T190542214886Z.json`.
- P05: `outputs/evidence/evidence-sufficiency-20261126T190554878399Z.json`.
- P19: `outputs/evidence/evidence-sufficiency-20261126T190623012759Z.json`.
- Paired review and offline replay: `outputs/validation/evidence-sample-20261126.json`.
- Earlier editorial preparation: `outputs/validation/evidence-sample-preflight-20261126.json`.
- Eight-negative selection/context pins: `outputs/validation/evidence-hard-negatives-preflight-20261126.json`.
- All eight raw report paths: `outputs/validation/evidence-hard-negatives-runs-20261126.json`.
- Paired negative review/audit: `outputs/validation/evidence-hard-negatives-20261126.json`.
- Positive selection/context review: `outputs/validation/evidence-positives-preflight-20261126.json`.
- Positive raw paths: `outputs/validation/evidence-positives-runs-20261126.json` and
  `outputs/validation/evidence-positives-resume-runs-20261126.json`.
- Paired positive review/audit: `outputs/validation/evidence-positives-20261126.json`.
- Versioned offline repair/replay: `outputs/validation/evidence-quote-replay-20261126.json`.

These are ignored local artifacts, not guaranteed by a fresh clone. The review
preserves raw report hashes, original/replay code hashes, source checks,
quotes, usage and timing. See [commands](COMMANDS.md#compare-evidence-policies-on-saved-rankings).
