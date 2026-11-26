# Supervisor discussion materials

The pipeline was updated on **25 November 2026**. The folder retains its original
preparation date. These artifacts describe implementation status; they do not
change the experiment or finalize open design choices.

- [Target full-flow PNG](full-flow.png) (3840 x 2160, 16:9 for slides),
  [PDF](full-flow.pdf), [SVG](full-flow.svg) and [renderer](render_full_flow.py),
  added 26 November, updated 27 November: see [the target flow](#target-full-flow) below.
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
  Qwen3-Reranker-4B is selected after its verified 120-question run: top-five
  full claim support rises from 82/100 to 92/100. The owner accepts the
  43.69-second mean for the school project/demo and withdraws the earlier
  10-second gate. Batch one remains the default; full-set 0.6B testing is
  optional. Context budget and complete workflow integration remain open.
  Shared DB tools and Agentic control
  are not built. Luna generation is implemented for Simple; a shared output
  validator is partial: completion/nonempty checks exist, citation checks are
  planned, and grounding/retry policy remains open.
- **C. Observability:** a trace records one question/workflow; spans record its
  operations. Simple retrieval and LLM calls record prompt, chunks/ranks, answer,
  usage and timing in PostgreSQL. Router, reranker, DB-tool and validator spans
  are not built. Reranker probes currently save separate JSON reports. Small
  timing comparisons are labeled as development evidence. The completed
  120-question 4B report is verified and summarized; reranker integration is
  still partial and no new model/DB/API work ran to update the diagram.
- **D. Offline evaluation:** separate from returning a user response. The six
  implemented summaries at 5/10/20 are annotated-chunk Recall, required-claim
  coverage, all-claims-supported rate, Precision, MRR and nDCG. Means cover 100
  answerable questions; 20 unanswerable cases are separate. These measure
  annotated retrieval evidence, not LLM answer accuracy. Unannotated passages
  remain unjudged; the held-out thesis protocol remains open.

## Target full flow

The full-flow image shows how the **finished** system is intended to answer one
question: user question → workflow router → Simple, Enhanced or Agentic RAG →
answer context → Luna answer generation → output validation → final answer.
Enhanced is drawn in detail: dense and lexical top-20 retrieval, RRF fusion,
Qwen3-Reranker-4B over the fused top 20, top five, an evidence check and planned
fixed DB-tool steps. The evidence check (`threshold_sufficiency`) first requires a
best Qwen score of at least 0.95 and then a Luna `sufficiency_v1` verdict of
`sufficient` with Python-verified source quotes. Otherwise Enhanced returns a
fixed "insufficient evidence" answer without an answer call.
Bottom strips show the offline data layer (document index, frozen sandbox DB,
models) and tracing. Evaluation metrics are left to the detailed pipeline above.

It is a target design, not a result. Solid green boxes are built and checked;
dashed gray boxes are planned; **OPEN** marks undecided choices (router method,
tool conditions and order, context budget, grounding/retry, sandbox fixtures).
Enhanced's evidence check and answer connections are built and offline-tested,
but no live end-to-end Enhanced answer has run yet; Agentic's connection is dashed.
The 82 → 92 figure is development retrieval evidence, not answer accuracy, and
0.95 is a development cutoff, not a final thesis policy.

```bash
python3 docs/presentations/2026-11-23/render_full_flow.py
```

This writes only `full-flow.svg`, `full-flow.png` and `full-flow.pdf`. The
image was rendered and visually inspected; the SVG parsed as XML and the PDF has
one page. No model, DB or API access was needed.

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
