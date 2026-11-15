# Independent candidate review

The separate reviewer approved the frozen edccbf9 request/source/consumer contract
before implementation, requiring the public non-exhaustive/static/timestamp-unproven
boundary and unchanged query2. The source parser and its tests were implemented by
a separate worker while selection, transport and public verification were implemented
in the coordinating task.

The parent reviewer independently ran the initial 19 focused tests successfully and
found a concrete identity hole: changing the indexed owner qualified_name to
UnrelatedOwner still admitted the positive (observed True). This was not used to
change an oracle. The candidate was corrected to require the parsed owner name as
qualified_name and an empty owner_name, and to compare recalled method owner_name,
owner_kind, semantic_adapter, evidence_class and symbol_type alongside the preexisting
row identity. Conflicting id/key aliases now reject. test_semantic_identity_and_conflicting_aliases
freezes this counterexample and related controls. owner_kind is an existing heuristic
role such as store, NOT the declaration type; the symbol_type=class and current source
range establish class declaration, so hardcoding owner_kind=class was rejected.

The first related run retained in focused-first-run.txt found a mechanical exact
composition-kwargs expectation missing the newly required defer flag and an old test
module import requiring PYTHONPATH=.:tests. The expectation now covers the new explicit
accounting flag; no capability oracle/threshold/budget changed. Final results are
recorded separately, not substituted for the original run.
