# Agentic RAG Development Roadmap

**Status:** Agentic RAG direction confirmed by the owner after a positive
supervisor discussion. Initial Simple/Enhanced definitions were approved on
2026-11-13; detailed Agentic design and the final experiment protocol remain open.
The owner rejected MLflow on 2026-11-16. Project-owned PostgreSQL tracing is
the new direction. Its [code and migration](TRACING_PLAN.md) were subsequently
applied on the owner's instruction and verified with one real P04 query.

The working study compares three RAG workflows and an adaptive router. The
owner approved a PostgreSQL docs + synthetic-runbook pilot with frozen sandbox
DB state and prior-knowledge controls. All corpus documents, questions/datasets,
prompts, answers and evaluation text will be
in English, as confirmed by the owner on 2026-11-05; multilingual support is
not required. The first four PostgreSQL 18 docs
sources/page-section scope are selected; all four HTML snapshots are saved
and hash-verified, with their IDs recorded in STATUS.md. The offline HTML
parser is implemented and all four snapshots have source-linked block outputs.
Section-aware chunking now produces 49 verified chunks with preserved code/tables.
A pinned local Nomic adapter passed a document/query runtime check and offline repeat.
The complete corpus snapshot, generator model, tools, and
the final corpus/evaluation protocol remain open.

## 1. Define the minimum testbed

- Prepare one versioned PostgreSQL documentation snapshot and explicitly
  synthetic deployment runbooks for the PostgreSQL assistant pilot.
- The initial docs [allowlist](../data/corpus/sources.json), its offline loader,
  and single-source downloader are implemented. All four selected sources are
  downloaded, hash-verified, parsed and chunked with source/section metadata.
  Synthetic-source ingestion remains to be implemented.
- Verify the [20 draft development questions](PILOT_SCOPE.md) against the
  saved documents and sandbox fixtures. Record expected answers and evidence.
  P01–P06 now have a [source-verified development subset](../data/evaluation/dev/README.md);
  P07–P20 remain drafts awaiting synthetic documents/tool fixtures.
- Define bounded, read-only DB tools and frozen state fixtures. An observation
  fixture must be labeled synthetic rather than presented as measured telemetry.
- Include LLM-only, changed-evidence, and insufficient-evidence controls;
  retain ordinary public-documentation questions too.
- Review and refine the [method-level design](METHOD_DESIGN.md) requested by
  the supervisor. Its format and detail level still need feedback.
- Expand the [source-backed literature comparison](LITERATURE_GAPS.md): paper,
  evaluated methods, data, metrics, and limitations relevant to this question.
  Do not call something a gap without checking the original paper.

**Done when:** the versioned sources, verified pilot answers/evidence, and tool
contracts are clear enough to build against. A method design and question
draft exist; the source/fixture verification work is not done yet.

## 2. Establish the local foundation

- Python package/CLI and module/data/test directory scaffolds now exist. The
  owner requested all planned file paths together; component behavior is still
  implemented in the stages below. Source/download/parser/chunking code, local
  embedding inference and the DB connection check work. Raw-SQL storage/import
  code is implemented and four snapshots/49 chunks are imported. Indexing is
  committed and dense query retrieval is implemented. The first P01–P06
  diagnostic, P05 wording diagnosis and repeatable 5/10/20 checker exist.
  Custom trace/span code and migration `0002` are applied, with one real query
  trace verified. Generator/answer work is next.
- Follow the [code structure and staged implementation plan](CODE_STRUCTURE.md)
  when filling in the scaffold modules.
- Run PostgreSQL with `pgvector` locally in Docker.
  The [Compose service and extension bootstrap](POSTGRES_SETUP.md) are now
  configured and passed temporary live checks. Python `check-db` also passed
  against the project service with PostgreSQL 18.6 and pgvector 0.8.7.
- Use parameterized raw SQL for application database access without an ORM
  (owner decision, 2026-11-06). Psycopg 3.3.8 is now an optional dependency,
  installed locally; environment settings and the explicit read-only
  connection/extension check are implemented. Alembic is selected, installed
  and configured for manually written raw-SQL revisions. The owner authorized
  application on 2026-11-07; revision `0001` is applied and its four empty
  retrieval tables are verified.
- Configure model, embedding and DB connections as needed. Review the small
  applied PostgreSQL trace/span migration and writers.
- Start with a command-line interface rather than a web UI.

**Done when:** a clean checkout can start the database and run the documented
starter checks.

## 3. Build fixed RAG first

- Clean, chunk, embed, and index the documents.
- Implement the approved Simple baseline: local dense document retrieval,
  followed by one final-answer call. Build and inspect retrieval first.
- Generate answers from retrieved evidence with source citations.
- Allow an insufficient-evidence response.
- Trace inputs, retrievals, outputs, latency, token usage, and estimated cost.

**Done when:** the baseline answers the development questions through an
end-to-end CLI and its question/step records can be inspected in PostgreSQL.

## 4. Add Enhanced RAG, then design Agentic RAG

- Share the baseline's ingestion, retrieval, model, and tool components across
  the three workflows where their behavior is the same.
- Implement the approved Enhanced document path: dense + PostgreSQL full-text
  retrieval, RRF merge/deduplication and reranking, then one shared answer call.
  Keep corpus/chunks, embedding and generator settings, answer prompt and maximum
  context token budget comparable with Simple. Measure component ablations on
  development data; model choices and numeric budgets are still open.
- Define bounded Enhanced tool steps in Python with explicit conditions/order;
  native LLM function calling is not required. Preserve the approved synthetic
  runbook/frozen-DB-state scope and comparable relevant tool access for the
  eventual fixed-versus-dynamic comparison.
- Defer detailed Agentic design until this stage after the fixed workflows.
- Use LangGraph for agentic orchestration.
- Expose document retrieval and the additional capability as tools.
- Let the agent select tools and decide whether more information is needed.
- Validate tool arguments and results.
- Add iteration, retry, timeout, and stopping limits.

**Done when:** the enhanced and agentic workflows both complete representative
questions; the agent uses tools without uncontrolled loops and both workflows
provide evidence for their answers.

## 5. Create a repeatable evaluation set

Expand the pilot set to cover:

- straightforward lookup;
- evidence spread across documents;
- current-information questions;
- questions requiring a non-retrieval tool;
- ambiguous questions; and
- unanswerable questions.

Keep development questions separate from any future held-out thesis test set.
Include the approved prior-knowledge controls from the evaluation draft;
keep related scenario/state variants in the same development/test split.
Before final testing, turn the [evaluation draft](EVALUATION_PLAN.md) into a
fixed protocol: define each metric, its calculation, question-type breakdown,
primary comparison, and acceptable quality margin. Record answer
quality, evidence use, tool behavior, latency, token usage, cost, and failures
for every run with stable question/run IDs and the model/configuration used.
Preserve per-run results so aggregate tables can be reproduced; include router
overhead in routed-policy results.

## 6. Evaluate the adaptive routing hypothesis

Compare always-simple, always-enhanced, always-agentic, and routed policies on
the same held-out questions. Report answer quality, cost, and latency by
question type, including router overhead. Define the acceptable quality
margin before final testing. Adaptive routing itself is not claimed as novel.

## Intentionally postponed

- Production web UI or hosted service.
- Multi-agent architecture.
- Long-term memory.
- GraphRAG.
- Multiple vector databases or orchestration frameworks.
- A new tracing or evaluation platform.
- Additional tools without evidence that the use case needs them.

## Immediate next step

The [512/1024-token chunker](CHUNKING.md) is implemented and verified on all
four saved sources. P01–P06 have verified answers and chunk evidence.
The [local Nomic adapter](EMBEDDING_SETUP.md) passed its first document/query
check. PostgreSQL + pgvector Compose is configured and temporarily verified.
The Psycopg dependency, environment settings and `check-db` command are now
implemented. The command passed on the persistent project service with
PostgreSQL 18.6, pgvector 0.8.7 and a verified read-only transaction.
Alembic setup and its live connection check have also passed.
Revision `0001` was applied on 2026-11-07; the four retrieval tables are verified
and were empty at that check. On 2026-11-12 the service was healthy and the
owner requested the committed import: four snapshots and 49 chunks are now
stored and field-verified. A second script run left contents/counts unchanged.
Embedding index/vector save functions now pass validation and temporary-table
DB tests. The corpus indexing script is now implemented and passed two full
real-Nomic runs with identical results and rollback. The owner subsequently
ran committed indexing; one index and 49 verified vectors now exist. The first
P01–P06 retrieval check now uses that index. Progress messages have
been added; no indexing rerun is needed for that change.
Dense `search_chunks()` passed SQL checks on 2026-11-14 with unchanged public
data. `retrieval.retrieve()` now composes query embedding and search after
index compatibility checks. Its first six-question real-model diagnostic found
annotated evidence in the top five for five questions; P05 has no reference hit.
P05's follow-up found E1/E2/E3 at ranks 17/11/46. Explicit `multicolumn` wording
raised E1/E2 to 1/2; SQL and stored data checks passed. The owner-approved
`scripts/check_retrieval.py` now reports full ranks and evidence hits at
5/10/20; two real-model runs matched with unchanged public data. P05 improves
from 0/3 annotated hits at 5/10 to 2/3 at 20; this does not select a production
context budget or demonstrate answer quality. The custom trace/span migration
and writers are applied, including checker `--trace` integration. Four tracing
DB tests passed and one real P04 trace/span is committed and verified. The
owner's one-question test is complete; a full traced batch remains optional.
The owner rejected MLflow on 2026-11-16. Generator selection and the evidence-
context/answer-prompt contract follow the first tracing increment. The
Simple/Enhanced designs are now approved, but hybrid/RRF/reranking and tool
steps are implemented after the baseline; Agentic details come later.
The [session handoff](HANDOFF.md) maps the inputs and existing code for this step.
Prepare the synthetic sources/evidence listed in
[PILOT_SCOPE.md](PILOT_SCOPE.md) and build retrieval.
Keep the embedding model/settings fixed across workflow comparisons and select
the generator before answer runs. Review the method
design with the supervisor and continue literature work in parallel; keep the
final thesis protocol open until its remaining choices are resolved.
