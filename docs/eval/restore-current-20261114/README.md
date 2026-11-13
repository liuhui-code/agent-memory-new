# Restore read/write current boundary (development only)

Base: 0dc58f2781d8c567b9e74fd8a14e4ec40028f880. No serving or evaluator changes.

## Current measured result

The unchanged persistence-key-restore scenario is **2/3**, not the stale 1/3
record. A same-machine selected-scenario comparison on prior 23e00f1 runtime
(0822bb2 is its documentation-only descendant, tools/tests diff empty) is also
2/3. All selected checks, paths, missing spans and token counts match. This is
NOT a new improvement attributable to the partial-source recovery stage.
Original and Chinese pass. English already contains the required owner and
source span, but also SessionAbility and ProfilePage, failing owner precision.

Command on each runtime (distinct fresh project/memory dirs):
`python tools/agent_memory.py eval-context-capability --cases docs/eval/system-capability-cases.json --case-id context-persistence-key-restore-owner --source docs/eval/fixtures/system-capability --project <fresh-project> --memory-home <fresh-memory> --json`

## Independent reproduction and source-operation boundary

Reused the previously frozen Bootstrap/Persistence/Registry development fixture
unchanged, after reading its rejected-read-marker result. Public compact output
remains 3/5 under the old required-owner/exclusion harness. Reader request and
mixed reader/writer request still select only Persistence. The mixed harness is
weaker than true both-owner acceptance; its failure is not a multi-target pass.
Writer, explicit writer and explicit registration controls pass.

`contract-diagnostic.json` uses actual method bodies, not whole-class inputs.
The clean Bootstrap method already produces checked:v2.1 plus persistenceread.
Thus lack of any method read witness is not the failing layer in that fixture.
Its reader query is classified multiple (conjoined actions), and inferred markers
include read, lifecycle AND write. Consumer cannot certify all of those from a
pure reader. Writer references preferences without a certified read and remains
unknown for read, rather than falsely proved absent. The real startup method has
an arrow callback and returns unresolved read conservatively. Neither changing
unknown to absent, changing multi to single, nor adding an unproved write witness
is justified by this investigation.

Current original English raw diagnosis selects onCreate as callable primary and
already carries its real source window. Extra startup/profile sources survive
projection; no incomplete primary body or source-read failure explains the last
original failure. No new independently proven implementation bug was found.

## Safe next design boundary

A future design needs compositional, scope-bound operation evidence: distinguish
requested output entities from actions, distinguish a read operation inside the
outer method from a nested callable, and preserve genuinely mixed reader/writer
requests and unknown competitors. These are contracts requiring independent
positive and negative fixtures, not a marker/weight tweak. No blanket relaxation
of existing multiple-target, complete-mechanism, exact-identity or unknown guards
is proposed. Other known canonical/archive/output failures are not retested here.

## Reproducibility / limits

`probe.py` runs the frozen public fixture; `inspect-clean.py` runs the original
English request against the standard materialized source using the formal CLI.
Initial diagnostic filename inspect.py shadowed Python stdlib inspect and failed
before runtime; renamed inspect-clean.py, then succeeded. No production change.
No full aggregate, new holdout, remote write, new repair count or external claim.
