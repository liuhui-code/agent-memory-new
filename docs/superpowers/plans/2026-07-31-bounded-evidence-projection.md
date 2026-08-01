# Bounded Evidence Projection Plan

## Objective

Ensure a bounded callable candidate with a current-source range remains visible in the
compact Context handed to the Agent. Preserve exact runtime-log identity, activated
graph paths, existing candidate limits, and the 1,500-token budget.

## Proven Defect

Independent development scenarios for lifecycle persistence and source replacement
reach the expected file at candidate-file, localized-file, callable, source-range, and
callable-evidence stages. The compact Context then omits that file because callable
focus can only narrow an existing wiki anchor unless the query names an explicit owner
kind. The Agent receives unrelated source excerpts even though stronger bounded source
evidence is already available.

This is a projection defect between retrieval evidence and Agent-visible Context. It is
not evidence that callable ranking, source-range selection, an Oracle, or a threshold
should change.

## Architecture

Keep `context` as the public facade and keep the existing callable-evidence contract.
Evolve the compact projection policy behind `focus_callable_anchors`:

- activated graph paths and exact log identities retain exclusive scope;
- uncertain or source-unlocatable callable evidence remains advisory only;
- an explicit target-owner match may continue to replace the candidate list;
- otherwise, a bounded primary callable missing from ordinary anchors receives one
  reserved position in the existing compact candidate budget;
- existing anchors remain as competing evidence for Agent reasoning;
- the callable range is marked `bounded_callable_primary` so excerpt focusing cannot
  drift outside the proven method;
- no project, path, filename, query phrase, language, or Oracle-specific rule is added.

This follows stratified retrieval and evidence-preserving late fusion: a calibrated
evidence lane receives bounded representation before final compression, without being
declared a diagnosis or root cause.

## Phases

1. Add projection unit tests for bounded missing evidence, existing evidence, uncertain
   evidence, activated paths, exact log identities, and fixed candidate count.
2. Implement the policy inside the existing Context projection boundary.
3. Run the independent compact-primary scenarios and compare all existing development
   cases against the accepted 185/231 baseline.
4. Run focused regression, performance, compile, JSON, four-Skill, diff, and 500-line
   gates.

## Stop Rules

- Stop if projection must increase compact anchor, source excerpt, token, graph, or
  query budgets.
- Stop if exact runtime-log identity or an activated path loses precedence.
- Stop if an uncertain candidate is materialized as a source anchor.
- Stop if aggregate gains hide any previously passing check regression.
- Stop before changing callable ranking or source-range selection; those require their
  own independently reproduced failure and phase.

## References

- Reciprocal Rank Fusion and evidence fusion:
  https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf
- BEIR heterogeneous retrieval evaluation: https://arxiv.org/abs/2104.08663
- GraphRAG local search context assembly:
  https://microsoft.github.io/graphrag/query/overview/
- Repository evaluation policy: `docs/evaluation-and-change-policy.md`

## Rejected Broad Projection

The first implementation materialized every missing `bounded` callable primary into
the compact candidate set while retaining ordinary anchors. Four previously failing
variants passed, but thirteen previously passing variants failed and 23 formal checks
regressed. Multi-file component relations, explicit forbidden-file cases, and a large
method window were displaced or diluted.

The implementation was reverted. The result proves that the current `bounded`
certainty describes score separation for one callable; it does not prove that a query
expects one source owner or that the callable may override multi-file and graph
evidence. No serving projection change is accepted until an independent intent or
evidence-set contract can distinguish those cases without query, project, path, or
Oracle-specific rules.
