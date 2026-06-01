---
name: agent-memory-learn
description: Use when the user asks the Agent to learn, index, understand, or update memory for a project entry file, feature directory, module, or selected part of the codebase.
---

# Agent Memory Learn

Use this skill to add part of a project to the memory system.

Prefer natural language from the user, then choose the narrowest runtime command.

`--project` selects the current memory archive and query context. If the code to learn lives elsewhere, pass that external source root with `--source`; learned data is still archived under `--project`.

For high-quality project learning, first read the target files and summarize business meaning in the required structure, then write it with `learn-business`. The runtime should store the Agent's structured understanding alongside the existing file, symbol, and log records.

```bash
python tools/agent_memory.py learn-business --project . --payload "<json>" --json
```

Payload shape:

```json
{
  "files": [
    {
      "file_path": "pages/ProfileDetail.ets",
      "summary": "ArkTS profile detail page",
      "business_summary": "个人信息详情页，负责加载用户资料并展示头像。",
      "business_terms": ["个人信息", "用户资料", "profile", "头像", "avatar"],
      "symbols": [
        {
          "symbol": "loadUserProfile",
          "symbol_type": "function",
          "business_summary": "加载用户资料的方法。",
          "business_terms": ["加载用户资料", "profile", "load profile"]
        }
      ],
      "logs": [
        {
          "message_template": "load profile failed",
          "function": "loadUserProfile",
          "level": "error",
          "business_summary": "用户资料加载失败时输出的错误日志。",
          "business_terms": ["用户资料加载失败", "profile failed"]
        }
      ]
    }
  ]
}
```

Use this structure when the user asks the Agent to understand a feature, page, module, or business flow. Include real file names, method names, fields, routes, resources, and logs. Business terms should include code naming and user-facing Chinese/English business wording when it can be inferred from the source. Do not invent business flows that are not supported by the code.

`learn-business` now defaults to object-level merge behavior:

- Update only the file, symbol, and log records named in the payload.
- Merge `business_terms` with existing terms instead of replacing them.
- Preserve existing non-empty `business_summary` values by default.
- Return `semantic_conflicts` when an incoming non-empty summary disagrees with an existing non-empty summary.

Before writing `learn-business`, organize the target code with these checks:

- File: what business area or page does this file own?
- Symbol: what business action, state, field, or side effect does this method or symbol represent?
- Log: what business event does this log represent, and what does it usually mean when it fails?
- Terms: include real business objects, page names, route names, resource keys, method names, and Chinese/English wording a user would naturally ask for.

`learn-business --json` now returns semantic quality feedback in addition to write counts:

```text
semantic_stats
semantic_gaps
semantic_followup
```

Use `semantic_stats` to judge coverage, and use `semantic_gaps` to find which files, symbols, or logs still need business meaning before relying on memory query results.

When `semantic_followup` is present, use its `followup_payload_template` for the next `learn-business` write instead of inventing a new payload. Follow `workflow_steps` in order.
Read `recommended_next_action` first. When it is `run_learn_business_now`, continue with the returned template before broader re-indexing or querying.
`semantic_followup` also carries:

- `truncated`: whether the current batch was capped
- `returned_counts` and `remaining_counts`: how much semantic work is visible now versus deferred
- file-level `priority_score` and `priority_reasons`: why a file is ahead of other semantic work
- `hint_terms` and `hint_context`: retrieval-oriented anchors the Agent should reuse when writing `business_terms` and `business_summary`

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
When `semantic_followup` is present, use it immediately as the next `learn-business` task for the learned files. If `truncated` is `true`, finish the visible batch first, then rerun learning or maintenance to fetch the next semantic batch.
Use `hint_terms` as seed vocabulary for `business_terms`, and use `hint_context` as the raw code anchor list you should read before writing the second-pass semantic summary.

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
If the learned files still lack business meaning, the JSON also includes `semantic_followup` with a second-pass payload template. Respect its priority ordering instead of enriching files in arbitrary directory order.

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
- Report parse feedback concisely: files indexed, symbols extracted, logs extracted, edge total, and whether semantic coverage is still missing for important files, symbols, or logs.
- Do not treat the wiki as a complete call graph.
- Treat `code_log_matches` and `edge_matches` as diagnosis hints, not runtime traces.
- Treat learned code context as evidence for future reflections and semantic facts.
