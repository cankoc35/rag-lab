# Qwen reranker development results

**Measured:** 2026-11-25. The paired 0.6B/4B probe below covers four selected
questions. A subsequent full 120-question **4B-only** run is verified in the
final section. **Current owner decision:** continue with Qwen3-Reranker-4B
for the school project/demo. The observed wait is accepted; the earlier
10-second gate is withdrawn. Full-set 0.6B testing is optional.

The owner requested Qwen3-Reranker-0.6B after the 4B probe exceeded the
10-second per-question reranking budget. Its separate
[profile](../configs/reranker_qwen06b.toml) pins revision
`e61197ed45024b0ed8a2d74b80b4d909f1255473`; the original 4B profile is preserved.
The [official model card](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B)
describes the same native yes/no scoring approach used by the existing adapter.

## Controls and verification

- Same P05/P07/P27/P19 questions, version-1.8 references and saved RRF top-20 lists.
- Same native scorer, dependencies, MPS/float16 and sequential batch size one.
- Both models were run sequentially in this session, with one load per model.
- All 2,400 prepared input token sequences match the original 4B preparation;
  maximum 821 tokens, no truncation. Only 80 pairs per model were scored here.
- Reference answers/requirements never enter model inputs; no retrieval, DB,
  hosted model call or answer generation ran.
- The 0.6B weight file is 1,191,588,280 bytes (1.19 GB); its hash matches the
  pinned download metadata. Both models' weight hashes match their smoke reports.
- All 227 offline unit tests passed. Independent checks recomputed all six
  metric summaries and verified candidate/source preservation. The fresh 4B
  rankings reproduce the historical four-question ranking exactly.

## Per-question result

Support means the number of required claims with annotated evidence in the
first five chunks. It does not grade a generated answer.

| Question | 4B support @5 | 0.6B support @5 | 4B reranking | 0.6B reranking |
| --- | --- | --- | --- | --- |
| P05: PostgreSQL index/plan | 2/3 | 0/3 | 30.85 s | 6.86 s |
| P07: Atlas names | 2/2 | 2/2 | 25.20 s | 5.44 s |
| P27: combined query/index evidence | 3/3 | 3/3 | 31.13 s | 6.39 s |
| P19: missing Boreal policy | N/A | N/A | 24.41 s | 5.11 s |

The mean is **27.90 seconds for 4B versus 5.95 seconds for 0.6B**: 4.69x faster,
or 78.67% less scoring time in this sample. Totals are 111.60 versus 23.81 seconds.
Model loading is separate: 6.21 versus 0.33 seconds. These are one-pass local
measurements, including the first inference without a separate warm-up, not
end-to-end answer latency or a controlled cold-disk benchmark. No p95 estimate
or guarantee of future latency follows from four observations. Every measured
0.6B question stays below 10 seconds; the proposed 2–3-second target is not met.

## Quality at five

These means cover only the three answerable questions. P19 stays outside them.
Relevance annotations are not exhaustive; unannotated passages remain unjudged.

| Metric | 4B | 0.6B |
| --- | --- | --- |
| Annotated chunk recall | 0.7333 | 0.6667 |
| Required-claim coverage | 0.8889 | 0.6667 |
| Questions with all required claims supported | 2/3 | 2/3 |
| Precision | 0.3333 | 0.2667 |
| MRR | 0.8333 | 0.6667 |
| nDCG | 0.7380 | 0.6176 |

The equal 2/3 completeness count hides P05's partial-support loss. At ten, 0.6B
finds support for two of P05's three claims; at twenty it finds all three.
Both models preserve identical candidate sets and complete required-claim
coverage at twenty. P19 receives a high top score with both models despite the
missing Boreal policy; scores are not calibrated answerability probabilities
and cannot be compared across models as confidence in a correct answer.

## Artifacts and next step

- 0.6B smoke: `outputs/reranking/qwen06b-20261125T182911681519Z.json`.
- Token preparation: `outputs/reranking/qwen06b-20261125T182928798306Z.json`.
- 0.6B probe: `outputs/reranking/qwen06b-probe-20261125T183017359618Z.json`.
- Fresh 4B probe: `outputs/reranking/qwen4b-probe-20261125T183231798011Z.json`.
- Verified paired comparison: `outputs/reranking/qwen06b-vs-4b-20261125T183231798011Z.json`.

The 0.6B model met the earlier latency budget with a quality loss on the
difficult P05 case. Its broader quality remains unmeasured. A full-set
[0.6B comparison](COMMANDS.md#run-the-qwen06b-profile) is optional after the
owner selected 4B. No default or answer workflow changed during this paired
probe; preserve its results as historical development evidence.

## Batch-four follow-up

The owner subsequently requested [a Qwen4B batch-four command](COMMANDS.md#run-qwen4b-with-batch-size-four).
It is prepared with full inputs, left padding, attention masks and explicit
position IDs. The default stays batch one; schema-2 reports record batch size
and do not invent individual pair timings for a batched forward.

All 229 offline tests passed. A native P05 check preserved all twenty ranks and
quality metrics, with maximum score difference 0.003842. It took **46.36 s**
versus the earlier batch-one **30.85 s**; batching did not improve this observed
case. This single check is not a full batching benchmark. Report:
`outputs/reranking/qwen4b-probe-20261125T184838008770Z.json`; audit:
`outputs/validation/qwen4b-batch4-20261125T184838008770Z.json`.

## Full 120-question Qwen4B run

The owner's run completed at **23:22 Istanbul time on 25 November 2026**.
All 120 version-1.8 questions have twenty scored candidates: **2,400 pairs**,
MPS/float16, **batch size one**. The native scoring adapter, pinned model and
saved RRF candidates are unchanged. No new retrieval, DB access, hosted API
call or Luna answer generation ran.

Independent offline verification passed: dataset/config/source/code/lock hashes,
120 unique question IDs and raw text, exact candidate/source preservation,
finite sorted scores, all six per-question metrics and aggregate summaries,
negative exclusion, unchanged claim support at twenty and timing totals.
Recorded weight/tokenizer hashes match the prior pretrained smoke metadata;
this verification did not reload the model or rehash the 8-GB weights.

### Quality at five

Same questions, index and v1.8 annotations; means cover **100 answerable**
questions. The twenty unanswerable cases are separate. Percentages describe
annotated retrieval evidence, not generated-answer accuracy.

| Metric @5 | Dense | Full-text | RRF | RRF + Qwen4B |
| --- | --- | --- | --- | --- |
| Annotated chunk recall | 90.33% | 73.47% | 88.62% | 94.90% |
| Required-claim coverage | 91.17% | 73.00% | 88.67% | 96.33% |
| All required claims supported | 83/100 | 65/100 | 82/100 | 92/100 |
| Precision | 26.00% | 21.80% | 25.40% | 28.00% |
| MRR | 0.8622 | 0.5722 | 0.8040 | 0.9733 |
| nDCG | 0.8397 | 0.5720 | 0.7771 | 0.9402 |

Twelve questions gain full support at five and two lose it (P03/P64): net
**+10 questions** versus RRF. Required-claim coverage improves for fifteen
questions and declines for two. At ten, complete support rises from 93/100
to 100/100. At twenty, both remain 100/100: reranking reorders the same
candidates rather than retrieving new evidence. Reference annotations remain
non-exhaustive; these are development results, not a held-out comparison.

### Observed latency and next step

- Scoring total: **5,243.02 seconds (87 minutes 23 seconds)**; model load 6.58 s.
- Mean / median per question: **43.69 / 43.08 seconds**.
- p95: **58.91 seconds** (nearest-rank definition); range **26.23–63.32 seconds**.

These timings include first inference and exclude retrieval/generation. The
owner accepts the measured wait for a school project and a one- or two-question
demo, selects **Qwen3-Reranker-4B** and withdraws the earlier under-10-second
requirement. Continue recording timing; no new latency cutoff is imposed.
The four-question 0.6B probe is not a matched full-set comparison, and a full
0.6B run is optional. Next integrate selected 4B into Enhanced's document
retrieval path. Existing pinned settings and the batch-one default already
match the choice; live answer-workflow integration is still pending.

Raw report: `outputs/reranking/qwen4b-probe-20261125T202218873027Z.json`
(SHA-256 `f43ef09c008a7fefe88d39201c0f0accdab6958200b6d623a466940ee7560a4e`).
Independent verification:
`outputs/validation/qwen4b-full-20261125T202218873027Z.json`.
