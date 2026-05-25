---
name: agent-memory-update
description: Use when the user says to remember something, when a durable project fact or user preference is discovered, or when a task episode should be stored in local Agent Memory.
---

# Agent Memory Update

Store durable facts or task episodes.

For a user preference or project fact:

```bash
python tools/agent_memory.py update \
  --project . \
  --type semantic \
  --fact "<fact>" \
  --source user \
  --confidence 1.0
```

For a task episode:

```bash
python tools/agent_memory.py update \
  --project . \
  --type episode \
  --task "<task>" \
  --summary "<summary>" \
  --outcome "<outcome>"
```

Rules:

- Store only durable facts, preferences, decisions, and reusable observations.
- Do not store secrets, API keys, passwords, or private credentials.
- Use `source user` for explicit user instructions.
- Use lower confidence for inferred facts.
