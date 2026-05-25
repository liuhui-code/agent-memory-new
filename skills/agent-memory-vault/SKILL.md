---
name: agent-memory-vault
description: Use when the user wants to view memory in Obsidian, when memory should be exported to Markdown, or after updates/reflections need to be mirrored for human review.
---

# Agent Memory Vault

Export the SQLite memory source of truth into an Obsidian-compatible Markdown mirror.

Run:

```bash
python tools/agent_memory.py vault-export --project .
python tools/agent_memory.py vault-index --project .
```

Rules:

- Obsidian is a generated mirror, not the source of truth.
- Do not parse edited Obsidian Markdown back into SQLite in the MVP.
- The vault path is `.agent-memory/vault/`.
