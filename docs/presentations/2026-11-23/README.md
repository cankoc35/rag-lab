# Supervisor discussion materials

Prepared on 23 November 2026 from the current code and project records.
Repository language is English. These are presentation artifacts, not a new
experiment or an implementation decision.

- [Pipeline PDF](pipeline.pdf): one-page diagram with implementation/status notes.
- [Pipeline PNG](pipeline.png): image for slides.
- [Pipeline SVG](pipeline.svg): editable vector diagram.
- [Briefing PDF](supervisor-brief.pdf): one-page speaking notes.
- [Briefing source](supervisor-brief.md): editable text matching the PDF.

Status labels are explicit: **DONE**, **NOT BUILT**, **PARTIAL** and **OPEN**.
Green arrows show the current direct Simple path. Dashed arrows show proposed
routing; they do not claim that a router or the other RAG methods exist.
The response box is an output, not an extra LLM call after a RAG workflow.
Tracing happens during execution; offline evaluation is a separate process.

## Diagram revision

The revised C section is **Evaluation for the thesis**, with four numbered
steps: fix the same questions/evidence, run every method plus LLM-only,
compare outcomes, and test whether routing helps. "Offline" means outside
live user traffic; it does not prohibit internet/API calls. This is a
separate comparison process, not additional steps before a user gets an answer.

The tracing status is now part of the heading **Tracing - partial coverage**,
with separate DONE / NOT BUILT lines. There is no detached status badge.

All three RAG paths now lead to a shared **Output validation** box before
Response. Its status is **PARTIAL / SHARED SCOPE OPEN**: completion/nonempty
checks already exist inside the Simple workflow; citation-label validation
is planned; grounding verification, failure/retry behavior and any extra LLM
call remain undecided. A valid source label alone does not establish support.
This depicts a proposed common stage, not a newly implemented validator or a
final experimental-policy decision. The briefing PDF/text are unchanged.

## Scope and evidence

“Basic” is the presentation label for the implemented **Simple** baseline.
The router currently has only a scaffold. Its method is undecided; rules,
a classifier and an LLM are options, not approved selections. It must use
question text/permitted runtime signals, never gold question-type labels.
LangGraph is selected for later Agentic work but is not implemented.
Frozen sandbox data and validated DB tools are also not implemented.

Current evidence comes from [STATUS](../../STATUS.md),
[PROJECT_CONTEXT](../../PROJECT_CONTEXT.md), [ROADMAP](../../ROADMAP.md),
[METHOD_DESIGN](../../METHOD_DESIGN.md), [EVALUATION_PLAN](../../EVALUATION_PLAN.md)
and the [paired development review](../../LLM_ONLY_COMPARISON.md).
Code was checked in the [workflow modules](../../../src/rag_workflow_lab/workflows/)
and [DB-tool scaffold](../../../src/rag_workflow_lab/tools/database.py).

The recorded corpus has 49 PostgreSQL and 12 Atlas chunks in separate embedding
sets. Ten questions are reference-verified development material; the held-out
test set is not prepared. The last paired Atlas results are from 18 November.
No paid calls, migrations or service changes were made to prepare these files.
