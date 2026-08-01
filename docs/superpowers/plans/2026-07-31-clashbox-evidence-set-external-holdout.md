# ClashBox Callable Evidence-Set External Holdout Plan

## Objective

Run the frozen shadow callable evidence-set contract once against a source-reviewed,
sealed, previously unused ArkTS repository. Measure cross-project generalization without
changing serving retrieval, compact Context, ranking, thresholds, or Oracle checks.

## Source Selection

Selected source:

- repository: `https://github.com/xiaobaigroup/ClashBox.git`;
- branch: `master`;
- reviewed head: `1fdc47eb9b3bdb715fb04c4b44e1d5238faf83e0`;
- license: GPL-3.0;
- local review clone: `/tmp/clashbox-evidence-set-holdout`.

Two candidates were rejected before any evaluation. `iwae/HarmonyOS-Inno` has only an
initial bulk source import, leaving no ArkTS evidence in the required pre-fix revision.
`AbnerMing888/HarmonyOsRefresh` has rich history but distributes its core implementation
as a HAR binary and retains mostly homogeneous examples. Neither justified weakening
the existing source-diff seal contract.

## Case Design

Five cases are derived from reviewed Git diffs and pre-fix source only:

1. URL profile update: one ViewModel callable owns Profile construction and context
   initialization before metadata assignment.
2. URL profile call path: the ViewModel caller and `Profile.loadContext` callee form a
   two-file graph-backed portfolio.
3. Dark-mode lifecycle: the settings interaction and root startup initialization are
   two independent owners of the same theme-mode contract.
4. Root event lifecycle: root `Index` owns shared listener cleanup; child configuration
   and proxy pages are explicit forbidden owners.
5. Configuration persistence: the WebView file writer and ViewModel repository updater
   are two distinct persistence owners.

Every case records exact pre-fix and post-fix revisions, reviewed changed files, source
spans, evaluation profile, explicit evidence-set Oracle, and leakage guards. Oracles are
hidden from the Runtime and Agent-facing query.

## Execution

1. Validate the unsealed pack without querying it.
2. Run `eval-seal-cases` against the review clone. The command must verify every commit,
   changed-file subset, review flag, calibration contract, and canonical digest.
3. Run `eval-context-capability` exactly once against the sealed pack and fixed source.
4. Do not modify the Provider, case wording, Oracle, source spans, ranking, or thresholds
   after observing the result.
5. Record formal Context and informational evidence-set outcomes separately.
6. Run local regressions and repository architecture gates without rerunning the holdout.

## Stop Rules

- Never inspect or execute any previously consumed holdout.
- Do not replace a failed case or relax its Oracle after the run.
- Do not infer root-cause correctness from an evidence-set state.
- Do not promote shadow output into compact Context from one external repository.
- Any observed defect becomes input to a new development fixture and a future, different
  holdout; this sealed pack remains immutable.

## Execution Result

The case pack was sealed with digest
`71378afa73fa6d46f201ca386d75c62ba0289a1bb9beac3361411e1aeb116c6b` and executed
exactly once. The run returned zero candidates for all five cases because the filtered
review clone could not be archived at the immutable revisions and the benchmark layer
silently copied its empty working tree. This is an infrastructure-invalid run, not a
retrieval-quality result; no observed metric may be used for tuning or promotion.

The sealed pack is consumed and will not be changed or rerun. The benchmark workspace
now fails closed when a non-working-tree revision cannot be materialized. A future gate
must use a different, previously unused external source and verify revision
materialization before the one permitted evaluation run. The compact invalid-run record
is retained in `docs/eval/clashbox-evidence-set-external-invalid-run.json`.

## References

- Selective prediction: https://arxiv.org/abs/1705.08500
- BEIR heterogeneous retrieval evaluation: https://arxiv.org/abs/2104.08663
- GraphRAG local context assembly: https://microsoft.github.io/graphrag/query/overview/
- Repository policy: `docs/evaluation-and-change-policy.md`
