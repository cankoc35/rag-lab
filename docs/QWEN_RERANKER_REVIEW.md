# Qwen3-Reranker-4B review

**Reviewed:** 2026-11-25. Research and a proposed comparison, not an installed
model or a final reranker decision. No model weights were downloaded or executed.

Follow-up: the owner requested [Qwen4B preparation](QWEN_RERANKER_SETUP.md).
Its pinned weights and separate native-Transformers environment are now local;
the runtime smoke and four-question probe passed. Measured top-20 latency is
24–32 seconds, exceeding the owner's new 10-second budget. The
[latency review](RERANKER_LATENCY_REVIEW.md) motivated smaller candidates. The
owner chose Qwen0.6B; its [paired probe](QWEN_RERANKER_COMPARISON.md) is complete.
The evidence below remains the earlier quality-oriented comparison.

Qwen3-Reranker-4B is a strong quality-oriented candidate. The earlier ModernBERT
recommendation prioritized a small, English-focused model. Published evidence
supports testing the 4B model rather than choosing only on size.

## Published quality evidence

The [Qwen technical report, Table 4](https://arxiv.org/html/2506.05176v3#S4.T4)
reports these reranking scores:

| Model | English MTEB retrieval | MTEB Code |
| --- | ---: | ---: |
| Qwen3-Reranker-0.6B | 65.80 | 73.42 |
| Qwen3-Reranker-4B | 69.76 | 81.20 |
| Qwen3-Reranker-8B | 69.02 | 81.22 |

All methods rerank the same top-100 candidates from Qwen3-Embedding-0.6B.
These are benchmark scores, not answer accuracy. Larger is not uniformly
better: 4B exceeds 8B on this English aggregate. This table does not include
the previously proposed gte-reranker-modernbert-base; its GTE baseline is a
different multilingual model.

The [Ettin reranker author's comparison](https://huggingface.co/blog/ettin-reranker#results),
published 2026-05-19, directly compares the relevant models:

| Model | English MTEB retrieval nDCG@10 |
| --- | ---: |
| gte-reranker-modernbert-base | 0.5843 |
| Qwen3-Reranker-0.6B | 0.5940 |
| Qwen3-Reranker-4B | 0.6367 |

These are means across six embedder pairings, including Nomic, on ten English
tasks with top-100 reranking. The 4B run caps input at 8,192 tokens. This is
another model developer's experiment, not a local PostgreSQL/Atlas result.
Do not mix its values with Qwen's different protocol.

## What the model does

The [official model card](https://huggingface.co/Qwen/Qwen3-Reranker-4B)
specifies 4B parameters, 32K context, instruction support and Apache-2.0 licensing.
It jointly scores an instruction, raw question and one document using the
relative next-token scores of `yes` and `no`. It is a decoder-based cross-encoder;
long answer generation is unnecessary. Preserve its scoring template and token
mapping. It can score the text returned by Nomic/RRF without replacing Nomic.

## Local memory and runtime

| Format | Approximate published file size | Source |
| --- | ---: | --- |
| Original weights | 8.04 GB in two shards | [Qwen files](https://huggingface.co/Qwen/Qwen3-Reranker-4B/tree/main) |
| Community GGUF Q8_0 | 4.28 GB | [Quantization publisher](https://huggingface.co/tensorblock/Qwen_Qwen3-Reranker-4B-GGUF#model-file-specification) |
| Community GGUF Q4_K_M | 2.50 GB | Same publisher |

These are file sizes, not total RAM requirements. Activations, buffers, batch
size, actual sequence length, the OS and other applications also need memory.
The owner's M3 Air with at least 24 GB makes a small-batch trial plausible;
this is a feasibility inference, not measured latency or memory use.
Quantized variants need their own quality checks and recorded revisions.

Apple GPU execution is available through [PyTorch MPS](https://huggingface.co/docs/transformers/main/apple_silicon).
Another candidate is GGUF with llama.cpp, whose current
[conversion code](https://github.com/ggml-org/llama.cpp/blob/master/conversion/qwen.py)
handles Qwen3 reranker scoring metadata and whose
[server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
exposes reranking. Neither route has been verified on this checkout.
Do not assume that generic chat or embedding examples implement correct reranking.

Current Nomic scripts pin Sentence Transformers 5.3.0; the current Qwen model
files advertise a newer Sentence Transformers integration. Verify adapter
compatibility or use the official Transformers scoring path in a separate
reranker environment. Preserve existing embedding locks/index identity.

## Proposed next experiment

1. Check the model's tokenizer and exact scoring template; pin model/runtime,
   precision and token handling. Never silently truncate SQL or policy evidence.
2. Run a small local feasibility check, recording cold load separately from
   warm scoring time and peak memory. A quantized Q8 variant is an option, not
   an assumed equivalent of the published original model.
3. If feasible, reuse each saved RRF top-20 list on dataset 1.8 and select the
   top five by reranker score. Compare with unchanged RRF/dense top-five results
   and a lightweight ModernBERT reranker using the same inputs and labels.
4. Report full required-evidence support, ranking metrics and latency. Keep
   negatives separate; no numeric reranker score alone certifies answerability.

No final winner is selected from the external benchmarks. Reranking only
reorders available candidates; it cannot repair an absent candidate or guarantee
that five independently high-scoring chunks jointly cover every required fact.
