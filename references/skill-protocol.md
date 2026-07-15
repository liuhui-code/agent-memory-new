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

The Query Skill loads its one-level code-design reference, authors `design-intent/v1` and candidate Deltas, then invokes deterministic runtime commands. `repository-model/v2` supplies one revision-bound baseline across understanding, comparison, impact, planning, and verification. v1 contracts/Deltas remain compatible; v2 adds evidence-backed coverage, evaluator dimensions, a decision, and a bounded change-plan DAG.

Design architecture edges may include `calls`, `reads_state`, `writes_state`, `exposes_api`, `consumes_api`, `registers_callback`, `implements`, and `overrides`. Each returned edge maps extractor provenance to `exact`, `static`, `heuristic`, or `inferred`; missing coverage remains an explicit gap.

Learn commands may populate those relations through the language-neutral `semantic-index/v1` adapter contract. Query and Maintain Skills consume normalized SQLite records and must not import language-specific parsing code. Incident causal roles (`observed`, `supports`, `possible`, `inferred`) do not replace edge precision classes.

Exact providers use the process-level `semantic-provider-request/v1` / `semantic-provider-result/v1` contract. Skills must not create shell commands from provider configuration or claim that an external provider is installed. `eval-semantic` is the read-only comparison path; normal learning falls back to static and reports the reason.

`design-assist`, `design-prepare`, `design-check`, `design-compare`, `design-progress`, `design-verify`, and `eval-design` are read-only. `design-assist` is the natural-language entry and returns compact structural pattern, principle, and interaction guidance without applying a pattern automatically. Full preparation must precede substantial candidate authoring so the Agent receives a candidate-independent baseline and an unclaimed template. Progress reconstructs the selected plan from bounded current evidence and never stores a session. `design-verify` automatically derives bounded ArkTS/TypeScript symbol, exported-signature, and source-relation Delta evidence from Git and parses existing JUnit/JSON reports; neither command runs tests. `design-outcome` explicitly stores only compact verification metrics. No command persists workbenches, contracts, proposals, progress, source, raw diffs, test reports/logs, comparisons, or generated reasoning. Learned experience and design outcomes cannot establish current architecture or create a hard rule.
