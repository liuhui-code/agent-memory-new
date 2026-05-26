# Phase 2: Memory Governance and Consolidation

Goal: keep Agent Memory useful as records grow by making memory auditable, reviewable, and consolidatable without adding new user-facing skills.

## Design Boundary

The user still works through four skills:

- `agent-memory-learn`
- `agent-memory-query`
- `agent-memory-maintain`
- `agent-memory-reflect`

The runtime remains `tools/agent_memory.py`. SQLite remains the source of truth. Obsidian remains a generated mirror.

## Partial Learning Behavior

`learn-entry` and `learn-path` merge into the existing codebase wiki by default. This supports the user workflow of adding one project part at a time.

Use `--replace` only when intentionally resetting the learned code scope.

## Fast Path

Normal task startup should stay quick:

```text
agent-memory-query -> context/search/wiki-search
```

Allowed work:

- filter by active status;
- return confidence, source, scope, evidence, and warning fields;
- update `use_count` and `last_used_at`.

Avoid:

- duplicate detection;
- merge;
- promotion;
- vault export.

## Maintain Path

Governance runs through `agent-memory-maintain`:

```bash
python tools/agent_memory.py maintain-health --project . --json
python tools/agent_memory.py maintain-review --project . --json
python tools/agent_memory.py maintain-status --project . --type semantic --id 12 --status stale --reason "source changed"
python tools/agent_memory.py maintain-merge --project . --type semantic --ids 3,8 --fact "..."
python tools/agent_memory.py maintain-promote --project . --episode-id 9 --fact "..."
```

## Memory Lifecycle

```text
active -> stale -> archived
active -> merged -> replacement active memory
active -> rejected
episode/reflection -> promoted semantic fact
```

Do not auto-delete memory in Phase 2.

## Review Signals

`maintain-review` should surface:

- stale memories;
- low-confidence memories;
- unreviewed reflections;
- unreviewed episodes;
- duplicate candidates.

Duplicate detection is deterministic and heuristic in Phase 2. It should propose candidates, not decide automatically.

## Reflection Compression

`agent-memory-reflect` should prefer durable structure:

```text
task
summary
mistake
lesson
future_rule
scope
evidence
confidence
```

The important motion is:

```text
episode -> reflection -> semantic fact -> future rule
```

This keeps the system aligned with the project idea that intelligence improves through recursive organization.

## Obsidian Mirror

Vault export includes generated governance pages:

```text
Governance/
  Health.md
  Review Queue.md
  Stale Memories.md
  Merge Candidates.md
  Low Confidence.md
```

These files are for review only. Edit memory through skills or runtime commands.

## Completion Criteria

- Existing databases migrate without manual reset.
- Query output includes governance metadata and advisory notice.
- Maintain commands can health-check, review, mark status, merge, and promote.
- Vault export writes governance dashboard pages.
- Skill docs preserve the four-skill interface.
