# Sole-literal-return fact: design review only

Review base14d714f. Read source_operation_roles, query_source_operation,
semantic_callable_profile, query_hierarchical_localization, query_callable_evidence,
query_collect and callback mask. No new fixture, public query, test or runtime change.
Cache/output independent results are owned by other reviewers; this document does
not assume either case supplies safe operation intent or a second architecture class.

## Existing interfaces and what they actually promise

- semantic_callable_profile.callable_roles appends source_operation_roles(source,
  file_path). Existing code_symbols.callable_roles is serialized through localization;
  this is a possible storage carrier for a versioned fact, not permission to act on it.
- source_operation_roles v2.1 supports only runtimecapability and persistenceread,
  with unresolved markers. Its NON_CODE_RE is not sufficient to extract an exact
  sole-literal grammar: it erases the very literal and has known template limits.
- certify_source_operation resets source_operation_match every call, requires
  explicit target cue, no quotations/multiple/non-source target, no typed/exact-name
  competition, expected markers wholly in those TWO supported families, known
  adapter/version/identity/range/digest for all candidates and no unresolved expected
  operations. Only one positively proven candidate gains match. This is NOT a
  generic executable-operation detector and does not cover cache/output loops.
- rank_callables sorts source_operation_match ahead of ordinary ranking. certainty
  makes that flag bounded; compact can then replace anchors. Setting this flag from
  competitors' negative literal facts would therefore accidentally grant a positive
  unique-owner certificate. Do not reuse that authorization flag for this proposal.

## What a narrow source fact could mean

At most: under a specifically supported syntax, the callable body consists solely
of returning a quoted literal token, with no other statements. This is a **body
shape fact**, not proof that calling it is side-effect-free, that it cannot implement
an operation, that its return value is irrelevant, or that another candidate owns
any requested operation. A literal SQL/HTML/program/config/route may be precisely
what the task asks to locate. A label can be a true API implementation.

A minimal eventual producer would need an exact known callable boundary and a
fully anchored grammar, not three regex occurrences. Reuse equal-position lexical
validation as a necessary gate, but callback_mask_lines erases literals and is not
itself an AST or sufficient body-shape witness. Match raw quoted token against its
known masked span only after safe header/body boundaries are established. Initially
reject unknown syntax, templates/interpolation, expression-bodied arrows, overloads,
computed names, decorators, generators/async/accessors, nested scopes and unsupported
languages rather than infer absence. Comments/trivia may be accepted only if their
exact spans are known; executable code must not disappear into the trivia mask.

Header matters: a sole return body with default parameter `x=sideEffect()`, parameter
destructuring getters, decorators or a receiver getter need not be side-effect-free.
Conservatively require an ordinary zero-argument declaration with known header shape
if any stronger no-body-operation use is considered; even this does not establish
runtime dispatch/receiver purity. No side-effect-free claim should be made at all.

## Identity, freshness, storage and stale-cache risks

Use existing symbol_key + path + typed symbol identity + inclusive callable range
and original-byte source_digest provenance. Never infer the fact from summary,
string_evidence, retrieved snippet or file-level marker. Missing field/version in
old archives is unknown, not a negative fact. Installing code does not update old
rows: normal learn-path merge must be separately tested, including replacement of
prior fact when a body gains a statement or source changes only by line endings.

query_collect filters scored derived matches with index_freshness, but localizer
load_file_callables also reads code_symbols by selected file directly; it does not
independently hash each candidate in that function. A digest's mere presence is not
freshness validation. A new negative fact must not silently inherit stronger
freshness guarantees than this chain supplies: trace current-source admission for
all candidates (including graph additions), or require an existing verified receipt.
Do not perform uncontrolled extra file reads or invent a second digest convention.
Caches/JSON copies must not preserve a private query authorization. Reset any future
query-specific decision at every query as source_operation_match currently does.

## Main blocker: query authority, not storage

There is **no existing generic contract** sufficient to mark the current cache or
output query as requiring execution rather than a returned literal. Existing target
cue means retrieval command, not that distinction; behavior markers are searchable
heuristics and alternative concepts, not operation-intent certificates. Broad owner/
implementation wording also applies to SQL-returning or HTML-rendering functions.
Absence of literal/text words is not positive evidence of an execution request.

Do not add readLine/delete/append/cache/loop token lists, named benchmark exceptions,
or reuse full-query lexical hints as authorization. A new syntactically explicit
request contract could eventually distinguish action implementation from quoted
artifact-return targets, but it needs independently justified grammar, unknown
fallback and positive/negative coverage. It cannot be presumed to cover today's
frozen queries merely because a pure description wins them.

Even with proven intent, negative fact about one candidate must not establish that
all remaining candidates satisfy the requirement. Keep true named target, literal/
text/log queries, quoted source, mixed requirements, multiple owners, negated clauses
and unknown candidates unchanged. Do not drop the literal source from retrieval or
claim its absence; any eventual conflict annotation must be separate from ordering
and from exclusive narrowing. An annotation alone will not prove a repair benefit.

## Recommendation / stop boundary

Producer-only body-shape storage is technically possible as a separately versioned,
source-bound fact with strict unknown behavior; reuse callable_roles transport, not
source_operation match or v2.1 checked status as a new certificate. Whether adding
that fact is useful enough to justify a schema/contract extension depends on actual
independent defects and consumer authority, not code elegance.

**Do not implement ranking/narrowing now.** First establish an auditable operation-
request contract that is genuinely supported by existing semantics or propose it
explicitly as new. Current inspected code does not provide that generic contract
for cache/output. This review identifies a precise missing authority rather than
claiming all remaining tasks impossible. No v3 revival, new score or query change.

## Follow-up: a falsifiable next design, not only a refusal

Read sibling reports now integrated as235fb51:
`docs/eval/cache-contract-review/LITERAL-NEGATIVE-REVIEW.md` and
`docs/eval/sole-literal-contract-review/README.md`. They establish two independent
operation-domain competitions worth investigating. They do not establish positive
request authority, and output's SingleRead or cache's FIFO remain legitimate rivals.

### Reuse assessment

behavior_marker_terms can be reused **unchanged as a shadow diagnostic input**.
TARGET_CUE, existing explicit/typed identity detection, multiple scope and non-source/
quoted request vetoes can likewise be reused. Their conjunction is a testable
hypothesis about requests, not an existing permission contract. Markers are emitted
from retrieval expansion and broad concepts; `read`, SQL, HTML/config, documented
algorithm descriptions and artifact-return implementations can legitimately share
operation words. More vetoes cannot turn absence of literal keywords into a proof.
Do not add or whitelist cache/output marker names merely because those cases fail.
The current v2.1 supported subset cannot be broadened by calling these inputs intent.

### Stage A: freeze request-authority truth table before source classifier

Propose one finite, separately reviewed table, before any runtime implementation:
1. Include the exact already-frozen cache/output failing queries and original
   strict oracles unchanged. Record actual existing marker set and veto outputs;
   do not rewrite them if the proposed gate is inactive.
2. Protect explicit label, real emitted log, requested literal/text/config/declaration,
   mixed source-plus-description and multiple-target queries from the existing
   protocols. A green control with the gate inactive is recorded as such, not as
   tested behavior inside the changed branch.
3. Add a small *pre-execution* adversarial group whose desired implementation returns
   constant SQL, HTML, program text or configuration, but whose natural request
   describes the artifact's read/iteration/deletion behavior without saying
   `literal`/`string`. Also include ordinary descriptive-label behavior and a
   no-explicit-name artifact-return request. An independent reviewer must label
   intended target roles from the fixed source and request, not gate outputs.
4. Add ambiguous historical operation, quoted instructions, negated operation,
   unknown language/intent and one-owner-two-actions versus two-owner mixed requests.
   These are unknown/refuse-new-authority, not inferred negatives.

Freeze the candidate gate specification: an existing retrieval target cue, nonempty
unchanged behavior_marker_terms, and all current explicit/typed/quoted/multiple/
non-source vetoes passing. Evaluate it read-only as a **shadow classifier**, not by
changing serving outputs. This gate is deliberately allowed to be falsified.
Stop if either mandatory original query is not admitted (no expansion to force it),
or if any artifact/mixed/ambiguous protected request is admitted as executable-only.
Report the semantic counterexample; do not patch it with SQL/HTML/label exceptions.
A table with false positives cannot authorize producer-to-consumer integration.
If all pass, that is bounded Development evidence for review, not proof of universal
intent and not permission to bypass unknowns.

### Stage B, only if separately approved after A

Freeze exact sole-return syntax/identity facts and controls already enumerated above,
including default-parameter effects, ASI return/newline, malformed bounds/digest,
old-index/version, same-file methods and executable interpolation. Verify the fact
through actual public learned records, normal-merge activation and unknown behavior.
Do not generate a source_operation_match or classify another method as positive.

### Stage C needs an explicit fallback decision before any candidate

A negative-only fact cannot choose a replacement or increase certainty. The safest
initial consumer experiment would record a query/source conflict and refuse *new*
exclusive primary authority, preserving existing source evidence under the unchanged
budget. It must not silently rerank to SingleRead/FIFO or assign boundedness to an
unknown alternative. If this produces no correct primary or violates an existing
strict public oracle, it is a failed repair, not success renamed as abstention.
Choosing a different executable owner would require an additional positive proof
contract; that is outside this negative-fact hypothesis and must not be slipped in.

Predeclare acceptance as both unchanged cache/output required public outcomes plus
all protected controls, actual full required source and current budgets. Stop if
retention alone cannot meet these strict outcomes. This may falsify the proposal's
usefulness even when source classification is correct. No score/marker/threshold
changes, added noise, relaxed oracle, or post-result query revisions are allowed.

This sequence has an actionable cheap first decision: test request authority before
investing in a parser or schema. No part of A/B/C has been executed or approved here.
