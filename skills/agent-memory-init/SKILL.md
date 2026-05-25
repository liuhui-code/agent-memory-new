---
name: agent-memory-init
description: Use when a local project needs Agent Memory initialized or verified, when .agent-memory or memory.db is missing, or when the user asks to initialize the memory system.
---

# Agent Memory Init

Initialize and verify the project-local memory runtime.

Run:

```bash
python tools/agent_memory.py init --project .
python tools/agent_memory.py doctor --project .
```

Rules:

- Use this before query/update/reflect if `.agent-memory/` is missing.
- Initialization must be idempotent.
- Do not modify shell profiles.
- If `doctor` fails, report the failed check exactly.
