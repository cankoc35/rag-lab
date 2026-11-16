# Evaluation protocol — first draft

**Status:** Working draft, updated 2026-11-16. The owner approved the initial
Simple/Enhanced design, prior-knowledge controls and PostgreSQL
docs/synthetic-runbook pilot. Metrics, thresholds,
sample sizes, and the complete final protocol remain open. This is a planning
artifact, not a result. Read the [method design](METHOD_DESIGN.md) first.

**Language decision (owner, 2026-11-05):** Development and held-out questions,
corpus/synthetic documents, prompts, answers, gold answers and rubrics will
be in English across all arms. Multilingual/cross-lingual retrieval is not
part of the required scope. The remaining protocol choices are still open.

## Comparisons

- **Primary candidate comparison:** routed policy versus always-agentic on
  the same frozen questions. The acceptable answer-quality difference must be
  specified **before** examining final-test outcomes.
- **Other fixed policies:** always-simple and always-enhanced.
- **Approved diagnostic control:** LLM-only with no retrieved documents or DB
  tools; not an additional router target.
- **Question-type reporting:** direct document, multi-document, live-tool,
  document-plus-tool, and unanswerable. A single overall average can hide
  failures in the tool-dependent groups.
- Run all three arms offline on each question. The router must choose from
  allowed input signals only; it cannot inspect gold answers or arm outputs.

## Approved initial fixed-workflow comparison

**Owner decision, 2026-11-13:** Simple uses dense retrieval; Enhanced uses
dense + PostgreSQL full-text retrieval, RRF merge/deduplication and reranking.
Both document paths use one final-answer call. Enhanced's relevant tool calls
are controlled by predefined Python steps/conditions. Agentic details are
deferred; the full study's final protocol is still open. See the
[operational definitions](METHOD_DESIGN.md#approved-initial-simple-and-enhanced-design).

Hold corpus/snapshot/chunk state, dense embedding settings, generator/settings,
answer prompt and maximum context token budget constant across the fixed arms.
Measure the actual context tokens, retrieval/reranking latency and final-answer
quality; do not assume the extra retrieval stages improve quality or cost.

Use dense-only → hybrid-only → hybrid + reranking as development ablations.
The primary Simple/Enhanced comparison measures the combined enhancement;
component-level claims require the corresponding ablation. These conditions
do not create extra primary workflows. P01–P06 are initial development checks,
not a sufficient final benchmark or a held-out set.

Record retrieval variant, candidate/context counts, fusion settings and
reranker identifier/settings with the existing per-run records. Reranker,
generator and numeric budgets/parameters remain unselected. Future additions
must be versioned and assessed on development data before freezing final tests.
Tool-dependent cases still need fixtures/contracts and their separate reporting;
the document-path decision does not finalize the future tool workflow.

## Implemented development retrieval diagnostic

The owner approved checking P01–P06 at 5/10/20 on 2026-11-14.
[check_retrieval.py](../scripts/check_retrieval.py) now validates the pinned
references, retrieves each unchanged raw question once across the selected
index and records annotated evidence ranks/cutoff IDs with run provenance.
Two locked real-model runs matched. These are annotation-ID diagnostics,
not semantic correctness grades, finalized recall definitions or a held-out
experiment. Valid alternative evidence remains relevant. The cutoff sweep
does not choose a production context budget or change the five-result baseline.
See the [development results](../data/evaluation/dev/README.md#repeatable-retrieval-checker).

## Candidate metrics and definitions to finalize

| Metric | Proposed measurement | Decision still open |
| --- | --- | --- |
| Answer quality | Manually verified answer/rubric; record each arm's raw answer and judgment per question. | Binary correctness versus graded rubric; annotator/judge procedure; acceptable quality margin. |
| Evidence use | Compare cited document IDs and tool result IDs with verified required evidence. | How to score partially sufficient evidence and valid alternative sources. |
| Tool behavior | Log tool name, arguments, result, call order, and whether the call was useful/necessary. | Annotation rules for multiple valid tool paths. |
| Monetary cost | Sum billed LLM input/output, router calls, and paid tool/API calls per query; record price version. | Treatment of local compute, embeddings, and shared ingestion cost. |
| Latency | Wall time from question receipt through router and selected workflow to final answer; also report component times. | Warm-up, concurrency, network variability, retry and timeout rules. |
| Router decision | Compare selected arm with the set of arms meeting the quality criterion at lowest measured cost, for analysis only. | Whether this oracle-style comparison is included; never use test labels to tune the router. |

Report quality, cost, and latency separately before combining them into any
single score. A cost saving is meaningful only alongside the measured quality
change. No result or target percentage is assumed here.

## Per-run result record

**Development material, 2026-11-06:** P01–P06 have
[verified reference answers and pinned evidence](../data/evaluation/dev/README.md).
The evidence checker validates references/integrity, not answer correctness
or retrieval performance. These annotations do not finalize the scoring
rubric; no scored retrieval or answer-generation run has occurred. P07–P20 remain drafts.
The subsequent [embedding runtime check](EMBEDDING_SETUP.md) produced two
vectors; it reports no retrieval or answer-quality metric.

Each run should link a stable `run_id` and `question_id` to the workflow or
router policy; question type; dataset/corpus/live-state versions; generator,
router, embedding, and judge model IDs/settings; prompt versions; code commit;
source and tool IDs; raw answer; raw tool results; token usage; timings; prices;
errors/retries; judgment; and timestamp. Store raw outputs unchanged and
derive summary tables from them. Exact schema/storage location remains TBD.

**Owner decision, 2026-11-16:** Use project-owned PostgreSQL tracing instead
of MLflow. A question execution has a `trace_id` and its operations have
`span_id`s; the existing `run_id` remains the batch link. The
[two-table migration and writers](TRACING_PLAN.md) are applied following the
owner's explicit instruction. One real P04 trace/span and four DB tests passed.
The checker can link `--trace` executions to question records; default checks
remain read-only. No generated-answer/tool traces or quality grades exist yet.
Keep JSON experiment records and later judgments linked to those identities.

## Consistency checks before final testing

1. Use the same question and source snapshot for every compared arm.
2. Keep comparable model settings and shared retrieval/tool implementations.
3. Define metric calculations and exclusion rules on development data.
4. Freeze the final-test set and evaluation settings; record later deviations.
5. Recompute every reported aggregate from the saved per-run records.
6. Report per-type outcomes, paired differences, uncertainty, failures, and
   negative results.

## Candidate controls for prior knowledge — PostgreSQL corpus option

**Approach approved by the owner, 2026-11-01; detailed protocol still open:**
These controls address the possibility that the generator already knows public
PostgreSQL documentation. They do not establish what a model saw during
training, and do not change the router's action space.

- Add an **LLM-only control**, with no retrieved documents or DB tools. Keep
  the question, generator, comparable instructions, and generation settings
  fixed. Record per-question gains and regressions against the RAG arms.
  A correct LLM-only answer does not prove memorization; an incorrect answer
  does not prove lack of prior exposure. Keep LLM-only-correct questions in
  the frozen test rather than selecting only questions that favor retrieval.
- Keep ordinary PostgreSQL questions, and supplement them with
  newly authored, explicitly synthetic deployment runbooks and seeded sandbox
  DB fixtures. Ask separately about public docs, runbook-specific facts,
  DB-specific facts, and combinations. Do not rewrite PostgreSQL semantics or
  defaults to create artificial facts. The owner approved adding runbooks;
  exact source content and fixture definitions remain to be prepared.
- For selected scenarios, prepare paired source states with the same question
  but a changed relevant fact. For example, a synthetic deployment policy
  permits at most 5 seconds of replica lag; a frozen DB state reports 3 seconds
  in A and 12 seconds in B. The question explicitly asks whether the stated
  lag criterion is met, not whether failover is safe overall. Check that both
  answers are correct and supported by the corresponding policy and tool
  output. Store state IDs and gold evidence outside the model-visible question.
- Treat such paired checks as evidence of source-sensitive behavior, not proof
  that every correct answer uses retrieval. A citation or a logged tool call
  alone is also insufficient. Include insufficient-evidence cases and score
  appropriate abstention separately from useful, supported answers.
- Freeze every source state for comparisons; give enhanced and agentic arms
  comparable relevant tool access. LLM-only/simple inability to inspect hidden
  DB state is a capability limit, not evidence that dynamic control is better.
  Split related scenario/state variants together between development and test
  to reduce leakage; label these diagnostic checks separately in reporting.

Related primary work: [Fakepedia (ACL 2024)](https://aclanthology.org/2024.acl-long.369/)
studies contextual grounding under conflict with parametric knowledge;
[CRAG (NeurIPS 2024)](https://arxiv.org/abs/2406.04744) includes dynamic facts
and mock APIs. The PostgreSQL runbook/DB-state design above is our proposal,
not a reproduced protocol or a novelty claim. The rubric, sample sizes, and
whether to include an oracle-evidence diagnostic remain open.

## Open decisions

Corpus version/coverage and exact tools, verified question set, quality rubric,
judge procedure, sample size, primary quality margin, cost accounting, latency
protocol, and exact result schema. These must be decided before the final
experiment. See [PILOT_SCOPE.md](PILOT_SCOPE.md) for the development draft.
