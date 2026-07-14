# Long-Term Repository Design Reasoning Evolution Plan

**Goal:** Evolve repository-grounded design reasoning into a durable, language-adaptable system that turns explicit quality goals and current code evidence into comparable design deltas, executable architecture checks, adaptive edit plans, and implementation verification.

**Architecture:** Keep the four public skills and the stable `tools/agent_memory.py` entry point. Introduce versioned intermediate representations between intent, repository evidence, proposal evaluation, and implementation verification. Runtime behavior remains deterministic; the Agent/LLM authors contracts and candidates while the runtime validates facts, rules, costs, and drift.

**Industry basis:** Use ATAM-style quality scenarios for tradeoffs, ArchUnit-style executable fitness rules, SCIP-style evidence provenance for precise code relationships, and CodePlan-style dependency-aware planning and post-edit replanning. Do not copy language-specific implementations into the runtime; preserve these ideas behind small local interfaces.

## Durable Boundaries

```text
Agent / four Skills
  -> DesignContract v1
  -> RepositoryEvidence / LanguageAdapter
  -> DesignDelta v1
  -> FitnessRule providers
  -> DesignEvaluation v1
  -> comparison / selected edit DAG
  -> actual diff verification
  -> compact evaluation metrics
```

- `DesignContract` owns goals, constraints, quality scenarios, and priorities.
- `RepositoryEvidence` owns current-source facts, provenance, confidence class, and gaps.
- `DesignDelta` owns proposed node/edge changes, assumptions, invariants, tests, and observability.
- `DesignEvaluation` owns findings, scenario coverage, cost, uncertainty, and verification conditions.
- Project rules are explicit version-controlled input; learned memories cannot silently become hard rules.
- Current code facts outrank project rules, user constraints, and governed experience in that order.
- Full proposals, generated reasoning, raw diffs, and chain-of-thought are not persisted.
- Every Python source file remains at or below 500 lines.

## Phase 1: Versioned Contracts and Fitness Rules

- [x] Define strict, backward-compatible `DesignContract v1`, `DesignDelta v1`, and `DesignEvaluation v1` loaders.
- [x] Accept the existing unversioned proposal as a legacy `DesignDelta` input.
- [x] Model quality scenarios with attribute, stimulus, environment, artifact, response, measure, and priority.
- [x] Model hard and advisory rules with stable ids, scope selectors, relation conditions, severity, rationale, and evidence.
- [x] Load optional project rules from a caller-supplied JSON file; do not infer or mutate project rules.
- [x] Refactor `design-check` to return the versioned evaluation envelope while preserving existing fields.

Acceptance:

- Invalid schema versions and malformed scenarios/rules fail clearly.
- Existing proposal callers and tests remain compatible.
- Built-in checks and explicit project rules produce deterministic findings.
- Evaluation output identifies every rule and evidence source used.

## Phase 2: Candidate Comparison

- [x] Add `design-compare` with two or more candidate files and an optional shared contract/rules file.
- [x] Block candidates with hard violations before ranking viable candidates.
- [x] Compare requirement/scenario coverage, boundary risk, affected consumers, change size, testability, observability, evidence coverage, and uncertainty.
- [x] Use a lexicographic/Pareto-style decision model; keep any aggregate score explanatory rather than authoritative.
- [x] Report the recommended candidate, decisive dimensions, tradeoffs, and ties.

Acceptance:

- A blocked candidate cannot outrank a viable candidate.
- Comparison is stable regardless of input order except for explicit final tie-breaking by candidate id.
- Every recommendation contains machine-readable reasons and unresolved tradeoffs.

## Phase 3: ArkTS Evidence Precision

- [x] Add evidence classes `exact`, `static`, `heuristic`, and `inferred` to architecture-slice output without a storage migration.
- [x] Map existing extractor provenance and evidence kinds to those classes.
- [x] Extend ArkTS static extraction for calls, state reads/writes, implements, overrides, exposed APIs, consumed APIs, and callbacks where syntax is unambiguous.
- [x] Keep ambiguous relationships out of the graph or mark them heuristic with reduced confidence.
- [x] Add a language-adapter protocol so future parsers can emit the same normalized relationships.

Acceptance:

- Every design edge exposes provenance and evidence class.
- Exact/static facts dominate heuristic facts in architecture slices.
- Narrow local analysis remains bounded to depth two, 80 nodes, and 160 edges.

## Phase 4: Plan-to-Diff Verification

- [x] Add `design-verify` with a selected proposal and actual changed files from `--base`, `--files`, or `--diff-file`.
- [x] Compare planned and actual files, including planned-file recall and unplanned-file ratio.
- [x] Re-run architecture fitness checks against the selected delta and current learned slice.
- [x] Report missing planned edits, unexpected edits, affected consumers, test requirements, observability requirements, and replan triggers.
- [x] Keep verification read-only and non-persistent.

Acceptance:

- Verification handles added, modified, deleted, and renamed paths from Git diff input.
- No-change and outside-project inputs fail safely.
- Output distinguishes implementation drift from pre-existing proposal risk.

## Phase 5: Evaluation and Governance

- [x] Add a deterministic design evaluation command for JSON case packs.
- [x] Seed ArkTS cases for state ownership, service boundaries, public API compatibility, route/config coupling, async error handling, persistence migration, callbacks, tests, and logs.
- [x] Measure contract validity, expected finding recall, candidate preference accuracy, planned-file recall, unsupported assumption rate, and payload size.
- [x] Document that only compact aggregate metrics may enter existing evaluation history; proposals and diffs remain ephemeral.
- [x] Add protocol, runtime, usage, README, and schema documentation without increasing the public skill count.

Acceptance:

- Golden cases run without network or LLM access.
- Evaluation failures identify the exact case and metric.
- Governance cannot promote a learned design pattern into a hard architecture rule automatically.

## Phase 6: Verification and Release Gate

- [x] Run focused design, graph, impact, CLI, and evaluation tests after every phase.
- [x] Run the complete test suite and Python compilation.
- [x] Enforce the 500-line Python limit, four-skill count, progressive-disclosure references, and stable CLI entry point.
- [x] Update `agent.md`, runtime/usage/protocol documentation, and `gitlog.md`.

## Performance Guardrails

- Reuse FTS5 and bounded active-edge traversal; do not scan the full graph per candidate.
- Build one architecture slice per shared contract and reuse it across candidates.
- Prefer local data-flow/static relations; global expansion requires explicit evidence gaps.
- Cap candidates at eight, proposal nodes at 200, proposal edges at 400, and rules at 200.
- Comparison and verification remain deterministic, read-only, and free of runtime LLM calls.

## Rollback

Each phase is independently removable. Removing compare, verify, or evaluation commands leaves `design-check` and repository evidence intact. Removing versioned contracts falls back to the legacy proposal loader. No phase changes stored memory semantics or requires a database rollback.
