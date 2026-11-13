# Cache witness and shared-record cross-class challenge

Read-only review, base `14d714f`. No runtime changes, new queries, fixtures,
or test executions. The cache design reviewed is commit `9f0c525`,
`docs/eval/cache-contract-review/PLAN.md`. This review does not approve a new
runtime abstraction, schema, consumer privilege or architecture.

## Cache: observations versus policy claims

Inputs: `docs/evidence/cache-eviction-current/{protocol.json,README.md,
rejected-hint.patch,frozen-tests.py.txt,before.json,after.json}`. These are
historical Development observations, not measurements on the current baseline.

ExpiryStore.trim visibly checks records.size, iterates that same records field,
compares record.updatedAt against earliest, updates earliest and chosen together,
and deletes chosen from records after the loop. This supports investigating a
bounded scan/select/remove source shape. It does not establish least-recent-use:
there is no access/update path showing when updatedAt changes. Minimum updatedAt
could represent oldest write, creation, or arbitrary external data rather than
oldest access. A timestamp name is not recency semantics. Removing one entry also
does not prove final size <= limit when the starting size exceeds limit by more
than one. Runtime Map behavior, mutation/concurrency and successful removal are
separate from recognizing syntax.

ArrivalPool performs a real guarded first-key removal. It cannot be classified
absent merely because timestamp scanning is unsupported. Full FIFO/LRU policy
claims additionally require insertion, reinsertion and access-order behavior.
CacheMonitor's literal-return implementation is a real explicit textual target.
ImagePool.remove is a real delete, not by itself a capacity eviction policy.
SplitExpiry and DeferredExpiry contain real operations but do not establish one
immediate method-local scan/select/delete chain.

The rejected hint adds a conjunction of size, for-of, delete and age tokens inside
one controlled body. It binds neither receivers nor selected keys nor execution
conditions. Its producer test passed while both public red queries remained red;
that is not a reusable policy certificate. In particular, a generic eviction
witness cannot be reported as satisfying a request for access recency or LRU.

Required design counterexamples, NOT newly created or executed tests: size on A,
iteration over B and deletion from C; unrelated deletion argument; maximum rather
than minimum selection; chosen-key reassignment; non-dominating size condition;
opaque/deferred calls; unconnected helper methods; reads that do not update time;
insertion/reinsertion changing first-key order; genuine FIFO, wrapper callers,
indirect operations and explicit literal targets. Unknown competitors cannot be
made absent by finding one positive timestamp witness.

## Shared-record is not the missing second class

Inputs: `docs/evidence/shared-record-current/{README.md,independent-protocol.json,
independent-results.json,original-intent.json,public.json}` and saved trace JSON.
The independent protocol expressly says its broad iteration query is exploratory,
not an assumed failing acceptance case. The named ChunkAssembler, AfterIteration
and DeferredAssembly public controls preserve all three identities/ranges. Thus
these controls cannot be retroactively reclassified as a frozen public red for a
missing dataflow certificate.

Their concrete source forms are also different:

- ChunkAssembler: loop element chunk contributes to scalar merged through
  `merged = merged + chunk`; the method returns merged.
- AfterIteration: loop logs chunk; a constant assignment occurs after the loop.
- DeferredAssembly: callback writes merged later; the method returns before that
  deferred execution is established.
- Cache: an ordering predicate over a loop value updates a minimum and its paired
  key; the selected key later feeds a mutating consumer on the iterated receiver,
  under capacity admission and a selected-key guard.

Both families mention local values, but the shared-record positive is a reduction
and return, not selected-key identity consumed by the same collection receiver.
It provides no capacity dominance, paired argmin/key update, or same-receiver
mutation evidence. A shared syntax utility might eventually serve both, but that
is not proof that one narrow witness contract solves both public failures.

The original shared-record first loss is not a missing existing loop certificate:
all variants initially focus the correct file; salience adds competitors. The
original compact retains the full target method. English retains a truncated
2–10 prefix of the correct 2–12 method under an explicitly reported budget
truncation. The requests are classified multiple. Existing collectionfold is a
coarse file hint, not a promised source-bound direct-value-flow role. No observation
shows a valid value/receiver witness being produced and then dropped by a consumer.

## Decision and missing gates

Do not count shared-record as a second independently demonstrated defect class for
the proposed cache witness. Do not implement a general def-use/control-flow schema
on this premise. Positive witness feasibility, request-to-role mapping, retention
permission and unique-primary permission remain distinct decisions.

For cache, a proposed witness still needs exact receiver/field binding, ordered
key/value definitions, same expression/selected-key use, guard/control scope and
intervening-write/escape handling, bound to actual indexed bytes and identity.
A recency claim additionally needs cross-method access-time update and call-order
facts, which the frozen fixture does not contain. For shared-record, direct loop
writes and returned accumulator binding could be studied separately, but no frozen
same-layer public acceptance red or source-bound request-role mapping currently
justifies claiming that study repairs the observed failure.

This is a limit on the present architecture argument, not a finding that either
category is permanently unfixable. No original oracle, protected FIFO/text control,
budget or failure count has been changed.
