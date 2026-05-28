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
- `evidence_chains`
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
- `allowed_relations`: `contains`, `emits_log`

`evidence_chains` are readable summaries of returned one-hop edges, not multi-hop graph paths.

If no result set matches, query miss recording still works normally.

## Obsidian Mirror

`vault-export` writes:

- `Codebase Wiki/log-statements.md`
- `Codebase Wiki/memory-edges.md`

These files are generated mirrors. Edit memory through the runtime and skills, not by editing vault files.
