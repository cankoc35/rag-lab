# Pilot chunking implementation

**Date:** 2026-11-06. **Status:** Implemented and verified offline on all four
saved PostgreSQL snapshots. The owner requested the 512/1024-token strategy
after reviewing the [block measurements](TOKEN_COUNTS.md). This is the first
pilot configuration, not a demonstrated optimum for retrieval.

## Rules in version 1

- **Soft target: 512 tokens. Application ceiling: 1024 tokens.** Both apply to
  the complete embedding input, including the document prefix, heading path
  and tokenizer special tokens. The application ceiling must not exceed the
  supplied tokenizer/model input budget.
- Process one `ParsedDocument` at a time. Group only consecutive content in
  the same heading path; explicit heading blocks also end a group. Never mix
  source snapshots, child sections or a restored parent section's earlier run.
- Keep every paragraph, code block and table intact. Before packing, pair a
  paragraph immediately followed by code/table when their complete input fits
  1024 tokens. This is an **adjacency heuristic**, not semantic classification.
  If the pair does not fit, keep its blocks separate. Pack units up to the soft
  target; larger intact units stand alone up to the application ceiling.
- Join body blocks with two newlines. Preserve their original text, SQL
  whitespace and structured table cells, including headers and spans. Render
  the heading path once before the body and prepend `search_document: ` by
  default. Store this exact string as `embedding_text` and count it whole.
- Headings become context, not standalone embedding chunks. The corpus runner
  also saves the original indexed heading blocks. Empty/heading-only documents
  produce no embedding chunks.
- **No automatic overlap.** Each non-heading block appears exactly once.
  Previous/next chunk IDs preserve document order across section boundaries.
  They provide links for later context expansion; retrieval does not use them
  yet. Table lag explanations and the nested NULL-lag note retain their paths
  and positions in that chain.
- An individually oversized block raises `ChunkOverflowError`, reporting
  source, snapshot, one-based block index, kind, measured size and ceiling.
  No partial chunk result or truncated block is returned. This version does
  not implement sentence splitting, SQL AST splitting or table row splitting.

## API and provenance

`chunk_document()` in [chunk.py](../src/rag_workflow_lab/ingestion/chunk.py)
accepts a parsed document, a token-counting callable, `TokenizerSpec` and
optional `ChunkSettings`:

```python
chunks = chunk_document(
    parsed_document,
    count_tokens=count_complete_input,
    tokenizer=tokenizer_spec,
    settings=ChunkSettings(target_tokens=512, max_tokens=1024),
)
```

The callable must count special tokens with padding and truncation disabled.
`TokenizerSpec` records the identifier, pinned revision, setup fingerprint and
input budget. The fingerprint must cover tokenizer files, backend version and
counting settings. The function performs no I/O and adds no application
dependency; ordinary unit tests use a synthetic counter.

Each immutable `Chunk` retains source/snapshot ID, source URL/hash, parser and
chunker versions, serialization version, tokenizer identity, budgets, prefix,
heading path, anchors, one-based source-block indices and original blocks.
It also contains body text, exact embedding text/count, zero overlap and
previous/next IDs.

Chunk IDs hash the full parsed document, tokenizer setup, settings, versions,
block positions, serialized input and count. The same inputs reproduce the
same IDs; changing content, snapshot, tokenizer or configuration changes their
identity. Neighbor IDs are assigned after hashing. The algorithm version is
`section-blocks-v1`; the input serialization version is `chunk-context-v1`.

## Run against saved sources

From the repository root, using the tokenizer cache prepared during measurement:

```sh
PYTHONPATH=src uv run --offline --no-project --python 3.11 scripts/chunk_corpus.py
```

The script uses an isolated `tokenizers==0.22.2` dependency, requires exactly
one snapshot per allowlisted source, and reparses each saved HTML through
`parse_snapshot()` with hash/allowlist checks. No corpus or tokenizer download
occurs; socket connections are blocked. Use `--snapshots-dir` to select a
directory containing one snapshot per source if more snapshots accumulate.

Outputs go to a new timestamped directory under `data/local/chunks/`, ignored
by Git. Each snapshot gets a JSON file containing chunks and indexed headings;
`summary.json` records settings, hashes, tokenizer setup and verification.
`--output-dir PATH` selects a new directory explicitly. Existing directories
are rejected, and all documents are validated before output creation.

At the chunking step, the Nomic Embed Text v1.5 tokenizer was still a
candidate, pinned at `e9b6763023c676ca8431644204f50c2b100d9aab`. Nomic has
since been selected for the initial pilot, and a [local embedding smoke check](EMBEDDING_SETUP.md)
passed. All saved chunk token counts still match. No database indexing or
retrieval evaluation has occurred.

## Verified corpus output

Initial run: `data/local/chunks/pilot-section-blocks-v1/`.

| Source | Content blocks | Chunks | Maximum tokens | Chunks above 512 |
| --- | ---: | ---: | ---: | ---: |
| PG-EXPLAIN | 114 | 37 | 688 | 3 |
| PG-MULTI | 15 | 3 | 498 | 0 |
| PG-PARTIAL | 41 | 5 | 502 | 0 |
| PG-STATS | 6 | 4 | 822 | 1 |
| **Total** | **176** | **49** | **822** | **4** |

All 176 non-heading blocks, including **46 code blocks and one table**, remain
unchanged and occur exactly once. Eight heading blocks are retained separately
as indexed metadata and represented in heading context. No chunk exceeds 1024
tokens. The longest code-containing chunk combines PG-EXPLAIN blocks 80–81
at 688 tokens. PG-STATS blocks 3–4, the caption and whole table, total 822.
The subsequent lag explanations and NULL-lag note remain in linked chunks.

Verification passed: **48 offline unit tests** (13 chunking tests plus the
existing 35), deterministic repeated chunk calls, complete-input token checks,
content/heading-boundary checks, neighbor-link checks and unchanged raw/parsed
input hashes. These results establish structural correctness on this corpus;
they do not measure retrieval or answer quality.

P01–P06 now have [source-verified reference answers and chunk evidence](../data/evaluation/dev/README.md).
The local adapter's document/query smoke check has passed, and Alembic revision
`0001` created the retrieval tables. Raw-SQL snapshot/chunk import code is
prepared and verified with rollback. Committed import and corpus indexing
are next; see [HANDOFF.md](HANDOFF.md) for runtime state and inputs.
Keep this chunking configuration versioned and shared across later comparisons.
