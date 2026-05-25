# Skill Protocol

Agent Memory skills are thin orchestration instructions. They do not store data directly.

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
