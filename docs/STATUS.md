# Current status

**Last updated:** 2026-11-17. This is the current implementation boundary.
Detailed dated records are in [STATUS_HISTORY.md](STATUS_HISTORY.md);
plans are in [ROADMAP](ROADMAP.md), decisions in [PROJECT_CONTEXT](PROJECT_CONTEXT.md),
and code/artifact paths in [HANDOFF](HANDOFF.md).

## Implemented

| Area | Current state |
| --- | --- |
| Sources | Four saved PostgreSQL 18 HTML snapshots; allowlist, downloader and offline parser |
| Chunking | 184 parsed blocks → 49 chunks; all content/code/table blocks preserved; target 512 / ceiling 1024; maximum observed 822 tokens |
| Embedding | Pinned local Nomic; normalized 768-dimensional document/query vectors |
| Database | Applied Alembic `0002`; four snapshots, 49 chunks, one index and 49 vectors |
| Retrieval | Index/model compatibility checks, query embedding and dense cosine search; default `limit=5` |
| Diagnostics | P01–P06 full ranks and annotated hits at 5/10/20; immutable JSON reports |
| Tracing | Lifecycle writers and opt-in `--trace`; one real P04 trace/span verified |
| Generator | Luna Responses API client, generator config and locked single-request smoke; hosted inference not verified |
| Questions | P01–P06 source-verified with 13 evidence records over nine chunks/blocks; P07–P20 drafts |

Nomic revision: `e9b6763023c676ca8431644204f50c2b100d9aab`, CPU float32,
1024-token application limit. Committed index:
`nomic-d4a8ebdbce1253c45ea50734d984a14a6258d9f1e7a332fd56964011eb886447`.
Keep pinned questions/snapshots/chunks/index unchanged when comparing workflows.

## Retrieval findings and limits

The initial dense check found annotated evidence in the top five for five
questions. P05's E1/E2/E3 ranks are 17/11/46; adding `multicolumn` in an
exploratory probe moved E1/E2 to 1/2. SQL distances and stored inputs passed
independent checks. This shows wording sensitivity, not a selected rewrite policy.

The repeatable checker matched prior ranks in two real-model runs. P05 has
0/3, 0/3 and 2/3 annotated hits at 5/10/20; P06 has 2/4 at each cutoff, with
valid evidence alternatives. These are annotation counts, not answer grades
or a held-out result; the sweep did not select a new production context budget.
See the [development results](../data/evaluation/dev/README.md#repeatable-retrieval-checker).

The owner authorized migration `0002` on 2026-11-16. A real P04 check committed
one `ok` trace and retrieval span; E1/E2 ranked 1/2 and answer/usage/cost stayed
NULL. Trace ID: `db808e0d-76ed-4148-9996-2a8988cc4ce7`. The full six-question
traced batch is available but has not run. Details: [TRACING_PLAN](TRACING_PLAN.md).

## Latest verification — 2026-11-17

- **124 offline unit tests passed**, plus the six-question pinned-reference check.
- **19 local PostgreSQL integration tests passed**, using temporary tables and
  synthetic vectors. `check-db` confirmed read-only PostgreSQL 18.6 + pgvector
  0.8.7; Alembic reported `0002 (head)`. Service health was checked this date,
  not inferred from older records.
- Ruff's unused/undefined-name checks and installed-dependency compatibility
  checks passed. The CLI refinement matched the prior version in 11 cases,
  including outputs, error codes and mocked side effects.
- Earlier this date, three real-SDK mock-transport checks covered completed,
  incomplete and HTTP 429 replies without network access or retries.
- `OPENAI_API_KEY` was absent at the last setup check. No hosted inference,
  generated answer or LLM/tool trace is verified. The smoke reads no corpus.

The review shortened repeated orientation prose and moved chronological
records intact to [history](STATUS_HISTORY.md). Source IDs, corpus artifacts,
embedding/index behavior, migrations and dataset annotations are unchanged.
Generated `.egg-info` metadata is ignored and no longer tracked; its files
remain on disk. All six public-table counts/fingerprints matched before and
after the review.
See `outputs/validation/refine-2026-11-17.json` for the final review checks;
older evidence paths are listed in the history.

## Next small step

Set `OPENAI_API_KEY` locally and run the [opt-in Luna smoke](../README.md#check-the-luna-api-client).
Initial settings: `gpt-6-luna`, reasoning `none`, maximum 1000 output tokens;
OpenAI SDK `3.51.0`. The smoke requires `--call-api`, uses Standard processing,
`store=False`, a 30-second timeout and zero retries. It makes no DB writes.

The 2026-11-17 price check was $0.10 / million input and $0.50 / million output
tokens: 4,000 uncached input + 1,000 billed output would cost $0.0009 before
extra services/taxes. This is an estimate, not observed usage. Recheck
[official pricing](https://developers.openai.com/api/docs/models/gpt-6-luna) before budgeting.

After connectivity, agree source-linked context/answer-prompt behavior and
connect one P04 answer, with retrieval and LLM spans under one workflow trace.
Build Simple before Enhanced's hybrid/RRF/reranking and fixed tools.

## Not yet completed

- Evidence-context assembly, answer prompt, Simple/LLM-only workflows and LLM tracing.
- Hybrid/full-text search, RRF, reranker and Enhanced tool conditions.
- Synthetic runbooks, Markdown ingestion, frozen DB fixtures and validated tools.
- Agentic workflow, LangGraph installation and adaptive router.
- Verified P07–P20 answers, a held-out test set, rubric/judges, metrics,
  quality margin, final model/settings choices, sample size and result runner.
- Supervisor review of the method design and a complete literature review.

The working study and controls are approved directions, not a frozen protocol
or evidence that Agentic RAG is better. Earlier observability/Enron proposals
are background. Detailed decisions live in PROJECT_CONTEXT and METHOD_DESIGN.

## Saved official-documentation snapshots

Each directory is under `data/local/snapshots/` and contains
`<source_id>.html` plus `manifest.json`. The parser used these saved copies.
PG-EXPLAIN was downloaded on 2026-11-02, the others on 2026-11-05; do not assume
an atomic, simultaneous capture. Synthetic sources are not yet included.

| Source ID | Snapshot directory | Bytes | SHA-256 |
| --- | --- | --- | --- |
| PG-EXPLAIN | `PG-EXPLAIN-20261102T173311Z-yhdhybna` | 70029 | `22b29b578fe330ce2a1eca03dcc6ecfb540eb6211e21cfa4d61d93d55e87bf7e` |
| PG-MULTI | `PG-MULTI-20261105T191707Z-96nc6y0c` | 21135 | `df6631e673511c60f9ea45dab2b5c69ab80ff1a747117af72236006dc59063d1` |
| PG-PARTIAL | `PG-PARTIAL-20261105T191707Z-kmf7w4sp` | 26463 | `ab67b4a1909a9be617038dcea60e34b7d8f898ca9e8b5f0a569e4df389caa18e` |
| PG-STATS | `PG-STATS-20261105T191715Z-zm7b259y` | 290994 | `4b872e1cd30fd40679c000bf3e5efc15d9f1e4d7a003aed877cfe2c09381c45c` |

## Parser outputs

Four example files are under `data/local/parsed/<snapshot_id>.json`, using
the snapshot IDs above. The CLI writes JSON to stdout; these examples were
saved separately during verification and are ignored by Git. Parser version:
`postgresql-html-v1`. There are 184 content blocks, not embedding chunks.

| Source ID | Heading | Paragraph | Code | Table |
| --- | --- | --- | --- | --- |
| PG-EXPLAIN | 4 | 82 | 32 | 0 |
| PG-MULTI | 1 | 12 | 3 | 0 |
| PG-PARTIAL | 1 | 30 | 11 | 0 |
| PG-STATS | 2 | 5 | 0 | 1 |

The second PG-STATS heading is `Note`, nested under its section's heading
path. This parser expects the pilot's explicitly closed DocBook HTML tags;
general web/PDF/Markdown and nested content tables are not supported.

## First steps when returning

Follow the reading order and resume checks in [HANDOFF](HANDOFF.md). Inspect
Git/service state before editing or running DB commands; dated successful
checks do not prove that local services are running in a new session.
