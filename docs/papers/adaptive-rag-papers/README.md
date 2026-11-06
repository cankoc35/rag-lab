# Adaptive RAG papers

These 10 papers were selected for the current **Adaptive RAG selection and trade-offs** working question within the Agentic RAG direction. The suggested order reflects reading convenience and relevance to the thesis question, not a quality ranking. This folder preserves the main list's numbering. Some PDFs are separately downloaded copies of papers in the main folder; the existing files were preserved.

| Order and PDF | Source / status | Why read it? |
| --- | --- | --- |
| [01 - Agentic vs Enhanced RAG](01-Agentic-vs-Enhanced-RAG.pdf) | [Ferrazzi et al., ACL Industry 2026](https://aclanthology.org/2026.acl-industry.5/) | The closest direct quality and cost comparison to the thesis question; inspect its baselines and experimental boundaries. |
| [02 - Adaptive-RAG](02-Adaptive-RAG-Question-Complexity.pdf) | [Jeong et al., NAACL 2024](https://aclanthology.org/2024.naacl-long.389/) | Understand no/single/iterative retrieval selection based on question complexity. |
| [03 - R2RAG](03-R2RAG-Simple-or-Agent.pdf) | [Ran et al., 2026 arXiv preprint](https://arxiv.org/abs/2602.20735) | Close prior work routing simple questions to single-pass RAG and difficult questions to an iterative agent. |
| [04 - RAGRouter-Bench](04-RAGRouter-Bench.pdf) | [Wang et al., 2026 arXiv preprint](https://arxiv.org/abs/2602.00296) | Evaluates pipeline selection through question-corpus fit, quality and resource consumption. |
| [05 - Budget-Constrained Agentic Search](05-Budget-Constrained-Agentic-Search.pdf) | [McCleary and Ghawaly, LREC 2026](https://aclanthology.org/2026.lrec-1.808/) | Effects of search/tool budgets on accuracy and cost; bounded experimental design. |
| [06 - HotelQuEST](06-HotelQuEST-Agentic-Search.pdf) | [Hadad et al., EACL Industry 2026](https://aclanthology.org/2026.eacl-industry.16/) | Quality-efficiency trade-offs in agentic search across question difficulty levels. Limited to hotel search. |
| [07 - MBA-RAG](07-MBA-RAG-Bandit-Selection.pdf) | [Tang et al., COLING 2025](https://aclanthology.org/2025.coling-main.218/) | An alternative router that learns retrieval strategy selection using accuracy and efficiency rewards. |
| [08 - When and How to Augment](08-When-and-How-to-Augment.pdf) | [Chen et al., NAACL Findings 2025](https://aclanthology.org/2025.findings-naacl.200/) | Accuracy-latency trade-offs and evaluation for question routing. |
| [09 - LLM-Independent Adaptive RAG](09-LLM-Independent-Adaptive-RAG.pdf) | [Marina et al., EMNLP 2025](https://aclanthology.org/2025.emnlp-main.439/) | Examine lightweight methods that do not require an LLM call for every routing decision. |
| [10 - Agentic Context and Tools](10-Agentic-Context-Tool-Use.pdf) | [Uniyal et al., ACL Industry 2026](https://aclanthology.org/2026.acl-industry.133/) | Examine when non-retrieval tools help in tasks involving documents in multiple formats. |

**Note:** Papers 03 and 04 are labeled arXiv preprints, not conference papers. The Agentic RAG direction is selected; the exact experimental question and protocol remain open. Do not make general performance claims before reading each paper's experimental setup and limitations. In particular, 03 shows that routing is already used; any potential contribution must depend on how our controlled comparison addresses question types, tool use, cost and latency. The initial source-backed comparison is in the [literature table](../../LITERATURE_GAPS.md).
