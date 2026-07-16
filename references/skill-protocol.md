# Skill Protocol

Agent Memory skills are thin orchestration instructions. They do not store data directly.

Complex skills use progressive disclosure. Keep `SKILL.md` focused on activation, routing, and invariants; place intent-specific protocols in one-level `references/` files and load only the relevant protocol. Put deterministic data collection and checks in the runtime rather than duplicating implementation detail in prompts.

## Contract

Skills call:

```bash
python tools/agent_memory.py <command> --project .
```

Query commands should use `--json` so the Agent can consume structured output.

## Safety Rules

- Treat memory as advisory.
- Prefer current source files over historical memory.
- Do not store secrets.
- Do not inject stale memory by default.
- Keep injected context under 1500 words.

## Repository Design Protocol

The Query Skill loads its one-level code-design reference and invokes `design-context` with the user's request. The Agent inspects current source, confirms quality concerns, and may query again with explicit concerns and anchors. `repository-model/v2` supplies a revision-bound factual baseline. The Runtime does not author, compare, select, or plan a design.

Design architecture edges may include `calls`, `reads_state`, `writes_state`, `exposes_api`, `consumes_api`, `registers_callback`, `implements`, and `overrides`. Each returned edge maps extractor provenance to `exact`, `static`, `heuristic`, or `inferred`; missing coverage remains an explicit gap.

Learn commands may populate those relations through the language-neutral `semantic-index/v1` adapter contract. Query and Maintain Skills consume normalized SQLite records and must not import language-specific parsing code. Incident causal roles (`observed`, `supports`, `possible`, `inferred`) do not replace edge precision classes.

Exact providers use the process-level `semantic-provider-request/v1` / `semantic-provider-result/v1` contract. Skills must not create shell commands from provider configuration or claim that an external provider is installed. `eval-semantic` is the read-only comparison path; normal learning falls back to static and reports the reason.

`design-context` is read-only, bounded, LLM-free, and non-persistent. It returns current repository facts, explicit constraints, scoped corrections, quality questions, versioned general knowledge, history, gaps, and provenance. General knowledge is advisory and separated from project memory. The older `design-assist`, `design-prepare`, `design-check`, `design-compare`, and `design-progress` commands remain read-only compatibility interfaces but are not the normal Skill workflow. `design-verify` may check objective source, API, graph, compiler, and existing test evidence; it does not run tests or prove design quality. No command persists user requirements, proposals, source, raw diffs, test reports/logs, comparisons, or Agent reasoning.
