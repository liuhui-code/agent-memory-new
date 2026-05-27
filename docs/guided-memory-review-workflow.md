# Guided Memory Review Workflow

This workflow turns raw memory governance signals into an Agent-readable cleanup plan.

The user should be able to ask:

```text
检查并整理记忆系统。
```

The Agent should run:

```bash
python tools/agent_memory.py doctor --project .
python tools/agent_memory.py maintain-health --project . --json
python tools/agent_memory.py maintain-plan --project . --json
```

## Runtime Boundary

`maintain-plan` is read-only. It proposes actions but does not mutate SQLite.

The Agent must ask for confirmation before running:

```bash
python tools/agent_memory.py maintain-status ...
python tools/agent_memory.py maintain-merge ...
python tools/agent_memory.py maintain-promote ...
```

## Action Types

- `archive`: stale memory can be moved out of the active path.
- `review`: duplicate candidates need human or Agent judgment before merge.
- `verify`: low-confidence memory needs evidence.
- `promote_or_mark_reviewed`: reflection may become a durable fact or be marked reviewed.
- `promote_or_archive`: episode may become a durable fact or be archived.

## Confirmation Rule

The Agent should group actions by risk:

```text
Low risk:
  archive stale records

Medium risk:
  review duplicates
  verify low-confidence records
  promote reflections or episodes
```

Actions with `command: null` need the Agent to draft the replacement fact, durable lesson, or verification step first.

## Example Agent Response

```text
Memory review found:
- 2 stale records that can be archived.
- 1 duplicate candidate that needs a merged fact.
- 3 unreviewed episodes that may contain durable knowledge.

I can archive the stale records now. For the duplicate and episode promotions, I will draft the replacement facts first and wait for confirmation.
```

After confirmed changes, run:

```bash
python tools/agent_memory.py vault-export --project .
```

Obsidian remains a generated review mirror. SQLite remains the source of truth.
