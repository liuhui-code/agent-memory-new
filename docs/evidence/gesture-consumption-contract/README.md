# Gesture argument consumption: bounded saved-evidence review

Base 6188afe. No public query, evaluation, new fixture, runtime change or GitHub
write. `audit.py` only parses the three unchanged local source files using the
current adapter and saves exact source/digests/entities/relations/call strings.
This offline parse is **not** the old SQLite archive or a new public reproduction.
Saved public evidence is from `commit-gesture-current` at 8d03c8a.

## The original target does not write known state

BoardGestureSurface.build 5–12 contains onActionUpdate callback 8–10:
`this.boardEngine.shift(event.offsetX, event.offsetY)` at line 9. Field boardEngine
has declared type BoardEngine. No BoardEngine declaration/shift implementation
exists in the fixed system-capability source tree (searched that tree). Therefore
source proves forwarding two event member expressions into a typed receiver call,
not which state is mutated, cells moved, points updated or completion changed.
The synthetic query's symptom description cannot supply that absent implementation.

The real competing CanvasInteractionSurface has callbacks 11–13 and 14–16;
each assigns `this.activeHandle = event.fingerList[0].id`. This is a direct callback
expression→state assignment, not absent gesture behavior. InteractionState has
`selectPointer(index:number)` assigning activePointer, but no gesture registration.
Neither a gesture marker nor a state-write marker alone establishes query ownership.

## Current offline typed facts and exact missing fields

Board callback entity is `BoardGestureSurface.onActionUpdate@8`, range 8–10,
signature `callback onActionUpdate@8`, key `symbol:fc39b9aeadd967bd1c0fd96b`.
Its `calls` relation has target_name shift, qualified target BoardEngine.shift,
line 9, detail `typed field call through boardEngine; arity=2`, confidence .9/static.
Target_key and target_file_path are null. It is unresolved typed identity, not a
resolved callee or a state-flow certificate. Callback signature has no event
parameter symbol/type identity; relation has no argument spans or values.

Canvas callback keys `symbol:2ce94d01e57e8ad928bd287f` and
`symbol:cb816d10e4e42e2f1f188493` both write target
`symbol:d8a66dc3b42384448f19a000` (activeHandle). These are actual same-owner state
edges, with line 11/14 representing callback start, not exact assignment line12/15.
No RHS event-field identity is encoded. All current parse gaps lists are empty;
empty gaps do not certify completeness or prove every semantic fact represented.

## First boundary, not downstream erasure

`semantic_ecma_callbacks.callback_callable_specs` receives a callback range and
builds a name/range signature; it does not model callback parameter declarations.
`source_call_scanner.scan_calls_masked` retains the balanced original call text
`this.boardEngine.shift(event.offsetX, event.offsetY)`. In
`semantic_ecma.callable_relations` typed_calls, the relation retains receiver type,
method and computed arity but drops the argument expressions/positions. Thus the
argument text exists at the scanner, but no expression-consumption relation is
constructed. `state_accesses` records state assignment without RHS provenance.
These are producer representation boundaries, not a discovered metadata loss in
SQLite/compact. No existing formal return/argument binding was found violated.

Saved actual public output keeps full Board build5–12 and Canvas build5–18,
truncated=false, plus InteractionState1–7. The Board field declaration is outside
its returned build excerpt, but within anchor read_window2–13; exact source may
be inspected under the existing read contract rather than inferred from names.
The gesture callback expressions themselves are already legally available to the
Agent with no new read. Raw callable primary is correct Board.build24.5, uncertain;
InteractionState.selectPointer23.645 and Canvas.build18.47 are alternatives.
Expected-source stages all pass, evidence_funnel.first_loss=null. Only precision
fails: three anchors, required Board retained; expected single scope observed
unknown. It is incorrect to call this first-loss of a target source or state edge.

## Why this is NOT render's second independent defect class

Render observation: a resolved local helper return is nested as Text argument;
ordinary call identity cannot distinguish consumed versus discarded result.
Gesture observation: an event parameter member is passed to an unresolved typed
callee, and a competing owner directly writes another event member to state.
They share the broad need to identify expressions and consumption positions, but
have different provenance prerequisites (resolved return vs callback binding,
receiver resolution, missing callee implementation). A generic expression graph
is not justified merely by this superficial similarity.

There is no independently frozen generic gesture public red in the inspected
ledger/material. The original synthetic failure is not that independent evidence.
Existing fixed keyboard experiment is a generic PASS with source body intact;
it must not be repackaged as a red. Comparison's independent generic failure had
empty anchors, while its separately established declaration-identity bug was fixed
and original precision remained2/3. That is not a same-layer consumption red.
No new query, noise source, fake BoardEngine implementation or scoring oracle was
introduced to force a second defect class.

## Finite next step / stop

One can design an inspectable source-fact sketch only: exact callback declaration
range + parameter binding identity, balanced receiver call argument positions,
member-access bytes, source digest and unknown-on-shadowing/alias/nesting. It must
say **argument forwarding**, not runtime mutation/state update or unique owner.
But it cannot yet become a shared production abstraction or an exclusion rule.
Need independently motivated public failure with real target definitions and a
specific existing-request authority first. Reusing the current red to author a
matching competition fixture would not supply independence. This branch stops at
this evidence boundary, not at a claim that all future gesture repair is blocked.
No original count change (still20), no full gate, no runtime/tests diff or remote.
