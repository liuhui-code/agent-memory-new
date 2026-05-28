# Query Miss Feedback Loop

Query misses are lightweight retrieval feedback.

The runtime records a miss only when a query has zero matches across memory and wiki result sets. This avoids manual keyword maintenance while still showing where memory failed to help.

Repeated open misses are merged by `source` and normalized query text. The first query text is kept for review, while `miss_count` and `last_seen_at` show recurrence. This prevents noisy duplicate rows while preserving the signal that a query pattern keeps failing.

## Recorded Sources

- `context`
- `search`
- `wiki-search`

## Commands

```bash
python tools/agent_memory.py miss-list --project . --status open --json
python tools/agent_memory.py miss-status --project . --id 1 --status resolved --resolution "learned relevant directory"
python tools/agent_memory.py miss-status --project . --id 2 --status ignored --resolution "not useful"
```

Statuses:

- `open`
- `reviewed`
- `resolved`
- `ignored`

## Maintain Flow

`maintain-plan` includes open query misses as `review_query_miss` actions.

The Agent should decide whether the miss means:

- learn an entry file or directory;
- add a durable semantic fact;
- reflect on a missing workflow rule;
- mark the miss ignored.

## Obsidian Mirror

Vault export writes:

```text
Governance/Query Misses.md
Codebase Wiki/query-misses.md
```

This file is generated. SQLite remains the source of truth.
