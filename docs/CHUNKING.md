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
retrieval evaluation occurred in that original chunking run.

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
`0001` created the retrieval tables. Four snapshots and 49 chunks have been
imported, field-verified and unchanged after a second run. The indexing script
has produced all 49 vectors twice with identical results in rollback checks;
the owner's later committed run produced one index and 49 verified vectors.
Dense query retrieval now works. The first six-question diagnostic exposes
a P05 reference-evidence miss in the top five; no chunking changes were made.
See [HANDOFF.md](HANDOFF.md) for runtime state and inputs.
Keep this chunking configuration versioned and shared across later comparisons.

## Atlas Markdown chunks — 2026-11-18

The same runner/algorithm now reads saved Atlas snapshots with an explicit
Markdown allowlist. It reparses pinned raw copies and verifies the saved
blocks before chunking; the HTML defaults and core algorithm are unchanged.

```sh
PYTHONPATH=src uv run --offline --no-project --python 3.11 scripts/chunk_corpus.py \
  --sources-manifest data/corpus/synthetic/sources.json \
  --markdown-run data/local/markdown/atlas-docs-v1-ssme1pql
```

The verified run is `data/local/chunks/atlas-docs-v1-section-blocks-v1/`:
six inventory chunks (60–268 tokens) and six policy chunks (59–204 tokens).
All 25 content blocks, one SQL block and two tables remain intact, with no
overlap or heading-boundary crossings. No chunk exceeds 512 tokens. The
existing 512/1024 limits, task prefix and tokenizer identity are retained.

Each source JSON includes content-block `body_tokens` and `contextual_tokens`
in `block_token_counts`, plus the usual heading records/chunks. Inline Markdown
remains in the exact counted text. See [token measurements](TOKEN_COUNTS.md#atlas-markdown-follow-up--2026-11-18).
Snapshot/state/version, raw/parsed/input-manifest hashes and code/tokenizer
provenance remain traceable through the saved artifacts and summary.

All 173 offline unit tests and original question-reference checks passed.
Independent read-back reproduced all Atlas chunks/counts. A temporary HTML
regression run reproduced the original 49 chunks/heading records exactly;
35 protected artifact/core-code hashes were unchanged. Record:
`outputs/validation/atlas-chunking-20261118.json`.
Atlas snapshots/chunks were subsequently imported and embedded in a separate
verified index/12 vectors. Atlas's first retrieval check found all positive
annotations in the top three. The first Atlas Simple/LLM-only answer pair is
also complete, with the original chunks unchanged. See [STATUS](STATUS.md).

## Expanded corpus fit assessment — 2026-11-23

The owner asked whether the existing method suits the expanded documents.
An offline assessment used the cached pinned tokenizer and unchanged
`chunk_document()` on the selected eight PostgreSQL and six Atlas sources.
Chunks were held in memory; no chunk files, vectors or DB records were saved.

| Scope | Content blocks | Candidate chunks | Maximum complete-input tokens |
| --- | ---: | ---: | ---: |
| Original four PostgreSQL sources | 176 | 49 | 822 |
| Four added PostgreSQL sources | 280 | 64 | 508 |
| Six expanded Atlas sources | 96 | 38 | 380 |
| **Total** | **552** | **151** | **822** |

All 108 code blocks and nine tables remain intact and occur exactly once.
No atomic block or candidate chunk exceeds 1024 tokens. Four candidate chunks
exceed the soft 512 target; all four belong to the original baseline.
The longest standalone code/table inputs use 658/811 tokens including context.
Repeated chunk calls are identical. Tokenizer/settings and the original four
sources' chunk counts/maxima match the saved baseline. All 153 protected
source/data/code artifacts are unchanged; only an assessment report was saved.

Two review points remain:

- Six Atlas candidates contain only document-header metadata (58–62 tokens).
  Keeping those fields as metadata rather than independent retrieval content
  is a possible future cleanup, not a demonstrated quality improvement.
- Sixteen code/table-to-following-paragraph adjacencies cross chunk boundaries,
  including three in the added PostgreSQL pages. These are structural flags,
  not sixteen established errors: a paragraph may introduce the next example.
  For instance, PG-CONSTRAINTS blocks 98–99 separate a foreign-key SQL example
  from the following ON DELETE discussion. The current heuristic protects a
  preceding paragraph/code pair, not every following explanation. Neighbor
  links are recorded but are not automatically expanded during retrieval.

Recommendation: retain this method/settings for the initial expanded baseline
and inspect these cases during evidence evaluation. Any later cleanup or
context expansion must be versioned and shared across comparison methods.
This check establishes structural/token fit, not optimal chunk size or
retrieval/answer quality. Heading-aware grouping is consistent with Microsoft's
[document-structure guidance](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-chunk-documents).

Report: `outputs/validation/chunking-fit-20261123T182131Z.json`, including
per-block counts, candidate layouts and flagged adjacencies. The same settings
were subsequently used for the persistent runs below; the algorithm is unchanged.

## Expanded persistent chunks — 2026-11-23

| Saved run under `data/local/chunks/` | Sources | Content blocks | Chunks | Maximum tokens |
| --- | ---: | ---: | ---: | ---: |
| `postgres-expanded-v1-section-blocks-v1/` | 8 | 456 | 113 | 822 |
| `atlas-expanded-v1-section-blocks-v1/` | 6 | 96 | 38 | 380 |
| **Total** | **14** | **552** | **151** | **822** |

Both runs use the existing CLI, cached tokenizer and unchanged 512/1024 rules.
Per-source JSON retains chunks, indexed headings and block token counts;
`summary.json` pins inputs, settings and code/tokenizer fingerprints. No
embedding inference or DB write ran.

Independent read-back matched every saved layout to the fit report and checked
complete-input token counts, exact block coverage/order, headings, serialization
and neighbor links. All 108 code blocks/nine tables are intact. The original
49 chunks, IDs and heading records match the baseline exactly. The existing
import loader accepts all eight HTML snapshots/113 chunks and six Markdown
snapshots/38 chunks without connecting to the DB.

All 43 offline chunk/parser/Markdown tests passed, and 153 protected artifacts
are unchanged. The six metadata-only Atlas chunks and split-follow-up review
points remain as documented; no cleanup or quality optimization was applied.
Record: `outputs/validation/corpus-expansion-chunk-20261123T182736Z.json`.
These records were subsequently imported: ten new snapshots/102 new chunks;
all fourteen selected snapshots/151 chunks matched local records on read-back.
The original 49 chunks were reused, and old controls/indexes are unchanged.
Import record: `outputs/validation/corpus-expansion-import-20261123T184700Z.json`.
The fourteen-snapshot/151-chunk shared embedding index is now created; see
[STATUS](STATUS.md#expanded-shared-embedding-index--2026-11-23) for its ID and checks.
The two local chunk directories are not separate search
corpora for the eventual comparison.
