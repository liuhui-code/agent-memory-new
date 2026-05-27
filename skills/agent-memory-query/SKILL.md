---
name: agent-memory-query
description: Use when the user asks to query, search, recall, inspect, or retrieve previous memory, project facts, reflections, task history, or codebase wiki context.
---

# Agent Memory Query

Retrieve memory context before substantial work or when the user asks what the system knows.

This skill intentionally stays small. Complex recursive workflows should use the templates in:

- `docs/templates/diagnosis-memory-query-template.md`
- `docs/templates/change-design-memory-query-template.md`

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
- Use `confidence`, `status`, `source`, `scope`, `evidence`, and `warning` fields when deciding what to inject.
- Avoid injecting stale or low-confidence memories as facts.
- Prefer reflections that include a clear trigger condition and repair action.
- Treat reflections missing scope or actionability as weak hints, not strong rules.
- Keep injected context concise.
- Do not run merge, promotion, duplicate detection, or vault export from this skill.
- For bug diagnosis, use the diagnosis template to query memory recursively as the problem frame changes.
- For design/change planning, use the change design template to query memory recursively as the proposed plan changes.
