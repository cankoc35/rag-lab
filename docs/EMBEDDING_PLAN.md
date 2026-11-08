# Embedding model — initial pilot decision

**Updated:** 2026-11-08. **Status:** Following the Nomic recommendation, the
owner authorized its first local embedding step. Nomic Embed Text v1.5 is
selected for the initial pilot; weights are cached locally and one document/
query runtime check plus an offline repeat passed. Retrieval quality is not
measured. PostgreSQL + pgvector is configured and revision `0001` created the
retrieval tables; corpus import/indexing remain pending. See
[EMBEDDING_SETUP.md](EMBEDDING_SETUP.md) for the exact revision/settings.

## Language decision and starting proposal

**Owner decision, 2026-11-05:** The entire repository and RAG system use
English, including corpus/synthetic documents, questions/datasets, prompts,
answers and evaluation content. Multilingual/cross-lingual support is not
required. This supersedes the Turkish-question/English-document rationale
for the earlier BGE-M3 proposal.

The pilot uses **one local dense embedding model and PostgreSQL +
pgvector** as the storage direction. Embed documents and questions with the same model/revision; keep
embeddings and index fixed across simple/enhanced/agentic comparisons. Select
by English technical-retrieval quality, input limits, tokenization and local
resource use. A multilingual model can perform well in English; language
labels alone do not establish superiority or inadequacy.

The owner reported **24 GB RAM or more** for the MacBook Air M3; the exact
capacity above that threshold was not specified.

## Candidates checked for the English-only scope

| Model | Approximate parameters | Dense vector dimensions | Documented maximum input | Pilot role |
| --- | --- | --- | --- | --- |
| `nomic-ai/nomic-embed-text-v1.5` | 137M | 768 (default) | 8192 tokens | Selected initial pilot model; adapter ceiling is 1024 |
| `BAAI/bge-base-en-v1.5` | 109M | 768 | 512 tokens | English alternative with a tighter chunk budget |

Input limits and vector dimensions were checked in the
[Nomic model card](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5) and
[BGE English model card](https://huggingface.co/BAAI/bge-base-en-v1.5).
Approximate counts were rounded from HF metadata:
[Nomic 136,731,648](https://huggingface.co/api/models/nomic-ai/nomic-embed-text-v1.5)
and [BGE 109,482,752](https://huggingface.co/api/models/BAAI/bge-base-en-v1.5)
tensor elements. This table is not a quality/speed ranking.

Nomic requires `search_document:` and `search_query:` prefixes for retrieval;
shared weights do not mean all inputs receive the same prefix. Preserve
model-specific pooling/normalization and backend settings. Verify the
adapter's actual input limit against the documented capacity and pin the
model/tokenizer revision.

Earlier multilingual candidates were `BAAI/bge-m3`,
`intfloat/multilingual-e5-small` and `Qwen/Qwen3-Embedding-0.6B`. None was
selected/downloaded. BGE-M3's proposed 1024-dimensional output was not turned
into a final database schema; dimensions depend on the selected model.

## Model size and hardware interpretation

Parameter count describes model weights; vector dimensions describe each
embedding stored in the database; token limits describe processable input.
These are separate quantities. More parameters do not guarantee better
retrieval on our questions.

The English-only scope allows these roughly 100–150M candidates to be
considered initially; a 0.6B or larger model is not mandatory. Measure batch
size, sequence length, backend, activations and concurrent LLM/Docker use.
There is no measured throughput or memory result on this device yet.

An 8192-token capacity does not require chunks of that size. A small target
size can coexist with a budget that preserves longer SQL blocks.
The chunker now uses a 512-token soft target and 1024-token ceiling with
explicit overflow errors. The pinned adapter uses the same tokenizer revision
and a 1024-token input ceiling; extending native context is not tested.

## pgvector and multiple models

The selected model's dense outputs fit the applied schema's `vector(768)`
column. Cosine-distance search is planned but not implemented yet.
[pgvector](https://github.com/pgvector/pgvector) supports exact and approximate
search. Its current HNSW `vector` limit is 2000 dimensions, so 768 fits.
Start the small pilot with exact search; assess HNSW as the dataset grows.
Exact search finds nearest vectors under the selected distance; it does not
guarantee semantic matching to the expected evidence.

Multiple embedding models are unnecessary initially. A later model comparison
requires a separate index scope and re-embedding for each model/revision.
Do not mix vectors from different models in one search space, even if their
dimensions match. Record chunk inputs and model-specific prompt/normalization
settings during comparisons.

## Tokenizer measurement and next verification

The owner requested block token measurement before model selection. At that step, the
Nomic candidate's tokenizer was pinned and used locally for all 184 parsed
blocks; see [TOKEN_COUNTS.md](TOKEN_COUNTS.md). Including headings, the
document prefix and special tokens, the maximum code block is 658 tokens and
the table is 811. Three blocks exceed 512. Only tokenizer metadata was
downloaded; no model weights or embedding inference were involved in that
measurement. Model selection and its runtime check came afterward.

The owner subsequently requested the 512/1024-token strategy; the
[implemented chunker](CHUNKING.md) produces 49 verified chunks, at most 822
tokens with that tokenizer. Nomic was then selected for the initial pilot;
the [local adapter check](EMBEDDING_SETUP.md) verified one complete 822-token
chunk and one 25-token query, producing finite, normalized 768-dimensional
vectors without truncation or inference network access. Offline replay matched.
Next, implement snapshot/chunk import into the existing PostgreSQL tables,
then embed/index the corpus and inspect retrieval on P01–P06. Their evidence
mapping is already source-verified. The service was stopped at the 2026-11-08
runtime check; see [HANDOFF.md](HANDOFF.md) before live DB work.
Use broader development evidence before making a model-quality comparison;
do not select models based on held-out test outcomes.
