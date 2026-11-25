# Terminal command reference

Copyable commands for the current implementation, updated on 2026-11-25.
Run them from the repository root. Initial dependency, database
and model setup are covered in [README](../README.md),
[PostgreSQL setup](POSTGRES_SETUP.md) and [embedding setup](EMBEDDING_SETUP.md).

Jump to [ask the LLM directly](#ask-the-llm-directly), [Simple RAG](#simple-rag),
[changed evidence](#changed-evidence-control),
[LLM-only](#llm-only-control), [retrieval](#retrieval-without-answer-generation),
[PostgreSQL](#postgresql-and-migrations), [tests](#tests-and-local-checks) or
[corpus preparation](#corpus-preparation-and-embedding-tools).

## Common setup

Run once in each terminal. `RAG_INDEX_ID` is a shell shortcut for the existing
pilot index; use another value only when selecting another stored index.

```sh
cd /Users/cankoc/Desktop/rag-workflow-lab
RAG_INDEX_ID='nomic-d4a8ebdbce1253c45ea50734d984a14a6258d9f1e7a332fd56964011eb886447'
```

Python reads environment variables; `uv --env-file .env` loads the ignored
local file explicitly. The commands below assume its DB settings and API key
are already configured. Retrieval commands also need the imported corpus and
cached model. LLM-only needs the tracked question JSON and DB tracing tables;
it does not need an embedding index or cached embedding model.

| Prefix / uv option | Meaning |
| --- | --- |
| `PYTHONPATH=src` | Make the local Python package importable. |
| `--offline` | Prevent dependency downloads by uv. Model/API requests can still use the network. |
| `--locked` | Require the script lockfile to match its dependencies. Used for scripts with committed locks. |
| `--no-project` | Use the selected script/environment instead of resolving project dependencies. |
| `--env-file .env` | Load local environment variables. |
| `--python 3.11` | Use Python 3.11 for a script's dependency environment. |
| `--python .venv/bin/python` | Use the existing project virtual environment. |

uv options go **before** the script; script options go **after** it. On a fresh
machine, omit `--offline` once to install dependencies. Chunking/token counting
use their uv script environments; `.venv` alone does not include their tokenizer.

## Ask the LLM directly

For a simple question and answer, copy the whole block into the terminal.
Change only the `question` line. It uses the existing `.venv` with the
`generation` dependencies and reads `OPENAI_API_KEY` from `.env`.
Each execution makes **one paid API request** using the generator settings
in `configs/pilot.toml` (currently Luna). It prints only the answer text.
No dataset, retrieval, embedding model or database is used; no project trace
or report is saved. This is a manual question, not an evaluation run.

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python - <<'PY'
from openai import OpenAI
from rag_workflow_lab.config import load_settings
from rag_workflow_lab.llm import generate_text

question = "What is a PostgreSQL index?"
settings = load_settings("configs/pilot.toml").generator
with OpenAI(base_url="https://api.openai.com/v1", timeout=30, max_retries=0) as client:
    result = generate_text(
        client, settings, prompt=question,
        instructions="Answer concisely in English. If you do not know, say so rather than guessing.",
    )
if result["status"] != "completed" or not result["answer"].strip():
    raise SystemExit("The model did not return a complete answer.")
print(result["answer"])
PY
```

`--offline` prevents dependency downloads; the API request still needs internet.
Each execution is independent and has no conversation history. Use the
[LLM-only control](#llm-only-control) for dataset questions with DB tracing.

## Simple RAG

Run one development question; change `P01` to another ID from P01–P06:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/run_simple_rag.py \
  --index-id "$RAG_INDEX_ID" --question-id P01 --call-api
```

Run all six development questions in dataset order:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/run_simple_rag.py \
  --index-id "$RAG_INDEX_ID" --all --call-api
```

| Script option | Required? | Meaning |
| --- | --- | --- |
| `--index-id ID` | Yes | Select the stored embedding index. |
| `--question-id P01` | Choose this or `--all` | Run one dataset question. |
| `--all` | Choose this or `--question-id` | Run every question in the selected dataset: six PostgreSQL or four Atlas. |
| `--dataset PATH` | Optional | Development question JSON; default: PostgreSQL P01–P06. |
| `--call-api` | Yes for execution | Allow one paid Luna call per question and DB trace writes. |
| `--help` | Optional | Print usage and exit without running the workflow. |

The runner loads Nomic once and uses dense top-five retrieval. Generator
settings are in [pilot.toml](../configs/pilot.toml). Tracing is always enabled
for this runner: each question has its own trace, linked by the batch run ID.
Raw results go to `outputs/answers/<run_id>.json`; exact prompts and step
records go to `traces` / `spans`. Quality review happens after generation.

Run the four Atlas questions with their separate index:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/run_simple_rag.py \
  --dataset data/evaluation/dev/atlas_questions.json \
  --index-id nomic-b98238adf1e5b69036fc64a756e3171b7459ad8842e8c3ea280fe9a777ad8ddf --all --call-api
```

Replace `--all` with `--question-id P07` for one Atlas question. The complete
pinned dataset scope must match the index before model loading, trace writes
or paid calls. Dataset path/hash and the scope-check code are recorded as provenance.

## Changed-evidence control

Repeat the same P08 question against the separate Atlas states. Both runs are
already completed; rerunning makes **two paid calls** and adds new DB traces.
Each command retrieves only its selected index's chunks. v1 should answer
5 seconds inclusive; v2 should answer 8 seconds inclusive.

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/run_simple_rag.py \
  --dataset data/evaluation/dev/atlas_questions.json \
  --index-id nomic-b98238adf1e5b69036fc64a756e3171b7459ad8842e8c3ea280fe9a777ad8ddf \
  --question-id P08 --call-api

PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/run_simple_rag.py \
  --dataset data/evaluation/dev/atlas_changed_evidence_v2.json \
  --index-id nomic-5710f4359df83e693a0d994cbf59c45d6ebe9b08695f0ff4d9f75ec062825a55 \
  --question-id P08 --call-api
```

See [CHANGED_EVIDENCE_CHECK](CHANGED_EVIDENCE_CHECK.md) for the comparison,
trace IDs, preparation artifacts and limitations. The model receives the same
raw question and prompt instructions; expected answers stay outside generation.

## LLM-only control

Run one unchanged question using Luna's own knowledge:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/run_llm_only.py --question-id P01 --call-api
```

Run all six questions for comparison with the existing Simple batch:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/run_llm_only.py --all --call-api
```

| Script option | Required? | Meaning |
| --- | --- | --- |
| `--question-id P01` | Choose this or `--all` | Select one unchanged development question. |
| `--all` | Choose this or `--question-id` | Select all questions in the chosen dataset. |
| `--dataset PATH` | Optional | Development question JSON; default: PostgreSQL P01–P06. |
| `--call-api` | Yes for execution | Allow one paid call and trace writes per question. |
| `--help` | Optional | Print usage without calling services. |

Generator settings match Simple: `gpt-6-luna`, reasoning `none`, maximum 1000
output tokens. The separate `llm_only_v1` prompt permits prior knowledge and
asks for concise English answers with uncertainty stated. It gives the task's
PostgreSQL 18 version label, without question-specific facts or answer hints.
Simple's evidence-only `answer_v1` prompt is unchanged.

Only the raw question enters `input`; no documents, gold, tools or prior
responses are supplied. There is no embedding/index lookup or corpus-file
validation. The database connection is solely an autocommit trace writer.
Each question has one `llm_only` trace and one LLM span with `sources: []`.
Reports use `outputs/answers/llm-only-<timestamp>.json`, with the same per-question
fields as Simple. Completion/error handling matches the Simple runner;
unknown cost stays NULL. Correct answers do not prove training-data membership.
The first live LLM-only batch completed; see the
[paired development comparison](LLM_ONLY_COMPARISON.md).

Run the same four Atlas questions without retrieval:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/run_llm_only.py \
  --dataset data/evaluation/dev/atlas_questions.json --all --call-api
```

Dataset selection still reads no corpus files and adds no source-specific
facts to the prompt. The first Atlas pair completed; see the
[comparison](LLM_ONLY_COMPARISON.md#atlas-source-specific-comparison--2026-11-18).

## Retrieval without answer generation

Check unique annotated-chunk recall and required-claim support at 5/10/20 with
local Nomic and read-only SQL. The default
dataset remains PostgreSQL P01–P06:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/check_retrieval.py \
  --index-id "$RAG_INDEX_ID"
```

| Script option | Required? | Meaning |
| --- | --- | --- |
| `--index-id ID` | Yes | Select the stored embedding index. |
| `--dataset PATH` | Optional | Development dataset JSON; defaults to PostgreSQL P01–P06. |
| `--method dense` / `full-text` / `hybrid` | Optional | Retrieval method; default: dense. Full-text needs no cached model; hybrid uses Nomic and RRF. |
| `--trace` | Optional, dense only | Also persist question/retrieval traces in PostgreSQL. |
| `--help` | Optional | Print usage and exit. |

Append `--trace` to a dense command to enable DB logging. Without it, the command
writes only a local report under `outputs/retrieval/`. Neither mode calls Luna.

For Atlas's P07–P09/P19 and its separate 12-vector index:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/check_retrieval.py \
  --dataset data/evaluation/dev/atlas_questions.json \
  --index-id nomic-b98238adf1e5b69036fc64a756e3171b7459ad8842e8c3ea280fe9a777ad8ddf
```

The index must match the dataset's complete pinned snapshot/chunk/input scope;
wrong, incomplete or expanded index membership fails before model loading.
P19's positive evidence scoring is N/A; its returned Atlas context is retained
for inspection. No LLM answer or abstention is tested by this command.

### Expanded 120-question diagnostic

Use the current annotation version and its unchanged shared fourteen-source/151-chunk index:

```sh
RAG_EXPANDED_INDEX_ID=nomic-b2793fdf4ef7869c0589851fb5ee19da961118e251066311e0219f79d534c3d1
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/check_retrieval.py \
  --dataset data/evaluation/dev/expanded_questions_v1_8.json \
  --index-id "$RAG_EXPANDED_INDEX_ID" --method dense
```

Replace `--method dense` with `--method full-text` or `--method hybrid` for the
other two methods, keeping the same dataset/index. Omit `--trace` for read-only
DB access. These runs do not call Luna; `--offline` controls dependency downloads.
The original version-1.7 runs completed on 2026-11-25; see their
[results and preserved report paths](EXPANDED_RETRIEVAL_COMPARISON.md).
Those saved rankings have already been rescored with version 1.8; the command
above starts a fresh retrieval run rather than reusing them.

Schema-4 reports use `annotated-evidence-v2`. Per question,
`evidence_chunk_recall_at_k` counts distinct annotated chunks and
`requirement_coverage_at_k` applies each required claim's `any`/`all` evidence
rule. The new `evidence_chunk_precision_at_k`, `reciprocal_rank_at_k` and
`ndcg_at_k` record the other three measures. `summary` averages per-question
values over the 100 answerable questions; `mean_reciprocal_rank_at_k` is MRR.
Precision divides by the fixed cutoff even with fewer returned results;
nDCG uses binary reference gains. Six summaries at three cutoffs give 18 scores.
The 20 unanswerable records have `null` positive coverage, with their missing-fact
reviews and returned rankings retained. Old evidence-ID fields remain inspectable.
`alternative_evidence_review` lists unannotated candidates as `not_reviewed`;
the script does not decide their semantic relevance or grade abstention.
See the [definitions](EVALUATION_PLAN.md#implemented-ranking-metrics--2026-11-25)
and [manual-review procedure](EVALUATION_PLAN.md#expanded-development-measurements--2026-11-24).

### Rescore saved rankings without retrieval

Use revised annotations with the original reports. These commands access saved
local files only; they need no DB, embedding model, `.env` or API:

```sh
PYTHONPATH=src .venv/bin/python -m scripts.rescore_retrieval \
  --dataset data/evaluation/dev/expanded_questions_v1_8.json \
  --report outputs/retrieval/dense-20261125T133729034758Z.json
PYTHONPATH=src .venv/bin/python -m scripts.rescore_retrieval \
  --dataset data/evaluation/dev/expanded_questions_v1_8.json \
  --report outputs/retrieval/full-text-20261125T133812795420Z.json
PYTHONPATH=src .venv/bin/python -m scripts.rescore_retrieval \
  --dataset data/evaluation/dev/expanded_questions_v1_8.json \
  --report outputs/retrieval/hybrid-20261125T133826756751Z.json
```

`--dataset` selects the revised annotations; `--report` selects a schema-4 raw
report whose dataset hash matches their pinned parent. All three commands were
verified on 2026-11-25. Each writes a new schema-1 annotation-rescore JSON under
`outputs/retrieval/`, preserving the raw report and reusing its rankings/query
hashes/timings. Measurements remain `annotated-evidence-v2`; no new timing was
measured. See [reference changes and scores](REFERENCE_REVIEW.md).

### Prepare and smoke-test Qwen4B

Download the pinned tokenizer/config only and check all saved RRF top-20 inputs:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --python 3.11 scripts/reranker_smoke.py --prepare
```

Download approximately 8 GB of original weights and score two fixed passages:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --python 3.11 scripts/reranker_smoke.py --download-model
```

Omit the flag once weights are local to repeat the smoke offline. `--prepare`
and `--download-model` are mutually exclusive explicit download modes;
`uv --offline` only controls package downloads. These commands use no DB,
`.env` or hosted API. Model settings are in `configs/reranker.toml`; reports
go to `outputs/reranking/`. Tokenizer preparation and the pretrained MPS/float16
two-passage smoke have passed; the weights are already local.
See [setup/results](QWEN_RERANKER_SETUP.md).

### Probe Qwen4B on saved RRF candidates

Rerank the same saved top-20 chunks for explicitly selected questions:

```sh
PYTHONPATH=src:. uv run --offline --locked --no-project --python 3.11 scripts/reranker_probe.py \
  --question-id P05 --question-id P07 --question-id P27 --question-id P19
```

Run all 120 questions (including the four previously probed) in one new report:

```sh
PYTHONPATH=src:. uv run --offline --locked --no-project --python 3.11 scripts/reranker_probe.py --all
```

This scores 2,400 pairs; the small probe suggests roughly 55 minutes, not a
guaranteed runtime. Repeat `--question-id ID` for a subset instead; it cannot be
combined with `--all`. The model loads once from local
files; progress appears after each batch (one pair by default). A new report under `outputs/reranking/`
preserves RRF ranks, reranker scores, timings and the existing metrics at 5/10/20
using development annotations 1.8.0. Reference answers never enter model inputs.
This command makes no downloads, DB/API calls, new retrieval or generated answers.

### Run Qwen4B with batch size four

Score the same four questions with four question/chunk pairs per forward pass:

```sh
PYTHONPATH=src:. uv run --offline --locked --no-project --python 3.11 scripts/reranker_probe.py \
  --config configs/reranker.toml --batch-size 4 \
  --question-id P05 --question-id P07 --question-id P27 --question-id P19
```

For all 120 questions:

```sh
PYTHONPATH=src:. uv run --offline --locked --no-project --python 3.11 scripts/reranker_probe.py \
  --config configs/reranker.toml --batch-size 4 --all
```

Twenty candidates require five forwards per question. `--batch-size` defaults
to 1 and must be positive; profiles, candidate selection and metrics are unchanged.
Inputs are left-padded with attention masks/position IDs and are never truncated.
Each chunk receives its own score. New probe reports use schema 2 and record
`batch_size`. Per-pair times are `null` for batched runs because individual pair
latency was not measured; question/total times remain actual observations.
Compare those times with the batch-size-one baseline; no linear speedup is assumed.

### Run the Qwen0.6B profile

The original 4B profile remains the default. Select the separate pinned 0.6B
profile explicitly. Download its approximately 1.19-GB weights and run the toy
smoke when setting up a fresh machine:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --python 3.11 scripts/reranker_smoke.py \
  --config configs/reranker_qwen06b.toml --download-model
```

Use `--prepare` instead of `--download-model` to check all 2,400 saved inputs
with its tokenizer. To rerank the same four comparison questions:

```sh
PYTHONPATH=src:. uv run --offline --locked --no-project --python 3.11 scripts/reranker_probe.py \
  --config configs/reranker_qwen06b.toml \
  --question-id P05 --question-id P07 --question-id P27 --question-id P19
```

For the complete 120-question set:

```sh
PYTHONPATH=src:. uv run --offline --locked --no-project --python 3.11 scripts/reranker_probe.py \
  --config configs/reranker_qwen06b.toml --all
```

Reports use the `qwen06b-` prefix. These runs use the same saved candidates,
sequential batch size one, full documents and existing metrics as the 4B probe.

### Full-text only

Search with PostgreSQL's English lexemes, OR matching and `ts_rank_cd`. This
uses the existing `.venv` DB dependency without loading Nomic or calling Luna.
It writes only a local `full-text-*.json` report; `--trace` is not supported.
Scores are `text_score` (higher first), distinct from dense cosine `distance`.

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python scripts/check_retrieval.py \
  --method full-text --index-id "$RAG_INDEX_ID"
```

For Atlas v1, use both its dataset and matching index:

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python scripts/check_retrieval.py \
  --method full-text --dataset data/evaluation/dev/atlas_questions.json \
  --index-id nomic-b98238adf1e5b69036fc64a756e3171b7459ad8842e8c3ea280fe9a777ad8ddf
```

For the v2 P08 variant:

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python scripts/check_retrieval.py \
  --method full-text --dataset data/evaluation/dev/atlas_changed_evidence_v2.json \
  --index-id nomic-5710f4359df83e693a0d994cbf59c45d6ebe9b08695f0ff4d9f75ec062825a55
```

The same pinned reference/index-scope checks apply to both methods. Full-text
returns matching chunks only, so its ranking may be shorter than the index.
See [FULL_TEXT_RETRIEVAL](FULL_TEXT_RETRIEVAL.md) for the query-policy check,
dense comparison, raw report paths and limits. RRF/reranking are not run by
the full-text mode.

### Hybrid RRF only

Merge up to 20 dense and 20 full-text candidates with equal-weight RRF,
`k=60`, deduplicating by chunk ID. This needs cached Nomic, the pinned artifacts
and the DB. It saves a local `hybrid-*.json` diagnostic, with no answer call or
trace write; `--trace` supports dense only. The report contains component
ranks/scores and `rrf_score`, with annotated evidence hits at 5/10/20.

PostgreSQL P01–P06:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/check_retrieval.py \
  --method hybrid --index-id "$RAG_INDEX_ID"
```

Atlas v1 P07–P09/P19:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/check_retrieval.py \
  --method hybrid --dataset data/evaluation/dev/atlas_questions.json \
  --index-id nomic-b98238adf1e5b69036fc64a756e3171b7459ad8842e8c3ea280fe9a777ad8ddf
```

Atlas v2 P08:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/check_retrieval.py \
  --method hybrid --dataset data/evaluation/dev/atlas_changed_evidence_v2.json \
  --index-id nomic-5710f4359df83e693a0d994cbf59c45d6ebe9b08695f0ff4d9f75ec062825a55
```

These are development defaults recorded in the report, not CLI tuning options
or final thesis budgets. The diagnostic returns the bounded union (at most
40 chunks), not the complete index ranking. See
[HYBRID_RETRIEVAL](HYBRID_RETRIEVAL.md) for the mixed P05 result and limitations.

## PostgreSQL and migrations

Start PostgreSQL in the background and wait until healthy:

```sh
docker compose up -d --wait postgres
```

Inspect running/stopped containers, recent logs, or stop PostgreSQL while
retaining its data volume:

```sh
docker compose ps --all
docker compose logs --tail 50 postgres
docker compose stop postgres
```

`-d` means background mode; `--wait` waits for health; `ps --all` includes
stopped containers. Append `--follow` to the logs command to stream new logs;
Ctrl+C ends log viewing.

Check DB connectivity, PostgreSQL version and pgvector with read-only SQL:

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python -m rag_workflow_lab check-db
```

Inspect the applied revision and migration history:

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python alembic current
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python alembic history
```

Append `--verbose` to either for more detail. Apply pending migrations
explicitly; this command **changes the database schema**:

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python alembic upgrade head
```

Append `--sql` to `upgrade head` to print the upgrade SQL without applying it.
Current repository head is `0002`; see [migration notes](../migrations/README.md).

## Luna connectivity check

Send one fixed English message with one paid request. This smoke test checks
the API connection without reading the corpus or writing DB traces:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/llm_smoke.py --call-api
```

Options: `--call-api` is required for execution; `--config PATH` selects a TOML
file (default `configs/pilot.toml`). Text, status and usage print to stdout.

## Tests and local checks

Run offline unit tests without API, database or model access:

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests/unit -v
```

Check pinned question references against local artifacts; no model or DB:

```sh
.venv/bin/python scripts/check_document_questions.py
.venv/bin/python scripts/check_document_questions.py --dataset data/evaluation/dev/atlas_questions.json
.venv/bin/python scripts/check_document_questions.py --dataset data/evaluation/dev/expanded_questions.json
.venv/bin/python scripts/check_document_questions.py --dataset data/evaluation/dev/expanded_questions_v1_1.json
.venv/bin/python scripts/check_document_questions.py --dataset data/evaluation/dev/expanded_questions_v1_2.json
.venv/bin/python scripts/check_document_questions.py --dataset data/evaluation/dev/expanded_questions_v1_3.json
.venv/bin/python scripts/check_document_questions.py --dataset data/evaluation/dev/expanded_questions_v1_4.json
.venv/bin/python scripts/check_document_questions.py --dataset data/evaluation/dev/expanded_questions_v1_5.json
.venv/bin/python scripts/check_document_questions.py --dataset data/evaluation/dev/expanded_questions_v1_6.json
.venv/bin/python scripts/check_document_questions.py --dataset data/evaluation/dev/expanded_questions_v1_7.json
.venv/bin/python scripts/check_document_questions.py --dataset data/evaluation/dev/expanded_questions_v1_8.json
```

`--dataset PATH` selects another question JSON file for this reference checker.
The checker validates references/integrity, not generated-answer quality.
The default file preserves P01–P06. The Atlas file contains P07–P09/P19,
including a corpus-scope unanswerable case with no positive answer chunk.
Simple/LLM-only runners also accept `--dataset`; Simple requires an index
matching that dataset's exact pinned scope. The completed
`expanded_questions_v1_8.json` contains the same 120 unique dev questions
(100 answerable/20 unanswerable), including new P81–P130. No preparation slots
remain. Version 1.8 changes twelve annotations only; version 1.7 preserves the
original completed file. Earlier `expanded_questions.json` and versions `1.1.0`
through `1.6.0` preserve the ten- through seventy-question files. All expanded versions pin the
same fourteen sources/151 chunks and require the shared index
`nomic-b2793fdf4ef7869c0589851fb5ee19da961118e251066311e0219f79d534c3d1`
for retrieval or Simple runs. Original PostgreSQL/Atlas files and defaults remain.
The negative-case check distinguishes absent entities from editorial reviews
of missing facts about documented entities; it does not automatically judge
semantic unanswerability or generated-answer quality.

Run opt-in integration tests against local PostgreSQL with applied `0002`:

```sh
PYTHONPATH=src RAG_LAB_TEST_DB=1 uv run --offline --no-project --env-file .env --python .venv/bin/python python -m unittest discover -s tests/integration -v
```

These DB tests write temporary tables/synthetic data and preserve public
records. `-v` gives verbose unittest output. To run one test file, add
`-p 'test_simple_runner.py'` to the unit-test command.

Check unused/undefined names and patch whitespace:

```sh
uvx --offline ruff check src scripts tests migrations --select F
git diff --check
```

The Ruff command assumes the tool is already cached locally.

## Corpus preparation and embedding tools

Snapshot and parse an explicitly selected Atlas Markdown state offline.
For the original two-document state:

```sh
PYTHONPATH=src .venv/bin/python -m rag_workflow_lab ingest-markdown --sources-manifest data/corpus/synthetic/sources.json
```

The six expanded documents are authored and hash-pinned; this command creates
their persistent snapshots/parsed blocks as a separate new run:

```sh
PYTHONPATH=src .venv/bin/python -m rag_workflow_lab ingest-markdown --sources-manifest data/corpus/synthetic/atlas-expanded-v1/sources.json
```

The saved expanded run is `data/local/markdown/atlas-expanded-v1-hyrbftbg/`
(six snapshots/134 blocks). Reuse it for chunking; invoking the command again
creates a separate new run. It preserves old states and makes no model or DB calls.

`--sources-manifest PATH` is required; `--config PATH` defaults to
`configs/pilot.toml`. The manifest pins source IDs, versions, state, filenames
and SHA-256 hashes. Only named `.md` files beside it are read. A changed file
fails hash verification; no directory scan includes other corpus or gold files.

Each run creates a new folder under `data/local/markdown/`, containing a
subfolder per snapshot with the raw Markdown, `manifest.json` and `parsed.json`.
The command prints paths and block counts. It uses no dependencies beyond the
standard library and makes no network, model or DB calls. No chunking runs.
The scoped reader supports ATX headings, paragraphs/lists, triple-backtick
fences and outer-pipe tables without escaped pipes; inline Markdown is retained.
Anchors such as `L31` identify one-based source lines.

`parse-source` defaults to the original HTML list; select all eight with
`--config configs/corpus_expansion.toml`. The chunk and import runners select
Markdown explicitly as shown below.

The current pilot corpus is already imported/indexed. The following commands
prepare artifacts or write corpus/index records; they are separate from
running questions against the existing index.

Check local configuration and the source allowlist:

```sh
PYTHONPATH=src .venv/bin/python -m rag_workflow_lab check-config
PYTHONPATH=src .venv/bin/python -m rag_workflow_lab check-sources
```

Both accept `--config PATH` (default `configs/pilot.toml`). They print JSON;
neither downloads documents nor connects to PostgreSQL.

Download a new HTML snapshot for one selected source (network access), or
parse the existing pinned PG-EXPLAIN snapshot offline (JSON to stdout):

```sh
PYTHONPATH=src .venv/bin/python -m rag_workflow_lab download-source --source-id PG-EXPLAIN --timeout 30
PYTHONPATH=src .venv/bin/python -m rag_workflow_lab parse-source --source-id PG-EXPLAIN --manifest data/local/snapshots/PG-EXPLAIN-20261102T173311Z-yhdhybna/manifest.json
```

Both accept `--config PATH`. `--source-id ID` is required; download accepts
`--timeout SECONDS` (default 30), while parsing requires `--manifest PATH`.
Downloads create new snapshot IDs; existing evaluation references stay pinned
to their recorded snapshots.

**PostgreSQL expansion snapshots**

The [expansion config](../configs/corpus_expansion.toml) selects eight sources;
the original config still selects four. Inspect the expanded list offline:

```sh
PYTHONPATH=src .venv/bin/python -m rag_workflow_lab check-sources --config configs/corpus_expansion.toml
```

The four added pages are already captured; use this only to request a fresh
snapshot of one page:

```sh
PYTHONPATH=src .venv/bin/python -m rag_workflow_lab download-source --config configs/corpus_expansion.toml --source-id PG-INDEX-TYPES --timeout 30
```

Other added IDs: `PG-ISOLATION`, `PG-VACUUM`, `PG-CONSTRAINTS`. Reuse the saved
[snapshot IDs/hashes](STATUS.md#saved-official-documentation-snapshots) for
reproducible work. This config contains no model settings; it is for source
acquisition/checks and `parse-source`. The saved pages are not yet chunked or
embedded. Original model/DB commands continue using `configs/pilot.toml`.

All eight HTML parser JSON files are already saved under `data/local/parsed/`.
To reparse one pinned expansion source offline and print its JSON to stdout:

```sh
PYTHONPATH=src .venv/bin/python -m rag_workflow_lab parse-source --config configs/corpus_expansion.toml --source-id PG-INDEX-TYPES --manifest data/local/snapshots/PG-INDEX-TYPES-20261123T175401Z-9bwzmjkd/manifest.json
```

Chunk saved snapshots, or measure saved parser-block token counts:

```sh
PYTHONPATH=src uv run --offline --no-project --python 3.11 scripts/chunk_corpus.py
PYTHONPATH=src uv run --offline --no-project --python 3.11 scripts/measure_block_tokens.py
```

Measure and chunk the saved Atlas Markdown run with the same algorithm/tokenizer:

```sh
PYTHONPATH=src uv run --offline --no-project --python 3.11 scripts/chunk_corpus.py \
  --sources-manifest data/corpus/synthetic/sources.json \
  --markdown-run data/local/markdown/atlas-docs-v1-ssme1pql
```

Both Markdown arguments are needed; `--snapshots-dir` applies only to HTML mode.

The expanded runs are already saved (113 PostgreSQL and 38 Atlas chunks):

```sh
PYTHONPATH=src uv run --offline --no-project --python 3.11 scripts/chunk_corpus.py \
  --sources-manifest data/corpus/postgres_expanded_v1.json \
  --output-dir data/local/chunks/postgres-expanded-v1-section-blocks-v1

PYTHONPATH=src uv run --offline --no-project --python 3.11 scripts/chunk_corpus.py \
  --sources-manifest data/corpus/synthetic/atlas-expanded-v1/sources.json \
  --markdown-run data/local/markdown/atlas-expanded-v1-hyrbftbg \
  --output-dir data/local/chunks/atlas-expanded-v1-section-blocks-v1
```

These exact commands reject their now-existing output directories. Reuse the
saved runs; choose a new `--output-dir` only for an intentional repeat. No
embedding or DB write occurs during chunking.

The reader verifies pinned snapshot metadata/raw hashes, reparses the saved
copies and checks saved blocks before chunking. Each chunk JSON also records
`block_token_counts` for non-heading blocks: body counts exclude special tokens;
contextual counts include prefix, heading path and special tokens. Headings
are saved separately and used as chunk context. The original HTML defaults
remain unchanged. Neither command embeds text or writes to the database.

| Tool | Optional script arguments |
| --- | --- |
| `chunk_corpus.py` | `--sources-manifest PATH`: source allowlist; `--snapshots-dir PATH`: HTML snapshots; `--markdown-run PATH`: select saved Markdown inputs; `--tokenizer-dir PATH`: cached tokenizer; `--output-dir PATH`: new chunk directory. |
| `measure_block_tokens.py` | `--parsed-dir PATH`: parsed blocks; `--tokenizer-dir PATH`: tokenizer cache; `--download-tokenizer`: allow its download; `--output PATH`: new JSON report. |

Chunking uses the cached tokenizer and makes no downloads/model calls. Token
measurement needs its cached tokenizer unless the explicit download flag is
used. Defaults write new artifacts under `data/local/chunks/` and
`outputs/token-counts/` respectively; existing output paths are not overwritten.

Check one document/query embedding pair locally:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --python 3.11 scripts/embedding_smoke.py
```

Options: `--config PATH` (default pilot config), `--dataset PATH` (default
development questions), `--question-id ID` (default P04), `--download-model`
(explicitly allow model downloads), `--output-dir PATH` (new output directory).
Default reports are under `outputs/embeddings/`; no DB records are written.

Import existing snapshot/chunk artifacts, then index stored chunks locally.
Both commands **commit DB records**:

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python scripts/import_corpus.py
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/index_corpus.py
```

The importer accepts `--chunks-dir PATH` (default the existing
`pilot-section-blocks-v1` run). To import Atlas's two snapshots/12 chunks:

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python scripts/import_corpus.py \
  --sources-manifest data/corpus/synthetic/sources.json \
  --markdown-run data/local/markdown/atlas-docs-v1-ssme1pql \
  --chunks-dir data/local/chunks/atlas-docs-v1-section-blocks-v1
```

`--markdown-run PATH` requires its separate `--sources-manifest PATH`; chunk
inputs are selected with `--chunks-dir PATH`. The default command retains the
HTML path. Markdown snapshot provenance/raw hashes, saved blocks, complete coverage, SQL/
table contents and rendered embedding inputs are checked before connecting.
One transaction commits snapshots and chunks together; repeated identical
imports preserve rows and conflicting existing IDs fail. The legacy
`source_snapshots.downloaded_at` stores `captured_at` for local Markdown.
No migration or embedding generation is performed by the importer.

Both expanded imports are committed (14 selected snapshots/151 chunks;
10 snapshots/102 chunks were new). With the DB running, these commands can
repeat either group while preserving identical existing records:

```sh
PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python scripts/import_corpus.py \
  --sources-manifest data/corpus/postgres_expanded_v1.json \
  --chunks-dir data/local/chunks/postgres-expanded-v1-section-blocks-v1

PYTHONPATH=src uv run --offline --no-project --env-file .env --python .venv/bin/python python scripts/import_corpus.py \
  --sources-manifest data/corpus/synthetic/atlas-expanded-v1/sources.json \
  --markdown-run data/local/markdown/atlas-expanded-v1-hyrbftbg \
  --chunks-dir data/local/chunks/atlas-expanded-v1-section-blocks-v1
```

The indexer accepts `--config PATH` (default pilot config) and repeatable
`--source-id ID` or `--snapshot-id ID`, mutually exclusive. With neither it
selects all stored chunks. Source IDs include all versions; snapshot IDs select
exact versions.

The expanded shared index is committed:
`nomic-b2793fdf4ef7869c0589851fb5ee19da961118e251066311e0219f79d534c3d1`.
These fourteen snapshots contain exactly 151 chunks. The command below was
used to generate its local Nomic vectors; reuse the saved index for questions.
An intentional repeat requires inference again and preserves identical rows:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/index_corpus.py \
  --snapshot-id PG-EXPLAIN-20261102T173311Z-yhdhybna \
  --snapshot-id PG-MULTI-20261105T191707Z-96nc6y0c \
  --snapshot-id PG-PARTIAL-20261105T191707Z-kmf7w4sp \
  --snapshot-id PG-STATS-20261105T191715Z-zm7b259y \
  --snapshot-id PG-INDEX-TYPES-20261123T175401Z-9bwzmjkd \
  --snapshot-id PG-ISOLATION-20261123T175402Z-2_17hssf \
  --snapshot-id PG-VACUUM-20261123T175402Z-lwwvgshl \
  --snapshot-id PG-CONSTRAINTS-20261123T175403Z-5w4qbo7f \
  --snapshot-id LOCAL-INVENTORY-fe15d4078bde0d46 \
  --snapshot-id LOCAL-POLICY-cb95d1ffabe529d7 \
  --snapshot-id LOCAL-QUERY-CATALOG-5040c4097f291207 \
  --snapshot-id LOCAL-BACKUP-680206816dba1b08 \
  --snapshot-id LOCAL-MAINTENANCE-913bdddf1eb94c40 \
  --snapshot-id LOCAL-ACCESS-8206771d2a7ea5a3
```

Exact snapshot selection excludes the original Atlas v1/v2 controls while
preserving their existing indexes. Prepare the expanded question dataset and
its scope references before using that new index with the question runners.

To embed only Atlas v1's 12 chunks (already committed locally):

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/index_corpus.py \
  --snapshot-id LOCAL-INVENTORY-246a17e09e73d871 --snapshot-id LOCAL-POLICY-d7124ea3bb39455d
```

For Atlas v2's separate 12 chunks (also committed locally):

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/index_corpus.py \
  --snapshot-id LOCAL-INVENTORY-45793a301230aad6 --snapshot-id LOCAL-POLICY-41c47f77f549370a
```

Every requested source or snapshot must have stored chunks; otherwise it fails
before inference/writes. Sorted unique selections are recorded in index settings.
See [STATUS](STATUS.md) for all four index IDs. Index identity includes code/runtime
provenance, so avoid unnecessary re-indexing after code changes. Select the
intended stored index explicitly when running questions afterward.
The diagnostic and both paid answer runners support explicit dataset selection.

## Finding command options

Every Python command above accepts `--help`. For example:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --python 3.11 scripts/run_simple_rag.py --help
PYTHONPATH=src .venv/bin/python -m rag_workflow_lab download-source --help
```

Add or update this reference whenever a runnable command or its options change.
