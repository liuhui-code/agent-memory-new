# Read-only post-action English precision investigation

The partial-source candidate's original three-variant result is 2/3. This report
investigates only the remaining English paraphrase. No serving code or candidate
workspace was changed. No full gate ran.

## Original first divergence

Public raw and compact both contain LightingStore, InteractionState.selectPointer,
and CommandOutputPage.build. There is no log-emitter or graph-neighbor promotion
here. An in-process observational wrapper returned every original function result
unchanged and traced:

1. focus_code_candidates selects only LightingStore as a file-level structural hit.
2. preserve_salient_evidence_candidates reintroduces the other two real symbols.
3. Callable localization selects DraftPage.reloadPreview as bounded primary, even
   though that file is absent from the selected anchor list.
4. Compact focus cannot locate that primary among anchors and conservatively
   retains the original set. The remaining failure is precision, not excerpt loss.

The query expresses four markers: actiondispatch, lifecyclesync, statewrite,
repositoryboundary. Existing target scope is conjoined multiple. Neither the
scope classifier nor thresholds were changed or proposed for relaxation.

## Independent public control

A frozen ThermostatStore/PointerState/CommandPanel fixture repeats the raw-stage
supplement pattern, but its compact output correctly keeps only ThermostatStore,
because callable localization selects the correct store. This is a useful negative
result: the supplement stage alone is not an independently proven compact defect.
Do not describe this control as red or as a newly fixed failure.

## Safe boundary

LightingStore's aggregate file evidence spans separate dispatch and refresh
methods. File-level coverage does not prove all supplemental source irrelevant,
and an extra state/write or command-display candidate is not disproven simply by
failing a heuristic complete-method check. A safe future change would need an
independent source-level ownership/operation contract and positive multi-owner,
literal, explicit-name and unknown-candidate controls. This investigation provides
no such new certificate, so it proposes no serving patch. The partial-source
budget candidate is untouched, and terminal-single scope work remains withdrawn.
