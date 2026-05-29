---
name: agent-memory-maintain
description: Use when the user asks to initialize, check health, update, repair, refresh, or sync the Agent Memory system or Obsidian vault.
---

# Agent Memory Maintain

Use this skill for memory system health and maintenance.

Memory data is stored in the current workspace `.agent-memory/` by default, next to `skills/` and `tools/`, not in the learned external source directory. Use `--memory-home <path>` when the user configured a custom location; otherwise the runtime uses `AGENT_MEMORY_HOME` or `./.agent-memory`.

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
python tools/agent_memory.py reflect-review --project . --json
python tools/agent_memory.py miss-list --project . --status open --json
python tools/agent_memory.py maintain-plan --project . --json
```

Use `maintain-plan` to propose grouped actions before changing records.

## Guided Review Workflow

When the user asks to clean, organize, review, or govern memory:

1. Run `doctor`.
2. Run `maintain-health --json`.
3. Run `maintain-plan --json`.
4. Present grouped actions to the user by risk and type, including open query misses.
5. Wait for confirmation before executing `maintain-status`, `maintain-merge`, or `maintain-promote`.
6. After confirmed changes, run `vault-export`.

If an action has `command: null`, draft the needed replacement fact or lesson first, then ask for confirmation.

When `maintain-plan` returns `promote_experience_candidate`, review the reflection as reusable experience. Check `candidate_fields`, `verification_method`, `source_cases`, and `skill_candidate`; do not promote it automatically.

When `maintain-plan` returns `review_query_miss`, inspect `suggested_fixes`:

```text
learn_missing_scope
add_business_terms
rewrite_reflection
ignore_noise
```

Choose the smallest fix. A miss caused by missing code context should trigger `agent-memory-learn`; a miss caused by weak business meaning should trigger `learn-business`; a miss caused by absent experience should trigger `agent-memory-reflect`; irrelevant misses can be marked ignored.

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

Promote a high-quality reflection into a durable semantic fact:

```bash
python tools/agent_memory.py maintain-promote \
  --project . \
  --reflection-id "<id>" \
  --fact "<durable fact>" \
  --json
```

Mark a query miss reviewed, resolved, or ignored:

```bash
python tools/agent_memory.py miss-status \
  --project . \
  --id "<id>" \
  --status resolved \
  --resolution "<what fixed the miss>"
```

Open misses are merged by normalized query text. Use `miss_count` and `last_seen_at` to prioritize recurring retrieval gaps before one-off misses.

## Refresh Indexes

```bash
python tools/agent_memory.py wiki-index --project .
```

Refreshing the wiki also refreshes extracted code log statements and the generated file/function/log edges.

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
- Treat `rewrite_reflection` and `mark_stale` actions from `maintain-plan` as confirmation-required reflection quality actions.
- Treat `promote_experience_candidate` as a review signal, not an automatic promotion.
- Treat `review_query_miss` actions as low-risk signals that may require learning a missing path, adding business terms, rewriting a reflection, or ignoring noise.
- Vault export includes generated code log statement, memory edge, query miss, reflection quality, and experience candidate pages for review.
