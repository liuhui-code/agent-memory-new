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
SQLite + Obsidian Vault Mirror
```

The first MVP keeps the runtime intentionally small:

- SQLite is the source of truth.
- Obsidian Markdown is a generated mirror.
- Skills call `tools/agent_memory.py`.
- Query commands support `--json`.
- Keyword search ships before vector search.
- Governance commands keep memory clean without slowing normal query flow.

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

Query miss commands manage feedback from failed retrievals. A miss is recorded only when `context`, `search`, or `wiki-search` has zero matches.

# 4. Code Learning Path

`learn-entry`, `learn-path`, and `wiki-index` update the codebase wiki.

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

# 5. Reflection Quality Path

Reflection quality belongs to `agent-memory-reflect` and is reviewed through:

```bash
python tools/agent_memory.py reflect-review --project . --json
```

`reflect-review` is read-only. It reports missing trigger conditions, missing repair actions, vague rules, unused reflections, and misleading outcomes.
