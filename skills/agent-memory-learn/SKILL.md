---
name: agent-memory-learn
description: Use when the user asks the Agent to learn, index, understand, or update memory for a project entry file, feature directory, module, or selected part of the codebase.
---

# Agent Memory Learn

Use this skill to add part of a project to the memory system.

Prefer natural language from the user, then choose the narrowest runtime command.

`--project` selects the current memory archive and query context. If the code to learn lives elsewhere, pass that external source root with `--source`; learned data is still archived under `--project`.

## Entry File

When the user names an entry file:

```bash
python tools/agent_memory.py learn-entry --project . --entry "<file>" --depth 2 --json
```

For an external source tree:

```bash
python tools/agent_memory.py learn-entry --project . --source "<external-project>" --entry "<file>" --depth 2 --json
```

This merges the entry-related files into the existing codebase wiki by default. Use `--replace` only when the user asks to reset the learned code scope.

Learning also extracts code log statements and rebuilds lightweight file/function/log edges. This happens automatically through the same command.

Read the returned `parse_stats` field. If `files_indexed`, `symbols_total`, and `code_logs_total` are unexpectedly low, tell the user what scope was learned and suggest a narrower entry file or a broader directory.

Examples:

```text
Learn the code around tools/agent_memory.py.
从 lib/main.dart 开始理解这个项目。
从 entry/src/main/ets/pages/Index.ets 开始理解这个鸿蒙页面。
把 src/app.ts 入口相关代码加入记忆系统。
```

## Directory

When the user names a directory:

```bash
python tools/agent_memory.py learn-path --project . --path "<directory>" --json
```

For an external source tree:

```bash
python tools/agent_memory.py learn-path --project . --source "<external-project>" --path "<directory>" --json
```

This merges the directory into the existing codebase wiki by default. Use `--replace` only when the user asks to replace the current learned scope.

Directory learning also refreshes log statement records for the learned files.

Use `--json` when another Agent skill will consume the result. The output includes `parse_stats` with counts by language, symbol type, log level, and memory edge total.

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

For an external source tree:

```bash
python tools/agent_memory.py wiki-index --project . --source "<external-project>"
```

Rules:

- Prefer `learn-entry` or `learn-path` over full-project `wiki-index`.
- Use the smallest scope that satisfies the task.
- Use `--source` when the source project is not the same as the current memory archive directory.
- For HarmonyOS projects, prefer `.ets` page/component entry files or `entry/src/main/ets` feature directories.
- HarmonyOS learning indexes `.json5` config, ArkTS project imports, router targets, and `$r(...)` resource references when present.
- ArkTS learning writes readable file/symbol summaries and network edges for imports, route targets, and resources.
- Default to incremental merge for partial learning.
- Use `--replace` only for explicit reset/relearn requests.
- After learning, query with `agent-memory-query` before editing.
- Report parse feedback concisely: files indexed, symbols extracted, logs extracted, and edge total.
- Do not treat the wiki as a complete call graph.
- Treat `code_log_matches` and `edge_matches` as diagnosis hints, not runtime traces.
- Treat learned code context as evidence for future reflections and semantic facts.
