# Named listener binding: independent bounded design review

Base 63970fc. Read-only review of retained Development evidence; no new query,
production edit, test execution, original oracle change or publication. The saved
native-listener report was executed on e760097, not freshly on this base.

## Evidence and existing contract

`docs/eval/native-listener-current-20261114/{protocol.json,independent.json,README.md}`
freezes Relay.connect(engine: Engine, target: DeliverySink), an object passed to
engine.observe, and accepted/rejected arrows invoking target's corresponding
members. The generic binding query selects Recovery instead; exact Relay,
accepts DeliverySink, exact Recovery and literal controls pass. The original
ResultListener failure variant also recalls its attach method; mechanism evidence
is consumed, not missing. Historical original remains 2/3, not a new measurement.

`query_typed_contract.py` deliberately recognizes named parameter/return/declaration/
literal relations. Its parameter invocation test uses token co-occurrence, not a
callback containment or receiver-flow proof. `semantic_ecma_mechanisms.py` produces
callback_binding from name-shaped calls. Neither promises the proposed stronger
relation. `context_callback_binding.py` is an excerpt context helper for bounded
property callbacks and scalar siblings, not an observer-registration resolver.
Reusing these labels as a stronger certificate would silently change their meaning.

## Smallest reviewable positive fact

A limited producer experiment may reuse the existing metadata transport, but must
represent a *call-argument callback forwarding to a typed parameter*, not assert
that observe is a known registration API. Required source witness:

1. A unique, current, supported enclosing callable and complete source interval,
   bound to its existing identity and digest. One unambiguous simple named typed
   parameter supplies receiver identity. No name-only cross-file type resolution.
2. An actual source call expression has an inline object as an argument. Its direct
   property value is the exact supported arrow callback. Record argument/object/
   callback containment, not merely lexical observe plus a nearby target call.
3. Inside that callback, a direct call uses the same enclosing parameter binding
   and explicit member. A different callback's invocation does not certify the
   requested property. No claim of payload equivalence or runtime invocation.
4. Shadow/reassignment/aliasing, computed or optional members, callback defaults,
   destructuring, extra nested callable scope, spread/getters, unresolved syntax,
   missing bounds/digest and unsupported language remain unknown. A deliberately
   narrow whole-body shape may reject these; do not build an incremental scope
   parser by accumulating counterexample regexes.

This is not API registration semantics, execution, causality, success/failure
behavior, unique owner, or proof that other candidates lack a binding. Existing
entities and ranges must not be relabeled or extended. Missing old-index facts
remain unknown until ordinary relearn. A parameter's annotation is a source type
spelling unless independently resolved; do not call it verified runtime interface.

## Minimum frozen controls before any implementation

Keep all five existing queries/sources/oracles unchanged. Add source-only controls
with acceptance outcomes frozen before execution:

- Same typed call in an object never passed to a call: no call-argument fact.
- Same target member invoked outside the callback, or in accepted rather than
  rejected: no rejected-forwarding fact.
- Two same-type parameters with different receiver names; parameter shadowed by
  arrow/catch/local declaration; reassigned before the callback: unknown rather
  than guessed receiver. A declaration-only/unused parameter is not forwarding.
- Literal/comment/template copies and unknown interpolation/slash preserve lexical
  admission boundaries; genuine nearby supported callback keeps its exact range.
- Two genuine forwarder methods, including same-named methods in separate owners:
  retain both identities; no automatic unique/bounded preference.
- Actual explicit receiver/member, literal, logging and mixed/multiple requests
  retain their old targets; no request token alone activates stronger authority.
- Install-only old index versus ordinary merge; unchanged identity/digest/ranges,
  normal serialization, and bounded compact output without new source access.

First test only source-to-fact output through public learn/list. The current public
red proves motivation, not this new fact's recognition contract. If supported
containment cannot be expressed safely without a general relation/scope framework,
stop this local experiment and document the architecture requirement. Multiple
variants of this listener problem are not two independent architecture defects.

Consumer admission remains separately unapproved. A generic “binds callbacks to
NamedType member contract” request must not be reduced to “accepts NamedType”.
No typed_contract_match/source_operation_match, rank boost, uniqueness or removal
of Recovery is authorized by this review. A reviewed consumer would need fresh
fixed public red/controls with the actual source witness and multiple-forwarder
protection; producer success alone is not an original failure improvement.
