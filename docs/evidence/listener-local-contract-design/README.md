# Named listener callback forwarding: finite local relation design

Read-only design on 63970fc. No runtime edits, query execution, new query, oracle
change, score/word-list adjustment, or claim of original improvement. Read AGENTS,
agent.md, implementation plan and evaluation/change policy. Evidence below is
historical Development evidence, not a fresh test result on this revision.

## What the saved evidence establishes

Source: `docs/eval/native-listener-current-20261114/README.md`, `protocol.json`
and `contract-observations.json` in the same directory. That run was based on e760097:
original native-listener 2/3, contract variant failing. The five fixed independent
queries have one generic binding red and four controls passing. These are the
inputs for a future falsification, not permission to tune a replacement query.

Original actual source is
`docs/eval/fixtures/system-capability/.benchmark-fixtures/evidence-funnel/src/adapters/NativeResultBoundary.ets`:
attach(runtime: NativeRuntime, listener: ResultListener), lines 7–16, passes an
object to runtime.setObserver; onFailure's arrow invokes listener.onFailure.
Independent protocol: Relay.connect(engine: Engine, target: DeliverySink), lines
6–11, passes an object to engine.observe; rejected's arrow invokes target.rejected.
Recovery contains a real queue.schedule call and remains valid for retry and text
requests. It is not an absent-operation or invalid-source candidate.

Both examples provide a syntactic *call-argument callback captures a typed formal
parameter and invokes its member* relation. Neither source proves that observe or
setObserver really registers, executes, or successfully delivers anything. The
local relation must be named accordingly, not “runtime observer registration.”

## Existing implementation and exact missing information

- `query_typed_contract.py:classify_contract`: explicitly accepts parameter,
  return, declaration, literal relations, and parameter invocation wording. It
  rightly does NOT turn “binds ... contract” into “accepts Type”.
- `_signature` handles simple parameter declarations; `match_candidate` invocation
  presently tests two method-evidence tokens, not receiver identity or scope.
  `query_hierarchical_localization.py:rank_callables` marks that operation match
  weak. `query_callable_evidence.py:certainty` makes weak matches uncertain. Keep
  this legacy contract unchanged; do not upgrade those old matches.
- `semantic_ecma_mechanisms.py:CALLBACK_RE` recognizes name-shaped on/add/register
  calls. Existing callback_binding records identify e.g. onFailure, attached to
  enclosing and nested callable. engine.observe itself does not match that regex.
  Co-occurrence of callback_binding + operation target.rejected is insufficient:
  nothing asserts call-argument containment or which formal target is referenced.
- `semantic_models.py:SemanticMechanism` has source_key, kind, terms, line,
  confidence/evidence_class and detail. Validation binds source_key to a callable
  and line inside it, but not the proposed inner intervals or receiver binding.
- `semantic_index.py` groups mechanisms by entity key and persists
  mechanism_evidence JSON. `semantic_mechanism_evidence.py` has a 4096-byte cap;
  extraction also has a 16-record callable cap. Absence after truncation, old
  indexing or unsupported syntax cannot prove the relation absent.
- `context_callback_binding.py` is source-window enrichment for property callbacks
  and scalar siblings. It deliberately does not establish registration semantics
  or typed receiver identity; do not repurpose its name as a certificate.

## Smallest falsifiable producer subset (proposal, not implemented)

Positive record only, attached to the OUTER already parsed callable key/range:

`(version, formal-name, bare-declared-type, argument-call-chain,
  callback-property, invoked-member, call-range, callback-range, invocation-line)`.

1. Known `.ts/.ets` source mask using existing conservative callback_mask_lines;
   whole input unknown means no new record, not “no forwarding”. Keep source
   bytes/digest, parsed signature, exact outer key and range unchanged.
2. One unambiguous bare named type parameter in an ordinary non-default signature.
   Reject type unions/generics/aliases, duplicate names, local or enclosing type
   shadowing, explicit `this` receiver, unknown enclosing scopes. Static declared
   type only; no runtime instance identity or framework/API resolution.
3. Balance original equal-offset `()[]{}` on known code. Prove an object literal
   is an actual argument of a member call inside that outer body. Only explicit
   ordinary property arrows with directly delimited bodies in that object. No
   spread, computed/get/set/shorthand/property-variable indirection, nested object
   or deferred helper callback. Do not trust line-only range containment alone.
4. In the property's direct arrow body prove a complete member-call token whose
   ROOT receiver is exactly the outer typed formal (not obj.target, obj.this,
   optional access, a new binding, a quoted string, or a separate sibling method).
   For the first subset allow only direct invocation statements and simple
   callback-parameter arguments. No nested callable/control-flow inference.
5. Reject any declaration/shadow/reassignment/destructuring of that receiver in
   the enclosing method, callback or an uncertain scope; reject aliases/escapes
   that prevent the simple binding check. Unknown does not erase legacy evidence.
   This conservative check must itself be demonstrated, not claimed from regex
   co-occurrence. Class/function/arrow generic outer scopes need rejection unless
   the module/owner scope is already proven, as in prior typed-field safeguards.
6. Retain both callback property and invoked member exactly. The requested member
   must constrain the relation: a success-only callback cannot satisfy a failure
   request merely because its receiver has ResultListener type. Multiple matching
   callbacks/outer forwarders stay distinct, never collapse into one owner proof.

This is a local syntactic relation extension, not a new graph/value-flow system.
No two-defect architecture permission is claimed. If implementing 2–5 requires
resolving arbitrary binding/scope or API behavior, stop this subset rather than
incrementally building an unreviewed JS parser.

## Can existing storage carry it?

Yes, conditionally, without a SQLite/schema migration: keep kind=callback_binding
and introduce an explicitly versioned, fully parsed detail representation of the
above tuple. source_key already supplies outer identity; line supplies invocation
location. Validate all inner intervals and tuple references at production. Detail
must fit the existing 240-character model limit (the generic mechanism() helper
currently truncates at 120: do NOT route proof through silent truncation). Emit
nothing if the complete record does not fit. Preserve terms as ordinary search
hints; consumers must not reconstruct the tuple from terms or callback: text.

The existing fields are adequate as a bounded transport envelope, **not already
an adequate authority contract**. A new typed detail version and strict decoder
are still necessary. Do not add a general source_operation_checked role, reuse
v2.1 unique-operation certification, or give old callback_binding records new
meaning. Record-cap loss and legacy indices remain unknown. Retention under the
16/4096 caps must be tested before promising public availability; do not raise
caps or reserve rank slots silently to make the fixture pass.

An alternative consumer-side source reread would avoid metadata evolution but
would duplicate proof scanning and need exact raw record identity/digest gating;
it is not the smaller first producer phase. No consumer should treat this detail
as a private source-read certificate.

## Consumer proposal and unresolved authorization boundary

A new explicit relation descriptor, separate from parameter/accepts, would require
an unambiguous single named type AND requested callback/member AND a callback-to-
that-type binding request in the retrieval target. Existing literal/declaration,
explicit callable, multiple-target, negated and log requests must retain their
current semantics. Do not classify by only “bind”, “callback” or a CamelCase type.
The original and independent fixed queries are its positive candidates, not a
license to expand arbitrary wording until they pass.

Exact rejected matches the independent property/member. For original “failure”
versus onFailure, only existing `text.identifier_tokens` may be evaluated as a
possible identifier-segment selector, with no hardcoded on-prefix stripping or
failure synonym list. Require selector evidence on BOTH callback-property and
invoked-member, reject competing segment matches. This can support a source-name
association, not claim that all failures or listener methods are semantically
covered. Success-only, wrong invoked member, similarly named types and ambiguous
members are necessary negative controls. If that narrow selector cannot safely
express the fixed original request, leave it unsupported; do not weaken it.

A positive local tuple can support displaying the matching enclosing method.
It cannot by itself authorize exclusive pruning of all other candidates or claim
that the user's native failure was delivered. Reusing typed_contract_match changes
sort precedence even with typed_contract_weak=True; it is a serving change, not
harmless metadata. If a later isolated consumer experiment reuses that route it
must set weak=True, retain the existing uncertain/multiple safeguards, and prove
that the new request descriptor does not override explicit retry/text/declaration
or multiple-owner requests. A strong unique/bounded extension is NOT proposed:
unknown competitors, missing roles, and static closure capture are not negatives.
First test producer learn/list facts; separately test exact fixed public red and
four controls. Failure to improve the existing red is a truthful stop, not grounds
to add score/weight changes or relax weak certainty.

## Required finite test matrix before any serving change

| Input/control | Required outcome |
|---|---|
| Existing attach/onFailure and connect/rejected source | Correct outer identity + typed receiver + callback/member tuple; no runtime-delivery claim |
| Same named type unused; interface declaration only | No new tuple; parameter/declaration controls retain meaning |
| Callback invokes different receiver or wrong member | No matching typed member tuple |
| Same name in another owner/file, split callback and invocation | No cross-owner relation |
| Callback parameter shadows target; outer rebind/destructure/alias | Unknown new relation; old evidence retained |
| Nested/deferred callback or unknown mask/template/slash | Unknown; no negative certificate and no loss of legacy source |
| Real Recovery retry and literal request (existing controls) | Existing source and body retained; do not suppress retry |
| Two real forwarders / two callbacks matching selector | Both positive tuples; consumer cannot certify unique owner |
| Old index, altered bytes/digest, malformed/cap-truncated detail | No trusted new match; normal merge only activates current facts |
| Ordinary accepts/invokes/literal/declaration typed queries | Existing classification and weak behavior unchanged |

This matrix is a design obligation, not new frozen executable sources or queries.
No matrix row has been run in this design review. A next approved step would
freeze the supported source grammar and counterexamples before implementation,
then run formal learn/list plus the already saved five public queries unchanged.
Schema roundtrip/caps, stable key/range/digest, installation-without-learn versus
ordinary merge, and actual compact bodies/budgets are mandatory checkpoints.
