# Closure scope check before candidate implementation

Original fixed oracle requires precision1.0 and forbids Recovery. Saved original
Development contract result (basee760097, historical, NOT freshly rerun) contains
only Recovery and fails six required checks. Latest real independent overlay
(base71f71ed) also keeps Recovery as compact result, despite actual Relay witness
now displayed in raw diagnostic. saved-accounting.json preserves these records.

Under the assigned prohibition on changing ranking/primary or excluding rivals,
a non-exclusive append of Relay leaves two files with precision0.5; independent
oracle requires exactly Relay. This is set accounting, not a new runtime result.
A display-only candidate has already been executed and did not fix the oracle.
No additional display or append prototype is useful under that constraint.

Reviewer suggests a separate weak-positive relevance ordering experiment, with
uncertain primary to avoid score-gap promotion to bounded/exclusive focus. That
would change rank/primary and therefore requires coordinator to explicitly
resolve the current scope prohibition. No implementation or new controls run
while this scope question is pending. It would not automatically solve the
precision oracle either: preserving Recovery still fails. Necessary missing
contract is relative request relevance under unresolved source qualifiers and
uncertain member attachment, not lack of stored source witness.
