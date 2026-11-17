# Terminal command reference

Copyable commands for the current implementation, checked against CLI help
on 2026-11-18. Run them from the repository root. Initial dependency, database
and model setup are covered in [README](../README.md),
[PostgreSQL setup](POSTGRES_SETUP.md) and [embedding setup](EMBEDDING_SETUP.md).

Jump to [Simple RAG](#simple-rag), [LLM-only](#llm-only-control), [retrieval](#retrieval-without-answer-generation),
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
| `--all` | Choose this or `--question-id` | Run every question in the pinned dataset; currently six. |
| `--call-api` | Yes for execution | Allow one paid Luna call per question and DB trace writes. |
| `--help` | Optional | Print usage and exit without running the workflow. |

The runner loads Nomic once and uses dense top-five retrieval. Generator
settings are in [pilot.toml](../configs/pilot.toml). Tracing is always enabled
for this runner: each question has its own trace, linked by the batch run ID.
Raw results go to `outputs/answers/<run_id>.json`; exact prompts and step
records go to `traces` / `spans`. Quality review happens after generation.

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
| `--all` | Choose this or `--question-id` | Select all six pinned questions. |
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

## Retrieval without answer generation

Check P01–P06 evidence ranks at 5/10/20 with local Nomic and read-only SQL:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --env-file .env --python 3.11 scripts/check_retrieval.py \
  --index-id "$RAG_INDEX_ID"
```

| Script option | Required? | Meaning |
| --- | --- | --- |
| `--index-id ID` | Yes | Select the stored embedding index. |
| `--trace` | Optional | Also persist question/retrieval traces in PostgreSQL. |
| `--help` | Optional | Print usage and exit. |

Append `--trace` to the command to enable DB logging. Without it, the command
writes only a local report under `outputs/retrieval/`. Neither mode calls Luna.

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
```

`--dataset PATH` selects another question JSON file for this reference checker.
The checker validates references/integrity, not generated-answer quality.
The default file preserves P01–P06. The Atlas file contains P07–P09/P19,
including a corpus-scope unanswerable case with no positive answer chunk.
The current Simple/LLM-only answer runners remain pinned to the original six
questions; they do not yet expose an Atlas dataset selection option.

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

Snapshot and parse the two local Atlas Markdown sources offline:

```sh
PYTHONPATH=src .venv/bin/python -m rag_workflow_lab ingest-markdown --sources-manifest data/corpus/synthetic/sources.json
```

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

`parse-source` still uses the original HTML source list. The chunk and import
runners select Markdown explicitly as shown below.

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

The indexer accepts `--config PATH` (default pilot config) and currently reads
all 61 stored chunks. Atlas has no vectors yet; Atlas-only selection is not
implemented. Index identity includes code/runtime provenance; select the
intended stored index explicitly when running questions afterward.

## Finding command options

Every Python command above accepts `--help`. For example:

```sh
PYTHONPATH=src uv run --offline --locked --no-project --python 3.11 scripts/run_simple_rag.py --help
PYTHONPATH=src .venv/bin/python -m rag_workflow_lab download-source --help
```

Add or update this reference whenever a runnable command or its options change.
