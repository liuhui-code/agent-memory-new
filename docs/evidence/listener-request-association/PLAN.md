# Proposed offline descriptor and name-association experiment

Based on v2 b8f5e6f. Design only until parent review; no runtime/ranking/query
selector change. Existing original/independent queries are observations, never
acceptance requirements to tune into green. No source fact is upgraded to delivery,
registration, causality or exclusive owner proof.

## Finite relational grammar, not phrase scoring

Recognize an entire English imperative sentence with this syntactic shape:

`Find|Locate the callable that binds <source noun phrase> callbacks to
 <target noun phrase containing exactly one TypeIdentifier> MemberIdentifier contract[.]`

TypeIdentifier starts uppercase and is a complete ASCII identifier (HTTP types
allowed); MemberIdentifier is one complete ASCII identifier, preserving case and
underscores. Source phrase and target qualifiers are preserved as explicitly
unverified qualifiers, not discarded or converted to registration API identity.
Type and member attach to the target of the binds-callbacks relation, not accepts,
returns, caller, wrapper or declaration relations. This is a structural descriptor
only: qualifier semantics are not certified by it.

Whole-sentence anchoring; no quoted strings/backticks, negation, alternatives,
conjunction/multiple requests, additional commands or unsupported punctuation.
Only one named type/member slot. Reject unknown relation wording, explicit caller/
wrapper/return/declaration targets and two types/members rather than recover one
substring. The grammar is intentionally narrow, not a general NL classifier.
The exactly recognized relation is callback-to-typed-parameter member association;
`bind` does not become `accepts`. Query source nouns remain unverified.

## Association rules, separate output lanes

Facts are supplied by frozen v2 output with exact source identities. Candidate fact
must have exactly equal declared type, and both callback property AND invoked
member must satisfy the requested member selector. No matching through detail,
method terms, code-body words, aliases, translation or score.

1. Exact lane: case-sensitive equality of selector/property/member. Keep every
   distinct matching outer source identity. Multiple true forwarders remain
   multiple. Exact relation is still a static association, not global uniqueness.
2. Segment lane: evaluated only if exact lane empty. Split existing strings by
   underscores and raw CamelCase/acronym boundaries, with no stopword removal,
   synonym expansion or special treatment of `on`. Match whole segments only;
   label every match uncertain association. Preserve original case information;
   case-insensitive segment comparison is an explicit weak normalization, never
   exact identity. A selector matching several DIFFERENT property/member spellings
   is collision/unknown, not preferred shortest name. Same spelling at multiple
   true forwarders retains all forwarders and multiple status.
3. Property/member disagreement is not a match unless both independently satisfy
   the same selector. A fact accepted→rejected cannot satisfy rejected-property
   intent. Type case differences are unknown, not normalized.

Every output reports evidence coverage. Supplied partial/capped/old-index domains
are unknown; no single returned fact becomes “the only implementation”. Old index
with no facts stays unknown, not no binding. No binding/absence certificate is
emitted. Exact/segment/collision/unsupported/empty-domain are distinct outcomes.

## Pre-freeze cohorts for review

- Original fixed independent five queries (verbatim) and original Native contract
  query verbatim. Observe grammar/association outcomes; do not require Native
  failure→onFailure to pass exact matching or count original improvements.
- Explicit synthetic names onFailure, failureCount, retryFailure, lower/upper case,
  HTTP acronym forms and snake_case. Freeze exact positive/weak-segment/collision
  expectations before code. on is an ordinary segment, not removable prefix.
- Callback property≠invoked member, two forwarders, two different member spellings,
  partial/capped fact list, old index empty. Distinct outer IDs remain distinct.
- Quoted/negated/wrapper/caller/return/declaration, two types/two members, extra
  command and unknown relation strings. Unknown rejects the entire descriptor.

These are new explicitly synthetic descriptor controls, not new benchmark queries
or changes to the original cases. Freeze full inputs, expected lane/status and
source provenance; then freeze implementation; execute once and preserve all
mismatches. No after-result lexical patches. No public context rerun, no ranking.
