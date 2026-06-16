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
- return only allowed one-hop network edges and compact evidence chains.

Avoid:

- duplicate detection;
- merge;
- promotion;
- vault export.
- recursive graph traversal.

Network query limits:

```text
max_depth = 1
edge_limit = 10
evidence_chain_limit = 3
allowed_relations = contains, emits_log
```

LLM skills may perform recursive reasoning by changing the query and calling the runtime again. The runtime itself should stay deterministic and bounded.

## Maintain Path

Governance runs through `agent-memory-maintain`:

```bash
python tools/agent_memory.py maintain-health --project . --json
python tools/agent_memory.py maintain-review --project . --json
python tools/agent_memory.py maintain-plan --project . --json
python tools/agent_memory.py maintain-status --project . --type semantic --id 12 --status stale --reason "source changed"
python tools/agent_memory.py maintain-merge --project . --type semantic --ids 3,8 --fact "..."
python tools/agent_memory.py maintain-promote --project . --episode-id 9 --fact "..."
python tools/agent_memory.py maintain-promote --project . --reflection-id 12 --fact "..."
```

`maintain-plan` is the bridge between raw review signals and Agent action. It proposes confirmable actions and does not mutate memory.

Query misses are also surfaced through `maintain-plan`. They are low-risk signals that a real query failed to hit memory or wiki context. The Agent should decide whether to learn a missing path, add a durable fact, or mark the miss ignored/resolved.

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
task_type
outcome
problem
task
summary
reasoning_summary
context_used
what_worked
what_failed
mistake
lesson
future_rule
scope
evidence
confidence
trigger_condition
anti_pattern
repair_action
applies_to
does_not_apply_to
anchor_type
anchor_key
semantic_field
existing_value
proposed_value
patch_reason
applies_to_current_code
superseded_by
misleading_score
```

The important motion is:

```text
episode -> reflection -> semantic fact -> future rule
```

This keeps the system aligned with the project idea that intelligence improves through recursive organization.

Reflection experience types are governed separately:

- `procedure_experience` can become a reusable skill pattern only after multiple verified cases.
- `correction_experience` acts as a guardrail and should not become the main query direction by default.
- `semantic_patch_experience` patches code business semantics through anchored learn governance instead of normal experience recall.

`maintain-plan` may return `review_semantic_patch`, `review_correction_experience`, or `review_retrieval_interference` when these lanes need review.

## Obsidian Mirror

Vault export includes generated governance pages:

```text
Governance/
  Health.md
  Review Queue.md
  Stale Memories.md
  Merge Candidates.md
  Low Confidence.md
  Reflection Quality.md
  Experience Candidates.md
  Reflection Reuse.md
  Query Misses.md
```

These files are for review only. Edit memory through skills or runtime commands.

## Completion Criteria

- Existing databases migrate without manual reset.
- Query output includes governance metadata and advisory notice.
- Query output includes `memory_intent`, `retrieval_lanes`, `memory_brief`, `correction_guards`, `semantic_patch_notes`, and `blocked_memory_notes`.
- Maintain commands can health-check, review, mark status, merge, and promote.
- Vault export writes governance dashboard pages.
- Skill docs preserve the four-skill interface.
