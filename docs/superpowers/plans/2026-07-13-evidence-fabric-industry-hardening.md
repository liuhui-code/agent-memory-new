# Evidence Fabric Industry Hardening Plan

**Goal:** Improve query, code graph, log graph, causal-chain, and impact-analysis quality as one coordinated system while preserving the local SQLite architecture and four public skills.

**Boundaries:** No vector database, graph database, daemon, full call graph, raw-log archive, or fifth public skill. Every Python file remains at or below 500 lines. Query work remains bounded; heavier repair stays in maintain workflows.

## Target Architecture

```text
User goal / change
  -> local-global goal router
  -> bounded query decomposition
  -> FTS5 + versioned code graph + log/incident anchors + experience
  -> novelty stop and diversity selection
  -> calibrated evidence fusion
  -> causal evidence classification
  -> answer / impact tests / governance feedback
```

## Industry Patterns Applied

- Path-oriented code analysis: preserve typed, inspectable source-to-target steps rather than returning unexplained related nodes.
- OpenTelemetry-style correlation: normalize event name, trace/span/request/session identity, resource, reason, error, and result fields without requiring an SDK.
- Causal RCA: distinguish association, temporal order, structural mechanism, runtime propagation, verification, and contradiction.
- Hybrid retrieval: combine specialized lanes after per-lane normalization; tune with project golden cases rather than assuming one universal fusion rule.
- Predictive test selection: learn from recommended tests, tests actually run, failures, misses, and flaky outcomes.
- Local/global graph retrieval: use local entity expansion for concrete symptoms and bounded aggregate summaries for architecture or recurring-theme questions.

## Phase 1: Versioned Edge Governance

- [x] Add `source_revision`, `extractor_version`, `valid_from`, `valid_to`, `evidence_kind`, and `last_verified_at` to `memory_edges`.
- [x] Backfill existing edges with conservative legacy metadata.
- [x] Write metadata for newly extracted structural edges.
- [x] Keep query eligibility limited to active edges, but physically replace refreshed scope edges so routine learning does not accumulate an unbounded historical graph.
- [x] Expose edge provenance and freshness through evidence normalization and graph quality.

Acceptance:

- Existing databases migrate idempotently.
- New edges state how and when they were produced.
- Query and impact traversal exclude invalid edges.
- Current edge versions are retained; refresh history remains in scope/refresh records instead of duplicate graph edges.
- Existing direct SQL inserts in tests remain compatible through defaults.

## Phase 2: Adaptive Query Execution

- [x] Extend the goal plan with `query_scope`, bounded subqueries, lane budgets, novelty threshold, and maximum rounds.
- [x] Generate at most three deterministic subqueries from symptom, code/change, and verification facets.
- [x] Stop when a round contributes no new stable evidence ids or the configured maximum is reached.
- [x] Deduplicate candidates and retain the strongest representation.
- [x] Apply source, file, and pattern diversity limits before final context output.
- [x] Route global questions to lightweight aggregate evidence instead of broad graph traversal.

Acceptance:

- Query expansion is deterministic and bounded.
- Audit output reports rounds, new evidence, stop reason, and selected scope.
- Repeated experience cannot consume the whole context.
- Local queries do not pay the cost of global aggregation.

## Phase 3: Log Correlation and Causal Evidence

- [x] Parse `trace_id`, `span_id`, `trace_flags`, `event_name`, `result`, and ability/module/resource identity from temporary logs.
- [x] Preserve those fields in the existing OTel-lite projection and runtime evidence output only.
- [x] Classify evidence chains as `association`, `supported`, `verified`, or `rejected`.
- [x] Report causal signals: structural mechanism, temporal precedence, runtime correlation, verification, and contradiction.
- [x] Keep chain confidence bounded by its weakest evidence and downgrade stale/invalid edges.

Acceptance:

- Shared text alone produces association, not verified causality.
- Structural plus runtime correlation produces supported evidence.
- A resolved incident with resolution evidence can produce verified evidence.
- Contradictory or rejected evidence is visible and cannot remain a positive chain.

## Phase 4: Impact-Test Feedback Loop

- [x] Add a compact `impact_feedback` table with change fingerprint, recommended tests, executed tests, outcome, failed tests, flaky tests, missed targets, and timestamp.
- [x] Add `impact-feedback --json` under the existing runtime entry point.
- [x] Recommend tests from code/test naming, graph proximity, and prior helpful feedback.
- [x] Keep direct static/dynamic evidence separate from historical prediction.
- [x] Add feedback summaries to impact audit and governance review.

Acceptance:

- Feedback stores summaries only, not diffs or test logs.
- Historical failing/missed tests receive bounded recommendation bonuses.
- Flaky-only evidence is marked and cannot dominate.
- Projects without feedback retain deterministic static recommendations.

## Phase 5: Governance and Documentation

- [x] Add edge-version, query-drift, weak-causal-chain, and impact-feedback signals to health/maintain outputs where bounded.
- [x] Update query and maintain skills without changing the public skill count.
- [x] Update runtime, usage, schema, and README documentation.
- [x] Record all meaningful changes in `gitlog.md`.

## Phase 6: Verification

- [x] Add focused unit tests for migrations, edge validity, query stopping/diversity/global routing, log correlation, causal levels, and impact feedback.
- [x] Run affected query, graph, log, incident, calibration, and impact tests.
- [x] Run the full test suite.
- [x] Run compile, line-limit, diff, and four-skill checks.

## Performance Guardrails

- Subquery count <= 3 and retrieval rounds <= 3.
- Candidate identity deduplication happens before fusion.
- Diversity selection is linear over bounded candidates.
- Graph traversal remains one hop and uses current source/target indexes.
- Global summaries use aggregate SQL with hard result limits.
- Impact feedback keeps one compact row per submitted evaluation.
- No raw log, diff body, test output, or generated answer history is persisted.

## Rollback

Disable query decomposition and test feedback handlers, remove the optional metadata columns/table in a later migration if necessary, and fall back to the existing single-query Evidence Fabric. Existing memory, code wiki, incident traces, and four public skills remain usable.
