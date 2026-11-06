# Chunking technical documents — source-backed research notes

**Date:** 2026-11-05. **Status:** Official product documentation and open-source
implementations were reviewed. The initial pilot strategy was implemented on
2026-11-06; see [CHUNKING.md](CHUNKING.md). No retrieval benchmark has shown
the strategy superior.

## Scope and limits of the findings

The target is PostgreSQL documentation mixing explanatory prose, SQL examples,
EXPLAIN output and tables. Splitters designed for source-code repositories
address only the code portion of this use case.

This review does not measure industry adoption rates. It describes documented
capabilities of production tools; availability does not establish universal
customer adoption or superiority on our corpus.

**Our inference from the sources:** First partition documents into structural
units, then group them within a size budget, and expand from matching search
fragments to broader source context when needed. Inspect a ready-made
splitter's overflow behavior separately to protect SQL integrity.

## Documented tool behavior

| Tool / product | Verified approach | Implication / limit for our use case |
| --- | --- | --- |
| Unstructured | Groups consecutive elements after partitioning. `by_title` uses heading boundaries, with configurable small-section merging. Oversized individual elements are text-split. Tables are isolated and become `TableChunk` elements when oversized. | Element preservation applies within size limits. Default use does not guarantee whole SQL statements. [Documentation](https://docs.unstructured.io/open-source/core-functionality/chunking) |
| Docling | `HybridChunker` refines hierarchical chunks using a tokenizer, splitting oversized pieces and merging suitable small peers. It can repeat table headers in continuation chunks. `LineBasedTokenChunker` tries to preserve lines but may split a line that alone exceeds the limit. | Structure and token budgets work together. Preserving a line does not preserve an entire multiline SQL query. [Documentation](https://docling-project.github.io/docling/concepts/chunking/) |
| Azure AI Search | Its Markdown parser creates sections from headings and carries heading metadata. Code blocks and tables are plain text inside the content field. | Header-based parsing does not imply SQL syntax analysis. [Documentation](https://learn.microsoft.com/en-us/azure/search/search-how-to-index-azure-blob-markdown) |
| LangChain | `MarkdownHeaderTextSplitter` groups by headings; a recursive splitter can subsequently constrain size. The default header splitter may change whitespace/newlines; the docs point to an experimental alternative for format preservation. | Structure recognition in stage one does not guarantee SQL preservation in stage two. [Documentation](https://docs.langchain.com/oss/python/integrations/splitters/markdown_header_metadata_splitter) |
| LlamaIndex CodeSplitter | Processes source code through a Tree-sitter AST parser and recursively splits oversized child nodes according to size limits. | Syntax-aware splitting exists. SQL dialect/grammar support, incomplete examples and non-SQL EXPLAIN output need separate handling. [API and source code](https://developers.llamaindex.ai/python/framework-api-reference/node_parsers/code/) |
| Amazon Bedrock | Hierarchical chunking searches small child chunks and returns broader parent chunks. Semantic chunking uses embedding similarity, a buffer and breakpoint thresholds. | Retrieval units and answer context can differ in size. This offers a design example for returning whole SQL examples; it is not implemented here. [Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-chunking.html) |
| LlamaIndex SemanticSplitter | Chooses sentence breakpoints using embedding similarity. The docs note that its sentence regex primarily targets English and the threshold may need tuning. | No guarantee of preserving code blocks as SQL statements. An alternative to compare later on natural-language content. [Example](https://developers.llamaindex.ai/python/examples/node_parsers/semantic_chunking/) |
| Anthropic Contextual Retrieval | Adds chunk-specific explanatory context before embedding and BM25 indexing. | Context enrichment is separate from boundary selection and differs from simply adding heading metadata. Automatic LLM explanations are not required for our first pilot. [Method](https://www.anthropic.com/research/contextual-retrieval) |

## Important distinctions for SQL

- An HTML/Markdown code block, a SQL statement and a SQL file are different
  units. A block may contain several independent statements, one statement,
  or a query and its plan output together.
- An AST is a code syntax tree. Splitting at node boundaries does not guarantee
  each resulting piece is an independently executable complete query. The
  CodeSplitter above also descends into oversized child nodes.
- PostgreSQL documentation includes teaching placeholders such as `...` and
  plan output that is not SQL. Sending every `pre` block to a SQL parser is
  therefore an unsuitable default. This is our inference from the current
  source examples.
- If multiple statements must be separated, a simple `split(';')` should not
  be assumed sufficient. Strings, comments and PostgreSQL dollar-quoted
  content need to be respected; SQL-aware splitting must be tested separately.
- Define an explicit fallback for a single query above the input limit.
  Avoid silently truncating it while presenting the result as a complete query.

## Local observations on the current corpus

These measurements use `block.text` in
`data/local/parsed/<snapshot_id>.json`. They are character counts, not token
measurements or retrieval results.

| Source | Largest code block, characters | Largest table text, characters |
| --- | --- | --- |
| PG-EXPLAIN | 1738 | — |
| PG-MULTI | 67 | — |
| PG-PARTIAL | 263 | — |
| PG-STATS | — | 3372 |

The parser already separates code and tables and preserves source/snapshot/
heading/anchor metadata. A new HTML parsing or OCR pipeline is unnecessary
for the initial pilot. Exact token fit depends on the selected embedding
model/tokenizer. [Sentence Transformers documentation](https://www.sbert.net/examples/sentence_transformer/applications/computing-embeddings/README.html#input-sequence-length)
also explains that inputs above the model limit may be truncated.

## Project strategy — initial pilot implementation

The owner requested **structure-aware, code-preserving, tokenizer-aware
chunking** after reviewing the measured corpus:

1. Use existing `ParsedDocument` / `ParsedBlock` records. Do not combine
   different sources or snapshots into one chunk; preserve heading hierarchy.
2. Use a 512-token soft target and 1024-token application ceiling, including
   headings, prefixes and special tokens. Require that the application ceiling
   fits within the supplied tokenizer/model input budget.
3. Keep normal-sized SQL/code blocks atomic. Do not split one in the middle
   to fill the target size. Link explanation/example/plan blocks through IDs;
   retain neighbor links for later context expansion. Immediately preceding
   paragraphs may be paired with code/table as a documented adjacency heuristic.
4. If code exceeds the soft limit but fits the hard limit, it may be retained
   alone. If it exceeds the hard limit, stop with an explicit error/flag.
   Choose a longer-input model, SQL-aware segmentation or parent-child
   retrieval before introducing a fallback. That choice remains open.
5. Preserve tables whole when they fit; oversized tables currently raise an
   explicit error. Row-group splitting with repeated column headers/captions
   is a future fallback, not implemented in version 1. Keep NULL-lag notes
   connected through section metadata and document-order links.
6. Record chunk ID, parser/chunker versions, settings, tokenizer/model ID and
   source-block positions. Start with zero automatic overlap; measure later
   context needs on development examples.

The implementation uses existing parser contracts and an injected tokenizer
counter without a new chunking framework. No separate chunking model or final
embedding model has been selected. Implementation results and the reproducible
offline corpus command are in [CHUNKING.md](CHUNKING.md).

## Proposed next verification

Block loss, code/table integrity, token overflow, anchors and deterministic
output have been checked offline. After retrieval exists, inspect whether required
evidence spans appear in top-k for development questions, whether complete
SQL/plan context is returned and whether results contain redundant copies.

Compare the starting approach with a simple token/recursive baseline using
the same corpus, embedding model and development questions. Semantic chunking
could be a later alternative; each needs a separate ingestion/index version.
Keeping chunking fixed across workflow comparisons and avoiding tuning on the
held-out set follows the [method](METHOD_DESIGN.md) and
[evaluation](EVALUATION_PLAN.md) drafts. These are proposed checks, not completed
experiments or results.
