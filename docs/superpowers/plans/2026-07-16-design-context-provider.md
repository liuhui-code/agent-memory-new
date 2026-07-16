# Design Context Provider Execution Plan

## Goal

Deliver Phase 1 of the long-term Design Context Provider while retaining old
command compatibility and the fixed four-Skill user surface.

## Tasks

- [x] Record the long-term architecture, industry references, authority model,
  two-pass retrieval protocol, compatibility policy, and evaluation direction.
- [x] Add a versioned general design-knowledge catalog outside project memory.
- [x] Add `design-context` as a thin facade through `tools/agent_memory.py`.
- [x] Compose current repository views, source anchors, project evidence,
  semantic corrections, verified warnings, and general knowledge.
- [x] Add explicit `--concern`, `--anchor`, `--constraint`, and `--compact`
  controls for Agent-directed expansion.
- [x] Attach authority, applicability, freshness, and provenance to context.
- [x] Guarantee that the facade emits no recommendation, candidate ranking,
  selected design, generated Delta, or change plan.
- [x] Move the Query Skill and user documentation to `design-context` while
  retaining legacy backend commands as compatibility-only.
- [x] Add contract, routing, authority, compactness, compatibility, and
  no-decision tests.
- [x] Run focused and full tests, compile checks, diff checks, exactly-four-Skill
  checks, and the 500-line source guard.

## Verification

- Design-context, legacy compatibility, and repository-design regression: 16 passed.
- Design, evidence-fabric, and experience-query integration regression: 45 passed.
- Full regression: 372 tests passed in 260.265 seconds.
- Compact context is contract-tested at no more than 1,500 estimated tokens,
  including a learned ArkTS graph with source anchors and relations.
- A local repository probe completed in about 0.6 seconds; this is a functional
  latency probe, not a production percentile baseline.
- Python compilation, JSON catalog validation, CLI help, diff whitespace,
  exactly-four-Skill, and 500-line source checks passed.

## Deferred

- ADR ingestion and lifecycle storage.
- A project architecture-constraint table and fitness-rule facade.
- Splitting and removing legacy design scoring/selection commands.
- Cross-language SCIP ingestion.
- Agent A/B design-quality benchmark automation.
