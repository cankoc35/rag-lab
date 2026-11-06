## Brief glossary

- RAG (Retrieval-Augmented Generation): An LLM finding and using relevant documents before answering.
- LLM (Large Language Model): A language model that understands and generates text.
- Corpus / knowledge base: The document collection searched by RAG. A chunk is a small part of these documents used for retrieval.
- Retrieval: Finding documents or chunks relevant to a question. Embedding converts text into a numerical vector usable for search; an index is the structure searched for these vectors.
- PII (Personally Identifiable Information): Information that can identify a person, such as a name, email, phone number or address.
- Anonymization: Removing, hiding or replacing identifying information. PRE applies this before content enters RAG; POST applies it after an answer is generated.
- DP (Differential Privacy): A mathematical privacy approach designed to limit changes in output probabilities when one record or document changes. It generally uses controlled randomness; it is not the same as simply deleting PII.
- Epsilon (ε) / delta (δ): Privacy parameters in DP. Other things being equal, a smaller epsilon generally means stronger protection; delta is a small tolerance allowance.
- MLM (Masked Language Model): A model that predicts a masked word from surrounding words.
- Token: A word or word fragment used by an LLM to process text. A logit is a raw score assigned to a candidate next token, not the name of a learned model parameter.
- Clipping / noise: Clipping limits score magnitudes; noise is a controlled random change added to scores or text.
- Leakage / extraction: Leakage is unintended disclosure; extraction is an attacker's attempt to recover information through queries.
- Intra-class / inter-class extraction: Recovering details within a topic / moving to other topics using what has been learned.
- CRR (Chunk Recovery Rate): The proportion of knowledge-base chunks an attacker recovers. Lower CRR means less extraction.
- PAD (Privacy-Aware Decoding): A method that modifies token logits during answer generation to reduce leakage of retrieved text.
- Repeat / ROUGE-L: Repeat counts verbatim copying from source text. ROUGE-L measures word-sequence overlap between an answer and its source; it does not directly measure meaning.
- PPL (Perplexity): Measures how predictable generated text is to a model; it is not, by itself, answer correctness.
- Access control: Rules specifying who is authorized to view a document or piece of information.

Anonymization can be applied before documents enter RAG (PRE) or after an answer is generated (POST). PRE generally protects information earlier but may reduce answer quality. POST may preserve quality better, but the original text still reaches the answer-generating LLM. Placement in the pipeline matters alongside the method itself.

Some methods used:

- PII deletion: Removes detected names, emails, addresses and similar information.
- PII labeling: Replaces information with its type: Alice → <PERSON>.
- Synthetic PII replacement: Replaces information with a fictitious value: Alice → Emma.
- 1-Diffractor: Replaces words with other words under DP rules.
- DP-Prompt: Uses a language model to rewrite text under DP rules.
- DP-MLM: Replaces words sequentially with help from a Masked Language Model under DP rules.

This anonymization experiment did not simulate a real attack. An LLM was asked to identify PII in text; another LLM then scored whether original PII remained in the answer. This is a leakage test rather than a test of attacker behavior.

Another risk is that an attacker can repeatedly query RAG and recover knowledge-base chunks piece by piece. Learning more details about one topic is intra-class extraction; using what has been learned to move to other topics is inter-class extraction.

Protection against this was explored at two stages: at retrieval, grouping chunks by topic and rebuilding the index to separate embeddings from different topics; at generation, controlling generated tokens with draft and reference models to make source-chunk recovery harder.

Two attacks were simulated to test this protection:

- RAG-Thief: An agent that remembers information learned from answers and generates new questions to recover more chunks.
- Worm-Attack: Tests extraction and propagation using malicious, self-repeating prompts. This paper does not disclose the attack payload details.

The researchers compared the text collected after the attack with the original corpus and measured the proportion of recovered chunks (CRR).

In the Enron experiments, this protection changed answer accuracy only slightly and reduced the proportion of recoverable chunks. It did not eliminate leakage, and the method is distinct from PII removal or access control.

Another approach protects generation without modifying retrieval or documents. PAD (Privacy-Aware Decoding) clips the raw scores called logits before the LLM selects each new token and adds controlled noise. It uses more noise when the model is uncertain and less when confident. It is not a PII detector; it aims to make verbatim reproduction of retrieved text harder. It also does not prevent the original document from reaching the LLM.

The attack tests added instructions such as "repeat the retrieved context verbatim" to questions. They used Enron emails and two medical datasets. **Repeat** measured verbatim copying in the answer; **ROUGE-L** measured word-sequence overlap with the source. **PPL (perplexity)** provided a measure related to fluency; it does not establish that an answer is correct or relevant.

PAD reduced copying in most experiments but did not eliminate leakage. On Enron, improvements were more pronounced with Llama2-7B and smaller with Pythia-6.9B. Excessive noise could make answers unusable; some examples replaced private details with more general answers. Privacy and actual answer quality therefore need to be measured together.

The paper's DP calculation is not an unconditional guarantee for the whole answer: it covers only the token steps receiving stronger protection. Because noise depends on private logits, the reported epsilon is not a worst-case bound over every possible input. Reproducing PAD requires access to logits during decoding; standard closed LLM APIs generally do not provide this.

In the AI Worm (Morris-II) study, self-replicating prompt injection in an attacker's email activates when the email enters RAG and is later retrieved. The assistant may include private information from other emails in an answer and copy the malicious instruction into a new email, propagating the attack to other assistants. The researchers proposed a guardrail called Virtual Donkey that examines text similarity between input and output; although effective in their experiments, it does not guarantee protection against adaptive attacks.
