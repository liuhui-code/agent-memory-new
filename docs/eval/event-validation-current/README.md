# Callable-local event/state handoff evidence (Development)

Base e7600976d0c2ca9a4f9031ad68caa21931fba411. Frozen public red and tests:
5b9ce84. No original case/oracle changes, full aggregate, holdout or remote writes.

## Established defect and causal implementation layer

Existing file-level ArkTS marker extraction already recognizes an event-shaped
handler, this-state write and presentation-shaped call as statehandoff. Callable
method evidence carries eventboundary/statewrite but omits the corresponding
statehandoff conjunction even when all three appear directly in the same method.
The independent SelectionBridge method has assignment then openEditor; partial
SelectionHint only writes, PanelLauncher only opens, SplitSelection separates
write from another method. Frozen Chinese public query returns Bridge plus Hint.
Its raw wiki method evidence has coverage2 for each. After adding only the existing
conjunction to bounded callable evidence, Bridge has coverage3 with statehandoff,
Hint lacks it, and public output contains just the correct full method source.
No thresholds, target scopes, candidate scores, selection rules or schema changed.
This is a same-method retrieval hint, NOT a value-flow/parameter proof, runtime
execution guarantee, diagnosis or uniqueness certificate. It does not prove that
all operations execute on one branch, or which domain object they manipulate.

## Admission and negative controls

Only TS/ArkTS, event-shaped current callable and strict direct this-state assignment
(not ==/===/!=/!==/<=/>=) plus the existing presentation-call predicate can add the
new hint. Existing unsupported nested/regex gate remains. Only this new hint also
uses ecma_callback_mask: unknown slash/interpolation/unclosed syntax declines it.
A dedicated scope check examines EVERY nested opening brace: only recognized
if/for/while/switch/catch/with blocks or else/try/finally blocks are allowed. Unknown
object/anonymous scopes, quoted/computed methods, getters/setters and callbacks
cannot donate their writes/calls to the outer event. Ordinary if/for/multilevel-if
positive controls remain accepted. No older collection/cleanup labels were changed.

Initial lexical version reproduced a nested-template false positive. A subsequent
review found quoted/computed object methods hidden by ordinary masking; both are
fixed in formal controls. An intermediate overly narrow straight-line-only check
was replaced by recognized control-block admission before final acceptance. Initial
runs are retained, but only focused-final and *-final reports describe final code.
No new scope parser claims beyond the bounded brace/keyword checks are made.

## Public and original acceptance

Independent public queries: Chinese handoff red->green; English handoff and explicit
Hint controls remain green. Real dual-owner request still retains both requested
owners AND its pre-existing SplitSelection extra. The strict probe correctly marks
that precision result false before and after. The test checks retention only for
that control and does not claim it solved. Original event-state-handoff improves
2/3->3/3 (Chinese fixed), complete expected source spans retained.

Final necessary related suite: 51 tests pass, including 7 new tests, callable
collection/cleanup, public collection/salience, source-operation contracts/identity,
and callback lexical admission. No full evaluation was run. Runtime file131 lines.

Command: PYTHONPATH=tests:. python -m unittest tests.test_callable_state_handoff
 tests.test_callable_collection_evidence tests.test_callable_cleanup_evidence
 tests.test_collection_owner_public tests.test_collection_salience_retention
 tests.test_source_operation_contract tests.test_source_operation_anchor_identity
 tests.test_callback_lexical_admission -v

## Separately requested validation-stop diagnosis

Current validation-stop remains1/3 before and after (original+Chinese fail). Chinese
raw wiki's only selected source is OrderCommitCoordinator structural_behavior, before
compact projection. Callable primary is unrelated ConsoleFailureReporter.report;
this disproves a purely compact metadata repair as sufficient for this variant.
Original retains AccountSettingsPage span plus JobDispatchPage/DispatchProfileService.
Known independent PreferenceEditor fixture already picks its correct method and did
not reproduce the historical identity mismatch, so no new identity fix is claimed.

Validation needs a separate frozen guard/dispatch competition to distinguish a
co-occurring file-level signal from a method's early-return branch plus subsequent
dispatch. Existing validation_guard_present scans a bounded700-char window and
looks for return/throw following if and validation signal, rather than proving
branch/dispatch binding. It cannot simply be promoted into a unique-owner certificate.
This stage fixes the independently red event evidence gap and preserves validation
as a specific unresolved file-focus/localizer investigation, not a generic impossibility.

## Existing-index activation

A fresh independent project was learned with an e760097 detached baseline runtime.
The Chinese query retained Bridge+Hint under both old code and new code without
relearning. Running ordinary new-runtime `learn-path --path . --json` on that SAME
project and Memory Home then returned only Bridge. Source bytes were unchanged.
Thus this is producer metadata refreshed through normal learn-path, not a schema
migration or retroactive certificate applied to old records. See index-upgrade.json.
A user must refresh learned source normally to obtain the new method hint.

Independent final read-only review checked twelve negative cases and four positive
cases, including computed/quoted/keyword object methods, nested templates, comparison
operators, callback/function scopes and try/catch/finally. No remaining blocking
review findings. Runtime is131 lines; Python compile, diff whitespace and fingerprint
checks passed. The hint also does not certify execution order.
