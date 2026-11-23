# Supervisor briefing

23 November 2026 | RAG Workflow Lab

## Aim

The project studies when Simple, Enhanced or Agentic RAG is useful, and whether a router can preserve answer quality at lower cost and latency. The exact research question and final evaluation protocol remain open.

## Completed

A working Simple RAG baseline is available through a CLI. Four PostgreSQL documentation sources and two synthetic Atlas documents produce 61 versioned chunks. Local Nomic embeddings are stored in PostgreSQL with pgvector. Each question retrieves five chunks, then Luna answers with citations or reports insufficient evidence. Traces record retrieved sources, prompts, answers, token usage and timings.

## Early evidence

Ten development questions have verified references. In the Atlas comparison, Simple answered two of three answerable questions completely; the third gave the correct rule but omitted the explicit reporting role. LLM-only honestly abstained on all three. Both abstained on the missing Boreal policy. This small development check is not a general accuracy result or a pure causal retrieval estimate.

## Next work

Next proposed: change a source fact in a separate version and check whether the answer follows it. Then prepare frozen sandbox data and read-only tools, build Enhanced retrieval and fixed tool steps, and add bounded Agentic orchestration. Build the router after these workflows, then perform a controlled comparison on a separate held-out set.

## Pipeline clarification

Source preparation happens before questions. The target question-time flow is question -> router -> one selected RAG -> answer. Today, the CLI selects Simple directly. The router is not implemented; rules, a classifier or an LLM remain possible choices. Offline experiments will run every workflow on the same questions, alongside an LLM-only control. Reranker, tool conditions, budgets and final scoring are still open.

---

Basis: repository code/design inspected on 23 November 2026; development results recorded on 18 November. No new model experiment or live database health check was run for this briefing.
