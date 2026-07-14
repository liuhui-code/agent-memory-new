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

The Query Skill loads its one-level code-design reference, then invokes deterministic runtime commands. Stable runtime-only schemas are `design-contract/v1`, `design-delta/v1`, `design-rules/v1`, and `design-evaluation/v1`.

Design architecture edges may include `calls`, `reads_state`, `writes_state`, `exposes_api`, `consumes_api`, `registers_callback`, `implements`, and `overrides`. Each returned edge maps extractor provenance to `exact`, `static`, `heuristic`, or `inferred`; missing coverage remains an explicit gap.

Learn commands may populate those relations through the language-neutral `semantic-index/v1` adapter contract. Query and Maintain Skills consume normalized SQLite records and must not import language-specific parsing code. Incident causal roles (`observed`, `supports`, `possible`, `inferred`) do not replace edge precision classes.

`design-check`, `design-compare`, `design-verify`, and `eval-design` are read-only. They do not persist contracts, proposals, raw diffs, comparisons, verification results, or generated reasoning. Learned experience cannot establish current architecture or create a hard rule.
