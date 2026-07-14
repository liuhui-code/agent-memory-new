# Design Preparation Workbench Plan

**Goal:** Give the Agent a revision-bound repository and constraint workbench before it authors candidate design Deltas, removing the circular dependency where `design-check` reveals synthesis evidence only after a proposal already exists.

## Boundaries

- Keep four public Skills and `tools/agent_memory.py` as the only runtime entry.
- Keep the runtime deterministic, read-only, LLM-free, and under the 500-line file limit.
- Reuse `repository-model/v2`, `design-intent/v1`, and `design-contract/v2`; do not add storage or session tables.
- The runtime prepares evidence and an unclaimed template. The Agent still reasons about and authors candidate designs.
- Candidate paths cannot define the baseline architecture.

## Phase 1: Preparation Protocol

- [x] Add `design-prepare --intent ... [--contract ...] [--rules ...]`.
- [x] Build one repository model from goal and explicit intent scope before any candidate exists.
- [x] Return a bounded `design-workbench/v1` with revision, capabilities, provenance, and evidence gaps.
- [x] Expose a bounded anchor catalog and supported relation vocabulary for valid Delta authoring.

## Phase 2: Candidate Authoring Guardrails

- [x] Generate a `design-delta/v2` candidate template bound to the intent and contract.
- [x] Seed only current baseline anchors; leave modifications, added nodes/edges, coverage claims, and verification claims empty.
- [x] Generate empty coverage-evidence skeletons for declared constraints and quality scenarios.
- [x] Report authoring gaps for missing acceptance criteria, measurable scenarios, baseline anchors, and current evidence.

## Phase 3: Integration and Gates

- [x] Route repository-grounded design through prepare, author, check, compare, implement, verify, and outcome.
- [x] Preserve all existing commands and v1/v2 compatibility.
- [x] Update runtime, usage, schema, Agent, Query Skill reference, README, and development log.
- [x] Run focused/full tests, compilation, diff check, four-Skill check, and 500-line gate.

## Acceptance

- The Agent can obtain design evidence without supplying a proposal.
- The workbench and later checks expose the same graph revision when the repository graph is unchanged.
- Generated templates cannot accidentally claim quality or verification coverage.
- No workbench, intent, contract, candidate template, source, or reasoning is persisted.
