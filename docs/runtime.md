# Agent Memory Runtime Specification

Version: 0.1
Status: Draft
Audience:
- Codex
- AI coding agents
- agent-memory runtime
- maintainers

Goal:
Define the execution protocol for:
- initialization
- querying
- updating
- reflection
- LLM interaction
- memory lifecycle

This document defines operational behavior, not implementation details.

---

# 1. System Overview

The system consists of four layers:

```text
LLM / Codex
    ↓
Skill / Protocol Layer
    ↓
tools/agent_memory.py
    ↓
Workspace memory home
    ↓
Per-project SQLite + Obsidian Vault Mirror
```

The first MVP keeps the runtime intentionally small:

- SQLite is the source of truth.
- Obsidian Markdown is a generated mirror.
- Skills call `tools/agent_memory.py`.
- Query commands support `--json`.
- Keyword search ships before vector search.
- Governance commands keep memory clean without slowing normal query flow.
- `--project` selects the memory archive and query context. Learning commands can use `--source` to read code from an external source tree into that archive. `--memory-home`, `AGENT_MEMORY_HOME`, or the current workspace `./.agent-memory` selects where memory data is stored.

See `docs/mvp-implementation-plan.md` for the full implementation plan.

---

# 2. Query Fast Path

`context`, `search`, and `wiki-search` are read-oriented commands.

They may:

- filter inactive, stale, merged, archived, or rejected memories;
- return confidence, status, source, scope, evidence, and warnings;
- update lightweight usage fields such as `use_count` and `last_used_at`.
- record a query miss when no result set has matches.
- return learned code log statements and lightweight edges between files, symbols, and log statements.
- return compact one-hop `evidence_chains` derived from allowed edge matches.
- bound result sets before JSON output so large archives do not return unbounded payloads.

They must not:

- merge records;
- promote episodes;
- run expensive duplicate scans;
- export the vault.
- recursively traverse the memory graph.
- return arbitrary relation types from `memory_edges`.

Network limits for the query fast path:

```text
max_depth = 1
edge_limit = 10
evidence_chain_limit = 3
allowed_relations = contains, emits_log
```

The runtime returns these limits in `network_limits` so skill callers know the context is intentionally bounded. Recursive reasoning belongs in the LLM skill layer: inspect the returned context, sharpen the query, and call `context` again.

`search` is also bounded. It returns `result_limits` in the JSON payload so callers can see the current cap for each result set.

# 3. Governance Path

Governance belongs to `agent-memory-maintain` and these runtime commands:

```bash
python tools/agent_memory.py maintain-health --project . --json
python tools/agent_memory.py maintain-review --project . --json
python tools/agent_memory.py maintain-plan --project . --json
python tools/agent_memory.py miss-list --project . --status open --json
python tools/agent_memory.py miss-status --project . --id 1 --status resolved --resolution "..."
python tools/agent_memory.py maintain-status --project . --type semantic --id 1 --status stale --reason "..."
python tools/agent_memory.py maintain-merge --project . --type semantic --ids 1,2 --fact "..." --json
python tools/agent_memory.py maintain-promote --project . --episode-id 1 --fact "..." --json
python tools/agent_memory.py maintain-promote --project . --reflection-id 1 --fact "..." --json
```

Governance actions should preserve history. Prefer status transitions over destructive deletion.

`maintain-plan` is read-only. It converts review signals into confirmable action candidates for the skill layer. It must not mutate SQLite.

Query miss commands manage feedback from failed retrievals. A miss is recorded only when `context`, `search`, or `wiki-search` has zero matches. Repeated open misses with the same source and normalized query are merged into one row with `miss_count` and `last_seen_at`, so maintenance can focus on recurring retrieval gaps instead of duplicate rows.

Query commands expand common natural-language problem descriptions into technical search terms before scoring rows. The expansion is deterministic and local. It helps symptom queries such as `页面跳转后白屏`, `图片资源显示不出来`, or `加载用户资料失败日志` match learned ArkTS route, resource, config, and log records without adding a vector database.

# 3.5 Structured Reflection Path

`agent-memory-reflect` should let the local Agent CLI organize a completed attempt before writing memory. For diagnosis, design, execution, and workflow attempts, prefer:

```bash
python tools/agent_memory.py reflect --project . --payload "<json>"
python tools/agent_memory.py reflect --project . --payload-file "<review.json>"
```

The payload stores the Agent-authored task review in `reflections`:

```json
{
  "task_type": "diagnosis",
  "outcome": "success",
  "problem": "Profile page opens blank after navigation.",
  "task": "diagnose profile blank page",
  "summary": "Queried memory and found a route path mismatch.",
  "reasoning_summary": "The useful clue was the route edge plus router.pushUrl log.",
  "context_used": ["query: profile blank page route", "file: pages/Home.ets", "log: router.pushUrl failed"],
  "what_worked": ["Search by business page name", "Check route edges"],
  "what_failed": ["Searching only generic blank-screen terms"],
  "hidden_assumptions": ["The blank screen happened after route navigation."],
  "negative_preconditions": ["Do not apply when no navigation occurred."],
  "verification_method": "Confirm route registration, inspect router logs, and reproduce navigation.",
  "reuse_feedback": "experience candidate until reused",
  "source_cases": ["episode:12", "reflection:7", "file: pages/Home.ets"],
  "skill_candidate": "arkts-route-blank-screen-diagnosis",
  "lesson": "ArkTS blank-screen diagnosis should combine business page names with route terms.",
  "future_rule": "When a HarmonyOS page opens blank after navigation, query business page terms plus route/router terms first.",
  "trigger_condition": "Page opens blank after route navigation",
  "repair_action": "Query memory with business page name, route terms, and related log template"
}
```

These fields participate in `search` and `context`, so later issue-location or design skills can retrieve successful and failed attempts by problem description, business term, file, log, or prior query.

The extra experience-candidate fields do not create accepted experience by themselves.
Future Agents must verify them against current source, logs, tests, and code wiki
evidence before using them as conclusions.

# 4. Code Learning Path

`learn-entry`, `learn-path`, and `wiki-index` update the codebase wiki.

`learn-business` writes Agent-authored business semantics into the existing code wiki tables:

```bash
python tools/agent_memory.py learn-business --project . --payload "<json>" --json
```

The payload contains files, symbols, and logs with `business_summary` and `business_terms`. Use it after the Agent has read the target source and organized the code's real business meaning. It does not create a separate business table; it enriches `code_files`, `code_symbols`, and `code_log_statements`.

`learn-business` uses object-level merge semantics by default. It updates only the addressed file, symbol, and log rows; merges `business_terms`; preserves existing non-empty `business_summary` values; and reports `semantic_conflicts` instead of silently overwriting conflicting summaries.

`learn-business --json` also returns semantic quality feedback for the submitted scope:

```text
semantic_stats
semantic_gaps
semantic_followup
```

`semantic_stats` reports coverage counts for file, symbol, and log business meaning. `semantic_gaps` lists the specific files, symbols, or logs that still lack `business_summary` or `business_terms`.
When gaps remain, `semantic_followup` returns:

- `command_template`
- `workflow_steps`
- `recommended_next_action`
- `truncated`
- `returned_counts`
- `remaining_counts`
- `followup_payload_template`

The follow-up template is priority-ordered and batch-limited so the Agent can enrich the highest-value files, symbols, and logs first without rebuilding anchors.

Recent `semantic_conflicts` are stored durably in SQLite and also flow into `maintain-plan` as `review_semantic_conflict` actions for later governance.

They also extract code log statements and rebuild deterministic code-wiki edges:

```text
code_file --contains--> code_symbol
code_file --contains--> code_log_statement
code_symbol --emits_log--> code_log_statement
```

This supports memory-aware diagnosis without adding a separate user-facing skill. An Agent can query an observed log or console message, receive `code_log_matches`, inspect `edge_matches`, then recursively query again with the related file/function names.

Learning commands return parse feedback. `learn-entry --json` and `learn-path --json` include `parse_stats`:

```text
files_indexed
languages
symbols_total
symbols_by_type
code_logs_total
code_logs_by_level
memory_edges_total
```

Agents should use these counts to detect narrow or failed learning scopes before relying on the codebase wiki.
When the learned files still lack business semantics, `learn-entry --json` and `learn-path --json` also include `semantic_followup` with a second-pass `learn-business` template scoped to the files just indexed.

# 5. Reflection Quality Path

Reflection quality belongs to `agent-memory-reflect` and is reviewed through:

```bash
python tools/agent_memory.py reflect-review --project . --json
```

`reflect-review` is read-only. It reports missing trigger conditions, missing repair actions, missing hidden assumptions, missing negative preconditions, missing verification methods, missing reuse feedback, vague rules, unused reflections, and misleading outcomes.

# 6. Search Batching

`search --json` supports batched aggregated retrieval:

```bash
python tools/agent_memory.py search --project . --query "<query>" --per-type-limit 10 --aggregate-limit 8 --cursor 0 --json
```

The response includes:

- `truncated`
- `next_cursor`
- `total_candidates_by_type`
- `returned_counts_by_type`
- `per_type_limit`
- `aggregate_limit`

Use `next_cursor` only when the current batch does not provide enough evidence. Query remains bounded by design.
