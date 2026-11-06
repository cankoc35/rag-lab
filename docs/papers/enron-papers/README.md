# Enron and privacy-preserving RAG reading

This folder collects studies that use Enron emails for RAG or examine RAG privacy risks on Enron. It is a literature archive, not the chatbot's retrieval corpus or a finalized thesis scope. Numbers are for organization.

| PDF | Original source | Brief focus |
| --- | --- | --- |
| [01 - Public/Private Retrieval](01-Public-Private-Retrieval.pdf) | [Arora et al., TACL 2023](https://aclanthology.org/2023.tacl-1.51/) | Multi-step retrieval across private/public sources using Enron and Wikipedia. |
| [02 - Enron RAG Privacy Leakage](02-Enron-RAG-Privacy-Leakage.pdf) | [Zeng et al., ACL Findings 2024](https://aclanthology.org/2024.findings-acl.267/) | Data/PII extraction attacks against an Enron RAG corpus and simple mitigations. |
| [03 - EnronQA Benchmark](03-EnronQA-Benchmark.pdf) | [Ryan et al., 2025 preprint](https://arxiv.org/abs/2505.00263) | A private-document QA benchmark built from Enron emails. |
| [04 - Privacy RAG Master's Thesis](04-Privacy-RAG-Masters-Thesis.pdf) | [Bodea, TUM master's thesis, 2025](https://www.cs.cit.tum.de/fileadmin/w00cfj/sebis/thesis/250422_Bodea_Thesis.pdf) | Anonymization and privacy-utility comparisons on Enron. A thesis, not a paper. |
| [05 - Anonymization Placement](05-Anonymization-Placement-RAG.pdf) | [Bodea et al., IWSPA 2026](https://arxiv.org/abs/2604.15958) | Applying anonymization before ingestion into the corpus or after answer generation. |
| [06 - RAGFort](06-RAGFort-Knowledge-Base-Defense.pdf) | [Li et al., AAAI 2026](https://ojs.aaai.org/index.php/AAAI/article/view/40432) | Defense against knowledge-base extraction on corpora including Enron. |
| [07 - GraphRAG Privacy Risks](07-GraphRAG-Privacy-Risks.pdf) | [Liu et al., ACL Findings 2026](https://aclanthology.org/2026.findings-acl.899/) | Leakage comparison of Naive RAG, GraphRAG and LightRAG on Enron. |
| [08 - LeakDojo](08-LeakDojo-RAG-Leakage-Benchmark.pdf) | [Zhang et al., ACL Findings 2026](https://aclanthology.org/2026.findings-acl.287/) | A benchmark of RAG data extraction attacks on corpora including Enron. |
| [09 - Hybrid RAG Retrieval Pivot](09-Hybrid-RAG-Retrieval-Pivot.pdf) | [Thornton, 2026 preprint](https://arxiv.org/abs/2602.08668) | Access-control leakage during hybrid retrieval on Enron. |
| [10 - Privacy-Aware Decoding](10-Privacy-Aware-Decoding.pdf) | [Wang et al., 2025 preprint](https://arxiv.org/abs/2508.03098) | PAD, a method for reducing privacy leakage during generation; evaluated on Enron. |
| [11 - AI Worm Email Attack](11-AI-Worm-Email-Attack.pdf) | [Cohen et al., arXiv preprint](https://arxiv.org/abs/2403.02817) | Self-replicating prompt injection in email agents and a guardrail. This PDF is an earlier arXiv version; the [CCS 2025 publication](https://doi.org/10.1145/3719027.3765196) has a different title and defense name. |
| [12 - RAG-CT Query Defense](12-RAG-CT-Query-Defense.pdf) | [Lyu et al., 2026 preprint](https://arxiv.org/abs/2609.16095) | Detecting PII extraction queries on Enron through retrieval score distributions. |

Suggested first reading: **02 → 03 → 04 → 05**. These directly address the Enron corpus, benchmark and privacy mitigations. Then, depending on interest, read **09** (authorization), **07** (GraphRAG), **06/08** (knowledge-base extraction) and **01** (public/private retrieval). Check the relevant PDF section and original source page before quoting, using numbers or reproducing a method.

The earlier eight-item, method-focused **subjective priority order** is not the file numbering: **06 → 10 → 11 → 05 → PRESS → Random Projection → 12 → 09**. The open author-PDF link for [PRESS (ICASSP 2025)](https://doi.org/10.1109/ICASSP49660.2025.10887843) no longer works; [Private RAG via Random Projection (OpenReview submission)](https://openreview.net/pdf?id=ykiRX7px95) is currently unavailable for download. No substitute PDFs were added for these two studies; accessible copies can be added later if found.
