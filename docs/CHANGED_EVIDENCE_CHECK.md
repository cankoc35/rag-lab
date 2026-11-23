# Atlas changed-evidence development check

## Purpose and frozen comparison

Check whether Simple RAG follows a changed source fact for the **same question**.
This is one development pair, not held-out accuracy or proof that all answers
are grounded. The owner authorized the complete preparation and test on
2026-11-23. Related variants stay together in the development split.

| Setting | Atlas v1 | Atlas v2 |
| --- | --- | --- |
| Document state | `atlas-docs-v1` | `atlas-docs-v2` |
| Maximum replay lag | 5 seconds, inclusive | 8 seconds, inclusive |
| Sources | Existing inventory and policy | Separate version 2.0 copies |
| Question | P08, unchanged | P08, unchanged |
| Index membership | Original 12 chunks | Separate 12 chunks |

Question: **What is the maximum lag allowed by the Atlas replica lag rule?**

Only the policy's threshold changes as a domain fact. Its paragraph, table
rows and boundary example all use the corresponding value. Document version,
state, date, file URLs and derived snapshot/chunk IDs also change for provenance.
The inventory's domain facts remain identical; its version metadata and policy
state reference are updated. Neither version contains a live lag observation.

Keep Nomic, chunking, dense cosine retrieval, `limit=5`, Luna/settings and
`answer_v1` fixed. Each call is independent, without conversation history or
tools. Select exactly the intended state's snapshots when indexing. A source-ID
filter includes **all versions** of that source and would mix these states.

## Review requirements recorded before calls

- v1: answer 5 seconds and indicate that the boundary is inclusive.
- v2: answer 8 seconds and indicate that the boundary is inclusive.
- Each answer must cite a retrieved passage supporting its state's limit.
- The two calls must have identical raw questions, instructions and generator
  settings; source context and provenance differ by state.
- Gold answers, evidence annotations and this comparison stay outside model
  input. Preserve existing datasets, prompts, indexes, reports and P09's earlier
  explicit-role omission.

The v2 [reference dataset](../data/evaluation/dev/atlas_changed_evidence_v2.json)
pins complete source/chunk scope and P08 evidence. The original
[Atlas dataset](../data/evaluation/dev/atlas_questions.json) remains unchanged.
The earlier LLM-only result is background; it is not a new matched control in
this two-call source-change comparison.

## Reproduce the two paid calls

These require the imported states, cached model, local DB and `.env` API key.
Each command makes one paid request and writes one trace with retrieval/LLM
spans. `--offline` prevents dependency downloads, not API access.

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

## Preparation record

v2 sources: `data/corpus/synthetic/atlas-docs-v2/`.
Saved snapshot run: `data/local/markdown/atlas-docs-v2-3jvgwbl6/`.
Chunks: `data/local/chunks/atlas-docs-v2-section-blocks-v1/`.
Both states have 25 content blocks, one SQL block and two tables preserved in
12 chunks. v2 complete inputs range from 59 to 268 tokens, below the 512 target.
The v2 import was repeated successfully. All three reference datasets passed;
the exact DB chunk/vector payloads and both index scopes were checked. Both
wrong-state dataset/index pairings were rejected before any model call.
Preparation record: `outputs/validation/atlas-changed-evidence-20261123-prepared.json`.

## Results

Both calls completed on 2026-11-23 and met the pre-recorded requirements:

| State | Actual answer | Citation | Trace ID |
| --- | --- | --- | --- |
| v1 | 5 seconds, inclusive; exactly 5 seconds satisfies the rule | `[S1]`, v1 policy | `d3a20767-0fdb-414f-9962-585268ed48ad` |
| v2 | 8 seconds, inclusive; exactly 8 seconds satisfies the rule | `[S1]`, v2 policy | `a626e4f2-8c08-4ec6-8603-3828eb0ad73c` |

Raw reports: `outputs/answers/simple-20261123T115533976548Z.json` (v1) and
`outputs/answers/simple-20261123T115600036150Z.json` (v2).
The relevant policy evidence ranked first in both runs. A fresh read-only
connection verified the exact instructions, question, full chunk texts,
source-label mapping, responses and usage in two traces/four spans. No state
mixing or gold fields entered the model input. The shared workflow code,
prompt, generator settings and model runtime match across the two calls.

Total reported usage: **3,457 input / 60 output / 3,517 total tokens**.
There were two paid requests and no new LLM-only calls. No price estimate was
added; DB cost remains NULL. Per-question workflow times were 2.616 s and
2.284 s, excluding model loading; this is not a latency comparison.

All earlier DB rows, source/dataset JSON files, corpus artifacts and answer
reports are preserved. Totals are eight snapshots, 73 chunks, three indexes/
73 vectors and 24 traces/37 spans; migration remains `0002`.
188 offline unit tests, 26 temporary-table DB integration tests and the
changed-file Ruff checks passed.

Comparison/review: `outputs/comparisons/atlas-changed-evidence-20261123.json`.
Independent persistence/preservation checks:
`outputs/validation/atlas-changed-evidence-20261123.json`.

This pair shows that the answer followed this particular source change. One
generation per state, the small synthetic corpus and version/provenance
differences limit the conclusion. It does not establish general accuracy,
universal source adherence or what the model encountered during training.
