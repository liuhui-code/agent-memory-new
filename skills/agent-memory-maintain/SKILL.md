---
name: agent-memory-maintain
description: Use when the user asks to initialize, check health, update, repair, refresh, or sync the Agent Memory system or Obsidian vault.
---

# Agent Memory Maintain

Use this skill for memory system health and maintenance.

## Initialize Or Repair

```bash
python tools/agent_memory.py init --project .
python tools/agent_memory.py doctor --project .
```

## Health Check

```bash
python tools/agent_memory.py doctor --project .
python tools/agent_memory.py maintain-health --project . --json
```

## Review Queue

When the user asks to review, clean, govern, merge, or check memory quality:

```bash
python tools/agent_memory.py maintain-review --project . --json
python tools/agent_memory.py maintain-plan --project . --json
```

Use `maintain-plan` to propose grouped actions before changing records.

## Guided Review Workflow

When the user asks to clean, organize, review, or govern memory:

1. Run `doctor`.
2. Run `maintain-health --json`.
3. Run `maintain-plan --json`.
4. Present grouped actions to the user by risk and type.
5. Wait for confirmation before executing `maintain-status`, `maintain-merge`, or `maintain-promote`.
6. After confirmed changes, run `vault-export`.

If an action has `command: null`, draft the needed replacement fact or lesson first, then ask for confirmation.

## Governance Actions

Mark a record stale, archived, rejected, merged, or active:

```bash
python tools/agent_memory.py maintain-status \
  --project . \
  --type semantic \
  --id "<id>" \
  --status stale \
  --reason "<why>"
```

Merge duplicate semantic facts:

```bash
python tools/agent_memory.py maintain-merge \
  --project . \
  --type semantic \
  --ids "3,8" \
  --fact "<consolidated fact>" \
  --json
```

Promote an episode into a durable semantic fact:

```bash
python tools/agent_memory.py maintain-promote \
  --project . \
  --episode-id "<id>" \
  --fact "<durable fact>" \
  --json
```

## Refresh Indexes

```bash
python tools/agent_memory.py wiki-index --project .
```

## Sync Obsidian Mirror

```bash
python tools/agent_memory.py vault-export --project .
python tools/agent_memory.py vault-index --project .
```

Rules:

- SQLite is the source of truth.
- Obsidian is a generated review mirror.
- Do not modify shell profiles.
- Report failed `doctor` checks exactly.
- `agent-memory-query` should stay fast; run heavier governance through this maintain skill.
- Do not auto-delete memory. Prefer stale, merge, archive, or reject status changes.
- `maintain-plan` is read-only. It proposes actions; it does not mutate memory.
- Merge only when the replacement fact is more precise than all source facts.
- Promote only durable lessons, not task logs.
