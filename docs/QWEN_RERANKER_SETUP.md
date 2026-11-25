# Qwen4B preparation and local smoke

**Prepared:** 2026-11-25. Target model: `Qwen/Qwen3-Reranker-4B`, revision
`22e683669bc0f0bd69640a1354a6d0aebcfeede5`.
Settings are in [reranker.toml](../configs/reranker.toml), separate from Nomic.

Follow-up: the separate [Qwen0.6B profile](../configs/reranker_qwen06b.toml) is
also prepared and locally tested. See the [paired comparison](QWEN_RERANKER_COMPARISON.md).
Scripts accept `--config`; the commands below retain the original 4B default.
The probe also accepts [batch size four](COMMANDS.md#run-qwen4b-with-batch-size-four);
one P05 check preserved ranks but was slower than batch one. Defaults are unchanged.

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

Weights were downloaded and the local smoke passed on **2026-11-25**:
two safetensors shards total 8,043,614,960 bytes (about 8.04 GB). Their SHA-256
hashes match the pinned download metadata. MPS/float16 loading took 18.51 seconds;
scoring the two short passages took 2.99 seconds. The relevant EXPLAIN passage
scored 0.962953 and the unrelated backup passage 0.000005104. Report:
`outputs/reranking/qwen4b-20261125T180455418462Z.json`.
This verifies local execution, not benchmark quality or real-candidate throughput.
No 120-question reranking or Enhanced answer workflow is implemented yet.
The smoke uses the pinned reranker template and normalized `yes`/`no` logits,
disables the KV cache and requests only the last-token logits. Loading/scoring
times are separate. A failed toy ordering exits nonzero; it is not an accuracy
benchmark. MPS absence fails explicitly without silently selecting a CPU fallback.

New reports under `outputs/reranking/` preserve settings, package versions,
tokenizer/weight checksums, input provenance and timing. No DB, `.env`, Luna key
or hosted model is involved. Model assets live under ignored `data/local/models/`.

## Saved-candidate probe — 2026-11-25

[reranker_probe.py](../scripts/reranker_probe.py) uses the same native scorer in
a separate lockfile with identical dependencies. It loads local weights once,
reranks explicitly selected saved RRF top-20 lists and preserves all candidates.
Use the [probe command](COMMANDS.md#probe-qwen4b-on-saved-rrf-candidates).

The diagnostic selection was P05 (known difficult PostgreSQL question), P07
(Atlas lookup), P27 (combined evidence) and P19 (unanswerable): **80 pairs**.
Only raw question text, headings and complete chunk bodies enter the model.
Version-1.8 references are used only for measurement.

| Question | Required claims supported in RRF top-5 | After Qwen | Scoring time |
| --- | --- | --- | --- |
| P05 | 0/3 | 2/3 | 31.82 s |
| P07 | 2/2 | 2/2 | 25.12 s |
| P27 | 1/3 | 3/3 | 29.83 s |
| P19 | N/A | N/A | 23.62 s |

Loading took 8.18 seconds; scoring totaled 110.40 seconds, about 1.38 seconds
per pair. These are sequential batch-size-one timings including the first
inference without a separate warm-up, not end-to-end RAG latency. A linear
projection for 2,400 pairs is about 55 minutes; full-run timing and peak memory
remain unmeasured.

P05 still lacks full annotated support at five. P19's top score is 0.906653
despite no established Boreal answer; scores are not calibrated answerability
probabilities, and no abstention threshold was selected. The three positive
questions are a targeted feasibility sample, not a general quality estimate.
The fixed candidate sets preserve recall and claim coverage at twenty.
No retrieval, DB access, hosted call or answer generation ran.

Report: `outputs/reranking/qwen4b-probe-20261125T181229740228Z.json`.
All 227 offline unit tests passed. Candidate/source preservation, score ordering,
all six metric summaries, negative exclusion and runtime hashes were independently
checked: `outputs/validation/qwen4b-probe-20261125T181229740228Z.json`.

## Preparation verification and next step

225 offline unit tests passed. A tiny randomly initialized native Qwen3 forward
verified the scoring API and oversized-input rejection without pretrained weights.
All 194 protected prior code/config/data/model-metadata/report files were unchanged.

The pretrained smoke and four-question real-candidate probe have passed. The
owner now requires reranking below 10 seconds per question; Qwen4B misses this
budget. The owner selected Qwen0.6B for the next trial; its paired probe is now
complete at 5.95 seconds per question with a P05 support loss. Next run its
120-question comparison using [the explicit profile](COMMANDS.md#run-the-qwen06b-profile).
Candidate selection,
labels and baseline reports must remain fixed. See the
[model review](QWEN_RERANKER_REVIEW.md) for external evidence and limitations.
