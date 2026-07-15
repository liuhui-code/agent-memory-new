# Code Log Statement Network

The memory runtime extracts code log statements during normal code learning.

This is part of the existing four-skill design:

```text
agent-memory-learn
  -> learn-entry / learn-path / wiki-index
  -> code_files + code_symbols + code_log_statements + memory_edges
```

The user does not need a separate log skill.

## What Gets Stored

The first version records single-line log-like statements from learned files:

- Python: `print(...)`, `logger.info(...)`, `logger.error(...)`, `logging.warning(...)`
- JavaScript and TypeScript: `console.log(...)`, `console.error(...)`, `logger.warn(...)`
- ArkTS: `console.info(...)`, `console.error(...)`, `hilog.info(...)`, `hilog.error(...)`
- Dart: `print(...)`, `debugPrint(...)`, `log(...)`
- Swift: `print(...)`, `NSLog(...)`, `os_log(...)`, `logger.error(...)`

Each record stores file path, line, nearest detected function, level, logger family, message template, and raw statement.

## Memory Edges

The runtime rebuilds deterministic code-wiki edges after every code learning update:

```text
code_file --contains--> code_symbol
code_file --contains--> code_log_statement
code_symbol --emits_log--> code_log_statement
```

This gives the agent a small network useful for diagnosis:

```text
Observed error text
  -> query code_log_matches
  -> inspect edge_matches
  -> jump to related file/function
  -> query again with refined hypothesis
```

It is not a complete AST or runtime trace.

## Query Behavior

`context` and `search` include:

- `code_log_matches`
- `edge_matches`
- `query_handoff.log_anchors`
- `network_limits`

`wiki-search` returns normal wiki file/symbol matches plus matching log statements with `kind: "log_statement"`.

The query fast path is deliberately bounded:

```text
keyword match -> top nodes -> allowed one-hop edges -> compact context
```

It does not recursively traverse the network. Current limits are:

- `max_depth`: 1
- `edge_limit`: 10
- `evidence_chain_limit`: 3
- `allowed_relations`: `contains`, `emits_log`, `imports`, `routes_to`, `uses_resource`

`edge_matches` are raw bounded one-hop relationships. `query_handoff.log_anchors` connects learned log statements to source inspection targets without claiming a call or causal chain.

For ArkTS, the same bounded network also connects learned `.ets` files through project imports, router target pages, and `$r(...)` resource references. This makes HarmonyOS page/component context more knowledge-like without adding a full AST graph.

If no result set matches, query miss recording still works normally.

## ArkTS Incident Traces

`incident-trace` compresses a temporary symptom and runtime log excerpt into `incident_traces` and `incident_trace_links`:

```bash
python tools/agent_memory.py incident-trace \
  --project . \
  --symptom "页面跳转后白屏" \
  --log-text "router.pushUrl failed for ProfileDetail" \
  --json
```

The command does not persist full raw logs. It stores a short `entry_log_text`, dominant log events, the ArkTS scene, matched code log anchors, and a compact candidate chain.

`context` and `search` can then return `incident_trace_matches` beside `code_log_matches` and `edge_matches`.

## Obsidian Mirror

`vault-export` writes:

- `Codebase Wiki/log-statements.md`
- `Codebase Wiki/memory-edges.md`
- `Codebase Wiki/incident-traces.md`
- `Governance/Incident Trace Review.md`

These files are generated mirrors. Edit memory through the runtime and skills, not by editing vault files.
