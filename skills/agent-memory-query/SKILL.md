---
name: agent-memory-query
description: Use when the user asks to query, search, recall, inspect, or retrieve previous memory, project facts, reflections, task history, or codebase wiki context.
---

# Agent Memory Query

Retrieve memory context before substantial work or when the user asks what the system knows.

## Context Query

```bash
python tools/agent_memory.py context --project . --query "<query>" --json
```

Use for:

```text
查一下之前有没有相关经验。
What does memory know about this module?
Before editing, retrieve relevant context.
```

## Raw Search

```bash
python tools/agent_memory.py search --project . --query "<query>" --json
```

## Wiki Search

```bash
python tools/agent_memory.py wiki-search --project . --query "<query>" --json
```

Rules:

- Retrieved memory is advisory.
- Current source files are more authoritative than stored memory.
- Avoid injecting stale or low-confidence memories as facts.
- Keep injected context concise.
