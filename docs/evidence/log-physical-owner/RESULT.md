# ECMA log function ownership uses physical coordinates

Baseline: remote e2c4d7b3, equivalent local 1ac73b1. Independent Development only;
not a consumed holdout, external project, aggregate pass, or closure of an old group.

Two actual public learn/list/context projects show the defect: a string containing
LS precedes a single-line method containing console.error. JobWorker.run (TS) and
FetchBridge.connect (JS) logs physically occur on line 3, but both list and context
return function=null. Log scanning already counts physical LF after universal
newline decoding; the ownership table alone used Python's broader splitlines.

Only extract_log_statements' ECMA ownership table now uses physical_source_lines.
Other languages, log recognition, templates, levels, logger, raw statements and
source hashes remain unchanged. Copied baseline databases merged at generation 2
return run/connect in actual list and context log anchors. Source locations stay 3.

A newly checked negative also exposes a pre-existing incorrect first-function
assignment: two callable declarations separated by active LS/PS on one physical
line cannot be uniquely resolved by this line parser. When extra splitlines
separators survive the existing code mask, keep every log but decline function
certification throughout that source. This is conservative uncertainty, not runtime
causal inference. The mask is not a complete JavaScript lexer; regex, interpolation
and lexical terminator semantics beyond its existing contract are not certified.

Validation: 39 focused unittest methods pass (focused.log), then the final five
new methods pass after adding no-final-newline controls (final-new-tests.log).
Five new methods cover TS/JS/ArkTS × space/LS/PS × LF/CRLF/CR and final/no-final
newline, adjacent methods, top-level logs, fake string/comment logs, active
separator uncertainty, old callback behavior, Python control and two actual public
CLI paths. These are overlapping runs, not 44 unique tests. The initial Python
control wrongly assumed print was not a recognized log; corrected the test to
preserve existing behavior, retaining tests-controls.log. Production did not change
Python parsing. An existing opaque test rewrote its tracked evidence; its generated
output is retained separately here, and the tracked historical original restored
byte-for-byte before commit.

Independent reviewer accepts narrow publication after the targeted pass. Callback
control demonstrates unchanged behavior, not new precise nested callback support.
No budget, default excerpt retention, oracle, ranking, or original request changes.
