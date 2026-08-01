# Callable Evidence-Set Shadow Plan

## Objective

Model callable retrieval as a bounded evidence set before allowing any candidate to
control compact source projection. Measure target scope, competing support, exclusion
conflicts, and certainty basis without changing serving anchors or token budgets.

## Proven Need

Two rejected experiments established that one scalar `bounded` flag is insufficient:

- projecting every bounded primary improved isolated misses but regressed multi-file,
  graph, exclusion, and method-window cases;
- subtracting a file-rank prior changed a correct two-file query from `uncertain` to
  `bounded` even though candidate order did not change.

The missing abstraction is a set-level calibration contract. Ranking confidence for one
candidate cannot express whether the request expects multiple owners or whether another
candidate has independent graph, typed-role, identity, or exclusion evidence.

## Architecture

Add a pure `CallableEvidenceSetProvider` behind the existing Context facade. It consumes
the user query, hierarchical localization output, and existing callable evidence, then
returns `agent-callable-evidence-set/v1` with:

- `mode=shadow` and `serving_projection_changed=false`;
- bounded members with source identity, position, owner kind, source locatability, and
  categorical support kinds;
- target scope: `single`, `multiple`, or `unknown`, with inspectable basis;
- competition facts: distinct files, same-role alternatives, graph-backed alternatives,
  and exclusion conflicts;
- calibration state: `single_candidate_supported`, `portfolio_required`, `conflicted`,
  `unresolved`, or `insufficient`;
- a boundary stating that this is retrieval calibration, not diagnosis.

The provider uses categorical evidence only. It does not add score weights or thresholds.
It may recognize explicit target-language cues and existing structured candidate fields,
but it must not contain fixture, project, path, filename, or Oracle terms.

The full Context stores this contract under `query_audit`. Compact Context omits it, so
Agent-visible anchors and the 1,500-token budget remain byte-compatible. Capability
evaluation observes the shadow contract and reports informational target-scope accuracy,
member recall, primary precision, and calibration-state counts. These metrics cannot
change `system_context_gate`.

## Phases

1. Add pure contract tests for explicit single target, explicit multi-target portfolio,
   graph competition, exclusion conflict, bounded member count, and missing evidence.
2. Add an integration test proving full Context contains the shadow audit while compact
   Context and serving anchors remain unchanged.
3. Add informational evaluator observation and aggregation without formal checks.
4. Run focused query/Context regression and a development smoke against the accepted
   185/231 baseline.
5. Run compile, JSON, four-Skill, diff, and 500-line gates.

## Promotion Conditions

The contract may influence compact projection only after a separate phase proves all of
the following on independent development fixtures:

- single-target precision is calibrated across owner kinds;
- multi-target and graph-backed evidence is never collapsed;
- exclusion conflicts always block projection;
- no existing formal check regresses;
- a new, untouched external holdout is run once after the design is frozen.

## Stop Rules

- Do not change callable ranking, certainty thresholds, compact anchors, excerpts, or
  budgets in this phase.
- Do not interpret `single_candidate_supported` as a root cause or diagnosis.
- Stop if the shadow contract requires project or Oracle knowledge at query time.
- Stop if evaluator metrics affect the formal Context gate.

## References

- Selective prediction: https://arxiv.org/abs/1705.08500
- BEIR heterogeneous retrieval evaluation: https://arxiv.org/abs/2104.08663
- GraphRAG local context assembly: https://microsoft.github.io/graphrag/query/overview/
- Repository evaluation policy: `docs/evaluation-and-change-policy.md`

## Execution Result

The shadow provider is implemented as a pure bounded policy. It emits at most three
members and uses existing target-role, graph, source-range, identity, and exclusion
fields. Full Context stores the result only under `query_audit`; compact Context does
not expose the contract and serving projection remains unchanged. Observation and
aggregation live in separate modules so the main capability runner remains below 500
lines.

Eight contract and integration tests cover single target, multi-target portfolio,
graph competition, exclusion conflict, insufficient evidence, member bounds, compact
non-interference, and informational metrics. The broader relevant regression passes
102 tests.

A 15-variant development smoke reports target-scope accuracy 0.3333, member recall
0.7556, and primary precision 0.5333. Calibration states are 1 conflicted, 1
insufficient, 2 portfolio-required, 1 single-candidate-supported, and 10 unresolved.
These values establish a deliberately low shadow baseline and prohibit serving
promotion. Every formal status, check, primary anchor, source excerpt, and first-loss
value matches the accepted 185/231 baseline.

The complete 231-variant observation produced no result inside the existing 12-minute
bounded window and was terminated. It is not counted as pass and was not rerun. The CI
scale run passed all query-latency and SQL-plan gates; unrelated incremental-maintenance
latency failed under the same elevated load, including a 9,854.305 ms large-method P95.
No threshold or implementation was changed from that observation.

Compile, 100 evaluation JSON, fixed four-Skill, diff, and 500-line gates pass. No
consumed external holdout was read, changed, or rerun.
