# Hybrid retrieval with equal-weight RRF

Implemented and checked on 2026-11-23. This component combines the existing
dense and English OR full-text searches. It does not implement reranking or
the complete Enhanced answer workflow.

## Initial development settings

These settings were recorded before the live runs and were not tuned afterward:

| Setting | Value |
| --- | --- |
| RRF rank constant | `k = 60` |
| Method weights | Dense `1.0`, full-text `1.0` |
| Candidates per method | At most 20, from the same selected index |
| Deduplication | `chunk_id` |
| Final ordering | RRF score descending, then chunk ID |
| Diagnostic cutoffs | 5, 10, 20 |

Each list contributes `1 / (60 + rank)`, with ranks starting at 1. An absent
candidate contributes zero for that list. Equal coefficients do not imply
that each chunk receives half its score from each method. Cosine and full-text
scores are retained for inspection but do not enter the fusion formula. See
the [RRF definition](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion).

## Code and outputs

`retrieval.reciprocal_rank_fusion(dense_matches, full_text_matches)` combines
the two lists without mutating them. It preserves source/citation fields and
returns one record per chunk with `rrf_score`, `dense_rank`, `full_text_rank`,
`distance` and `text_score`. A missing component rank/score is NULL: the chunk
was not in that method's bounded candidate list, not necessarily absent from
its complete ranking.

`retrieve_hybrid(connection, embedder, index_id, question, limit=5)` retrieves
up to 20 candidates per method, fuses their union and returns up to `limit`
records. It reuses dense model/index compatibility checks and the caller's
model, connection and transaction. The union can contain at most 40 chunks.
Only the unchanged raw question is passed to the searches; gold stays outside.

`scripts/check_retrieval.py --method hybrid` loads Nomic once per run and uses
read-only SQL. The diagnostic requests the full bounded union, rather than
only the helper's default five results, and records fusion settings, component
ranks/scores, query/data/index/code provenance and annotated hits at 5/10/20.
Its report remains schema version 2. `--trace` currently supports dense only;
hybrid diagnostics create no traces. Simple still uses its existing dense path.

## Results on unchanged development questions

Cells count annotated evidence records in the first five. They are not answer
grades, distinct chunks or exhaustive semantic-recall measurements.

| State / question | Dense | Full-text | RRF |
| --- | ---: | ---: | ---: |
| PostgreSQL P01 | 1/1 | 1/1 | 1/1 |
| PostgreSQL P02 | 1/1 | 1/1 | 1/1 |
| PostgreSQL P03 | 2/2 | 2/2 | 2/2 |
| PostgreSQL P04 | 2/2 | 2/2 | 2/2 |
| PostgreSQL P05 | 0/3 | 2/3 | 1/3 |
| PostgreSQL P06 | 2/4 | 2/4 | 2/4 |
| Atlas v1 P07 | 1/1 | 1/1 | 1/1 |
| Atlas v1 P08 | 2/2 | 2/2 | 2/2 |
| Atlas v1 P09 | 3/3 | 3/3 | 3/3 |
| Atlas v1 P19 | N/A | N/A | N/A |
| Atlas v2 P08 | 2/2 | 2/2 | 2/2 |

**P05 is mixed:** E2 reaches RRF rank 4 and E1 rank 9. RRF finds one annotated
record at five and two at ten, improving on dense but trailing full-text at
five. E3 has dense/full-text ranks 46/43, outside both 20-candidate windows,
so fusion cannot recover it. The P05 union has 26 unique chunks. Agreement on
less relevant passages can push useful passages down; no weights or budgets
were changed to hide this result. Reranking is a separate next step, not an
assumed fix.

P19 returns related Atlas content without establishing a Boreal limit. No
answer or abstention was generated. The two P08 states are related development
variants. These small checks do not establish general accuracy or a best RRF
parameter choice; final candidate/context budgets remain open.

## Records and verification

The later pilot coverage audit confirmed that these runs cover all **ten
verified unique questions**, not all twenty pilot drafts. P08's second state
makes eleven observations. P10–P18/P20 still lack verified references and,
for most cases, the required sandbox catalog/lag/plan evidence. Retrieval-only
methods cannot supply an unprovided database observation. Selected source
scopes are fully chunked/indexed; embeddings are not limited to gold passages.
Audit: `outputs/comparisons/pilot-retrieval-coverage-20261123.json`.

Raw hybrid reports under `outputs/retrieval/`:

- PostgreSQL: `hybrid-20261123T164729411936Z.json`.
- Atlas v1: `hybrid-20261123T164729409769Z.json`.
- Atlas v2: `hybrid-20261123T164729410070Z.json`.

Component reports remain unchanged; their paths and all per-question ranks
are in `outputs/comparisons/dense-full-text-rrf-20261123.json`.
Independent checks reconstructed each union, score, component rank and tie
order from the preserved component reports, then checked source fields/index
scope against the DB. All eleven question/state observations passed.

201 offline unit tests, 32 temporary-table DB integration tests and all three
reference checks passed. All public rows/counts and 79 protected source/data/
artifact/report hashes are unchanged. No migration, dependency, embedding
update, API call or trace write was needed. The original dense retrieval
function body is unchanged. Validation:
`outputs/validation/rrf-retrieval-20261123.json`.

See [COMMANDS](COMMANDS.md#hybrid-rrf-only) for copyable runs. Qwen3-Reranker-4B
is now selected and its 120-question comparison is verified; see
[results](QWEN_RERANKER_COMPARISON.md). Next integrate RRF top-20 → Qwen4B →
initial top-5 into Enhanced's document retrieval path. Keep unreranked baselines
unchanged; final candidate/context budgets remain open.
