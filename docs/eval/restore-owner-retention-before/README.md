# Fixed restore retention before: different layer, stop

Base production ed3fd70; protocol, five exact queries, synthetic source bytes,
expected identities/spans and stop condition frozen in 06936f4 before execution.
This is a new recipe-catalog Development fixture, not copied benchmark code, not
holdout or a device execution claim. No tuning or production patch was attempted.

One CLI init/learn-path and five raw/compact context pairs completed successfully.
`public-before.json` preserves full outputs; per-query traces capture existing
functions without altering their result. `execution-started` prevents rerunning
this frozen experiment. `results.json` separately checks identity and line coverage.

| Frozen task | Identity | Full required span | Result |
| --- | --- | --- | --- |
| reader | fail | fail | Repository.load instead of CatalogRestorer |
| real-log | pass | pass | emitting source retained |
| explicit-wrapper | pass | pass | CatalogPanel retained |
| two-targets | pass | fail | both owners retained, Restorer excerpt ends at 7, missing 8–9 |
| unknown-reader | pass | pass | DeferredReader retained; read remains unresolved |

## Branch coverage is negative, not a demonstrated restore repair opportunity

For reader, raw anchors include the correct CatalogRestorer.onCreate and separate
wrapped_log_caller entries for CatalogPanel and CatalogWarmup. However NONE of
its raw code anchors has graph_neighbor true. A real source import is not equivalent
to promotion provenance on the selected match. Correct reader was not bounded
primary: CatalogRepository.load is primary (34, target_owner_kind_match=true,
structured_owner_kind), versus CatalogRestorer.onCreate 30. The task's phrase
"rebuilds its repository" is consumed as a repository owner-kind cue; this observed
reason is retained, not edited away to obtain the intended graph branch.

The compact focus line trace evaluates the graph condition at line 72, then
continues to path selection and line 94, rather than returning anchors at the graph
protection branch. Compact contains only CatalogRepository.load. This is a red at
a different localization/owner-kind layer. It does NOT demonstrate original
restore's bounded-correct-primary + graph-neighbor protection retaining a separate
wrapper. We do not retrofit its failure as that defect or change query/source to
force coverage.

Actual imports and wrapper statements exist in protocol sources; other frozen
controls show imports graph provenance in public output. The target query's lack
of that provenance remains a failed coverage condition, not proof the source
relation is absent. DeferredReader retains source_operation_unresolved:persistenceread
for its arrow body; no unknown-to-absence or broader certificate was introduced.

The two-target source truncation is an additional observed control failure, not a
passing multi-owner acceptance result. Its oracle is unchanged. Three of five
complete frozen checks pass, four of five identity checks pass; none is new repair
credit. The primary experiment did not reach its preregistered branch, so execution
stops here without variants, patches, threshold changes or further queries.

Current limitation: original restore still lacks an independent matching public
red for graph protection's collateral wrapper retention. These observations do not
authorize primary+graph-only projection or treating every other log as unrelated.
No full gate, original group rerun, external validation or serving improvement.
