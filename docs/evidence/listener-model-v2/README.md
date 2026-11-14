# Listener model v2: isolated actual-CLI compatibility result

Base2ec802f. Frozen before execution:faeb0dc,b2e7d6c,2893a65,55113b8,
079a9df,4f170fa,5bb5703,4ee9dd9. One v2 CLI run, then frozen model/comparison checks.
Previous failed v1 artifacts remain unchanged in their own evidence directory.
No production tools/tests/schema changed; no selector, scoring, query or oracle
edit. Temporary runtime was copied, instrumented, and used via the real CLI for
normal SQLite init/learn/list/context. No fake output or SQL row injection.

## Results and what passed

- All original20 source-fact controls pass through actual indexing. Native now
  retains both onReady/onFailure facts, unlike prior v1. Their complete source
  identities and exact offsets do not join or casefold descriptive operation text.
- Added case collision control retains two distinct same-line invocations:
  onFailure and onfailure. Same outer typed parameter, different exact member
  spelling and source offsets, independently persisted.
- Added over32768-byte source produces no optional facts while retaining baseline
  source identities and old mechanisms. Optional unknown does not abort old index.
- The23rd control is capacity-conditioned, NOT a Boolean full-fact expectation.
  Its16 old mechanisms occupy3378 bytes, unchanged in order/serialized payload/
  search terms.16 source facts are produced; none fit the718 remaining bytes.
  Side column contains[] (2bytes), total3380. All facts are unknown at persistence,
  no old mechanism displaced. The dedicated capacity assertion passes.
-32 named model checks pass: explicit v2 roundtrip, clean legacy unknown,9 legacy
  null/empty batch/entity/mechanism pollution rejections, old-reader version
  rejection, signature/coordinate/unit/identity/version/size/receiver controls,
  decoder-vs-source distinction, artificial arithmetic cap cases and actual CLI
  capacity preservation. These are the enumerated checks, not all possible inputs.
- Old index has no witnesses before or after installing code without learning.
  Normal merge adds Relay's two facts. Eleven stable identity fields unchanged.
- Five unchanged public queries remain generic red plus four controls green.
  Actual anchor bodies/ranges and primary identity remain the same. Numeric
  record_ids change during merge; explicit Relay.connect budget892→893, others
  unchanged, all≤1500. No original-group rerun or original failure improvement.

`run.txt` reports22 pass out of23 because the capacity-conditioned case stores
`pass:null` pending its separate exact-packing assertion. `comparison.txt` has a
misleading inherited terminal print calling all falsey entries “failures”, so it
prints actual-near-cap. That is a reporting-label defect, not a failed capacity
assertion or altered oracle: model-results and actual-capacity-observation retain
its passed independent validation and measured omission. Output is preserved as
executed rather than silently rewritten.

## Actual model / database scope

This is a real experimental schema change: batch typed_invocation_witnesses and an
optional SQLite code_symbols side column. It is not “zero schema”. The fact
transports independently of old SemanticMechanism identity; existing mechanisms
are neither enriched nor replaced, so their text is never used as source authority.
The version is semantic-index/listener-experiment-v2. Old batch readers reject it.
Legacy v1 presence of any recognized typed field rejects even null/empty values;
clean legacy v1 imports an empty optional collection, not guessed proofs.

Persistence generates the exact original mechanism JSON first. The side column
is limited to4096 minus its UTF8 bytes, including both JSON arrays' punctuation.
No added cap, no reordering/compression to rescue Native. SQL NULL contributes
zero side JSON bytes when[] cannot fit. Whole optional records only. Truncation
means unknown, never absence. This fixes the prior experiment's risk of inflating
a legacy record and pushing the old suffix out of its budget.

## Decoder is not source authentication

At source time, the prior bounded extractor and its source-slice assertions check
actual code and bind exact key/path/range/signature/original-byte digest. It still
reuses existing parsing helpers; it is not an independent parser correctness proof.

At decode, the model checks exact fields/version, declared formal index/name/type
against the supplied entity signature, legal named receiver, coordinate unit,
non-bool integers, nesting within the claimed snapshot/outer bounds, and equality
with the supplied batch source digest and entity identity. This verifies consistency
of supplied data. It does not reread source or authenticate an untrusted provider.
A deliberately changed but syntactically valid invoked member passes structural
decode and fails the subsequent source-slice check; that explicit test passes.
No runtime execution, API registration, dynamic receiver, positional value
forwarding, unique owner, negative certificate or causal authority is added.

Known unsupported syntax remains bounded by the original prototype. No claim for
arbitrary encodings/newlines, defaults/generic scope/overloads or fully resolved
framework types. Longer/unknown optional input returns no facts while preserving
legacy indexing. Snapshot/line-position claims beyond tested sources remain a
future explicit contract, not automatically established by32 passing checks.

## Stage boundary

This supports a finite optional local adapter/model protocol's technical
feasibility, not deployment approval. Such a local extension is not automatically
a general architecture overhaul, but model/DB/public-list changes still require
review. The direct weak lexical case has not become a second strong-contract
failure. Selector semantics and request-side members remain separate unapproved
work. No experiment component is imported by committed production code.

Additional untested model boundary: this version does not establish a complete
batch-wide MAX witness limit, duplicate-record policy or every invalid entity-kind
case. Existing source extraction is bounded, but arbitrary supplied batches need
separate limit/kind/duplicate validation review. Do not promote32 checks to a full
untrusted-provider acceptance gate. Capacity's stored pass:null remains literally
not evaluated by the ordinary tuple comparator; only the distinct capacity
contract was evaluated and passed, not the omitted full-fact oracle.
