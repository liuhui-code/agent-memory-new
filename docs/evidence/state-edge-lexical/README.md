# Lexical state-edge admission

Base623981f; independent public red778ca5f. Three methods containing only a plain
string, comment or plain template mentioning `this.count` produced six real
reads_state/writes_state edges to a genuine @State field. The public list output
is joined only by typed code_symbol references, never bare cross-namespace IDs.
`before.json`/`after.json` also preserve public context output.

The minimal helper uses existing strict callback_mask_lines solely for state edge
body text. Verifiable noncode cannot generate these edges. Unknown lexical input
(slash, interpolation, unclosed text) retains the complete legacy body behavior.
Existing qualified owner lookup, source/target identity, line/confidence/detail,
operation regex, source ranges and declaration parsing are unchanged. The helper
keeps semantic_ecma at492 lines to allow independent declaration work to integrate.

Actual public red:1 test with3 failing noncode subcases. Candidate:47 focused tests
pass,0 failures/errors/expected failures. Four genuine read/write edges to two
separate owners survive; ordinary identifiers do not create an edge; six additional
unknown lexical inputs exactly match the legacy regex result. Multiline noncode
followed by genuine reads/writes remains recognized. Independent read-only review
found no blocker.

Same-source/same-memory activation: old code indexes13 typed state edges; swapping
runtime alone leaves13; normal learn-path merge yields7, precisely removing the6
noncode edges while keeping4 genuine and3 legacy-unknown edges. No schema migration
or automatic historical refresh is claimed. See activation.json and saved runner.

Original comparison-target group remains2/3 before and after, all individual
statuses unchanged; this is a separately demonstrated producer bug fix, not an
original231 precision improvement. No full suite ran.

Important unresolved boundaries: nested object-method `this` is still interpreted
by the old owner logic; unknown lexical inputs may retain old false edges. Equality
operator handling is unchanged in this stage and requires a separate public red.
No causal ordering, complete lexical/scope analysis or data-flow certificate is
created. This is not the separate @State modifier declaration patch.
