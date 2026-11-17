# Simple RAG vs LLM-only: first development comparison

**Run date:** 2026-11-17. Six unchanged development questions, one generation
per condition. All 12 calls completed. Findings below are a non-blind post-run
editorial comparison against the existing answer requirements, not a frozen
judging protocol, a held-out accuracy estimate or an LLM-judge score.

## Setup

Both conditions used `gpt-6-luna`, reasoning `none`, maximum 1000 output tokens,
Standard processing, zero retries and the same question text/dataset hash.

| Condition | Evidence and instructions | Recorded operations per question |
| --- | --- | --- |
| Simple RAG | Five whole retrieved chunks; `answer_v1` requires evidence-backed citations | One retrieval span and one LLM span |
| LLM-only | Raw question only; `llm_only_v1` permits prior knowledge and labels the task PostgreSQL 18 | One LLM span; no documents/tools/history |

PostgreSQL 18 is available to Simple through its source context. The prompts
and input formatting intentionally differ; this is not an identical-prompt
retrieval ablation. No question-specific answer hints or reference answers
were sent in either condition. LLM-only's missing citations are not penalized.

## Answer findings

“Meets” means the answer covers the recorded mandatory claims. “Partial”
includes correct but incomplete answers; it does not mean the whole answer
is false. The earlier Simple review is preserved unchanged.

| Question | Simple RAG | LLM-only | Main observation |
| --- | --- | --- | --- |
| P01: EXPLAIN vs ANALYZE | Meets | Meets | Both distinguish estimates from actual execution and say ANALYZE executes the query. |
| P02: leading B-tree columns | Meets | Partial | LLM-only explains the general leftmost-column benefit, but omits the leading-equality/first-inequality range rule that Simple provides. |
| P03: partial-index predicate | Partial | Partial | Both explain implication/recognizability; neither explicitly separates eligibility from planner selection. Simple had the missing distinction in retrieved S3. |
| P04: NULL replay_lag | Meets | Partial | Both reject numeric zero. LLM-only does not explicitly explain a fully caught-up idle standby and omits the optional monitoring-presentation distinction. |
| P05: filtering only created_at | Partial | Meets | LLM-only explains conditional index use, PostgreSQL 18 skip scan, costs and EXPLAIN. Simple lacked PG-MULTI evidence and explicitly acknowledged the composite-index gap. |
| P06: Seq Scan with partial index | Meets | Meets | Both distinguish eligibility from cost-based selection and give sensible Seq Scan cases. |

The descriptive completeness counts are **4/6 for Simple** and **3/6 for
LLM-only** under these recorded requirements. These are not general accuracy
rates. Simple is more complete on P02/P04; LLM-only is more complete on P05;
both are partial on P03. Added advice beyond the recorded claims was not
independently given a separate exhaustive expert grade.

## Observed usage and latency

| Measure, six questions | Simple RAG | LLM-only |
| --- | ---: | ---: |
| Input tokens | 15,328 | 523 |
| Output tokens | 457 | 621 |
| Total tokens | 15,785 | 1,144 |
| Reasoning tokens | 0 | 0 |
| Cache-read tokens | 0 | 0 |
| 30-minute cache-write input tokens | 15,310 | 0 |
| Workflow batch seconds | 19.262 | 19.031 |
| Estimated Standard token cost, USD | 0.00214405 | 0.0003628 |

Input/cache token categories are disjoint, and reasoning tokens are already
included in output. Estimates use the checked [Luna rates](https://developers.openai.com/api/docs/models/gpt-6-luna)
and [cache pricing rules](https://developers.openai.com/api/docs/guides/prompt-caching),
excluding taxes/other services; they are not invoices. DB cost stays NULL.
Simple's duration excludes model loading; both rows measure workflow-only
execution. With one separate batch each, the similar times do not establish
a latency advantage. LLM-only used much less input, but generated more output.

## Interpretation and next proposal

Luna can provide substantial PostgreSQL knowledge without our supplied
documents, including the full P05 skip-scan explanation. This does not prove
it memorized the questions or the selected corpus. The current evidence-only
Simple policy can leave an answer partial when retrieval misses needed
passages, even where the model can supply an answer in the own-knowledge control.

In this pair, retrieved evidence is associated with more complete P02/P04
answers, while P05 exposes a retrieval gap and P03 exposes an answer omission
despite available evidence. Do not conclude that RAG is universally better,
that retrieval is unnecessary, or that these differences have one proven
cause: the sample is small, outputs are stochastic and instructions differ.

Keep all six questions, including LLM-only-correct questions, and preserve
both raw baselines. The proposed next small step is one explicitly synthetic
PostgreSQL runbook with source-specific facts, followed by changed/missing-
evidence checks. Such cases test source sensitivity beyond public factual QA.

## Records and integrity checks

- Simple run: `simple-20261117T183619008413Z`.
- LLM-only run: `llm-only-20261117T191359474642Z`.
- Raw reports: corresponding JSON files under `outputs/answers/`.
- Independent control checks: `outputs/validation/llm-only-20261117T191359474642Z.json`.
- Paired raw answers, per-requirement notes and calculations:
  `outputs/comparisons/simple-vs-llm-only-20261117T191359474642Z.json`.

A fresh read-only connection verified six new LLM-only traces/six LLM spans,
exact raw-question inputs, empty sources, prompt/settings, outputs and usage.
No retrieval spans were created. Public totals are 14 traces/21 spans;
corpus/index, older traces and the Simple raw report are unchanged. The run
changed no application code, prompt, dataset or migration. The 159 offline
unit and 21 DB integration checks remain prior verification; they were not
repeated for this execution/documentation-only step.
