# Agent Memory SQLite Schema

SQLite is the source of truth for the MVP. Obsidian files are generated mirrors.

Storage lives in a memory home, defaulting to the current workspace `./.agent-memory`. Each `--project` archive gets an isolated store at `projects/<project_id>/`. `--memory-home` or `AGENT_MEMORY_HOME` can override the default.

## Project Identity

`project_id` is `sha256(abs_project_path)[:16]`, where the path is the archive/query context passed as `--project`, not necessarily the source tree being learned.

## Tables

- `projects`: one row per project path.
- `episodes`: task history and outcome summaries.
- `semantic_facts`: durable facts, preferences, and project knowledge.
- `reflections`: lessons, mistakes, and future rules.
- `code_files`: lightweight file-level wiki index.
- `code_symbols`: lightweight symbol-level wiki index.
- `code_log_statements`: log, print, and console statements extracted from learned source files.
- `memory_edges`: lightweight relation edges between learned files, symbols, and log statements.
- `query_misses`: failed retrieval attempts that may need later learning or reflection.

`code_files`, `code_symbols`, and `code_log_statements` also store Agent-authored business semantics:

- `business_summary`: concise business meaning of the file, method, field, route, resource, or log.
- `business_terms`: JSON array of searchable business terms grounded in code names, fields, routes, resources, logs, or UI wording.

## Governance Fields

Phase 2 adds memory governance metadata while keeping SQLite as the source of truth:

- `status`: `active`, `stale`, `merged`, `archived`, or `rejected`.
- `scope`: where a fact or reflection applies.
- `evidence`: source file, episode, user instruction, or command output behind the memory.
- `last_used_at` and `use_count`: lightweight usage signals updated by context queries.
- `reviewed_at`: when a memory was checked or consolidated.
- `merged_into_id`: replacement memory after consolidation.
- `stale_reason`: why a memory should no longer be trusted directly.

`episodes` also track `importance`, usage counts, and derived fact/reflection ids.

`reflections` also track reflection quality and reuse:

- `trigger_condition`: when the Agent should remember the reflection.
- `anti_pattern`: the mistake or weak pattern to avoid.
- `repair_action`: the concrete next action.
- `applies_to` and `does_not_apply_to`: applicability boundaries.
- `last_applied_at`, `applied_count`, and `last_outcome`: reuse feedback from later tasks.

`query_misses` track retrieval feedback:

- `query`: the user or Agent query that produced no results.
- `normalized_query`: lowercased whitespace-normalized query used to merge repeated open misses.
- `source`: `context`, `search`, or `wiki-search`.
- `result_counts`: JSON counts for each result set at miss time.
- `miss_count`: how many times the same open miss has been observed.
- `last_seen_at`: most recent repeated miss timestamp.
- `status`: `open`, `reviewed`, `resolved`, or `ignored`.
- `resolution`: how the miss was handled.

## Code Log Statement Network

`learn-entry`, `learn-path`, and `wiki-index` extract code log statements as part of the existing codebase wiki workflow. This does not add a fifth user-facing skill.

`code_log_statements` stores:

- `file_path` and `line`: where the statement appears.
- `function`: nearest detected function or class-like symbol.
- `level`: `print`, `debug`, `info`, `warning`, `error`, `exception`, or similar.
- `logger`: logger family such as `print`, `logging`, `logger`, `console`, `hilog`, `debugPrint`, or `NSLog`.
- `message_template`: first string literal or compact argument text.
- `raw_statement`: the original single-line statement.

`memory_edges` currently stores deterministic code-wiki edges:

- `code_file --contains--> code_symbol`
- `code_file --contains--> code_log_statement`
- `code_symbol --emits_log--> code_log_statement`
- `code_file --imports--> code_file`
- `code_file --routes_to--> code_file`
- `code_file --uses_resource--> code_symbol`

The ArkTS edges connect learned pages/components to imported project files, router target pages, and `$r(...)` resource references. These edges are intentionally lightweight. They help diagnosis and design queries move from a symptom or page name to related files, functions, routes, and resources, but they are not a complete call graph.

Query commands do not recursively traverse `memory_edges`. The fast path only returns allowed one-hop relations, currently `contains`, `emits_log`, `imports`, `routes_to`, and `uses_resource`, with hard output limits. Heavier network health checks belong to maintain commands.

## Staleness

`semantic_facts` and `reflections` include `is_stale` for backwards compatibility. New governance commands also set `status = 'stale'`. Stale records are excluded from `context` by default.

## Confidence

`semantic_facts.confidence` and `reflections.confidence` are 0.0 to 1.0 scores. User-provided facts should usually be 1.0.

## Lifecycle

```text
active -> stale -> archived
active -> merged -> replacement active memory
active -> rejected
episode/reflection -> promoted semantic fact
```

Query commands consume governance metadata. Maintain commands create, review, merge, stale, archive, reject, or promote memory records.
