# Project context

**Updated:** 2026-11-17. This file records purpose and lasting decisions.
Use [STATUS](STATUS.md) for progress, [ROADMAP](ROADMAP.md) for sequence,
[HANDOFF](HANDOFF.md) for code/artifacts and [history](STATUS_HISTORY.md) for
dated implementation details. Repository: `/Users/cankoc/Desktop/rag-workflow-lab`.

## Purpose and boundaries

Build a useful PostgreSQL documentation and sandbox-database assistant while
learning Agentic RAG engineering. The supervisor endorsed this thesis direction
and requested a [method design](METHOD_DESIGN.md); the draft is not yet reviewed.
The final thesis title, research question, contribution and protocol remain open.
This is not the MOTIF-RAG evaluation library.

**Owner decisions:**

- **2026-11-01:** Use public PostgreSQL documentation, synthetic deployment/
  operations runbooks and frozen sandbox DB state. Include a meaningful
  non-retrieval capability and prior-knowledge controls.
- **2026-11-05:** Keep the entire repository and RAG system English: code,
  docs, prompts, corpus, questions, answers and rubrics. Only chat may be Turkish.
- **2026-11-06:** Work in small, testable increments with short, readable code;
  follow [Simplicity First](../AGENTS.md#simplicity-first).

The first source allowlist selects PostgreSQL 18: Using EXPLAIN, Multicolumn
Indexes, Partial Indexes and the `pg_stat_replication` statistics section.
Four saved snapshots exist; synthetic runbooks and DB fixtures are pending.
P01–P06 have verified answers/evidence; P07–P20 are drafts. The 20-question
pilot is development material, not the final sample size or a held-out set.

## Selected direction and earlier alternatives

The working study compares Simple, Enhanced and Agentic RAG, then asks whether
a router can retain acceptable answer quality at lower cost/latency than
always using Agentic RAG. Neither routing nor adding a DB tool is claimed as
novel; the contribution needs a controlled experiment and deeper literature review.

Earlier alternatives were observability for failure localization and
privacy-preserving RAG over Enron. They remain background literature, not
active thesis directions. MLflow was considered earlier and rejected by the
owner on 2026-11-16 in favor of small project-owned PostgreSQL tracing.

## Implementation and comparison approach

**Approved initial definitions, 2026-11-13:**

| Workflow | Initial design |
| --- | --- |
| Simple | One dense retrieval pass and one answer call; no hybrid/reranking or sandbox tools. |
| Enhanced | Dense + PostgreSQL full-text retrieval, RRF merge/deduplication, reranking and one answer call. Relevant tools follow fixed Python conditions/order. |
| Agentic | Comparable relevant tool access and dynamic model decisions; detailed design deferred. |

Share corpus/chunks, dense embedding settings, generator/settings, answer
prompt and maximum context budget. Both fixed document paths cite evidence
and may abstain. Native LLM function calling is not required for Enhanced's
fixed steps. Exact tools/conditions and Agentic graph/loop details remain open.
The workflows are not implemented by recording these decisions.

Use dense-only → hybrid-only → hybrid + reranking as development ablations,
not extra main workflows. Build the Simple baseline before orchestration or UI.
Ingestion, retrieval, model calls, tools and evaluation remain separate modules.
Tool retrieval/reranking is only a proposal if a larger tool catalog warrants it.

**Evaluation controls approved, 2026-11-01:**

- Include LLM-only without retrieval/tools, retaining questions it answers correctly.
- Add source-specific synthetic facts, changed-evidence pairs and insufficient-
  evidence cases. Do not alter PostgreSQL semantics to manufacture facts.
- Freeze document/DB state per question. Keep related scenario variants in one
  split and development questions separate from final tests.
- Give Enhanced and Agentic comparable relevant tool access. Simple's inability
  to inspect hidden DB state is a capability limit, not proof of better control.

Define metric calculations, per-run records, primary comparisons and an
acceptable quality margin before final testing. Report answer/evidence/tool
quality, tokens, cost, latency and failures by question type; include router
overhead and mistakes. A negative result is valid. See [method](METHOD_DESIGN.md)
and [evaluation](EVALUATION_PLAN.md); neither is a finalized protocol.

## Technical choices and open selections

| Component | Confirmed choice |
| --- | --- |
| Runtime | Python 3.11+, initially a CLI |
| Storage | Local Docker PostgreSQL + pgvector; parameterized Psycopg SQL, no application ORM |
| Migrations | Alembic raw-SQL revisions; SQLAlchemy only for migration connections; head `0002` |
| Embeddings | Local `nomic-ai/nomic-embed-text-v1.5`, pinned revision, CPU float32, 768 dimensions |
| Chunking | Whole blocks within sections; target 512 / ceiling 1024 tokens including context; no overlap or silent truncation |
| Generator | Initial `gpt-6-luna` via OpenAI Responses API; reasoning `none`, maximum 1000 output tokens; SDK `3.51.0` |
| Tracing | Project-owned `traces` / `spans` through raw SQL; separate writer for retrieval logs |
| Agent orchestration | LangGraph selected, not installed |

Nomic revision: `e9b6763023c676ca8431644204f50c2b100d9aab`. Preserve exact
`search_document: ` / `search_query: ` inputs, mean pooling, full-vector
layer normalization and L2 normalization. Checksummed safetensors load through
native installed code, without downloads during inference. Index identity
records input/model/runtime/code provenance. Identical writes are accepted;
conflicting payloads under existing IDs fail rather than overwrite evidence.
See [chunking](CHUNKING.md), [embedding setup](EMBEDDING_SETUP.md) and
[database setup](POSTGRES_SETUP.md) for contracts and dependency pins.

**Owner, 2026-11-17:** Start with an inexpensive paid hosted generator. The
Luna client and opt-in smoke are prepared and checked offline; no hosted call
or quality result is verified. Use the same generator/settings across workflow
comparisons; final experimental models/settings remain open. Do not send
private corpus content to a hosted provider without an explicit decision.

**Hardware:** The owner reported a MacBook Air M3 with at least 24 GB RAM;
the exact capacity above that threshold is unspecified. Local generator
comparison may follow later without confounding workflow comparisons.

**Still open:** Full corpus coverage, synthetic runbooks/DB fixtures and tool
contracts, reranker, candidate/context/fusion budgets, Enhanced tool conditions,
Agentic/router design, final model count, rubric/judges, metrics, quality margin,
held-out set and sample size. No generated-answer or thesis result exists.

## Where to find the literature

The [main RAG list](papers/rag-papers/README.md),
[adaptive RAG branch](papers/adaptive-rag-papers/README.md),
[Enron branch](papers/enron-papers/README.md) and
[brief Enron notes](papers/enron-papers/enron-notes.md) are research material,
not corpus inputs. The [literature comparison](LITERATURE_GAPS.md) records
paper-specific methods and limits; do not assume all papers are read.
