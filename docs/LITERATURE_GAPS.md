# Literature comparison — initial source-backed table

**Status:** Working draft, checked against the linked primary papers on
2026-11-01. This is a focused start for the proposed Agentic RAG experiment,
not a systematic review or a claim that no other work covers these topics.
“Our remaining question” below is **our inference from each paper's stated
method and experiment**, not necessarily a flaw identified by its authors.

| Paper and source | What it compares / measures | Our remaining question after this paper |
| --- | --- | --- |
| [Ferrazzi et al., *Is Agentic RAG worth it?* (ACL Industry 2026)](https://aclanthology.org/2026.acl-industry.5.pdf) · [local PDF](papers/adaptive-rag-papers/01-Agentic-vs-Enhanced-RAG.pdf) | Naive baselines, enhanced pipeline, and agentic approach across RAG components; reports quality measures, tokens, and latency. | Its agent has **one retrieval tool** and cannot use an external live-data tool. The authors explicitly limit the comparison to pure RAG (§3, Appendix F). How does fixed versus dynamic control compare when both have the same retrieval and live-tool access? |
| [Jeong et al., *Adaptive-RAG* (NAACL 2024)](https://aclanthology.org/2024.naacl-long.389.pdf) · [local PDF](papers/adaptive-rag-papers/02-Adaptive-RAG-Question-Complexity.pdf) | Routes no retrieval, single-step retrieval, and multi-step retrieval by predicted question complexity; evaluates QA accuracy/F1, retrieval steps, and time on open-domain QA sets. | Its action space concerns **retrieval depth**, not a comparison between fixed tool-capable workflow control and an agent that chooses non-retrieval tools. This follows from the three methods defined in §1–§3. |
| [Wang et al., *RAGRouter-Bench* (2026 preprint)](https://arxiv.org/html/2602.00296) · [local PDF](papers/adaptive-rag-papers/04-RAGRouter-Bench.pdf) | Same query/corpus setting for LLM-only, NaiveRAG, GraphRAG, HybridRAG, and IterativeRAG; studies quality and resource efficiency. | Its five targets are structured retrieval paradigms (§3.1), rather than matched fixed/agentic workflows with a non-retrieval tool. The authors also note the fixed target set and synthetic-query limitations (Appendix E). |
| [Liang et al., *DynaRAG* (2026 preprint)](https://arxiv.org/html/2603.18012v1) | Uses retrieved web pages plus selective API fallback; compares with LLM-only and direct-RAG baselines on CRAG using accuracy, hallucination, and missing-answer rates. | It shows that live API access and fallback already exist. Its reported baselines (§IV-B) do not isolate **fixed enhanced versus iterative agentic control with equal tool access**; this is an inference about the reported comparison. |
| [Bai et al., *Learning to Route* (2025/2026 preprint)](https://arxiv.org/html/2510.02388v2) | Routes among no-source, document, database, and hybrid-source paths; compares fixed paths with several routing strategies using answer accuracy, tokens, and routing time (§5). | It studies **which information source/path** to choose. Our working question instead asks when to pay for agentic workflow control, with the relevant sources available to fixed and agentic candidates. This distinction needs further literature checking. |

## What this table supports so far

- Comparing RAG variants, adaptive routing, and external tool/source access
  have all been studied. None can be claimed as a new invention here.
- A **candidate** narrower experiment is to compare fixed and agentic control
  under matched access to document retrieval and a live-data tool, then test
  whether a router selects the cheaper adequate workflow by question type.
- The table does **not** establish that this combination is globally novel.
  Search further and refine the claim before writing the thesis proposal.

## Next review pass

Check the remaining [adaptive paper list](papers/adaptive-rag-papers/README.md),
especially R2RAG and tool-using agent papers, against the same columns. For
every added row, record the paper's actual baselines, dataset, metrics, and
scope; separate author-stated limitations from our inferred difference.
