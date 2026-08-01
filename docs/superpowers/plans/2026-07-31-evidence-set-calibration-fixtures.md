# Callable Evidence-Set Calibration Fixture Plan

## Objective

Calibrate the shadow callable evidence-set contract on reviewed, isolated ArkTS
fixtures without changing serving retrieval, compact Context, ranking, thresholds,
Oracle gates, or the fixed four Skills.

## Design Boundary

The Runtime remains a context supplier. The evidence set describes bounded retrieval
facts for Agent CLI reasoning; it does not select a root cause. The contract stays in
full Context `query_audit`, reports `serving_projection_changed=false`, and remains
absent from the 1,500-token compact handoff.

Evaluation uses an optional `oracle.evidence_set_oracle` with explicit target scope,
expected member and primary files, forbidden active members, and allowed calibration
states. These values produce informational metrics only and cannot create formal
Context checks.

## Independent Fixture Strategy

Use two disjoint fixture groups, each with three wording variants per scenario:

1. explicit single owner;
2. explicit multi-owner flow;
3. graph-backed caller and callee competition;
4. production owner with an explicit example or demo exclusion;
5. unknown marker with insufficient evidence.

The editable development group uses beacon leases, receipts, dialogs, and quotas. The
frozen calibration group uses cipher rotation, media readiness, sync flush, and archive
retention. Names, paths, methods, and domain terms are not shared across groups.
`fixture_group` materialization gives each group an isolated index, so neither group
changes the accepted 185/231 development corpus statistics.

## Execution Phases

1. Add the informational Oracle and aggregate metrics.
2. Run the development group and classify failures by scope, members, primary,
   exclusion guard, and state.
3. Accept only generic shadow-contract corrections proven by multiple development
   variants; do not modify serving projection.
4. Freeze the provider and run the calibration group once.
5. Record the first calibration result without tuning on it.
6. Run focused and broad tests, JSON validation, compilation, fixed-Skill, diff, and
   500-line architecture checks.

## Stop Rules

- Do not read or rerun consumed external holdouts.
- Do not add project, fixture, path, identifier, language, or Oracle special cases.
- Do not change formal checks, compact anchors, source excerpts, ranking scores,
  budgets, or SLO thresholds.
- Do not promote the shadow contract to serving behavior from synthetic calibration
  evidence alone.
- Record a calibration defect as new development input for a later cycle; do not tune
  against the frozen pack.

## References

- Selective prediction: https://arxiv.org/abs/1705.08500
- BEIR heterogeneous retrieval evaluation: https://arxiv.org/abs/2104.08663
- GraphRAG local context assembly: https://microsoft.github.io/graphrag/query/overview/
- Repository policy: `docs/evaluation-and-change-policy.md`

## Execution Result

The evaluation protocol now explicitly measures target scope, active-member recall,
primary precision, calibration-state accuracy, active forbidden-member hits, and
guarded exclusions. Excluded candidates remain inspectable guards but are removed from
the active evidence portfolio. A locatable candidate requires independent typed-owner,
direct-identity, or graph support before a single-candidate state is supported;
semantic-mechanism similarity alone remains insufficient. Explicit single-target
grammar covers determiner, `one`/`single`, `return only`, and existing Chinese cues.
Lower-camel method exclusions are exposed through a reusable query-language fact
without changing positive retrieval or serving candidate filtering.

The initial 15-variant development run passed all formal Context checks. It revealed
scope grammar, method-exclusion, and weak-support calibration defects across independent
variants. After generic shadow-only corrections, focused exclusion and insufficient
runs passed 9/9; their target scope, member recall where defined, primary precision
where defined, and state accuracy were all 1.0, with zero active forbidden hits.

After the provider was frozen, the disjoint calibration pack ran once. All 15 variants
and all five scenarios passed. Informational target-scope accuracy, member recall,
primary precision, and calibration-state accuracy were each 1.0. The state distribution
was six `single_candidate_supported`, six `portfolio_required`, and three
`insufficient`; two excluded alternatives were retained as guards, with zero active
forbidden-member hits. Governance reports `calibration/frozen/project_neutral` and
`tuning_allowed=false`.

The result is calibration evidence for a shadow retrieval contract, not external proof
and not permission to control compact source projection.

Validation passes 105 Context/query/evaluation tests plus 10 focused query-exclusion
and semantic-profile tests. Python compilation, 102 evaluation JSON documents, the
fixed four-Skill inventory, diff hygiene, and the repository-wide 500-line Python gate
also pass. No consumed external holdout was read, changed, or rerun.
