---
name: agent-memory-wiki
description: Use when the Agent needs lightweight codebase understanding, needs to search files or symbols, or when project structure changed and the codebase wiki should be refreshed.
---

# Agent Memory Wiki

Update and search the lightweight codebase wiki.

Refresh the index:

```bash
python tools/agent_memory.py wiki-index --project .
```

Search the index:

```bash
python tools/agent_memory.py wiki-search --project . --query "<query>" --json
```

Rules:

- Use the wiki to narrow source inspection, not replace it.
- Re-index after large file moves or new modules.
- The MVP wiki is lightweight and does not include a complete call graph.
- For user-facing workflows, prefer natural language requests and let this skill choose the runtime command.
- Future entry-file learning should call `learn-entry` once that runtime command exists; until then use `wiki-index` and `wiki-search`.
