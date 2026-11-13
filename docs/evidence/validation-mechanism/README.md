# Verified lexical text for two callable behavior hints

Base1105717. See TIMELINE.md: initial observations preceded Git freeze and are
explicitly diagnostic. Formal acceptance protocol/test was committed at a66b520
BEFORE formal-red.txt; supplemental string-value controls at325cf51 preceded the
candidate. No retroactive Git-freeze claim.

## Scope and actual public evidence

Only callable_behavior_hints INSTANCE_WRITE_RE and EARLY_RETURN_GUARD_RE now inspect
known-code text for .ts/.ets sources. Strict callback_mask_lines success supplies
that text; unknown syntax uses the original body. Other extensions, INCLUDING .js,
retain the original behavior. This is not an all-ECMAScript/native-language repair.
No other hint regex, marker family, method_terms_from_source, string_evidence,
ranking, query wording, certificate or original evaluator was changed.

Public semantic method IDs/qualified names and exact ranges were first validated.
The literal/comment/plain-template methods then formally fail: they synthesize
statewrite and guardreturn despite containing those operations only as noncode.
The literal source does not contain those synthesized marker spellings. Candidate
removes those false labels while preserving the source text for ordinary retrieval.
True assignments of string values and guards returning error strings retain their
respective labels and string evidence. Throw-only keeps its old no-guardreturn
behavior; this stage does not expand guard types or fix equality operators.

## Limits preserved, not hidden

The initial fixture's regex poisoned container-range parsing: class1..1 and methods
without semantic IDs. before/preflight preserve it. The supported supplemental
protocol isolates that unrelated parser deficiency; it is NOT an unknown-regex
public success. Unknown interpolation has public legacy control; regex/unclosed
and non-.ts/.ets cases have helper legacy-equivalence controls. Unknown cases can
retain false labels. Other raw-source hints such as stateread/statebranch remain
unchanged and are not claimed fixed. Hints are retrieval cues, not unique-owner,
causal or execution-scope certificates.

## Verification and activation

-38 focused tests pass,0 failures/errors/expected failures: new public/lexical
  controls plus callable behavior/state-handoff/collection and semantic indexing.
- Same-source/same-memory activation independently checked from1105717: code-only
  still has the six false synthesized marker occurrences; normal learn-path merge
  removes those six. Real controls survive. Semantic key,path,qualified identity,
  ranges,digests and raw string_evidence are unchanged. No automatic code-install
  refresh or schema migration is claimed.
- Original validation-stop group remains1/3 before/after with identical statuses.
  No original231 improvement or full-suite claim. This is marker correctness only.
- Review checked the narrow diff and evidence timeline; no code blocker reported.
