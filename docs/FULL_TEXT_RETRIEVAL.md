# Full-text retrieval development check

Implemented on 2026-11-23 as the first Enhanced retrieval component. Simple
still uses its existing dense path. Fusion, reranking and Enhanced answer
generation are not implemented by this step.

## Search behavior

`store.search_chunks_full_text(connection, index_id, question, limit=5)` uses
parameterized raw SQL and the caller's connection/transaction. It searches only
chunks belonging to the selected embedding index, so PostgreSQL, Atlas v1 and
Atlas v2 remain separate. Vectors define membership; no vector calculation or
embedding model is used by full-text search.

PostgreSQL normalizes the unchanged question with `to_tsvector('english', ...)`.
The resulting unique lexemes are individually quoted and combined with OR in
a `tsquery`. Chunk bodies use the same English processing. Matching chunks are
ordered by `ts_rank_cd` descending, then chunk ID; the default ranking weights
and normalization 0 are used. Source/snapshot IDs, citation URLs and metadata
are returned alongside `text_score`. This score is not a cosine distance or a
probability. Empty, stop-word-only and unmatched queries return no rows.

This uses PostgreSQL's existing [text-search parsing/ranking](https://www.postgresql.org/docs/18/textsearch-controls.html).
The generic OR policy is this project's initial development choice, not a
special PostgreSQL RAG feature. It uses no selected gold terms, synonyms,
question rewrite or LLM. Broad terms can also return irrelevant passages.

No migration, new stored column, GIN index, re-embedding or dependency was
needed for the current 73-chunk corpus. Search vectors are computed per query;
this is not a scalability or latency claim. PostgreSQL also documents
[full-text search without a physical index](https://www.postgresql.org/docs/18/textsearch-tables.html).

## Query-policy check

The first implementation used `plainto_tsquery('english', question)`, which
requires every remaining term to match. All eleven question/state observations
returned zero candidates. Those three AND reports are preserved. A general OR
policy was then selected on development data and tested again; the question
texts and corpus states stayed fixed. This is not a held-out policy comparison.

Initial AND reports, under `outputs/retrieval/`:

- PostgreSQL: `full-text-20261123T160138426889Z.json`.
- Atlas v1: `full-text-20261123T160138423955Z.json`.
- Atlas v2: `full-text-20261123T160138423917Z.json`.

## Dense versus full-text results

Each cell counts **annotated evidence records in the top five**, not distinct
chunks, correct answers or general retrieval recall. Some annotations share a
chunk, and equivalent evidence may exist elsewhere.

| State / question | Dense | Full-text OR |
| --- | ---: | ---: |
| PostgreSQL P01 | 1/1 | 1/1 |
| PostgreSQL P02 | 1/1 | 1/1 |
| PostgreSQL P03 | 2/2 | 2/2 |
| PostgreSQL P04 | 2/2 | 2/2 |
| PostgreSQL P05 | 0/3 | 2/3 |
| PostgreSQL P06 | 2/4 | 2/4 |
| Atlas v1 P07 | 1/1 | 1/1 |
| Atlas v1 P08 | 2/2 | 2/2 |
| Atlas v1 P09 | 3/3 | 3/3 |
| Atlas v1 P19 | N/A | N/A |
| Atlas v2 P08 | 2/2 | 2/2 |

P05 E1/E2 move from dense ranks 17/11 to full-text ranks 3/2. E3 remains low
at 43 versus dense 46. Full-text also returns unrelated passages, and not all
rank movements improve: P04 evidence moves from 1/2 to 2/3 and Atlas P08 from
1 to 2. These findings justify inspecting a later fusion, not assuming it works.
P19 returns eight related Atlas chunks without establishing a Boreal limit;
no answer or abstention was generated. P08's v2 observation is a state variant,
not an independent new question.

Final raw reports, under `outputs/retrieval/`:

| State | Dense | Full-text OR |
| --- | --- | --- |
| PostgreSQL | `dense-20261123T160248409228Z.json` | `full-text-20261123T160338258476Z.json` |
| Atlas v1 | `dense-20261123T160248407229Z.json` | `full-text-20261123T160338256041Z.json` |
| Atlas v2 | `dense-20261123T160248407240Z.json` | `full-text-20261123T160338256008Z.json` |

The [command reference](COMMANDS.md#full-text-only) has copyable commands.
`check_retrieval.py --method full-text` needs the DB/pinned artifacts, but no
cached model or ML packages. It records the query policy, raw-question hash,
dataset/index/code provenance, ranking scores and annotation hits at 5/10/20.
Reports remain schema version 2; `text_score` identifies full-text ranks, while
dense ranks retain `distance`. Dense is still the default. `--trace` currently
supports dense only; full-text diagnostics are read-only and untraced.

## Verification and next step

193 offline unit tests and 31 temporary-table DB integration tests passed.
Coverage includes stemming, OR matching, deterministic score ties, limits,
same-source version isolation, unindexed chunks, empty/quoted input, transaction
ownership and a CLI path without models. All three reference checks passed.
The final report rankings/scores were read back against live SQL. All public
rows and 69 protected source/dataset/artifact/report files were unchanged.
Dense search/storage function bodies are unchanged. Migration remains `0002`;
totals remain eight snapshots/73 chunks, three indexes/73 vectors and 24 traces/
37 spans. No API call or trace write occurred.

Local records: `outputs/comparisons/dense-vs-full-text-20261123.json` and
`outputs/validation/full-text-retrieval-20261123.json`.

The later [equal-weight RRF check](HYBRID_RETRIEVAL.md) is now complete:
P05 has 1/3 annotations at five and 2/3 at ten, trailing full-text alone at
five. Its initial `k=60` and 20 candidates per method were not tuned afterward.
Reranking, final study budgets and Enhanced answer generation remain open.
