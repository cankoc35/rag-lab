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
The complete corpus snapshot, final generator settings, tools, and
the final corpus/evaluation protocol remain open.

## 1. Define the minimum testbed

- Prepare one versioned PostgreSQL documentation snapshot and explicitly
  synthetic deployment runbooks for the PostgreSQL assistant pilot.
  Two English Atlas documents are authored as Markdown, version 1.0/state
  `atlas-docs-v1`; offline snapshot/parsing now produces 37 blocks. They are
  now chunked into 12 chunks, imported and embedded in a separate Atlas-only
  index. The original PostgreSQL index/49 vectors is preserved.
  A later separate Atlas v2 state changes the lag limit from 5 to 8 seconds;
  its two snapshots/12 chunks and isolated index are committed. The unchanged
  P08 question follows this change in two fresh Simple calls.
- The initial docs [allowlist](../data/corpus/sources.json), its offline loader,
  and single-source downloader are implemented. All four selected sources are
  downloaded, hash-verified, parsed and chunked with source/section metadata.
  A separate local Markdown manifest/reader is implemented and verified;
  synthetic-source token measurement/chunking and Atlas reference checks
  are verified. The Markdown import is committed and idempotence-checked;
  Atlas's source-filtered index is committed and independently verified.
- Verify the [20 draft development questions](PILOT_SCOPE.md) against the
  saved documents and sandbox fixtures. Record expected answers and evidence.
  P01–P06 now have a [source-verified development subset](../data/evaluation/dev/README.md);
  P07–P09/P19 have a separate verified Atlas reference subset, preserving the
  original six-question file. P10–P18/P20 still need verified sources/tool fixtures.
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
  trace verified. The owner approved the initial Luna API client on 2026-11-17;
  its connectivity smoke and one full Simple P04 answer have passed.
  Source-linked context, `answer_v1` and retrieval/LLM tracing are implemented;
  the six-question Simple batch later completed. LLM-only was then prepared
  with offline tests; its first live comparison later completed.
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
  application on 2026-11-07; `0001` created the retrieval tables and `0002`
  subsequently added tracing. The corpus/index are populated.
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

The connectivity smoke and one Simple P04 answer passed on 2026-11-17.
The [single/batch runner](../README.md#run-simple-rag) completed P01–P06;
post-run editorial review found four answers meeting recorded requirements
and two partial answers (P03/P05). The live LLM-only control also completed;
the [paired editorial comparison](LLM_ONLY_COMPARISON.md) found Simple more
complete on P02/P04 and LLM-only on P05, with both partial on P03.
The Atlas inventory and policy now have verified local snapshots/parsed blocks.
Atlas token measurement/chunking and P07–P09/P19 references are complete.
The two Atlas snapshots/12 chunks are imported and embedded in a separate,
verified index. The first Atlas retrieval diagnostic found all positive
annotations in the top three across P07–P09; P19 returns Atlas policy text
without establishing a Boreal limit. Both runners now support dataset selection
and the first Atlas answer pair is complete: Simple has two complete answers
and one partial P09 (explicit reporting role omitted); LLM-only abstains on
the three answerable questions. Both abstain appropriately on P19. The subsequent
[changed-evidence pair](CHANGED_EVIDENCE_CHECK.md) is complete: P08 returns
5 seconds inclusive for v1 and 8 seconds inclusive for v2, both supported by
their own policy. The original states, baselines and P09 omission are preserved.
Final scoring remains open.

The [full-text component](FULL_TEXT_RETRIEVAL.md) is now implemented with
index-scoped English OR matching and read-only diagnostics. P05 has 2/3
annotated evidence records in the first five versus 0/3 for dense; other
top-five counts match. This is development evidence coverage, not answer quality.
The initial unsuccessful AND reports are preserved.

The [equal-weight RRF component](HYBRID_RETRIEVAL.md) is also complete with
initial development settings `k=60` and 20 candidates per method. P05 has
1/3 annotations at five and 2/3 at ten; full-text alone has 2/3 at five.
The mixed finding and the original baselines are preserved.

**Proposed next small step:** choose/pin a reranker and candidate/context
limits, then add reranking and compare against the three retrieval baselines.
Simple remains dense-only; Enhanced answer generation and fixed tools are
separate work. Final thesis settings are not frozen.

Preserve the P01–P06 questions and five-result baseline. Build Simple before
hybrid/RRF/reranking and fixed tools; Agentic details come later. Use
[HANDOFF](HANDOFF.md) for code/local inputs, [STATUS](STATUS.md) for checks and
[PROJECT_CONTEXT](PROJECT_CONTEXT.md) for decisions. Changed source states, DB
fixtures/tools and the final protocol still need work; review the method design with the supervisor
and continue literature research in parallel.
