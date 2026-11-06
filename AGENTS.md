# Language policy

- Keep the entire repository in English: documentation, README files, code comments and docstrings, identifiers, messages, prompts, datasets, corpus documents, and evaluation text.
- The user may communicate in Turkish in this chat. Respond in natural Turkish when they do, keeping established AI and software engineering terms in English where appropriate. This chat preference does not change the repository's English-only policy.

# Repository instructions

Before project work or answering “where did we leave off?”, verify this is the `rag-workflow-lab` checkout (not MOTIF-RAG), then read `README.md`, `docs/PROJECT_CONTEXT.md`, `docs/STATUS.md`, and `docs/ROADMAP.md` in that order. Read `docs/METHOD_DESIGN.md` and `docs/EVALUATION_PLAN.md` before changing the experiment, and `docs/LITERATURE_GAPS.md` before making a novelty claim. This is an Agentic RAG chatbot and empirical thesis project, not the MOTIF-RAG evaluation library. The supervisor liked the Agentic RAG direction; the precise research question, corpus, models, and architecture remain open. Label proposals as proposals and ask before making a major scope decision.

For “where did we leave off?”, briefly report the actual current state, confirmed decisions, open decisions, and next concrete action. Do not infer completed work from a plan. If files conflict, flag the conflict instead of silently choosing a thesis direction. After a meaningful work session, update `docs/STATUS.md` with progress and the next action. When a lasting decision changes, update `docs/PROJECT_CONTEXT.md` and, if it affects the sequence, `docs/ROADMAP.md`. Keep `README.md` as the short public entry point; do not duplicate entire conversations in these files.

## Build approach

- Work in small, testable steps. Establish a simple retrieval-and-answer baseline before adding agent orchestration or a UI.
- Keep document ingestion, retrieval, model calls, tools, and evaluation separable. Add dependencies only for a concrete need.
- When adding agentic behavior, document retrieval is one tool; add at least one genuinely different tool that serves the chosen use case. Do not claim tool use where none occurred.
- Preserve source identifiers so answers can cite the evidence actually used. Allow the chatbot to say it lacks sufficient evidence.
- Keep experiments reproducible: record dataset version, model identifier and settings, prompt version, code version, and tool configuration.
- Keep development questions separate from any future held-out thesis test set. Do not invent results or claim Agentic RAG is better without a fair comparison.

## Safety and verification

- Never commit secrets, `.env` files, private documents, or sensitive run traces. Use an example environment file if configuration is added later.
- Do not send private corpus content to a hosted API without the owner's explicit decision.
- Keep networked or paid model tests opt-in; ordinary tests should run without API access.
- After code changes, run relevant tests and report what passed or could not be run. Do not invent setup or test commands before they exist.
- Update `README.md` when a proposed choice becomes a decision or the project reaches a material milestone.

