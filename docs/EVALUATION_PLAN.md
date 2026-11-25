# Evaluation protocol — first draft

**Status:** Working draft, updated 2026-11-25. The owner approved the initial
Simple/Enhanced design, prior-knowledge controls and PostgreSQL
docs/synthetic-runbook pilot. Metrics, thresholds,
final thesis sample sizes, and the complete final protocol remain open. This is a planning
artifact, not a result. Read the [method design](METHOD_DESIGN.md) first.

**Owner decision, 2026-11-23:** Prepare 100 answerable questions split 50
PostgreSQL-only, 30 Atlas-only and 20 combined, plus 20 unanswerable questions.
Broader topics and the source distribution are approved. The completed
[allocation matrix](RETRIEVAL_DATASET_PLAN.md) defines source/evidence coverage;
the current verified development set completes all 100 answerable plus 20 unanswerable questions. The four new PostgreSQL pages are
captured and the six expanded Atlas documents are authored/hash-pinned.
All fourteen sources have saved parser outputs and 151 verified chunks in a
shared Nomic embedding index. The unchanged ten questions now have
[revalidated expanded-scope references](../data/evaluation/dev/expanded_questions.json),
including P19's full-corpus absence review. Cumulative
[version 1.7.0](../data/evaluation/dev/expanded_questions_v1_7.json) completes
all 120 records, including P81–P130, while preserving the seventy inherited
records and source pins. All 23 topic budgets are met; all 120 are dev.
All six agreed development retrieval metrics are implemented as
`annotated-evidence-v2` / report schema 4; the
[expanded retrieval comparison](EXPANDED_RETRIEVAL_COMPARISON.md) completed
on 2026-11-25. The subsequent targeted reference review creates version 1.8.0;
all saved rankings have been rescored with the revised shared annotations.
Further relevance review, final held-out selection and scoring
remain open. Using this set for tuning requires
a separate held-out thesis set. Missing attributes and
runtime observations use explicit editorial reviews; entity scans alone do not
establish their semantic unanswerability. No expanded answer comparison has run.

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
- Run all three arms on each frozen question in the evaluation runner; hosted
  APIs may be used. Here "offline evaluation" means outside live user traffic.
  The router must choose from
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
reranker identifier/settings with the existing per-run records. Luna is the
initial generator client; reranker and final experimental budgets/settings
remain open. Future additions
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

The Atlas diagnostic was subsequently run on 2026-11-18 with explicit
`--dataset` and an exact index/snapshot/chunk/input scope check. All six positive
annotations across P07–P09 rank within the first three. P19 has no positive
evidence score; its returned Atlas policy text does not establish a Boreal
limit. This is a 12-chunk development check, with no answer/abstention grading
or LLM-only comparison. See the
[Atlas results](../data/evaluation/dev/README.md#atlas-retrieval-diagnostic--2026-11-18).

The [full-text development check](FULL_TEXT_RETRIEVAL.md) was completed on
2026-11-23 using the same pinned question/index pairs. Initial plain AND
returned no candidates in all eleven state observations; those reports are
preserved. English OR over normalized raw-question lexemes was then selected
on development data. At five results, P05 has 2/3 annotated evidence records
versus dense 0/3; other top-five counts match, although individual ranks can
worsen. No gold terms, query rewrite, RRF or answer generation were used.
P19 has no positive evidence score. P08's two states are related variants,
not independent test questions. This does not freeze the lexical policy,
establish general recall/answer quality or tune a held-out protocol.

The later [RRF development check](HYBRID_RETRIEVAL.md) uses equal method
weights, `k=60` and 20 candidates per method, selected before the live runs.
It combines unchanged raw-question results in the same pinned index scope.
P05 has 1/3 annotations at five and 2/3 at ten, versus dense 0/3 and full-text
2/3 at five; other top-five counts match. E3 is outside both candidate windows.
The mixed result is preserved without parameter retuning. Every fused score,
source rank and union was reconstructed from the saved component reports.
These are development defaults, not final thesis budgets or proof that fusion
improves answer quality. Reranking and answer-level comparisons follow later.

### Expanded development measurements — 2026-11-24

The owner authorized adapting the diagnostic to all 120 questions. The initial
reports used schema **3** and measurement version **`annotated-evidence-v1`**, with fixed
cutoffs **5, 10 and 20**. The dataset remains version 1.7.0; question text,
source state and retrieval settings are unchanged. These definitions govern
the next development comparison, not the final thesis scoring protocol.

For an answerable question, let `G` be the set of distinct annotated chunk IDs
and `R_k` the chunk IDs in its first `k` returned results:

| Report field | Definition |
| --- | --- |
| `evidence_chunk_recall_at_k` | `len(G & R_k) / len(G)`. Several evidence records in one chunk count once. This is annotated-chunk recall, not exhaustive semantic recall. |
| `requirement_ranks` | First rank at which the annotated support for each required claim is available. For `any`, the earliest returned supporting record suffices; for `all`, every selected record must be available, so use their latest rank. Missing necessary support gives `null`. |
| `requirements_supported_at_k` | Requirement IDs whose support rank is at most `k`. Two records from the same retrieved chunk can support an `all` requirement. |
| `requirement_coverage_at_k` | Supported requirements divided by that question's total requirements. This measures available annotated support, not whether an LLM expressed the claim correctly. |
| `summary.mean_evidence_chunk_recall_at_k` | Arithmetic mean of per-question annotated-chunk recall over answerable questions only. |
| `summary.mean_requirement_coverage_at_k` | Arithmetic mean of per-question requirement coverage over answerable questions only. Each question has equal weight. |
| `summary.all_requirements_supported_rate_at_k` | Fraction of answerable questions whose requirement coverage is 1 at `k`. |

Empty returned results give zero coverage for an answerable question. If fewer
than `k` chunks return, use that actual prefix without padding. A rank of `null`
means absent from the method's returned candidate set, not absent from the corpus.
The existing RRF candidate cap remains 20 per component; this measurement change
does not broaden its search or change Simple's five-chunk context.

The 20 unanswerable questions have `null` recall/requirement coverage and no
positive denominator. They remain separate records with their bucket, missing
fact/absence review and full returned ranking. Related text is not a retrieval
failure, nor does an empty result prove successful abstention. Answer-level
abstention and unsupported-claim grading require a later generation check.
An all-negative report has `null` positive means rather than zero or 0/0.

For positives, `alternative_evidence_review` lists returned, unannotated chunk
IDs at each cutoff with status `not_reviewed`. Unannotated does not mean wrong;
the existing annotations are not exhaustive. Open candidate text from the
pinned local chunk files and review it against the required claims. Save manual
notes separately with dataset/report hashes, question/chunk IDs, supported
requirement IDs and reasoning; keep raw reports unchanged. Review candidates
across all methods consistently. An accepted reference addition needs a new
annotation version and the same rescoring across methods; this script does not
automatically accept alternatives or infer semantic sufficiency from keywords.

Old `evidence_ranks` and `evidence_hits_at_k` remain for reference-ID inspection;
they are not deduplicated metrics and must not be averaged as chunk recall.
Old reports are preserved. Reports also retain question type, primary bucket
and scenario family for later grouped review. Measurement version and the
SHA-256 of this document join the existing dataset/code/index provenance.
No live expanded comparison ran while implementing these measurements.

### Agreed metric extension — 2026-11-24

The owner agreed to retain six development retrieval-quality metric types,
each reported at **5, 10 and 20**, plus retrieval elapsed time separately.
The intended comparison table therefore has **18 quality scores per method**;
latency is a seventh measurement type, not another cutoff-based quality metric.

Implementation status below is current as of 2026-11-25.

| Quality metric | Implementation status | Purpose |
| --- | --- | --- |
| Annotated-chunk recall | Implemented | Fraction of distinct reference chunks retrieved. |
| Requirement coverage | Implemented | Fraction of required claims with available annotated support under any/all rules. |
| All-requirements-supported rate | Implemented | Fraction of answerable questions with complete required-claim support. |
| Precision | Implemented 2026-11-25 | Fraction of the fixed top-k positions occupied by distinct reference chunks. |
| MRR | Implemented 2026-11-25 | Average reciprocal rank of the first reference chunk within the cutoff. |
| nDCG | Implemented 2026-11-25 | Ranking quality relative to the ideal reference ordering, rewarding reference chunks near the top. |

Recall and claim support remain the main evidence-availability measures;
Precision, MRR and nDCG are complementary diagnostics. MRR alone cannot show
that every claim of a multi-evidence answer is supported. Retrieval elapsed
time is already recorded per question. Saving the agreement on 2026-11-24 did
not change code; the extension was implemented on 2026-11-25 as described below.

Initial new scores must be labeled **reference-based**: current positive
annotations do not enumerate every valid passage. An unannotated chunk is
unjudged, not automatically semantically irrelevant; annotation gaps can affect
all these metrics. Start with binary reference relevance for nDCG; graded
relevance labels are not prepared. The 20 unanswerable questions stay outside
positive-quality averages, with separate context/answer-level review.

**Resume order:** check the live index scope and run dense/full-text/RRF with
the implemented six metrics on the same 120 raw questions
and 151-chunk index. Review alternative evidence consistently across methods;
version accepted reference additions and rescore all methods against the same
labels. Preserve raw reports. No new LLM calls are needed to compute the metrics.
Final held-out selection, semantic judging and thesis scoring remain open.

The [local-paper metric review](RETRIEVAL_METRIC_REVIEW.md), completed on
2026-11-24, recommends keeping this six-metric plan for the first comparison.
MAP@K is optional; paper-specific Hits/completeness definitions are not
interchangeable with ours. Consistent alternative-evidence judgments and
grouped results take priority over adding more metric names. These review
recommendations add no metrics or implementation changes.

### Implemented ranking metrics — 2026-11-25

`check_retrieval.py` now writes schema **4** with measurement version
**`annotated-evidence-v2`**. The original three metric definitions, raw inputs,
cutoffs, corpus/index scope and retrieval settings are unchanged. Old reports
remain immutable. No dependency or database schema change is needed.

Use the same set `G` of distinct annotated chunk IDs. An unannotated chunk is
not counted as a reference hit; this is a reference-based scoring convention,
not a semantic irrelevance judgment. Duplicate evidence records never give a
chunk extra gain. With one-based returned rank `r`, binary relevance is 1 for
reference chunks and 0 otherwise in these calculations.

| New per-question field | Formula / rule | Batch summary |
| --- | --- | --- |
| `evidence_chunk_precision_at_k` | `len(G & R_k) / k`, always dividing by the requested cutoff. | `mean_evidence_chunk_precision_at_k` |
| `reciprocal_rank_at_k` | `1 / r` for the first reference chunk if `r <= k`; otherwise 0. This is reciprocal rank for one question, not MRR yet. | `mean_reciprocal_rank_at_k` is MRR@k. |
| `ndcg_at_k` | `DCG_k / IDCG_k`, with `DCG_k = sum(1 / log2(r + 1))` over reference hits at ranks `r <= k`. `IDCG_k` puts `min(k, len(G))` reference chunks at consecutive ranks starting at 1. | `mean_ndcg_at_k` |

Short results are not padded with fake chunks. Precision nevertheless uses
fixed `k`: two returned reference chunks yield P@5 = 2/5. If those are all
reference chunks and occur at ranks 1 and 2, recall and nDCG can both be 1.
IDCG uses the total unique reference count, not only the hits returned, so
missing references do not artificially make nDCG perfect. At a cutoff below
the total reference count, IDCG is limited to that cutoff.

An answerable question with no returned references has zero for all three new
scores. A reference beyond the cutoff contributes nothing at that cutoff.
The 20 unanswerable questions have `null` values and are excluded from positive
means; all-negative batches have `null` means. Every answerable question has
equal weight. The five mean fields plus all-requirements-supported rate give
six quality summaries at three cutoffs: 18 scores per method. Retrieval elapsed
time remains a separate per-question observation.

Twenty-three diagnostic unit tests passed, including hand-calculated examples,
rank/cutoff boundaries, duplicate references, short/empty results, ideal-gain
normalization and negative exclusion. All 120 questions also passed fixture
checks through each method, without a model or DB. These are implementation
checks, not measured retrieval results. The subsequent measured run is recorded below.

### Expanded retrieval run — 2026-11-25

Dense/full-text/RRF each retrieved all 120 raw version-1.7.0 questions from
the same exact 151-chunk index, with the definitions and settings above frozen.
All six metrics at 5/10/20 were independently recomputed. Positive means cover
100 answerable questions; 20 negatives remain unscored. Full reference support
at five is 80/60/77 of 100 for dense/full-text/RRF; at twenty it is 87/90/96.
These are annotated-support results, not answer accuracy or final-study estimates.

The [comparison record](EXPANDED_RETRIEVAL_COMPARISON.md) preserves raw report
hashes, descriptive timing, group results and targeted alternative-evidence notes.
No source, question, reference or retrieval setting changed. P108/P116 have
proposed requirement corrections; other questions have candidate equivalent
passages. They were unapplied in the original run. The subsequent version-1.8
review and common rescoring are recorded below; original rankings stay frozen.
No Luna call or trace write ran; all DB table fingerprints were preserved.
The reports pin this protocol's pre-run hash; subsequent progress edits are
documentation changes, not retroactive measurement changes.

### Reference revision and offline rescoring — 2026-11-25

[Version 1.8.0](../data/evaluation/dev/expanded_questions_v1_8.json) preserves
the 120 raw questions, source state, bucket/family labels and twenty negative
records. An alignment screen covered all 120; twelve questions received
targeted source-backed corrections. Ten equivalent evidence records were added,
three unasked/redundant records removed, two comparisons made optional and one
compound guarantee requirement separated into two necessary claims. Counts are
251 requirements and 202 evidence records; the schema/formulas remain unchanged.
The [change record](../data/evaluation/dev/reference_review_v1_8.json) explains
every accepted span and before/after requirement. No automatic semantic acceptance
or exhaustive pooled judging is claimed; this is a single-editor development review
informed by observed retrieval results.

`python -m scripts.rescore_retrieval` validates the revised dataset and its pinned
parent, requires unchanged queries/scope/negative records, and applies the same
measurements to saved ranks. It writes a new schema-1 `retrieval_annotation_rescore`
report with parent-report/revised-dataset hashes and measurement version
`annotated-evidence-v2`. Original queries, rankings and timings remain unchanged;
no DB/model access or new timing run occurs. Raw reports are immutable.

The [rescored comparison](REFERENCE_REVIEW.md) gives full support @5 of 83/65/82
and @20 of 88/95/100 for dense/full-text/RRF. These changes result from labels,
not improved retrieval execution. Individual recall/ranking scores can decrease
when references are added or redundant references removed. Equivalent reference
passages need not all be retrieved to support every required claim. RRF's 100/100
at twenty is complete annotated support on this development set; answer accuracy,
abstention and held-out performance remain unmeasured here.

### Qwen4B development feasibility probe — 2026-11-25

The local MPS/float16 probe uses unchanged saved RRF top-20 candidates and
version-1.8 references. P05 (known difficult PostgreSQL), P07 (Atlas lookup),
P27 (combined evidence) and P19 (unanswerable) were selected before inference
to exercise the path, not estimate general quality. Only raw question text,
heading paths and whole chunk bodies enter scoring. All candidates and source
fields are retained, with original RRF ranks, new scores and measured times.
The same six metrics at 5/10/20 apply; P19 remains outside positive means.
No score threshold, generator or workflow change was selected. The
[probe results](QWEN_RERANKER_SETUP.md#saved-candidate-probe--2026-11-25) precede
the complete 120-question comparison. Original baselines remain immutable.

### Paired Qwen0.6B/4B development check — 2026-11-25

The owner requested the smaller Qwen model after requiring reranking below
10 seconds per question. Both models used the same four selected questions,
saved top-20 candidates, raw input token sequences, version-1.8 labels, native
scorer, dependencies, MPS/float16 and batch size one. A fresh 4B run reproduced
the historical ranking. Cold-process model loading is recorded separately;
scoring includes first inference without a separate warm-up. The
[paired result](QWEN_RERANKER_COMPARISON.md) shows lower latency with a P05
support loss. These four observations do not estimate p95, held-out quality
or answer accuracy. No threshold, production winner or final protocol was
selected; the complete 120-question 0.6B comparison remains next.

### Batch-four preparation — 2026-11-25

The probe's batch size is now explicit (default 1). Batch-four inputs retain
the same question text, whole documents, candidate order and per-pair scores;
left padding, attention masks and position IDs isolate the inputs. Schema-2
reports record batch size and actual question time; per-pair times are null
when not individually measured. A native P05 verification preserved all ranks
but took 46.36 seconds versus the earlier 30.85-second batch-one observation.
This is one correctness/runtime check, not evidence that batching is faster.
Four-question and full-set batch-four measurements remain unrun.

## Candidate final-study metrics and definitions to finalize

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
rubric. This describes the annotation-preparation step; later Simple/LLM-only
development runs are recorded below. P07–P09/P19 now have a separate verified
Atlas subset; P10–P18/P20 remain drafts. Atlas retrieval has now run; its answer
comparison and abstention checks were subsequently completed as recorded below.
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
remain read-only. One later Simple P04 answer has retrieval/LLM spans under
one trace, with exact prompt/source map, output and reported usage. Both
mandatory requirements and optional guidance passed post-run editorial review;
this is not a benchmark grade. Tool traces remain future work. The later
Simple P01–P06 batch completed and was independently
checked; post-run editorial review found four answers meeting recorded
requirements and P03/P05 partial. This is development review, not a frozen
judging protocol or evidence of retrieval's causal contribution. The later
live LLM-only batch was independently verified and compared in a
[paired editorial review](LLM_ONLY_COMPARISON.md). Dedicated insufficient/
changed-evidence controls and broader evaluation remain open.
See [STATUS](STATUS.md) for the records and remaining controls.
Keep JSON experiment records and later judgments linked to those identities.

## Consistency checks before final testing

**LLM-only control, 2026-11-17:** `run_llm_only.py` selects the same
raw questions without reading corpus/index artifacts. `llm_only_v1` permits
prior knowledge and labels the task PostgreSQL 18, matching the documentation
version available in Simple's context. Both use Luna, reasoning `none`, a
1000-output-token maximum, concise English, uncertainty instructions and no
tool execution. The instruction texts intentionally differ: Simple requires
supplied evidence/citations, while LLM-only receives no sources and can use
prior knowledge. Record both prompt versions rather than claiming identical
instructions. Each control attempt has one trace/LLM span with `sources: []`;
DB access is logging only, and no tools/history/gold enter the request.
The first live P01–P06 comparison is recorded in
[LLM_ONLY_COMPARISON](LLM_ONLY_COMPARISON.md): Simple meets the recorded
requirements on four questions, LLM-only on three. This small non-blind
development review does not freeze the judging protocol or establish causality.

**Atlas follow-up, 2026-11-18:** Both runners now accept `--dataset`; Simple
requires the complete pinned index scope and LLM-only still reads no corpus.
With unchanged questions, prompts and generator/settings, all eight calls
completed. Post-run requirement review found Simple P07/P08 complete and P09
partial because the reporting role was not explicit; LLM-only honestly abstained
on all three answerable questions. Both appropriately abstained on P19 without
assigning an Atlas limit to Boreal. Review criteria were recorded before calls.
See the [paired Atlas results](LLM_ONLY_COMPARISON.md#atlas-source-specific-comparison--2026-11-18).
This records practical source access in one small pair, not general accuracy
or an identical-prompt causal retrieval ablation. Preserve the role omission
and both raw outputs. The source-change control was still pending at that stage.

**Changed-evidence follow-up, 2026-11-23:** The owner authorized a complete
one-question document-state pair. Atlas v2 changes the lag limit from 5 to
8 seconds inclusive, with consistent boundary examples and version metadata.
P08 wording, `answer_v1`, generator/settings and the dense top-five workflow
stay fixed. Its full v2 source scope is pinned in a separate dataset/index;
v1 and all earlier results are preserved. Two new Simple calls return the
corresponding inclusive limit with supported S1 citations. Exact prompt/source/
response/usage persistence and scope isolation passed read-back checks.
Review requirements were recorded before calls. This is one development
source-sensitivity check; it does not establish universal grounding, training
membership or general accuracy. No new LLM-only call was needed for this
document-change pair. See [CHANGED_EVIDENCE_CHECK](CHANGED_EVIDENCE_CHECK.md).

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
  defaults to create artificial facts. The first two Atlas documents are
  authored in `data/corpus/synthetic/`, version 1.0/state `atlas-docs-v1`.
  Offline local snapshot/parsing and token measurement/chunking are verified.
  P07–P09/P19 reference verification is complete in a separate Atlas subset.
  P19 has no positive evidence IDs and a complete two-document absence review;
  its raw question omits the draft's answer-disclosing clause. Atlas snapshots/
  chunks are now imported and embedded in a separate verified Atlas-only index.
  The Atlas retrieval diagnostic has run with all positive annotations in the
  top three. The first paired answer/abstention check has also run; changed
  broader checks and DB fixtures remain. The later v1/v2 P08 document-change
  pair is complete as recorded above; additional state pairs remain open.
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
