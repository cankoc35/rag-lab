# Qwen4B preparation and local smoke

**Prepared:** 2026-11-25. Target model: `Qwen/Qwen3-Reranker-4B`, revision
`22e683669bc0f0bd69640a1354a6d0aebcfeede5`.
Settings are in [reranker.toml](../configs/reranker.toml), separate from Nomic.

The [smoke script](../scripts/reranker_smoke.py) has its own uv lock and uses
native Transformers 5.5.0 / PyTorch 2.10.0 / Tokenizers 0.22.2. No Sentence
Transformers upgrade or embedding lock/index change is needed. The initial
runtime target is MPS with float16 and one question/passage pair per forward.
The application limit is 2,048 tokens; inputs exceeding it are rejected rather
than truncated. This does not change the model's native context capability.

## Tokenizer preparation

```sh
PYTHONPATH=src uv run --offline --locked --no-project --python 3.11 scripts/reranker_smoke.py --prepare
```

`--prepare` explicitly permits downloading only the pinned tokenizer/config
files. It validates dataset 1.8 and checks all saved RRF top-20 question/chunk
inputs using the model's own chat template. Each document is its heading path,
a blank line and the complete chunk text. Only the raw question and document
enter tokenization; evaluation requirements and reference answers do not.
`uv --offline` controls package downloads, not an explicit model-asset download.

Verified result: **2,400 pairs, maximum 821 tokens, zero oversized pairs**.
MPS is available on the checked machine. This checks input fit, not pretrained
model execution or retrieval quality. Report:
`outputs/reranking/qwen4b-20261125T152717058435Z.json`.

## Download weights and run the two-passage smoke

```sh
PYTHONPATH=src uv run --offline --locked --no-project --python 3.11 scripts/reranker_smoke.py --download-model
```

This explicitly downloads approximately 8 GB of original safetensors weights,
then compares one fixed EXPLAIN passage with one unrelated backup passage.
Subsequent runs omit `--download-model` and load local files only:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --python 3.11 scripts/reranker_smoke.py
```

Weights have **not** yet been downloaded or run. No 120-question reranking or
Enhanced answer workflow has been implemented by this preparation.
The smoke uses the pinned reranker template and normalized `yes`/`no` logits,
disables the KV cache and requests only the last-token logits. Loading/scoring
times are separate. A failed toy ordering exits nonzero; it is not an accuracy
benchmark. MPS absence fails explicitly without silently selecting a CPU fallback.

New reports under `outputs/reranking/` preserve settings, package versions,
tokenizer/weight checksums, input provenance and timing. No DB, `.env`, Luna key
or hosted model is involved. Model assets live under ignored `data/local/models/`.

## Verification and next step

225 offline unit tests passed. A tiny randomly initialized native Qwen3 forward
verified the scoring API and oversized-input rejection without pretrained weights.
All 194 protected prior code/config/data/model-metadata/report files were unchanged.

Next run the weight/runtime smoke, then time a small real RRF candidate set before
implementing the full top-20 → rerank → top-5 comparison. Candidate selection,
labels and baseline reports must remain fixed. See the
[model review](QWEN_RERANKER_REVIEW.md) for external evidence and limitations.
