# Document-question development subset

**Version:** `postgresql18-document-dev` / `1.0.0`, verified on 2026-11-06.
[document_questions.json](document_questions.json) contains P01–P06 from the
[pilot draft](../../../docs/PILOT_SCOPE.md), with unchanged question text and
source-verified English reference answers. The remaining 14 pilot questions
are still drafts. This is development data, not the held-out thesis test set.

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
```

The read-only checker verifies file hashes, source/snapshot/chunk identities,
block contents and positions, exact text spans, anchors, neighbor links and
claim-to-evidence references. It requires the saved local artifacts but no
model, tokenizer package, database or network access. It does not decide
whether an answer is semantically supported; that support was reviewed against
the saved source passages when the dataset was authored.

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
104 offline unit tests passed. No generated answers or final-test results exist.
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
