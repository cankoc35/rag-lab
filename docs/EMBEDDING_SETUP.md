# Local embedding setup and first runtime check

**Date:** 2026-11-06. **Status:** The owner authorized the next step after the
Nomic recommendation. Nomic Embed Text v1.5 is now the initial pilot embedding
model, with a working local document/query adapter. This is a runtime smoke
check, not a retrieval-quality comparison or a final thesis model verdict.

## Selected setup

| Setting | Value |
| --- | --- |
| Model | `nomic-ai/nomic-embed-text-v1.5` |
| Revision | `e9b6763023c676ca8431644204f50c2b100d9aab` |
| Output | 768 float32 values |
| Backend | Native Transformers NomicBERT through Sentence Transformers |
| Device | CPU, two PyTorch threads |
| Application input ceiling | 1024 tokens, including prefix/headings/special tokens |
| Pooling / normalization | Mean pooling, full-vector layer normalization (`eps=1e-5`), then L2 normalization |
| Remote model code | Disabled (`trust_remote_code=False`) |

Settings are in [pilot.toml](../configs/pilot.toml). Model files are stored at:

```text
data/local/models/nomic-ai--nomic-embed-text-v1.5/
  e9b6763023c676ca8431644204f50c2b100d9aab/
```

Ten selected assets total **547,886,235 bytes**, including safetensors weights,
configuration, pooling and tokenizer files. A local `model_manifest.json`
records their SHA-256 and sizes. Model loading checks these hashes first.
No pickle weights or model-repository Python files are downloaded by the
setup script. This whole directory is Git-ignored.

The model card documents extended context up to 8192 tokens; this first
adapter stays within the native base context and uses **1024**. It does not
configure or test a RoPE extension. MPS/GPU execution is also not tested.

The [Nomic model card](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5)
specifies task prefixes and the Matryoshka normalization recipe.
[Transformers NomicBERT documentation](https://huggingface.co/docs/transformers/model_doc/nomic_bert)
describes native loading and context extension.
[Sentence Transformers](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html)
supports local-file loading and explicit prompts. The tested versions below
use native NomicBERT without executing remote model code.

## Adapter behavior

[embeddings.py](../src/rag_workflow_lab/embeddings.py) has no model download or
ML import on module import. `NomicEmbedder.from_local(settings.embedding)`
explicitly loads the verified cached snapshot. Base CLI checks and ordinary
tests continue to run without ML packages or model files.

- `embed_document(chunk.embedding_text)` accepts the chunker's exact serialized
  input with its existing `search_document: ` prefix. It does not prepend it
  again. Inputs with a missing/wrong/duplicated leading task prefix fail.
- `embed_query(question)` accepts raw question text and adds `search_query: `
  once. Gold answers, requirements and evidence annotations are never passed.
- The adapter counts complete input without truncation or padding, rejects
  overflow before inference, and compares complete token IDs with the IDs
  prepared by Sentence Transformers. Changed or truncated input fails.
- It returns an immutable result with task, model/revision, adapter version,
  input SHA-256, token count and vector. Output must contain 768 finite values
  with an L2 norm close to one.

The embedding extra is optional in `pyproject.toml`. The reproducible smoke
script uses an isolated environment and its own checked-in lockfile, without
changing the base application's runtime dependencies or installing the project.

## Run the opt-in check

From the repository root, first authorize dependency/model downloads explicitly:

```sh
PYTHONPATH=src uv run --locked --no-project --python 3.11 scripts/embedding_smoke.py --download-model
```

The script downloads only the pinned public model assets, then blocks network
connections during local loading/inference. It validates the existing question
references, checks token counts for all 49 saved chunks, and embeds **one**
largest chunk and **one** raw development question (P04 by default). Choosing
the largest chunk exercises the input budget; it is not a retrieval decision
or a claim that this chunk fully answers P04.

After the first download, repeat fully offline:

```sh
PYTHONPATH=src HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --offline --locked --no-project --python 3.11 scripts/embedding_smoke.py
```

Runs write `smoke.json` to a new directory under `outputs/embeddings/`, ignored
by Git. Use `--output-dir PATH` to choose a new directory. Existing output
directories and differing existing model manifests are not overwritten.
Reports include the complete vectors, exact inputs/hashes, source/chunk and
question IDs, model manifest hash, library versions, runtime settings, code
commit/file hashes and observed timings. Those timings are not a benchmark.

## Observed result

Verified runs:

- Initial: `outputs/embeddings/nomic-smoke-v1/smoke.json`.
- Offline repeat: `outputs/embeddings/nomic-smoke-offline-v1/smoke.json`.

| Input | Identity | Tokens | Vector dimensions | L2 norm |
| --- | --- | ---: | ---: | ---: |
| Document | PG-STATS blocks 3–4, caption and whole table | 822 | 768 | 0.9999999685 |
| Query | P04, with query prefix | 25 | 768 | 0.9999999565 |

The offline repeat produced identical values for both vectors on this device.
All 49 saved chunk token counts matched the runtime tokenizer. Forward token
IDs matched complete input IDs, and an oversized query was rejected before
inference. All **59 offline unit tests** passed: the existing 48 plus 11 new
adapter/config checks using fake inference, without ML packages or network.

Tested versions: Sentence Transformers 5.3.0, Transformers 5.5.0, PyTorch
2.10.0, Tokenizers 0.22.2, Hugging Face Hub 1.33.0, NumPy 2.4.6 and
Safetensors 0.8.0, on Python 3.11.15 / macOS arm64.

The saved corpus, chunks and six-question annotations were unchanged by the
smoke check, which performed no ranking, answer generation or DB operations.

**Follow-up, 2026-11-12:** PostgreSQL + pgvector setup and revision `0001` are
complete. Snapshot/chunk import code is prepared and passed a full-corpus round
trip with rollback; the service is healthy and the tables remain empty. Next
run the importer for a committed import, then embed/index the corpus and use
P01–P06 to inspect retrieval. See [HANDOFF.md](HANDOFF.md) for resume checks.
Keep the selected model/revision and embedding settings shared across later
workflow comparisons.
