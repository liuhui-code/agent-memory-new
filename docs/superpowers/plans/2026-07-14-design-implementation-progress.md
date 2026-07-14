# Design Implementation Progress Plan

**Goal:** Turn the selected `change-plan/v1` from a static DAG into a read-only implementation checkpoint that tells the Agent which steps are complete, ready, pending, or blocked while code is being edited.

## Boundaries

- Keep four Skills, one runtime entry, SQLite truth, and the 500-line file limit.
- Recompute progress from the selected proposal, current graph revision, Git Delta, and existing test reports.
- Do not execute tests, apply patches, create sessions, or persist workbench/progress state.
- Accept optional caller-owned completed step ids for human review obligations that static evidence cannot prove.
- Preserve `design-check`, `design-compare`, `design-verify`, and legacy proposal behavior.

## Phase 1: Progress Evidence

- [x] Add `design-progress` with proposal, intent/contract/rules, Git base/diff, test evidence/report, and completed-step inputs.
- [x] Reuse the checked `change-plan/v1`, automatic source Delta, and bounded test evidence.
- [x] Match file/symbol implementation steps to actual Git changes.
- [x] Match test and observability obligations only to passed verification references.

## Phase 2: Step State Machine

- [x] Classify every step as `completed`, `ready`, `pending`, or `blocked`.
- [x] Respect DAG dependencies and hard-block architecture/revision/test failures.
- [x] Return bounded next-ready steps, counts, blockers, and evidence gaps.
- [x] Keep manual completion explicit, bounded, and non-persistent.

## Phase 3: Integration and Gates

- [x] Add the prepare -> author -> check/compare -> progress -> verify -> outcome workflow to the Query Skill and docs.
- [x] Add compatibility, partial progress, completion, and failure tests.
- [x] Run full tests, compilation, CLI help, diff check, four-Skill check, and line gate.
- [x] Benchmark progress reconstruction on a representative ArkTS repository.

## Acceptance

- Changed planned files/symbols become completed without caller-supplied file lists.
- Passed report evidence completes only matching test/observability obligations.
- The first dependency-satisfied incomplete steps are returned as next actions.
- Stale candidate revisions and failed tests block progress.
- No progress payload, diff, source, test report, or manual acknowledgement enters SQLite.
