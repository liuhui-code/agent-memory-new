# Fresh output-loop reimplementation, 2026-11-15

This is NEW work from 066cc1a (production fced64c4), not recovery of the
unavailable 8b2c304 or its 55 historical commits. No remote write was performed.

## Fixed observations and result

The unchanged independent protocol was frozen first. Its generic public query
initially lost PipeCollector.collect and selected OutputDescription.label.
The final public compact result contains collect, including its complete lines
2-10 and same-read digest-bound snapshot. The two explicit-name queries still
return class anchors, not their requested exact method symbols. Their file
retention controls pass but their historical symbol expectations remain unmet;
this report does NOT claim all three independent queries fully pass.

The unchanged original Development category context-process-output-read-loop-owner
was freshly run before and after. Before: 2/3, with original failing precision
while its required span was already present. Final: 3/3, with original selecting
only src/io/ProcessOutputReader.ets. English paraphrase and Chinese remain pass;
they do not activate this finite English grammar. This is one newly verified
original failed variant on the current baseline, not a restored historical count.
Only this original group ran; no aggregate/full gate/231/holdout was run.

## Mechanism and boundaries

A finite whole-source adapter recognizes a direct same-local sequence: parameter
readLine -> cursor, const empty string array, while(cursor !== null), direct push
of that cursor, reread from the same receiver, and return of that array's join.
It is a static source-shape witness, NOT SDK type, dynamic execution, value-flow
across arbitrary code, runtime success, unique owner, or global absence proof.
After-loop/deferred accumulation, single reads, swapped locals/receivers,
shadowing, extra unknown syntax, unknown lexical forms and ASI ambiguity abstain.

The separate finite request grammar requires explicit output iteration AND
accumulation ownership. It adds no keyword score, marker-only focus, name gate,
recall terms, threshold change, or code-specific identifiers. Unsupported wording
retains the baseline. This is deliberately not arbitrary natural-language support.

Qualification requires actually recalled file AND matching method records, exact
current source digest/generation and owner/method ranges from SQLite; TypeScript
and ArkTS static adapters are explicitly validated. Qualification reads <=12
recalled candidate files, <=2 MiB each. All qualifying files are retained, up to
3; more or incomplete compact source projection falls back instead of choosing
a unique winner. Multiple owners were verified using normal learn-path and public
CLI. A shorter query that recalled only label symbols correctly stays baseline.
No previously unrecalled file or loop method is promoted from label recall alone.

OutputLoop has independent private authority/context classes. No Render or
Lifecycle authority is inherited. Shared formatting is pure. Exact query/pool,
receipt and view bindings, source drift, copied/tampered objects, path/log/graph
protection and complete 1500-token projection are checked. Baseline and trial
protection both apply. Facade enrichment preserves authority only on inactive,
unchanged freshness/path state, and accounts once for the actual adopted result.
The finite render, lifecycle and output grammars do not overlap; output is tried
last but inactive output performs no extra pass or mutation. Shared composition
now explicitly defers output accounting, so its structural unit assertion was
updated to include that declared parameter, not relaxed.

## Failures retained and review corrections

- Initial source parser incorrectly tried to consume EOF through a helper that
  rejects EOF. Corrected explicit end check; initial positive test had errored.
- First public candidate did not activate because copied ArkTS-only row validation
  rejected genuine TypeScript-static rows. It was replaced with output-specific
  validation; the unchanged first candidate output remains in candidate.json.
- Trace harness initially omitted the test memory-home; setup-only SQLite open
  failed. Corrected to use the same test memory-home, no oracle/source change.
- ASI controls exposed return-newline acceptance; asi-before.txt retains failures.
- Independent read-only review exposed Unicode/comment line separators and strict
  binding names. Finite parsing now rejects the eight extra splitlines separators
  and enum/package/eval/arguments; dedicated regressions cover these. Reviewer
  independently rechecked both fixes and found no remaining reviewed blocker.
- Initial multi-owner public test's short query recalled only label symbols, so
  expected source authority was unjustified. Retained as a fallback control; the
  separate positive uses the already-frozen independent generic query, not a new
  searched-for oracle. public-render.txt retains the initial failure plus the
  expected new-defer structural assertion mismatch. No evaluation fixture/query
  or gate was edited.

Final relevant test results are in final-related.txt; earlier batches and
intermediate diagnostics are retained. Review covers the finite source adapter,
private authority and shared hooks, not arbitrary language support or full gate.
