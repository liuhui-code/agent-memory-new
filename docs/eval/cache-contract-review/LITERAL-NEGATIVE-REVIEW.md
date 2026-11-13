# Narrow literal-only body evidence: read-only feasibility review

No code, new fixture, query, original rerun or score change. Read existing frozen
cache and output-loop public results; do not reinterpret the failed marker trial.
This is a potential negative evidence contract, not full operation verification.

## Existing two-domain observations

1. `docs/evidence/cache-eviction-current/protocol.json`, `before.json`, README:
   CacheMonitor.render's entire method is a single literal return. Both executable
   eviction and timestamp scan/delete requests choose it instead of real source.
   ArrivalPool.trim and CacheMonitor.render explicit controls remain correct.
2. `docs/evidence/output-loop-followup/protocol.json`, `independent-dedupe.json`,
   `dedupe-result.md`: OutputDescription.label's entire body is a literal return.
   After accepted raw budget repair, raw contains PipeCollector.collect as well as
   PipeCollector.label, SingleRead.read and the description. Compact still chooses
   OutputDescription.label. Exact collect/read controls retain their frozen strict
   failures or passes; no expectation is changed here.

These are independent cache eviction versus stream iteration/accumulation operation
families with the same narrow observed mismatch: a literal-only body supplies none
of the requested execution operation but is selected through textual relevance.
This is stronger motivation for a shared **literal-body classification** than two
cache variants. It is not proof that one existing query-intent certificate covers
both, nor that filtering those methods will make either unchanged oracle pass.
In output, removing two label methods could still choose SingleRead rather than
collect. In cache, genuine FIFO and split/deferred/unknown competitors remain.

## Exact negative assertion proposed

For one identity-bound callable, a complete supported body consisting solely of
`return <non-interpolated string literal>` (optional syntax-defined terminator and
validated comments/whitespace) proves only that this body itself does not perform
iteration, collection deletion or accumulation. It does execute a return and may
be the desired label/text implementation. It is NOT globally irrelevant, non-code,
non-executable, or proof that callers cannot use its string to drive operations.

Admission must bind full callable bounds, signature and source digest/adapter to
the same source snapshot. A truncated mechanism window, file summary, empty
method_evidence, string_evidence presence, name label/render, or regex occurrence
of return is insufficient. Complete body classification must reject malformed or
unsupported grammar rather than trusting a missing parse result.

Unknown includes executable template interpolation, concatenation/coercion,
computed/parenthesized expressions outside an explicitly supported grammar,
multiple statements or branches, calls, mutations, getters/default parameters
with effects, decorators/unsupported callable kind, unclosed strings/comments,
shadowed/ambiguous identity, stale bytes, partial bounds and old index records.
Default parameter initializers deserve special care: even a literal-only body
can have parameter-evaluation effects, so either classify only the body and grant
no whole-callable permission, or refuse such signatures for the proposed consumer.
Whole-file lexical fallback is not a negative proof. Unknown must remain retained.

## Consumer permission, separate from classification

Only an independently certified request for an operation incompatible with a
literal-only body could decline to use that body as the PRIMARY implementation.
It need not remove the method's text, source anchor, logs or relation context.
Explicit method requests, literal/text/declaration requests, actual emitted-log
queries, mixed source+label requests and unresolved/ambiguous task intent must keep
the old behavior. A quoted method mention is not automatically an operational
request. No new vocabulary or scoring multiplier is proposed to guess permission.

Negative evidence for A does not prove B meets the request or is unique. If all
alternatives are unknown, do not fabricate a bounded winner, claim no implementation
exists, or silently delete every candidate. A consumer needs an explicit safe
fallback contract. With multiple actual requested roles, a text-return method may
be a required role even if another role is operational. This contract must not
inherit exclusive authority from source_operation_match or a changed score gap.

## Existing representation and integration risks

Current source_operation v2.1 has no literal-only certificate; checked/unresolved
roles for read/capability do not imply this fact. method/string evidence are lossy
retrieval terms. Full identity/range/digest fields can bind a classifier's input,
but no persisted tri-state literal classification exists. Dynamic inspection at
query time would add bounded source access/freshness work; persisted evidence would
need versioning and ordinary relearn semantics. Neither is authorized by this note.

The existing NON_SOURCE_TARGET veto and target-scope flags are useful protection
inputs, not a demonstrated positive "execute this operation" classifier. The loop
query says iteration/accumulation ownership, while cache uses executable scan or
scan/delete; equating them by new keywords would recreate earlier speculative
intent rules. Exact-symbol and typed-match branches also precede ordinary score
certainty, so bypassing them can break genuine named/literal requests.

Even excluding primary eligibility changes ranking/selection policy. It can reveal
a different wrong winner, alter boundedness, lose required same-file alternative
ranges, or activate compact narrowing. Proposed acceptance must compare raw and
compact identities, actual required bodies and budgets, not just disappearance of
the label. Keep all existing caps and protected graph/log/multiple-source evidence.

## Gate assessment and validation plan, not executed

The two independent families support review of a common narrowly defined body
classification gap. They do NOT yet establish a single sound request-conditioned
consumer contract or justify a generic dataflow architecture. A tiny classifier
and a request permission are separate design questions. A broad parser, universal
negative-candidate framework or new proof schema still requires scope review and
cross-class validation of that specific abstraction, not just this shared symptom.

Reuse existing source/query/oracle bytes unchanged for any approved experiment:
- cache generic two reds plus explicit FIFO and literal controls;
- output generic post-dedupe red plus exact collect/read controls, keeping the
  existing stricter symbol assertions unchanged;
- pre-register classification controls for strings/comments/escaped quote/template
  without interpolation, interpolation/call/return expression, partial/stale range,
  default parameter effects, multiple methods, and duplicate/unknown identity;
- pre-register consumer controls for explicit literal/method, real logs, mixed
  label+operation, multiple real operations, unknown competitor and all-unknown.

New controls above are required but NOT created or declared passing. Baseline and
candidate must actually enter intended classification and permission branches.
First demonstrate classifier correctness without granting serving authority. Then,
only if request admission and fallback are reviewed, run fixed public cases once.
Any new regression, unchanged old red, or merely changed wrong winner rejects the
serving candidate; do not broaden query terms, source grammar or oracles afterward.
No guarantee of original cache/output score improvement follows from the idea.

## Decision

Feasible as a sharply bounded source fact to investigate, with less semantic scope
than timestamp/dataflow proof. NOT yet implementation-ready as a selector: positive
request permission and unknown fallback are unproved. The original tasks are static
implementation-location tasks; access-LRU or final-size correctness must not be
invented as additional gates. Preserve that correction while reviewing this narrower
alternative, rather than reviving the rejected cache marker or v3 loop priority.
