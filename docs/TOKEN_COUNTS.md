# Parsed-block token measurements

**Follow-up, 2026-11-06:** The owner requested the 512-token target and
1024-token application ceiling. [Chunking is now implemented](CHUNKING.md)
and all four sources produce 49 verified chunks. The block measurements below
remain the original measurements, distinct from complete chunk sizes.

**Measured:** 2026-11-05, 20:38 UTC. **Scope:** All 184 parsed blocks from the
four saved PostgreSQL sources. These are block measurements, not finished
chunks, embeddings or a retrieval-quality benchmark. Nomic was a candidate at
measurement time and was later selected and checked with the
[local embedding adapter](EMBEDDING_SETUP.md).

## Tokenizer and counting rules

- Candidate: `nomic-ai/nomic-embed-text-v1.5`.
- Pinned revision: `e9b6763023c676ca8431644204f50c2b100d9aab`.
- Runtime: Python 3.11.15 and `tokenizers==0.22.2`.
- Only `tokenizer.json`, `tokenizer_config.json`, `special_tokens_map.json`
  and `sentence_bert_config.json` were downloaded. No model weights or remote
  Python code were loaded. Corpus text was tokenized locally.
- Every tokenizer file is checked against its pinned SHA-256 in the
  [measurement script](../scripts/measure_block_tokens.py). Input file hashes,
  parser/source/snapshot identifiers and the script hash are saved in the JSON
  report.
- Truncation and padding are disabled. A 9,002-token probe verified that input
  beyond 8,192 tokens is counted completely.

The JSON report records three views for each block:

| Field | Input counted | Special tokens |
| --- | --- | --- |
| `body_tokens` | Original `ParsedBlock.text` | Excluded |
| `prefixed_tokens` | `search_document: ` + body | `[CLS]` and `[SEP]` included |
| `contextual_tokens` | Prefix + heading path + two newlines + body | `[CLS]` and `[SEP]` included |

Heading paths are joined with ` > `. Heading blocks and blocks without a
heading path use prefix + body, avoiding repetition of the heading itself.
SQL/code whitespace and existing table text are preserved. Counts are obtained
by encoding each complete string; independently counted pieces are not added
together. This serialization is named `block-context-v1`; it does not finalize
the future chunker's input format.

All tables below use **`contextual_tokens`**, including prefix, headings and
special tokens. Percentiles use nearest rank. Threshold counts mean strictly
greater than the stated number.

The task prefix follows the [Nomic model card](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5).
The pinned [tokenizer configuration](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5/blob/e9b6763023c676ca8431644204f50c2b100d9aab/tokenizer_config.json)
and [Sentence Transformers configuration](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5/blob/e9b6763023c676ca8431644204f50c2b100d9aab/sentence_bert_config.json)
both specify 8,192 tokens. The later adapter uses a verified 1024-token
application ceiling; extended context is not tested. These block measurements
remain distinct from the adapter's runtime checks.

## Results

| Source | Blocks | Median | P95 | Maximum | Over 512 |
| --- | ---: | ---: | ---: | ---: | ---: |
| PG-EXPLAIN | 118 | 102 | 378 | 658 | 2 |
| PG-MULTI | 16 | 42 | 282 | 282 | 0 |
| PG-PARTIAL | 42 | 46 | 129 | 293 | 0 |
| PG-STATS | 8 | 63 | 811 | 811 | 1 |
| **All sources** | **184** | **82** | **329** | **811** | **3** |

| Block kind | Blocks | Median | P95 | Maximum | Over 256 | Over 512 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Heading | 8 | 14 | 17 | 17 | 0 | 0 |
| Paragraph | 129 | 77 | 208 | 329 | 4 | 0 |
| Code, including SQL and EXPLAIN output | 46 | 200 | 452 | 658 | 16 | 2 |
| Table | 1 | 811 | 811 | 811 | 1 | 1 |

Across all kinds, 21 blocks exceed 256 tokens, three exceed 512, one exceeds
768, and none exceeds 1,024 or 8,192. There were no `[UNK]` tokens in the
measured contextual inputs.

The three blocks above 512 tokens are:

| Source / one-based block index | Kind | Body only | Prefix + body | With heading context | Source anchor |
| --- | --- | ---: | ---: | ---: | --- |
| PG-STATS / 4 | Table | 785 | 791 | 811 | `PG-STAT-REPLICATION-VIEW` |
| PG-EXPLAIN / 81 | Code | 637 | 643 | 658 | `USING-EXPLAIN-ANALYZE` |
| PG-EXPLAIN / 77 | Code | 499 | 505 | 520 | `USING-EXPLAIN-ANALYZE` |

The table has 21 rows including its header. Code blocks can contain a query
and its plan/output; these measurements do not classify every code block as
a single SQL statement.

## Implications for the next step

A strict 512-token ceiling would require special handling for two code
blocks and the table, even before adjacent explanations are grouped with
them. None of the current blocks needs splitting merely to fit this
candidate's configured 8,192-token limit. That does not imply using 8,192-token
chunks: grouping, retrieval quality and the final serialized chunk size still
need to be checked.

Next, choose a soft target for ordinary chunks and an explicit budget/policy
for intact code and tables, then implement section-aware chunking. Recount
the complete serialized chunks, including any repeated table headers or added
context. These Nomic-tokenizer counts do not establish counts for BGE or any
other tokenizer, and do not select the final embedding model.

## Artifacts and reproduction

Run from the repository root with Python 3.11+ and `uv`:

```sh
uv run --no-project --python 3.11 scripts/measure_block_tokens.py --download-tokenizer
```

The download flag permits the four pinned tokenizer files to be fetched if
missing. The script's isolated dependency environment does not change the
application's dependencies. The four parsed JSON inputs must already exist;
the script does not fetch or parse corpus documents. It rejects multiple
snapshots for the same source to prevent accidental double-counting.

After the initial dependency/tokenizer download, an offline repeat is:

```sh
uv run --offline --no-project --python 3.11 scripts/measure_block_tokens.py
```

Each run writes a new timestamped JSON under `outputs/token-counts/`. Use
`--output PATH` for a chosen filename; existing reports are never overwritten.
Tokenizer files are cached under `data/local/tokenizers/`. Both directories
are ignored by Git. The original report for this measurement is
`outputs/token-counts/nomic-v1.5-pilot-blocks.json`; it contains all 184 block
records and complete input/tokenizer hashes.

Verification: all **552 counts** (three views for each of 184 blocks) matched
`BertTokenizerFast` from `transformers==4.57.6`, loaded only from the cached
tokenizer with network access disabled. The 9,002-token probe also passed
through that wrapper without truncation. The 35 existing offline unit tests
passed. An offline repeat produced identical per-block counts, summaries and
input metadata. Missing cache files, modified tokenizer checksums, duplicate
source snapshots and existing-output protection were also checked. The local
validation record is `outputs/token-counts/nomic-v1.5-pilot-validation.json`.
All four raw and parsed source hashes remained unchanged. No embedding
inference, DB operation or answer evaluation was run.
