# Retrieval metric review against the local papers

**Reviewed:** 2026-11-24. **Scope:** the next dense/full-text/RRF development
comparison, before generation, reranking or agent orchestration.
This review recommends keeping the agreed six quality metrics plus retrieval
time. Additional candidates below are proposals, not implemented features or
changes to the owner-approved metric count. No retrieval or paid model run was made.

## Evidence inspected

The local collection contains 47 PDFs across three folders, with 44 distinct
byte hashes; these are not 47 independent studies. All were screened for metric
terms. The eight relevant papers below received targeted evaluation-section
review, not a complete systematic review. PDF page numbers are one-based.
Five pages from four core papers were also rendered and visually checked to
resolve two-column text order and table headings. Local versions govern this
table; in particular, MultiHop-RAG is the saved arXiv v1.

| Local paper / primary source | Verified location and measurement | Implication for this step |
| --- | --- | --- |
| [MultiHop-RAG](papers/rag-papers/06-MultiHop-RAG-Benchmark.pdf), [official v1](https://arxiv.org/html/2401.15391v1) | PDF pp. 3, 7; section 2.3 and Table 5: MAP@K, MRR@K and Hits@K; null queries excluded from positive retrieval scoring. | MRR has direct precedent. MAP is a useful optional ranking diagnostic. Its Hits definition must not be silently replaced with a binary any-hit definition. |
| [Is Agentic RAG worth it?](papers/rag-papers/10-Agentic-vs-Enhanced-RAG.pdf), [official paper](https://aclanthology.org/2026.acl-industry.5/) | PDF pp. 5-6; sections 3.3-3.4, Tables 4-5: nDCG@10 for query rewriting and document-list refinement. Section 3.5 evaluates generated answers separately. | Supports nDCG as a complementary retrieval-ranking metric; ranking scores do not establish answer quality. |
| [RAGChecker](papers/rag-papers/09-RAG-Diagnostics-RAGChecker.pdf), [official paper](https://proceedings.neurips.cc/paper_files/paper/2024/hash/27245589131d17368cccdfa990cbf16e-Abstract.html) | PDF pp. 4-5; sections 3.2-3.3.3: retriever claim recall and chunk-level context precision; generator faithfulness, noise sensitivity and hallucination are separate. | Required-claim coverage and context precision address different needs. Our annotation-based coverage is not the paper's claim-entailment evaluator. |
| [RAGAS](papers/rag-papers/08-RAG-Evaluation-RAGAS.pdf), [official paper](https://aclanthology.org/2024.eacl-demo.16/) | PDF pp. 3-4; section 3: context relevance is a ratio of LLM-selected useful sentences to context sentences; faithfulness and answer relevance concern generated answers. | Sentence-level context relevance is not another name for our chunk-ID precision. Defer this separate semantic judging pipeline; it is not required for the first rank-based comparison. |
| [ToolRet](papers/rag-papers/19-ToolRet-Retrieval-Benchmark.pdf), [official paper](https://aclanthology.org/2025.findings-acl.1258/) | PDF p. 5; section 5.1: nDCG@K, Recall@K, Precision@K and Completeness@K; completeness is 1 only when all target tools are retrieved. | Complete-support reporting is useful. Our all-requirements-supported rate fills a related document-evidence need, but is not tool-set Completeness@K. |
| [IRCoT](papers/rag-papers/02-IRCoT-Iterative-Retrieval.pdf), [official paper](https://aclanthology.org/2023.acl-long.557/) | PDF p. 5; section 4.1 and footnote 7: gold-paragraph recall under a maximum 15-paragraph budget; the authors explain why their unranked, variable-size iterative output does not use standard fixed-k ranking metrics. | Our fixed retrieval methods produce ranked lists, so cutoff metrics fit this step. Revisit output order and budget definitions before applying them to an iterative agent. |
| [HotpotQA](papers/rag-papers/23-HotpotQA-MultiHop-Questions.pdf), [official paper](https://aclanthology.org/D18-1259/) | PDF p. 7; section 5.2: answer EM/F1, supporting-fact sentence EM/F1 and joint answer/support scores. | Full evidence and answers deserve separate checks. Sentence support and joint answer grading require different annotations/outputs from this chunk-retrieval diagnostic. |
| [MuSiQue](papers/rag-papers/24-MuSiQue-MultiHop-Benchmark.pdf), [official paper](https://aclanthology.org/2022.tacl-1.31/) | PDF p. 8; section 6 and Table 3: human Answer F1 and Support F1; a separate answerability check for MuSiQue-Full. | Evidence coverage and answerability are distinct. Preserve separate negative reporting; do not infer successful abstention from a retrieval ranking. |

## Recommendation for the agreed plan

Keep these six metric types at 5/10/20: annotated-chunk recall, requirement
coverage, all-requirements-supported rate, Precision, MRR and binary-reference
nDCG. At the review date, the first three were implemented and the last three
were pending; see the implementation update below.
Record retrieval time separately. This is sufficient to start the controlled
retrieval comparison, not to establish final chatbot or thesis performance.

**MAP@K is optional.** It would add another view of ranking across relevant
items and improve direct comparability with MultiHop-RAG. Because nDCG already
assesses more than the first relevant result and complete-claim support is
reported separately, the current comparison does not require MAP as a seventh
quality metric. Adding it needs an explicit decision and versioned definition.

**Do not add Hits@K by name alone.** MultiHop-RAG section 2.3 describes it as
the fraction of evidence appearing in the retrieved set, resembling our
annotated recall. A binary question-level hit rate would instead ask whether
at least one reference chunk occurs in the prefix. That is a different formula
and cannot demonstrate that a multi-evidence question is fully supported.

**Keep full-support reporting.** ToolRet's strict target-tool coverage and
HotpotQA's support evaluation motivate checking completeness. Our metric uses
required claims with alternative/complementary evidence groups; retrieving
every annotated chunk is not necessary when an `any` group has alternatives.
Do not rename it as an exact reproduction of those papers' metrics.

## What matters more than increasing the metric count

1. Review the union of returned candidate chunks from all three methods using
   the same relevance/claim-support rules. Missing reference annotations can
   affect every reference-based score, including recall, MRR and nDCG. An
   unannotated chunk remains unjudged, not automatically semantically wrong.
   Preserve raw rankings; version accepted label additions and rescore all
   methods against the same labels.
2. Report PostgreSQL-only, Atlas-only and combined-question groups separately,
   alongside the answerable-question macro means. The 20 negative cases have
   no positive recall denominator and remain outside those means.
3. Retain retrieval-time observations and describe model warm-up/caching and
   measurement boundaries. Median/p95 summaries are a proposed reporting
   improvement, not a new retrieval-quality metric or a paper result.
4. Inspect the sum of stored chunk token counts for each returned prefix as a
   context-size diagnostic. Those counts use the embedding tokenizer; they are
   not Luna's actual input-token usage or a final shared context-budget decision.

Faithfulness, answer correctness/relevance, hallucination, noise sensitivity,
citation support and refusal quality belong to a later generation evaluation.
RAGChecker's semantic entailment and RAGAS's sentence extraction need their own
validated judging setup; implementing more rank formulas does not supply it.

## Resume boundary at the review date

The existing plan remains unchanged: implement and offline-test
Precision/MRR/nDCG with explicit short-result rules and a new measurement
version. Then verify the live shared index and run the same 120 questions
against dense/full-text/RRF. Carry out consistent alternative-evidence review
before interpreting reference-based scores as semantic retrieval performance.
MAP, binary hit rate, latency summaries and extra diagnostics are not added by
this review. No source, question, chunk, embedding or application code changed.

## Implementation update — 2026-11-25

The agreed six metrics are now implemented as `annotated-evidence-v2` /
schema 4; see the [formulas and edge cases](EVALUATION_PLAN.md#implemented-ranking-metrics--2026-11-25).
Precision/MRR/nDCG passed offline checks; the paper findings and metric count
are unchanged. MAP and the other optional diagnostics remain unimplemented.
The next step is the real same-input dense/full-text/RRF comparison, followed
by consistent alternative-evidence review. No expanded retrieval run has started.
