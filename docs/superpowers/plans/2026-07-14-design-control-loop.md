# Repository-Grounded Design Control Loop Plan

**Goal:** Evolve repository-grounded design checks into a revision-bound design control loop that shares one repository model across understanding, synthesis, evaluation, planning, verification, and calibration.

## Durable Boundaries

- Keep the four public Skills and `tools/agent_memory.py` as the only runtime entry point.
- SQLite remains authoritative for learned repository facts and compact governed outcomes.
- Agent-authored intent, candidates, decisions, plans, and raw verification details remain caller-owned or disposable runtime artifacts.
- Current source and exact/static repository evidence outrank rules and historical outcomes.
- Historical outcomes can calibrate risk and strategy but cannot create hard architecture rules.
- Every Python source file remains at or below 500 lines.

## Stable Pipeline

```text
DesignIntent v1
  -> RepositorySnapshot v2
  -> baseline ArchitectureView v2
  -> DesignContract v2
  -> DesignCandidate / DesignDelta v2
  -> evidence-backed DesignEvaluation v2
  -> DesignDecision v1
  -> ChangePlan v1 DAG
  -> implementation and replan triggers
  -> DesignVerification v2
  -> compact DesignOutcome v1
```

The deterministic runtime supplies facts, validates schemas, checks evidence, builds plans, and verifies outcomes. The Agent interprets user intent and authors materially different candidates. No runtime LLM or hidden chain-of-thought is introduced.

## Phase 0: Protocol and Ownership

- [x] Define versioned repository snapshot, architecture view, intent, coverage evidence, change plan, verification, and outcome envelopes.
- [x] Preserve `design-contract/v1`, `design-delta/v1`, and existing command output fields.
- [x] Add repository revision, freshness, capability, evidence-gap, and provenance fields to all design outputs.
- [x] Document persistence and authority for every artifact.

Acceptance:

- Old proposal and contract files continue to load.
- Every evaluation identifies the baseline revision and capabilities used.
- Ephemeral design artifacts do not enter SQLite.

## Phase 1: Repository Model v2

- [x] Add one read-only repository-model builder over normalized code files, symbols, logs, and active edges.
- [x] Build a goal-derived baseline before reading candidate anchors, preventing candidate-confirmation bias.
- [x] Merge goal-discovered and explicit-scope anchors while identifying their origin.
- [x] Expose topology, ownership, behavior, data, failure, runtime, and change views from one bounded snapshot.
- [x] Reuse graph revision and report stale, empty, truncated, or unsupported capabilities explicitly.

Acceptance:

- Design, comparison, and verification can reuse the same baseline snapshot.
- Candidate-only paths do not suppress goal-discovered consumers or owners.
- View construction remains depth-bounded and indexed.

## Phase 2: Design Intent and Evidence-Backed Contract

- [x] Define `design-intent/v1` with goal, scope, exclusions, acceptance criteria, constraints, and questions.
- [x] Extend normalized contracts with intent id and evidence requirements without breaking v1 callers.
- [x] Replace boolean scenario coverage with `claimed`, `supported`, and `verified` states.
- [x] Require supported coverage to cite Delta nodes/edges and repository evidence; require verified coverage to cite a verification obligation.
- [x] Treat unsupported claims as uncertainty, not successful coverage.

Acceptance:

- Existing string coverage remains accepted as `claimed`.
- Unsupported claims cannot improve candidate ranking as supported coverage.
- Every scenario reports missing evidence and its next verification action.

## Phase 3: Candidate Synthesis Protocol

- [x] Keep synthesis in the Query Skill and a one-level progressive-disclosure reference.
- [x] Return a compact synthesis brief containing baseline facts, extension points, constraints, gaps, and candidate diversity requirements.
- [x] Require a smallest viable candidate first and alternatives only for material tradeoffs.
- [x] Define `design-decision/v1` with selected/rejected candidates and explicit tradeoffs.
- [x] Do not add an Agent-specific runtime wrapper or persist generated reasoning.

Acceptance:

- The Skill can author candidates without embedding the full repository or graph.
- Candidate diversity is structural or behavioral, not wording variation.
- The runtime remains deterministic and LLM-free.

## Phase 4: Multi-Dimensional Evaluation

- [x] Introduce a registry of bounded evaluator providers.
- [x] Retain structural gates and project fitness rules while exposing bounded evaluation dimensions through provider interfaces.
- [x] Evaluate constraints, evidence coverage, compatibility, ownership, dependency direction, failure flow, change cost, testability, observability, and uncertainty.
- [x] Rank viable candidates by hard gates and Pareto/lexicographic dimensions using supported coverage rather than claims.
- [x] Report sensitivity points, tradeoff points, unresolved risks, and decisive evidence.

Acceptance:

- A hard violation always blocks a candidate.
- A claimed-only scenario cannot outrank supported coverage.
- Every decision dimension is explainable and deterministic.

## Phase 5: Change Plan DAG

- [x] Generate `change-plan/v1` from the selected Delta and baseline.
- [x] Plan symbol/file edits, dependencies, expected Delta, tests, observability, and verification obligations.
- [x] Topologically order schema/API, implementation, consumers, configuration, tests, and instrumentation.
- [x] Detect cycles and expose replan triggers.
- [x] Keep plans bounded and disposable.

Acceptance:

- Every planned node has stable id, target, dependencies, expected changes, and verification.
- Public API and state-owner changes schedule known consumers after their prerequisite.
- Invalid or cyclic plans fail visibly.

## Phase 6: Verification and Replanning

- [x] Compare planned and actual files and symbols.
- [x] Compare expected and current graph Delta against a fresh repository revision.
- [x] Accept structured test evidence with command, status, exit code, and summary while preserving legacy command strings.
- [x] Verify scenario obligations and classify coverage as verified only with evidence.
- [x] Emit bounded replan triggers for drift, missing consumers, failed tests, stale graph, and unmet obligations.

Acceptance:

- Verification distinguishes stale graph gaps from implementation mismatch.
- Failed test evidence cannot satisfy an obligation.
- Symbol-level drift is reported separately from file-level drift.

## Phase 7: Governed Calibration

- [x] Add compact `design_outcomes` storage without proposals, diffs, source, test logs, or reasoning.
- [x] Record planned/actual recall, unplanned ratio, scenario verification, failed-test count, replan count, and outcome.
- [x] Summarize calibration for later risk hints and evaluation confidence.
- [x] Never convert outcomes into hard rules automatically.
- [x] Add maintain-health visibility and bounded retention/indexes.

Acceptance:

- Outcome recording is explicit and auditable.
- Design checks remain read-only.
- Calibration can be deleted without damaging repository facts or memory.

## Phase 8: Verification and Performance Gate

- [x] Add protocol, baseline independence, evidence coverage, evaluator, plan, verification, calibration, and compatibility tests.
- [x] Run the complete test suite, compilation, diff checks, four-Skill check, and 500-line gate.
- [x] Benchmark baseline construction, comparison reuse, and verification on the large archive.
- [x] Update Agent, runtime, usage, schema, Skill protocol, Query Skill reference, and local development log.

## Performance Guardrails

- Read one graph revision per design operation.
- Build one baseline per contract and reuse it across candidates.
- Batch node and edge reads; never issue SQL from evaluator loops.
- Keep local views at depth two, 80 nodes, and 160 edges unless a caller explicitly lowers the bounds.
- Cap candidates at eight, plan steps at 200, and evidence references per coverage item at 20.
- Store only compact outcome metrics and keep runtime design artifacts disposable.

## Rollback

The v2 models wrap existing v1 inputs and outputs. Removing synthesis briefs, evaluator providers, change plans, structured verification, or calibration leaves existing design checks operational. Dropping `design_outcomes` loses only calibration metrics. Repository facts and the four public Skills remain valid.

## Results

- Final complete suite: 316 tests passed in 217.371 seconds.
- Focused design/evidence/semantic/impact/governance suite: 57 tests passed in 37.777 seconds.
- Large archive: 312 MiB SQLite, 16,300 learned files.
- Warm single-candidate design check median: 0.496 seconds over three runs.
- Warm two-candidate comparison median: 0.490 seconds over three runs with one reused baseline.
- Public comparison payload reduced from 55,627 to 22,558 bytes after removing repeated internal architecture models.
- Python compilation, diff checks, fixed four-Skill count, CLI entry, and 500-line limit passed.
