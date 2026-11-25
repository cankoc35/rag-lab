# Reranker latency requirement and smaller candidates

**Reviewed:** 2026-11-25. Research only; no new model was downloaded or selected.

**Follow-up:** the owner chose Qwen0.6B for a trial. It is now downloaded and
tested: mean 5.95 seconds per question versus a fresh 27.90-second 4B run, with
P05 top-five support loss. See [paired results](QWEN_RERANKER_COMPARISON.md).
The Ettin proposal below remains unimplemented; full 0.6B evaluation is next.

## Requirement

The owner requires per-question reranking to stay below 10 seconds and prefers
substantially less. This concerns the complete top-20 reranking stage, not one
question/chunk pair. Qwen4B's measured 23.62–31.82 seconds misses that requirement.
A 2–3-second target is a proposal, not a measured result or a finalized thesis rule.

## Shortlist

| Candidate | Approximate parameters | Published input limit | Proposed role |
| --- | --- | --- | --- |
| [Ettin 68M](https://huggingface.co/cross-encoder/ettin-reranker-68m-v1) | 68M | 7,999 tokens | First small-model probe; English encoder |
| [Ettin 150M](https://huggingface.co/cross-encoder/ettin-reranker-150m-v1) | 151M | 7,999 tokens | Quality alternative if the smaller model loses necessary support |
| [GTE ModernBERT](https://huggingface.co/Alibaba-NLP/gte-reranker-modernbert-base) | 149M | 8,192 tokens | Another English encoder baseline |
| [Qwen3-Reranker-0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B) | 596M | 32K tokens | Smaller Qwen option; still larger than the encoder candidates |

The [Ettin author's benchmark](https://huggingface.co/blog/ettin-reranker#results)
compares ten English MTEB tasks with top-100 reranking and six embedding models.
Mean nDCG@10 is 0.5915 for Ettin 68M, 0.5994 for Ettin 150M, 0.5940 for Qwen
0.6B, 0.5843 for GTE ModernBERT and 0.6367 for Qwen4B. These are developer-run
benchmark aggregates, not local PostgreSQL/Atlas results or answer accuracy.
Published throughput uses H100/RTX 3090/Intel CPU setups and cannot establish
Mac latency; the ordering also varies with hardware and batching.

[MiniLM-L6-v2](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2)
is a smaller 22.7M baseline, but its
[configuration](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2/blob/main/config.json)
limits positions to 512. Full question/chunk fit would require checking its own
tokenizer; silently truncating policy or SQL evidence is not acceptable.

## Earlier Ettin proposal (deferred)

Probe `cross-encoder/ettin-reranker-68m-v1` on the same P05/P07/P27/P19 top-20
candidate lists, with full headings/text and version-1.8 references. Verify all
inputs with its tokenizer. Compare CPU/MPS and small batches while retaining
all candidates; keep model load and first inference separate from warm latency.
Report median, p95 and maximum question latency along with existing quality
metrics. Check that every measured question meets the 10-second budget; a fast
average alone is insufficient. This does not guarantee future request latency.

The released model has a modular encoder/classification head. Verify its exact
head and library compatibility in a separate locked environment; it is not a
model-ID substitution in the Qwen yes/no scorer. Preserve Nomic's environment,
all source/chunk/index state, Qwen configuration and prior results. Once a small
candidate is feasible, compare it on all 120 questions. No private/hosted model
call or change to the final evaluation protocol is proposed here.
