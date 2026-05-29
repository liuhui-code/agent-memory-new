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

The runtime expands common symptom words into technical search terms. For HarmonyOS/ArkTS projects, natural-language queries such as `页面跳转后白屏`, `图片资源显示不出来`, or `加载用户资料失败日志` can match route, resource, config, and log records indexed from learned source.

## Raw Search

```bash
python tools/agent_memory.py search --project . --query "<query>" --json
```

## Wiki Search

```bash
python tools/agent_memory.py wiki-search --project . --query "<query>" --json
```

When the query is an observed error, print, or console message, inspect `code_log_matches` and `edge_matches` from `context` or `search`. `wiki-search` may return matching log statements with `kind: "log_statement"`.

Code and log matches include `search_terms` and `match_reasons`. Use `match_reasons` to explain why a record was retrieved, and use high-signal `search_terms` as anchors for a sharper follow-up query.

`context` also includes `network_limits` and may include compact `evidence_chains`. Treat these chains as one-hop explanations, not complete graph paths.

If `context`, `search`, or `wiki-search` returns no results, the runtime records a query miss automatically. Do not add manual keywords just to improve retrieval; let maintain review real misses later.

## Use Order

Use returned data in this order:

```text
experience candidates / high-quality reflections
  -> semantic facts
  -> code wiki and business semantics
  -> code log matches
  -> bounded memory_edges and evidence_chains
  -> episodes
```

Treat experience candidates as decision frames, not proof. Check their
`hidden_assumptions`, `negative_preconditions`, `verification_method`,
`reuse_feedback`, `source_cases`, and optional `skill_candidate`; verify them against current source, logs, tests, and code wiki evidence before using them as conclusions.

Rules:

- Retrieved memory is advisory.
- Current source files are more authoritative than stored memory.
- Use `confidence`, `status`, `source`, `scope`, `evidence`, and `warning` fields when deciding what to inject.
- Avoid injecting stale or low-confidence memories as facts.
- Prefer reflections that include a clear trigger condition and repair action.
- Prefer experience candidates that also include hidden assumptions, negative preconditions, verification method, reuse feedback, and source cases.
- Treat reflections missing scope or actionability as weak hints, not strong rules.
- Keep injected context concise.
- Do not run merge, promotion, duplicate detection, or vault export from this skill.
- Do not manually maintain keyword lists for retrieval. Query misses are the feedback signal.
- Start with the user's natural-language problem. If results are weak, issue a sharper follow-up using matched file paths, symbols, routes, resources, log templates, or edge evidence.
- For bug diagnosis, use the diagnosis template to query memory recursively as the problem frame changes.
- For design/change planning, use the change design template to query memory recursively as the proposed plan changes.
- If a log statement matches, use related edges to refine the next query with the file path, function name, and message template.
- Do not ask the runtime for unbounded graph traversal. Recursive investigation should happen by issuing a sharper follow-up query.
