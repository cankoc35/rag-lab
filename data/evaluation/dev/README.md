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

No retrieval/model-answer run was performed and the evaluation runner, scoring
metrics and final thesis protocol remain unimplemented or open. The
[local Nomic adapter](../../../docs/EMBEDDING_SETUP.md) has since passed a
document/query runtime check. PostgreSQL + pgvector and the four retrieval
tables now exist. Snapshot/chunk import code is prepared and verified with
rollback; committed import and corpus indexing are next before using these
questions for retrieval checks. See the
[session handoff](../../../docs/HANDOFF.md) for current state and local inputs.
