# Design Quality Hardening Execution Plan

**Goal:** Replace optimistic design metrics and weak implementation evidence with measurable evaluation coverage, a real dependency DAG, revision-bound verification reports, semantic completion checks, an optional production ArkAnalyzer provider, and conservative outcome calibration.

## Non-Negotiable Boundaries

- Keep four public Skills, one Python runtime entry, SQLite truth, and generated Vault mirrors.
- Keep every Python source file at or below 500 lines.
- No runtime LLM, daemon, vector database, graph database, automatic code modification, or hidden test execution.
- Current source/exact evidence outranks historical outcomes. Calibration can add warnings or break otherwise equivalent ties; it cannot create hard rules.
- External semantic providers run out of process. Missing ArkAnalyzer/SDK must be visible as unavailable, never mislabeled exact.

## Phase 0: Stable Baseline

- [x] Commit the previously verified prepare/progress/automatic-verification workflow without `memory.md`.
- [x] Preserve the 324-test baseline and rollback point.

## Phase 1: Evaluation Integrity

- [x] Return `null` instead of a perfect score when preference or verification has no evaluated samples.
- [x] Add per-metric sample counts and explicit `not_evaluated` coverage.
- [x] Calculate contract validity from evaluated contract obligations instead of a constant.
- [x] Add repository-backed positive/negative candidate pairs and implementation verification cases.
- [x] Add a minimum-case quality gate that cannot pass on vacuous metrics.

## Phase 2: Real Change Plan DAG

- [x] Remove fallback chaining between unrelated implementation steps.
- [x] Derive dependencies from current/proposed graph edges and target-specific coverage references.
- [x] Make consumer review depend only on the changed API it reviews.
- [x] Make tests and observability depend on the implementation steps they verify.
- [x] Return multiple ready steps when independent work can proceed in parallel.

## Phase 3: Revision-Bound Verification Evidence

- [x] Define optional `verification-run/v1` provenance with base/head revision, start/end time, report digest, and source digests.
- [x] Bind JUnit/JSON evidence to the current Git head when provenance is present.
- [x] Treat missing provenance as legacy caller evidence and stale/mismatched provenance as advisory, never verified.
- [x] Expose provenance status, stale reasons, and report bounds without persisting report bodies.
- [x] Add compiler-diagnostic report ingestion as a separate evidence type.

## Phase 4: Semantic Completion for Added Files

- [x] Parse proposal-declared untracked ArkTS/TypeScript files with the existing semantic adapter.
- [x] Complete added-node steps only when the expected class/component/function is present.
- [x] Distinguish `in_progress` from `completed` for an existing file with missing expected structure.
- [x] Include untracked-file API/relation evidence without treating it as a Git commit Delta.

## Phase 5: Production ArkAnalyzer Provider

- [x] Add an optional external package under `providers/arkts-arkanalyzer` using the published ArkAnalyzer Scene/type/call-graph APIs.
- [x] Map requested files, stable signatures, source locations, inheritance, state, and resolved call edges into `semantic-provider-result/v1`.
- [x] Require the `arkanalyzer` dependency and optional OHOS SDK explicitly; fail unavailable when missing.
- [x] Add fixture-backed contract tests and a live smoke command that skips when the dependency is absent.
- [x] Evaluate static versus ArkAnalyzer output with `eval-semantic` before recommending exact mode.

## Phase 6: Conservative Outcome Calibration

- [x] Add bounded non-source calibration features to verification/outcome records: archetype, change-size bucket, risk count, and API/graph Delta counts.
- [x] Aggregate profiles only after at least five reviewed outcomes for the same archetype.
- [x] Add advisory historical-risk evidence to checks and use it only after hard gates/current evidence in comparison.
- [x] Prevent calibration from satisfying coverage, changing graph facts, or creating architecture rules.

## Phase 7: Release Gates

- [x] Update runtime, schema, usage, design, Provider, Skill, Agent, README, and development log documentation.
- [x] Run focused and complete tests, compilation, CLI/provider help, diff check, four-Skill check, and line gate.
- [x] Benchmark evaluation, planning, verification, progress, and calibration on the 6,995-ArkTS-file sample repository.
- [x] Commit the completed hardening release; push only when explicitly requested.

## Acceptance

- No design metric reports success without evaluated samples.
- Independent implementation steps can be ready concurrently.
- A stale test report cannot verify a current design obligation.
- An empty or structurally wrong new file cannot complete an add-node step.
- Exact Provider output requires a real ArkAnalyzer analysis result.
- Historical outcomes influence only bounded advisory risk after sufficient samples.
