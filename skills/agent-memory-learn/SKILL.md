---
name: agent-memory-learn
description: Use when the user asks the Agent to learn, index, understand, or update memory for a project entry file, feature directory, module, or selected part of the codebase.
---

# Agent Memory Learn

Use this skill to add part of a project to the memory system.

Prefer natural language from the user, then choose the narrowest runtime command.

## Entry File

When the user names an entry file:

```bash
python tools/agent_memory.py learn-entry --project . --entry "<file>" --depth 2 --json
```

This merges the entry-related files into the existing codebase wiki by default. Use `--replace` only when the user asks to reset the learned code scope.

Learning also extracts code log statements and rebuilds lightweight file/function/log edges. This happens automatically through the same command.

Examples:

```text
Learn the code around tools/agent_memory.py.
从 lib/main.dart 开始理解这个项目。
把 src/app.ts 入口相关代码加入记忆系统。
```

## Directory

When the user names a directory:

```bash
python tools/agent_memory.py learn-path --project . --path "<directory>"
```

This merges the directory into the existing codebase wiki by default. Use `--replace` only when the user asks to replace the current learned scope.

Directory learning also refreshes log statement records for the learned files.

Examples:

```text
Learn the skills directory.
把 src/payment 目录加入记忆系统。
```

## Whole Project

When the user asks to refresh the whole codebase wiki:

```bash
python tools/agent_memory.py wiki-index --project .
```

Rules:

- Prefer `learn-entry` or `learn-path` over full-project `wiki-index`.
- Use the smallest scope that satisfies the task.
- Default to incremental merge for partial learning.
- Use `--replace` only for explicit reset/relearn requests.
- After learning, query with `agent-memory-query` before editing.
- Do not treat the wiki as a complete call graph.
- Treat `code_log_matches` and `edge_matches` as diagnosis hints, not runtime traces.
- Treat learned code context as evidence for future reflections and semantic facts.
