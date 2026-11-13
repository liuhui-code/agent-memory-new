# Separate callable statewrite operator correction

Base881aab8 (accepted lexical stage). Protocol and public test were Git-frozen at
341da38 before the public observation/formal red: actual comparison-only methods
for ==/=== receive synthesized statewrite even though stateread is already present.
This is a different producer from the previously repaired semantic state edges.

The final dedicated ECMA_INSTANCE_WRITE_RE retains the original ASCII field-name
pattern and original assignment family (=,+=,-=,++,--); only bare '=' now excludes
following '=' or '>'. It is selected only for .ts/.ets. All other extensions retain
INSTANCE_WRITE_RE, including its old behavior. Shared DIRECT_STATE_WRITE_RE and
all other marker families remain unchanged. No implicit-read or new operator family
is introduced. Actual assignment of an arrow-function value still counts as write.

Review caught that initially reusing DIRECT_STATE_WRITE_RE would broaden fields to
Unicode. unicode-candidate-red.txt preserves the negative result. The final private
pattern corrects that scope leak; it is not claimed as an additional user bug fix.

Unknown lexical syntax still falls back to RAW TEXT, but that raw text is checked
with the new operator predicate for .ts/.ets. Thus unknown output is not promised
byte-identical to pre-operator hints. A comparison is not a write; a regex literal
containing a fake assignment can still yield the old false write. Unknown syntax
has no lexical/scope proof and this remains a non-causal retrieval hint.

## Verification

-46 related tests pass,0 failures/errors/expected failures, including6 new public/
  operator tests. Comparisons, whitespace/newlines, arrow token boundary, genuine
  writes, mixed comparison+assignment, ASCII field-domain and other-language old
  behavior have controls. Earlier candidate45 logs precede the final unknown test.
- Public source identities/ranges are valid before interpreting labels. Same-source/
  same-memory activation independently starts at881aab8: code-only retains2 false
  comparison write hints; normal learn-path merge removes them, keeps stateread and
  all6 real-write controls, and preserves semantic key/path/range/digest/string text.
- Original validation group remains1/3 and comparison group2/3, every variant's
  status unchanged before/after. No original231 improvement or full-suite claim.
- Independent review confirmed final ASCII predicate, real positives, activation
  and original-group status. Candidate scope correction is disclosed, not hidden.
