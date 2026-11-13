# Remaining-category follow-up at 8d03c8a

Read-only audit; no serving, test or oracle edits. Only combined-commit, gesture
and native-listener groups were rerun (three variants each), not full acceptance.
All three remain 2/3; individual failures are unchanged.

## Combined commit

Chinese still fails. Raw/compact retains OrderCommitCoordinator.commitOrder and
its complete8..15 method, including early return, dispatch and save. The unrelated
primary callable is ConsoleFailureReporter.report, strongly matched through query
error/log vocabulary. Compact companions are wrapped log callers, not missing
method parsing. The query explicitly mentions an error; its logs cannot globally
be declared irrelevant just because a combined owner exists. No terminal-single
scope inference or exclusivity rule is reinstated. The safe next prerequisite is
independent request-scoped log-vs-operation evidence, not a score adjustment.

## Gesture

Original variant retains correct BoardGestureSurface.build and complete5..12 body.
Its candidate is uncertain against InteractionState.selectPointer; compact also
keeps CanvasInteractionSurface, whose actual code contains genuine gesture event
callbacks. No parsed range or callback entity loss was found. A certificate based
only on presence of gesture syntax cannot label the genuine neighboring gesture
implementation absent. Query-to-state/receiver binding remains the missing piece.

## Native listener contract

The actual source fixture group is `.benchmark-fixtures/evidence-funnel`. An initial
public trace mistakenly copied only the main fixture; it is explicitly retained
as listener-wrong-fixture-excluded.json and is NOT evidence about this scenario.
listener-public.json/listener-symbols.json are rerun against the correct group.

The failed contract wording prefers retryFailedResult (string evidence, score38)
over onFailure callback(score36). Raw anchors retain ResultListener interface1..4
and actual callback12..14, but compact keeps only recovery. SQLite has the full
attach method7..16, owner, source key and exact signature including both NativeRuntime
and ResultListener parameter types; the fields are not missing from the producer.

Supplemental diagnostic queries were separately frozen, not substituted for the
original oracle: explicit interface declaration and qualified attach select the
correct file. Existing accepts-ResultListener/invokes-onFailure grammar selects
attach as primary but correctly marks the operation relation weak/uncertain and
retains a competitor. It does not prove that the nested runtime observer callback
forwards to that same parameter at runtime. The original more general “binds ...
contract” query does not meet the explicit parameter grammar. Widening that grammar
or claiming a lexical token conjunction is a receiver-flow certificate would be
new unsupported authority, not recovery of a lost signature.

## Outcome

No independently demonstrated violation of an existing range/entity/identity
contract arose in these three checks. This is not a claim of permanent inability:
the exact missing relation and currently retained fields are documented to guide
future independently frozen binding evidence. No speculative runtime patch made.
