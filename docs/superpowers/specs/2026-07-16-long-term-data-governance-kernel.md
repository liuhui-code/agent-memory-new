# Long-Term Data Governance Kernel

## Goal

Keep Agent Memory trustworthy as project code, experience, and feedback grow,
without adding user-facing Skills or turning SQLite into a full event-sourced
system.

The fixed user surface remains:

- `agent-memory-learn`
- `agent-memory-query`
- `agent-memory-maintain`
- `agent-memory-reflect`

`tools/agent_memory.py` remains the only runtime entry and SQLite remains the
source of truth.

## Decision

Use a hybrid governance model:

```text
current entity tables
  <- confirmed governance actions
  <- governance cases (future durable projection)
  <- immutable observations
  -> bounded aggregate projections used by query and maintain
```

Do not adopt full Event Sourcing. Current semantic, reflection, code, log, and
edge tables remain the queryable current state. Append-only records are used
selectively where history, attribution, or delayed confirmation matters.

## Domain Model

### Entity

An Entity is current project knowledge: semantic fact, reflection, episode,
code file, code symbol, code log, or graph edge. Durable memory entities use
their table ID. Derived code entities must increasingly expose stable keys such
as file path, symbol key, log fingerprint, or edge identity so rebuilds do not
silently detach governance evidence.

### Observation

An Observation records what happened without deciding what the Entity now
means. Existing observation families are retained and clarified:

- `retrieval_feedback`: relevance or trust observation about a retrieved
  semantic fact or reflection.
- `experience_usage_events`: observed task use outcome.
- `reflection_reuse_events`: provenance linking an applying reflection to a
  reused reflection; it is not an independent ranking vote.
- `query_misses`: repeated absence of usable retrieval evidence.
- `semantic_conflicts`: a review record created by incompatible code-business
  semantics.

Observations need correlation and idempotency fields where they can affect
ranking: `task_id`, `query_id`, `event_key`, `verified`, and timestamps. Raw
temporary user logs and Agent reasoning are excluded.

### Stable Signal

An Observation is not automatically a Stable Signal. A signal may affect
ranking only when one of these conditions holds:

1. it is explicitly verified;
2. its reason is intrinsically verified, such as `verified_useful`; or
3. the same scoped outcome appears in at least two independent tasks.

`used` and `ignored` are never direct ranking labels. Presentation order and
task context can cause both. `helpful` and `misleading` require stability.
`superseded` creates governance work but does not directly determine relevance.

### Governance Case

A Governance Case groups stable observations into one reviewable problem. Its
future durable schema should include a stable case key, lane, target entity,
failure class, supporting observation IDs, status, recommendation, and review
metadata. Until durable cases are justified by volume, `maintain-plan` actions
serve as bounded ephemeral case projections.

### Governance Event

A Governance Event is an append-only audit record for an applied mutation such
as status change, merge, promotion, semantic correction, or scope refresh. It
stores old/new state references and the supporting Case. This is selective
audit logging, not full Event Sourcing. Add it only after feedback correctness
and stable entity identity are in place.

## Interface Policy

No new data-governance command is introduced in the current phase.

- `retrieval-feedback` records an observation and also closes or confirms an
  existing feedback row through optional lifecycle arguments.
- `experience-usage` records an actual use observation.
- `maintain-health` summarizes stable and pending observations.
- `maintain-plan` proposes review or closure actions.
- existing maintain mutation commands apply confirmed changes.

Skills hide backend commands from normal users.

## Query Policy

Feedback lookup is candidate-directed:

1. FTS and deterministic retrieval collect candidate semantic/reflection IDs.
2. One bounded SQL query fetches feedback only for those candidate IDs.
3. Stable signals are grouped by entity, reason, and independent task.
4. Query-scoped overlap is applied after candidate selection.
5. Ranking consumes the bounded aggregate, never the global latest N events.

This prevents older relevant evidence from disappearing behind an unrelated
global tail and avoids per-result SQL queries.

## Integrity Policy

- Reject observations whose target Entity does not exist in the project.
- Use an optional unique `event_key`; derive it from `task_id` and observation
  identity when a task ID is supplied.
- Validate lifecycle values in the command and storage layer.
- A closed feedback row no longer participates in ranking.
- Keep backward-compatible rows readable; uncorrelated legacy duplicates may
  satisfy repetition but should be reviewed before promotion.
- Mutating maintain commands must eventually check affected row counts and
  emit governance audit events.

## Scale Policy

The target scale is at least 500,000 rows per project database.

- Use composite indexes matching candidate-directed lookup.
- Use partial indexes for active feedback when compatible with existing
  SQLite deployments.
- Avoid whole-table aggregation on query paths.
- Maintain bounded rollups for health and governance views.
- Add retention only after rollups are durable and auditable.
- Run `PRAGMA optimize` after schema/index migrations and expose query-plan
  regressions in performance tests.

## Provenance Policy

Use a small provenance vocabulary inspired by W3C PROV:

- Entity: governed memory or current code anchor.
- Activity: learn, query, reflect, maintain, merge, or refresh operation.
- Agent: local Agent, user, or deterministic Runtime.
- Relations: generated, used, revised, invalidated, or derived from.

The relational implementation uses compact IDs and references, not RDF.

## Phased Delivery

### Phase 1: Feedback Correctness

- Remove the unfinished generic context-feedback model.
- Add feedback verification, correlation, idempotency, and closure metadata.
- Validate referenced semantic/reflection records.
- Stop single unverified observations from changing rank.

### Phase 2: Candidate-Directed Aggregation

- Fetch retrieval and usage observations by candidate IDs.
- Aggregate independent observations once per signal.
- Preserve existing output explanation fields.
- Add high-volume regression fixtures.

### Phase 3: Maintain Integration

- Report pending versus stable feedback.
- Add closure command templates to review actions.
- Keep data mutations confirmation-gated.

### Phase 4: Durable Cases And Audit

- Add durable Governance Cases only when repeated workload demonstrates value.
- Add append-only Governance Events for confirmed maintain mutations.
- Rebuild health projections from audit records and current state.

### Phase 5: System Evolution

- Keep data governance separate from Runtime algorithm evolution.
- Offline incident-context evaluations classify data failures versus retrieval,
  ranking, path-search, or compaction failures.
- Runtime changes require before/after quality gates and token/performance gates.

## Acceptance Criteria For Current Phase

1. One unverified feedback event does not change rank or trust.
2. One verified event or two independent task observations can change the
   bounded aggregate.
3. Resolved or ignored feedback stops affecting queries.
4. Duplicate task feedback is idempotent.
5. Nonexistent record references are rejected.
6. Candidate feedback remains visible even after more than 200 unrelated
   feedback rows are written.
7. Maintain exposes stable and pending feedback without a new user-facing
   Skill.
8. Existing databases migrate in place and existing verified feedback remains
   effective.

## References

- Microsoft Azure Architecture Center, Event Sourcing pattern:
  https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing
- W3C PROV-O:
  https://www.w3.org/TR/prov-o/
- OpenTelemetry context propagation:
  https://opentelemetry.io/docs/concepts/context-propagation/
- Google Rules of Machine Learning:
  https://developers.google.com/machine-learning/guides/rules-of-ml
- SQLite foreign keys, partial indexes, and PRAGMA optimize:
  https://www.sqlite.org/foreignkeys.html
  https://www.sqlite.org/partialindex.html
  https://www.sqlite.org/pragma.html
