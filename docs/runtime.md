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

They must not:

- merge records;
- promote episodes;
- run expensive duplicate scans;
- export the vault.

# 3. Governance Path

Governance belongs to `agent-memory-maintain` and these runtime commands:

```bash
python tools/agent_memory.py maintain-health --project . --json
python tools/agent_memory.py maintain-review --project . --json
python tools/agent_memory.py maintain-plan --project . --json
python tools/agent_memory.py maintain-status --project . --type semantic --id 1 --status stale --reason "..."
python tools/agent_memory.py maintain-merge --project . --type semantic --ids 1,2 --fact "..." --json
python tools/agent_memory.py maintain-promote --project . --episode-id 1 --fact "..." --json
python tools/agent_memory.py maintain-promote --project . --reflection-id 1 --fact "..." --json
```

Governance actions should preserve history. Prefer status transitions over destructive deletion.

`maintain-plan` is read-only. It converts review signals into confirmable action candidates for the skill layer. It must not mutate SQLite.

# 4. Reflection Quality Path

Reflection quality belongs to `agent-memory-reflect` and is reviewed through:

```bash
python tools/agent_memory.py reflect-review --project . --json
```

`reflect-review` is read-only. It reports missing trigger conditions, missing repair actions, vague rules, unused reflections, and misleading outcomes.
