# Direct invocation versus callback capture: shared core, not two proven defects

Read-only follow-up on the same 63970fc worktree. Read actual saved JSON, not only
the frozen PLAN/oracle. No new sources, queries, test run, producer or consumer
change. All public observations below are historical captures.

## Actual outputs checked

`docs/evidence/typed-parameter-invocation/before.json`, raw AND compact:

| Cohort | method evidence / actual call | typed match | weak | certainty |
|---|---|---|---|---|
| Direct | target rejected / target.rejected(...) | true | true | uncertain |
| CommentOnly | target rejected record / comment plus record(target) | true | true | uncertain |
| OtherReceiver | fallback rejected / fallback.rejected(target) | absent | absent | ordinary bounded fallback |
| DifferentParameter | record(target); other.rejected(...) | absent | absent | ordinary bounded fallback |

The source in frozen protocol makes Direct the only actual invocation on the
DeliverySink parameter. CommentOnly's match does not satisfy that stronger fact.
But the initial strict no-match oracle assumed stronger authority than implemented:
`tests/test_query_typed_contract.py:test_receiver_operation_is_lexical_evidence_only`
and `query_typed_contract.match_candidate` intentionally define token evidence.
`rank_callables` marks operation matches weak, and `certainty` returns uncertain.
OtherReceiver/DifferentParameter's ordinary bounded fallback is not a positive
typed-relation certificate either. Do not relabel those results as identity proof.

`docs/evidence/weak-typed-reservation/after.json` was inspected separately:
samefile primary remains weak/uncertain CommentOnly.forward, but Pair.ts retains
both ranges 3–6 and 10–12; crossfile retains CommentOnly and Direct source ranges.
Thus published raw identity and weak-reservation repairs preserve the real source;
they did not establish precise receiver evidence or change this primary. These
already fixed projection defects must not be counted as new receiver defects.

Listener `docs/eval/native-listener-current-20261114/independent.json` records the
separate generic binding request selecting Recovery instead of Relay. Its contract
is None. The existing typed recognizer does not promise callback capture/forwarding.
The saved original ResultListener failure query also has contract None. That is a
missing expressible relation, not evidence that a current strong tuple was lost.

## Finding and architecture decision

There is a real reusable *technical subrelation*: a source-bound formal parameter
of a bare named type is the root receiver of a particular syntactic member call.
Direct calls and calls inside a captured callback both need that exact fact. The
comment/wrong-receiver cohorts are useful discrimination controls for this core.

There are NOT currently two independent demonstrated violations of an existing
strong receiver contract. Direct weak lexical behavior is explicitly allowed;
callback forwarding is outside the existing contract. Their different desired
query forms do not alone meet the repository's two-independent-defect architecture
gate. No finite model implementation or serving change is authorized by this
comparison. It is legitimate to propose a shared local interface, not to assert
that the old evidence already proves a cross-cutting architecture fix necessary.

## Minimum explicit witness model if a later local extension is approved

Use a typed, versioned optional record, not terms/detail parsing. A minimal core:

- source snapshot binding: file path, source key, exact outer callable range,
  original-byte source digest and semantic adapter/version; reuse these from the
  validated indexed parent where possible, but require exact join equality;
- formal binding: parameter index/name and bare declared type, plus declaration
  interval in the exact signature/source snapshot;
- invocation: exact member identifier and receiver/call intervals with defined
  decoded-coordinate units; mode `direct` versus `captured_callback`;
- validation state: positive witness only. Missing, unknown, unsupported, stale,
  truncated or contradictory data is not false/absence. Do not add a negative
  certificate or default to known-empty on old indices.

A callback witness must additionally contain a separately typed extension:
argument call interval and syntactic receiver/member; object-argument interval;
property name; callback body interval; and the scope path linking the invocation
back to the same outer formal declaration without an intervening binding. A
nested callback cannot satisfy a direct invocation request just because it lies
inside the outer line range. An unpassed object callback cannot satisfy the
call-argument relation. These are extra obligations, not redundant core fields.

For the first conservative subset, direct mode accepts only direct statements in
known ordinary method bodies; callback mode only a directly passed object with
explicit ordinary property arrows and simple invocation bodies. Shadowing,
reassignment, aliasing, dynamic/optional receiver access, two same-type parameters,
unknown lexical scopes or unsupported defaults/generics yield no new witness.
No framework registration, eventual execution, actual object instance or causal
success is implied by either mode. Retain multiple valid witnesses separately.

SemanticMechanism currently has no such typed field. An optional structured
extension is a real model/version/roundtrip compatibility change even if stored in
its existing JSON database column. Existing consumers must not infer proof from
human-readable descriptions. Strict validation and cap behavior must preserve
whole witnesses or omit them as unknown; installation alone cannot update old
indices. See README representation review for the from_dict/old-reader issue.

## Separate consumers, not one broad typed authority flag

Direct request: existing explicit parameter+invokes-member grammar may obtain a
new exact-source association only from direct-mode witnesses. Preserve the old
weak lexical indicator under its current meaning; do not quietly reinterpret it
or mark every unmatched candidate absent.

Callback request: require a distinct explicit binding-to-named-type descriptor
and matching property/member selector. `bind` is not `accepts`. The original
failure/onFailure identifier-segment mapping still requires independent approval;
no on-prefix special case or synonym fallback. A direct call outside a callback
cannot satisfy the callback-mode descriptor.

Neither consumer gets a unique-owner or bounded/exclusive certificate just from
one available witness. Multiple forwarders, unknown candidates, explicit retry,
logs/text/declaration and multiple-target requests require unchanged protection.
Existing raw/compact source and budget guarantees remain independent tests.

## Concrete next step, if approved

A finite isolated model-only test could encode/decode the known Direct positive
and CommentOnly/OtherReceiver/DifferentParameter non-witness controls, then the
known Relay relation with its additional containment requirements. It must test
missing/unknown versions, stale digest, mismatched outer key/range, invalid offset
nesting, and record-cap loss; no runtime producer or query precedence change.
This would test representation feasibility, not fulfill the architecture gate or
repair either public query. The current review stops before that execution and
asks for the appropriate local-extension scope decision rather than manufacturing
a second defect or changing the frozen oracle.
