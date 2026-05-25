---
name: agent-memory-query
description: Use before starting substantial local coding or agent work, or when the user asks to recall project facts, prior lessons, reflections, task history, or codebase wiki entries.
---

# Agent Memory Query

Retrieve concise memory context before substantial work.

Run:

```bash
python tools/agent_memory.py context --project . --query "<user task>" --json
```

Use the result as advisory context only.

Rules:

- Inject at most 1500 words.
- Prefer high-confidence semantic facts and recent reflections.
- Do not inject stale memories unless clearly labeled.
- Current source files are more authoritative than stored memory.
- If the database is missing, use `agent-memory-init`.
