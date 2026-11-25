# Supervisor discussion materials

The pipeline was updated on **25 November 2026**. The folder retains its original
preparation date. These artifacts describe implementation status; they do not
change the experiment or finalize open design choices.

- [Pipeline PNG](pipeline.png): high-resolution image for slides, 4200 x 3000.
- [Pipeline PDF](pipeline.pdf): one-page vector diagram for zooming or printing.
- [Pipeline SVG](pipeline.svg): editable vector image.
- [Renderer](render_pipeline.py): diagram text, layout and export commands.
- [Earlier briefing PDF](supervisor-brief.pdf) and [Markdown](supervisor-brief.md):
  speaking notes from **23 November**, unchanged. Their counts and status predate
  the expanded corpus, 120-question evaluation and reranker probes; use the updated
  diagram for the current implementation boundary.

## Reading the diagram

**DONE** means implemented, **PARTIAL** means some components work, **NOT BUILT**
means planned, and **OPEN** marks an undecided choice. Green arrows connect
implemented components; dashed arrows show planned connections. Implemented
retrieval components inside Enhanced do not mean its answer workflow is built.

- **A. Preparation:** 14 selected sources become 151 chunks and Nomic vectors
  in the shared PostgreSQL/pgvector index. Earlier control states are retained.
- **B. Question time:** current CLI requests go directly to Simple. The future
  router selects one workflow; rules, classifier or LLM remain open. Simple uses
  dense top-five retrieval. Enhanced shows dense/full-text top-20, RRF fusion,
  the first 20 candidates, Qwen3 reranking and proposed answer-context selection.
  Qwen3-Reranker-4B and 0.6B have local probes; final model, context budget and
  complete workflow integration remain open. Shared DB tools and Agentic control
  are not built. Luna generation is implemented for Simple; a shared output
  validator is partial: completion/nonempty checks exist, citation checks are
  planned, and grounding/retry policy remains open.
- **C. Observability:** a trace records one question/workflow; spans record its
  operations. Simple retrieval and LLM calls record prompt, chunks/ranks, answer,
  usage and timing in PostgreSQL. Router, reranker, DB-tool and validator spans
  are not built. Reranker probes currently save separate JSON reports. Small
  timing comparisons are labeled as development evidence. The owner reported
  starting the 120-question 4B run; no completed full-set report was reviewed
  for this revision.
- **D. Offline evaluation:** separate from returning a user response. The six
  implemented summaries at 5/10/20 are annotated-chunk Recall, required-claim
  coverage, all-claims-supported rate, Precision, MRR and nDCG. Means cover 100
  answerable questions; 20 unanswerable cases are separate. These measure
  annotated retrieval evidence, not LLM answer accuracy. Unannotated passages
  remain unjudged; the held-out thesis protocol remains open.

## Regenerate and verify

From the repository root, with Python and `rsvg-convert` installed:

```bash
python3 docs/presentations/2026-11-23/render_pipeline.py
```

This overwrites only the three pipeline exports. The revised PDF was rendered
and visually inspected; SVG XML, page count, required labels, text bounds and
local Markdown links were checked. No model inference, API call, migration,
DB access or benchmark change was needed. Application tests were not repeated.

Sources: [STATUS](../../STATUS.md), [METHOD_DESIGN](../../METHOD_DESIGN.md),
[EVALUATION_PLAN](../../EVALUATION_PLAN.md), [HANDOFF](../../HANDOFF.md) and
[Qwen comparison](../../QWEN_RERANKER_COMPARISON.md), checked against the current
[workflows](../../../src/rag_workflow_lab/workflows/),
[retrieval](../../../src/rag_workflow_lab/retrieval.py) and
[tracing](../../../src/rag_workflow_lab/tracing.py) code.
