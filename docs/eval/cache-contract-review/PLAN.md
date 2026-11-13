# Cache source-bound permission review

Read-only design, base edbda31. No runtime edits, query executions, parameter changes
or new acceptance claim. Inputs are the already frozen
`docs/evidence/cache-eviction-current/{protocol.json,README.md,frozen-tests.py.txt,rejected-hint.patch}`.
Historical baseline is a6c1d93, not a current measurement. Existing original group
remains historically 2/3; the rejected hint candidate never closed the independent
public failures. This review does not reopen that candidate.

## 1. Concrete defect and why the hint was insufficient

The two frozen generic tasks select CacheMonitor.render, whose method returns a
literal sentence. ExpiryStore.trim implements a capacity guard, scans records,
tracks a minimum timestamp/key, and deletes that key. The explicit ArrivalPool.trim
and CacheMonitor.render controls pass. ArrivalPool really performs first-key FIFO
removal and must not be categorized as "no eviction" merely because it lacks time.

The rejected patch appended cacheeviction when size/for-of/delete/age patterns
co-occurred in a conservatively bounded method. Its own comment correctly called
this a retrieval conjunction, not policy proof. It did not link the size receiver,
iterated collection, selected key, compared value or deleted receiver. It also
provided no permission to overrule textual/exact targets or to preserve the right
operation in compact. Unit hint green with public red was correctly rejected.

## 2. Smallest proposed evidence object: bounded scan/removal witness

This is a review contract, NOT permission to add a source_operation role or a new
schema. A witness would describe only directly observed syntax/data dependencies
within one indexed method, bound to project, adapter/version, typed symbol ID,
owner identity, path, full range and digest of the same bytes used for extraction.
The payload must include supporting source intervals and identifier binding slots,
not just a boolean or bag of words. Names below describe variables, not required
identifier vocabulary.

For the frozen timestamp method, all obligations must hold:

1. One resolved field receiver R is used for capacity size, loop iteration and
   delete. Its field/type declaration is source-bound to the same owner. Textual
   receiver spelling without declaration/binding consistency is insufficient.
2. The limit comparison is a dominating admission guard for this operation, either
   explicit over-capacity block or complementary early-return shape. Arbitrary
   size mention elsewhere does not discharge this condition.
3. Direct for-of iterates R into key K and element V in this callable's own scope.
   Within the loop a numeric/order expression over V is compared with accumulator
   M; on that branch M becomes that same expression and chosen C becomes K.
4. The after-loop delete receiver is R, and its argument is C. C starts in the
   declared unset state and is guarded as set before deletion. No intervening
   reassignment, aliasing escape or opaque call may invalidate R/C/M/value binding.
5. Every contributing operation belongs to this one callable, not another method,
   callback, getter, object method or template interpolation. Lexical masking alone
   cannot prove the binding/control obligations above.

This proves a restricted **source scan/select/remove shape**, not executable API
semantics, a globally unique owner, timestamp validity, least-recent-use behavior,
concurrency safety, termination, or successful eviction. A Map type annotation
alone does not prove the runtime object is an unmodified built-in Map. Exact limits
on type/import binding and possible overrides must be recorded; an unproven API
binding cannot be described as verified runtime deletion.

### Challenge clarification: minimum timestamp is not access recency

The frozen ExpiryStore never shows how updatedAt is initialized or updated on a
successful access. A minimum stored field is therefore not a demonstrated least-
recently-used item. There is no cross-method access→timestamp-update→selection
binding, and a method merely named get/update would not supply it. Different clocks,
stale fields, creation timestamps and non-refreshing reads remain unresolved.

Likewise, one selected-key delete does not prove the collection ends at or below
limit: it may begin more than one item over capacity. Successful deletion and
runtime Map behavior are also not certified. ArrivalPool contains genuine first-key
removal syntax, but a complete FIFO policy additionally depends on insertion and
refresh ordering; it must never be called absent just because timestamp proof is
missing. References to FIFO elsewhere in this plan denote that frozen first-key
removal control, not a verified global eviction policy.

Consequently this proposal is ONLY a static deletion-chain witness. It cannot
claim to satisfy the original cache task's access-recency or final-capacity
requirements, even if the independent scan queries later pass. A reversed maximum
comparison, unrelated delete parameter, reassigned chosen key, or size/iteration/
delete on different receivers must fail the minimum-selection witness. Proving
actual recency would require separately sourced access/update linkage and its
unknown controls; no such expansion or new fixture is authorized in this stage.

The witness can support inclusion of the actual method/source as operation evidence.
It cannot by itself authorize deleting other owners, choosing a unique primary,
changing the 1500-token budget, or turning a diagnostic task into a single-method
request. Thus **evidence production and consumer authority are separate gates**.

## 3. Three states and required refusals

- `supported-shape`: all obligations proved within the declared small grammar and
  byte-bound range. Never equate it with global program behavior.
- `known-literal-only`: the entire relevant method is validated as a direct literal
  return with no executable interpolation/call/side-effect. This only describes
  this method; it is still the correct target for explicit text/literal requests.
- `unknown`: every remaining case, including another genuine algorithm. Absence of
  the timestamp shape is not absence of eviction or task relevance.

Unknown cases include aliases/destructured/rebound receivers, computed/optional
access, dynamic keys beyond the bound key variable, shadowed identifiers, imported
or overridden collection APIs not proven by available binding facts, helper-based
selection/deletion across methods, nested/deferred writes, async/await/intervening
opaque calls, unsupported control flow and malformed/missing/stale ranges/digests.
Different source IDs at overlapping ranges remain different identities. Missing
old-index fields and unrecognized adapters remain unknown until ordinary relearn
produces a compatible witness; installing code cannot fabricate prior evidence.

Frozen SplitExpiry and DeferredExpiry are unknown for a direct-method witness.
ImagePool.remove is a known direct removal but unknown as a capacity/time eviction
policy. ArrivalPool is a real alternate FIFO shape, not a literal competitor and
not negative evidence. Even if the first implementation supports no FIFO witness,
its unknown status blocks exclusive timestamp priority.

## 4. Consumer contract is not yet available

The existing v2.1 consumer supports runtimecapability/persistenceread only, rejects
multiple targets and unknown candidates, and treats exact/typed identities as vetoes.
Adding cacheeviction to supported would not establish these new obligations.
Existing callable_roles/method_evidence can carry hints, and symbol rows provide
range/digest/owner provenance, but do not represent receiver def-use links or
control dominance. Existing call/state edges are not such a certificate either.

A non-exclusive retention proposal might keep a proved requested operation alongside
literal context rather than replacing it with a description. However it still needs
request-to-operation binding and a budget policy. The frozen first query asks about
an executable scan; the second names timestamp scan/delete. They are not interchangeable
with an explicit method/literal/FIFO request. No new keyword triggers or broad
source-versus-string ranking rule is proposed. If the needed requested shape cannot
be derived from reviewed existing query representation, stop before serving edits.

The initial grant, if approved later, must be limited to **retaining source evidence
for a matched requested operation**, never uniqueness or causality. A retention-only
implementation may still leave CacheMonitor primary and fail the unchanged public
oracle. That outcome is a failed candidate, not justification to soften expectations.
An additional primary-selection permission requires a separately justified contract.

## 5. Architecture gate: not met by these two cache queries

Two queries over one cache fixture, timestamp and FIFO variants, or independent
copies of the same cache defect do not constitute two independent defect classes.
Cache currently proves one operation-versus-description competition class. Listener
registration/forwarding is another domain, but receiver/event binding is different;
no evidence yet demonstrates that the proposed scan/selection/dominance abstraction
solves both. Archive and loop v3 candidates are isolated and cannot supply accepted
cross-class authority. Do not borrow their failures as automatic architecture approval.

A general def-use/dominance subsystem or persistent proof schema therefore lacks the
required cross-class evidence. A bounded standalone development checker could test
feasibility without runtime/schema integration, if separately authorized. It must
not grow regex exceptions until it accepts the original fixture. If safe support
requires a real parser/CFG beyond existing facilities, document that dependency and
stop rather than build an ad hoc parser under a "small marker" label.

## 6. Executable validation plan (not executed or implementation-approved)

### Gate A: freeze and review, before code

Reuse the exact six sources and four queries from the existing protocol, preserving
all bytes and oracles. Hash the protocol and source bodies. Keep historical candidate
results intact. Review a proposed bounded grammar and binding rules separately.
Pre-register mutation controls as proof tests, not tuned retrieval queries:

- same receiver across guard/iteration/delete versus different receiver at each site;
- selected K versus unrelated delete argument; same V expression versus unrelated M;
- guard dominates versus size test after delete or in disjoint branch;
- direct scope versus frozen split/deferred and quoted/computed object methods;
- reassignment/shadow/alias/optional/dynamic access and intervening call => unknown;
- full literal return versus executable interpolation and literal requests;
- true FIFO, second true timestamp owner, unknown competitor and legacy/missing fields;
- duplicate typed ID versus distinct ID at same bounds, stale digest and JSON roundtrip.

These controls are newly proposed, not already run or green. Actual fixture additions
must be frozen once before candidate evaluation; do not adjust them after outcomes.

### Gate B: standalone proof feasibility, no serving edits

Evaluate the frozen sources and controls with an isolated checker only. Inspect each
binding slot and source interval; verify confidence states do not overclaim API binding.
Failure to justify the original timestamp shape conservatively means unknown and stop.
A fail-closed unknown result is safety success but not usefulness/acceptance success.

### Gate C: only after representation/consumer approval

Use the existing formal init / learn-path / context runner from
`docs/evidence/cache-eviction-current/probe.py.txt` (adapt output directory only) on a
fresh Development memory. Run the same four fixed tasks once raw and compact for
baseline/candidate, with no query/source/noise changes. Both generic old reds must
meet the unchanged test assertions and actual required method-body checks; explicit
FIFO and literal controls must remain correct. Record stage traces to prove any gain
occurs at the approved permission boundary, not accidentally changed recall/ranking.

If any generic red remains or any control regresses: reject and restore production,
retain patch/results, do not rerun with new words or widen supported grammar. No original
benchmark or aggregate run is needed to decide this gate. Only an accepted independent
candidate could justify later single-group post-hoc verification under parent approval.

### Gate D: necessary related contracts, not full suite

Before integration, run source-operation unknown/index-refresh/serialization,
source identity/digest, typed/exact owner precedence, graph/multiple/log protection,
and source-budget rollback regressions. Record old-index install-only versus ordinary
merge behavior. Keep hard caps and full competing evidence; unsupported/multiple
operations cannot be collapsed to a single winner to make the tests green.

## Review decision requested

Approve or reject **standalone bounded witness feasibility** first, with no runtime
consumer privilege. Serving implementation is not yet justified because existing
fields do not express the full witness and request-conditioned retention/selection
permission is missing. This is a concrete testable design boundary, not a claim that
cache is permanently blocked or a proposal to repeat the rejected marker experiment.
