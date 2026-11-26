# Reranker thresholds and evidence sufficiency

**Reviewed:** 2026-11-26. The research and exploratory replay below preceded
implementation. The owner subsequently approved three independent comparison
modes, now implemented and offline-tested; see [current status](STATUS.md#evidence-checks-implemented--2026-11-26).
No winning policy or final threshold is selected. A subsequent
[three-question live sample](EVIDENCE_CHECK_SAMPLE.md) checks the implementation;
broader checker quality remains open.

## Two different policies

- **Question gate:** proceed only if the maximum of twenty reranker scores is
  at least the threshold. Passing retains the original top-five context.
- **Chunk filter:** discard each candidate below the threshold, then retain up
  to five in existing reranked order. This can remove required supporting evidence
  even when another chunk has a high score.

Neither policy alone establishes that the selected passages jointly support
every requested claim. Qwen's native implementation computes a two-class
yes/no softmax score; its 0–1 range does not establish calibration for our
corpus-level answerability labels. See the [official Qwen model card](https://huggingface.co/Qwen/Qwen3-Reranker-4B).

## Primary literature

- [Corrective Retrieval Augmented Generation](https://arxiv.org/html/2401.15884),
  sections 4.2–4.4 and appendix B.3: a separately trained T5 evaluator uses upper
  and lower thresholds to trigger Correct/Incorrect/Ambiguous retrieval actions.
  It also filters knowledge strips. Thresholds differ across datasets and its
  score scale is -1 to 1; its numeric values are not Qwen defaults.
- [Selective Question Answering under Domain Shift](https://aclanthology.org/2020.acl-main.503/),
  sections 3.1 and 4: a confidence threshold controls answering versus abstention.
  Evaluate risk (error among answered questions) versus coverage (fraction
  answered). The study finds overconfidence under domain shift and uses a
  calibrator. It concerns extractive QA answer confidence, not Qwen reranker
  scores; section 5.7 explicitly distinguishes identifying unanswerable questions
  from selective prediction under domain shift.
- [Sufficient Context](https://research.google/pubs/sufficient-context-a-new-lens-on-retrieval-augmented-generation-systems/)
  and its [official implementation](https://github.com/hljoren/sufficientcontext#-selective-generation-with-sufficiency--confidence):
  selective generation combines context-sufficiency information with model
  confidence and applies an abstention threshold. This is not a single raw
  reranker cutoff or proof that a pre-generation gate is infallible.

## Saved-score replay

Same pinned Qwen4B 120-question report, twenty candidates per question, dataset
v1.8 (100 answerable, twenty unanswerable). Only saved scores were inspected;
no model, DB, API or new answer generation ran. Exploratory thresholds:

| Threshold | Question gate: answerable passed /100 | Question gate: unanswerable passed /20 | Separate chunk filter: full annotated support @5 /100 |
| --- | --- | --- | --- |
| 0 (no cutoff) | 100 | 20 | 92 |
| 0.50 | 100 | 16 | 92 |
| 0.80 | 100 | 14 | 92 |
| 0.90 | 100 | 13 | 87 |
| 0.95 | 100 | 8 | 85 |
| 0.99 | 97 | 3 | 76 |

The first two result columns describe the question gate, not generated-answer
accuracy. The final column is a different experiment: filtering individual
chunks. Unannotated passages remain unjudged; support counts use existing
references, not exhaustive semantic relevance labels.

The lowest answerable top score is 0.963506; the highest unanswerable top score
is 0.998812. Thus no single maximum-score cutoff can both retain all 100
answerable questions and block all twenty unanswerable questions in this sample.
A cutoff can reduce unwanted passage flow without solving evidence sufficiency.

Source: `outputs/reranking/qwen4b-probe-20261125T202218873027Z.json`.
Replay/provenance: `outputs/validation/qwen4b-threshold-review-20261126.json`.

## Proposal, not a decision

Keep the unfiltered baseline. If adopting a threshold, first specify whether
it gates questions or filters chunks. Tune it on development/calibration data,
including difficult negatives and multi-evidence positives; count false passes,
unnecessary rejections and lost required evidence. Freeze the policy before
a separate held-out evaluation. Actual answer-level risk requires generation
results; the saved-score table cannot measure it. Recheck after changing the
model, instruction, corpus or candidate policy. No universal cutoff is endorsed.

## Alternatives review — 2026-11-26

The owner requested a broader literature/implementation review before applying
the proposed 0.95 question gate. It remains a trial candidate, not a configured
runtime policy. The following are distinct checks, with different inputs/labels:

| Approach | Checks | Evidence and limits | Fit for this project |
| --- | --- | --- | --- |
| Scope/metadata filters | Environment, source state, version or other known attributes | [Azure vector filters](https://learn.microsoft.com/en-us/azure/search/vector-search-filters) filter nonvector fields before/after retrieval. They require suitable metadata and can exclude useful evidence when scope is wrong. | Can prevent explicit environment/state mixing; allow shared PostgreSQL documentation and valid cross-source questions. No filter schema is implemented here. |
| Calibrated gate | Whether to answer, using labeled confidence signals | [Selective QA](https://aclanthology.org/2020.acl-main.503/) evaluates risk versus answered-question coverage. Its QA confidence/calibrator is not a raw Qwen score or a general unanswerability detector. | Useful comparison; additional calibration data cannot turn overlapping raw scores into a perfect separator. |
| Whole-context sufficiency | Whether the question can be answered from the selected passages together | [Sufficient Context](https://research.google/pubs/sufficient-context-a-new-lens-on-retrieval-augmented-generation-systems/) studies missing evidence separately from failure to use evidence. Its selective-generation system combines sufficiency with model confidence. | Most directly targets our distinction between relevant passages and enough evidence for every requested fact; local performance remains unmeasured. |
| Answer grounding/entailment | Whether generated claims follow from the supplied evidence and address the query | [AWS contextual grounding](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-contextual-grounding-check.html) separates grounding/relevance scores. [NeMo fact-checking](https://docs.nvidia.com/nemo/guardrails/configure-guardrails/guardrail-catalog/fact-checking) supports LLM self-checks and AlignScore. | Complementary post-generation validation; not proof of completeness, a correct source state or corpus-wide truth. Model checks can fail. |
| Corrective retrieval | Whether to refine evidence or retrieve again | [CRAG](https://arxiv.org/html/2401.15884) uses a trained evaluator, three action regions and web fallback. [Self-RAG](https://arxiv.org/html/2310.11511) learns retrieval/relevance/support critique behavior with trained reflection tokens. | A bounded internal retry is a later option; web search cannot supply authoritative fictional Atlas/Boreal facts. These papers do not establish a gain on our dataset. |

### What the primary sources establish

The [Sufficient Context author explanation](https://research.google/blog/deeper-insights-into-retrieval-augmented-generation-the-role-of-sufficient-context/)
uses sufficiency plus self-rated answer confidence for selective generation,
and reports a better selective accuracy/coverage trade-off than confidence
alone on its evaluated settings. This supports testing an additional signal;
it does not establish that an arbitrary pre-generation Luna checker will improve
this project or that sufficiency alone determines answer correctness.

[Self-RAG](https://arxiv.org/html/2310.11511) distinguishes passage relevance
from generated-statement support and uses specifically trained critic/generator
behavior. Borrowing those distinctions does not require claiming that our
prompted checks implement the published training/inference method.

[NeMo](https://docs.nvidia.com/nemo/guardrails/configure-guardrails/guardrail-catalog/fact-checking)
explicitly notes that self-check performance depends on the checking LLM.
Using the same model for generation and checking can share failure modes.
[Azure's ranker documentation](https://learn.microsoft.com/en-us/azure/search/semantic-search-overview)
also warns that score distributions vary with infrastructure/model updates.
These product documents describe supported mechanisms, not benchmark evidence
that one mechanism outperforms another on our corpus.

### Proposed experiment and implementation boundary

Keep the unfiltered Qwen4B baseline and the proposed maximum-score 0.95 gate
as explicit comparison conditions. The stronger *candidate*, by task fit,
is a separate whole-context sufficiency check with:

- the raw question and exactly the selected passages, without gold answers;
- a structured sufficient/partial/insufficient decision, evidence references,
  short supporting excerpts and identified missing facts;
- Python validation that cited IDs belong to the input and quoted text exists.
  Valid IDs/excerpts alone do not establish entailment or sufficiency;
- an explicit insufficient-evidence result when the checked evidence is inadequate.

For example, a Boreal lag question with only an Atlas lag policy should identify
the missing Boreal-specific policy instead of treating the related topic as
enough evidence. Correct identity/state must still be checked; the checker is
a fallible model, not a truth oracle.

First prepare the checker prompt/output contract and a small, manually reviewed
development sample containing hard negatives, straightforward positives and
multi-evidence positives. Test unfiltered / threshold-only / sufficiency-check
conditions with the same question/source state, initial top-five context,
final generator and answer prompt. Count wrong passes, unnecessary abstentions,
partial answers and grounding failures. Record all extra calls/cost/latency.
Test a 5-to-10 context expansion separately so its effect is not conflated with
the gate. Use a separate held-out evaluation after development choices are frozen.

At the review stage this was a proposal and no runtime behavior changed.
The subsequent owner-approved implementation adds the three explicit modes,
`sufficiency_v1`, literal quote validation, a saved-ranking runner and an Enhanced
context hook. The checker uses the existing Luna settings, requires explicit
paid-call opt-in. The later [three-question sample](EVIDENCE_CHECK_SAMPLE.md)
is reviewed; no comparative advantage is established. No fallback or new model is added;
Simple's final-answer path is unchanged. Whether to share the policy across
final study arms remains open. This research made no inference, DB or paid calls.
