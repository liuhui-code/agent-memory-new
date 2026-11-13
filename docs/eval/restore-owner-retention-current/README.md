# Restore owner retention: read-only consumer audit

Runtime inspected: `ed3fd70`. This is NOT a new context run or a new measurement
of the original group. No query, oracle, source fixture, production code, threshold
or source-operation certificate was changed. No tests or new queries were run.

## Saved evidence and actual source

Saved commands/output: `docs/eval/restore-current-20261114/context-persistence-key-restore-owner-clean.json`.
The last two entries contain raw and compact JSON in `stdout`. The query is the
unchanged English variant requesting the lifecycle read implementation rather than
the archive screen. Related historical result: `original-current.json` and README
in the same directory, recording 2/3 (also 2/3 in its prior-runtime comparison).
These outputs predate this audit; old excerpt/identity presentation must not be
represented as newly measured after later fixes.

Source paths below are relative to `docs/eval/fixtures/system-capability/`:

| Anchor | Saved provenance | Actual method evidence |
| --- | --- | --- |
| `src/abilities/ProfileBootstrapAbility.ets` | raw `query_handoff.callable_evidence.primary`: `onCreate`, bounded; source range 15–19 | Lines 14–20 create preferences, deserialize `getSync('sessions', '[]')` into ProfileList and connect it through `() => profiles`. This is the requested read implementation; the file also has a separate save method. |
| `src/abilities/SessionAbility.ets` | raw `wiki_matches`: `onCreate`, score 26.25, reasons include `graph_neighbor`, `graph_relation:imports`; raw `query_handoff.code_anchors`: source wiki, code_symbol record 5, graph_neighbor true, range 6–8 | The method calls `this.profileService.loadProfile()`. Its graph association is real retrieved evidence, not something this audit proves irrelevant. |
| `src/pages/ProfilePage.ets` | raw `query_handoff.code_anchors`: source `wrapped_log_caller`, code_log_effect record 10, `aboutToAppear`, range 8–10; retained compact anchor | The method also calls `this.profileService.loadProfile()`. It is NOT a salient-only addition. |

`src/services/ProfileService.ets`, lines 4–6, implements loadProfile with
`hilog.error(..., 'profile load failed session invalid')`. Neither extra method
nor this service performs the preference read/rebuild. That does not prove the
callers unrelated to every possible diagnostic task, or establish their absence
from a broader execution path. Missing links are not negative causal evidence.

Raw `query_handoff.path_context.activated` is false with
`activation_reason=no_strong_log_anchor`; this means no activated strong log path,
not absence of useful log evidence. Compact retains the primary plus the two
extra sources. A graph-protected source and a log-derived source are distinct lanes.

## Current consumers: no demonstrated missed exclusive certificate

- `context_callable_focus.focus_callable_anchors`: after bounded/multiple/path
  checks, any graph_neighbor prevents ordinary narrowing when the primary lacks
  target_owner_kind_match/preferred-artifact qualification. This protects the
  entire anchor set, not only the graph anchor. It therefore offers a specific
  design question: why must graph protection also preserve a separately admitted
  log anchor? It is not evidence that retaining only primary+graph is safe.
- `query_salient_source_retention.redundant_source_supplement` deliberately exempts
  graph provenance. It cannot be used to delete Session based on lexical overlap.
- `query_log_owner_admission.admitted_log_owners` requires a wiki function/method
  covering all inferred mechanisms (at least two), without a multiple-target
  permission. Saved primary wiki evidence is a code_file with aggregated behavior,
  not a complete method witness. Do not transfer file markers to onCreate.
- `query_source_operation.certify_source_operation` requires supported complete
  mechanism coverage, known valid candidates and appropriate request scope.
  Saved onCreate roles contain `source_operation_checked:v2.1` and
  `source_operation_unresolved:persistenceread`. The arrow callback is a conservative
  static-parser limitation; unresolved does not mean no read. Bounded localization
  is not a substitute for an exclusive source-operation certificate.

The frozen independent Bootstrap/Persistence/Registry experiment in
`docs/eval/restore-current-20261114/{protocol,baseline,contract-diagnostic}.json`
remains useful evidence of different scope/multi-mechanism limits. It lacks this
combination of graph-neighbor and wrapper provenance and cannot certify a fix at
this consumer layer. No existing independent public red plus controls currently
establishes that the broad graph guard is misusing an already granted permission.

## Minimum independent before design, NOT executed

Before any candidate, freeze a source-grounded reader, a genuine graph neighbor,
and a separate wrapper/log source, together with the natural task and expected
source roles. Observe the same first retention layer through public raw/compact.
The expected exclusion of the wrapper must be justified by task/source evidence,
not by absent graph edges or the original oracle alone. Keep the graph evidence
and logs visible unless a separately reviewed contract authorizes a narrower form.

Required controls: a real log/caller request, explicitly named wrapper, genuinely
required two-source relation, multiple real readers, and an unknown/unresolved
reader. Preserve identity/ranges/digest, uncertainty, source/budget limits, and
requested roles. Prove any permission independently per lane; do not infer one
primary owner from rank or strip all non-primary anchors. If the fixture needs a
new request-to-relation certificate to specify its oracle, stop and review that
contract rather than treating it as a missing implementation branch.

This stage supplies a bounded next experiment specification only. It creates no
new query, v3 expansion, source-operation relaxation, architecture approval, repair
count, full acceptance or external generalization claim.
