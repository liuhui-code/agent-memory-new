# Conditional and touch current Development follow-up

Fixed baseline: 3d62965. No serving change, no aggregate evaluation.

## Current original checks

`eval-context-capability --cases docs/eval/system-capability-cases.json --case-id context-conditional-data-loading-owner --json`
returns **3/3**. All variants return only FolderCollectionLoader. The older ledger's
2/3 is stale. This is not a repair in this stage and no causal attribution to an
individual prior change is established.

The same command for `context-touch-access-safety-owner` remains **2/3**.
Chinese returns JobDispatchPage, WrappedProfileService and PlaybackTouchSurface;
original and English return only PlaybackTouchSurface. The selected original query
was reproduced in a clean materialized fixture (`trace.py`): raw wiki contains the
correct touch file alone, while compact callable primary is ConsoleFailureReporter.
Static wrapped log evidence supplies the additional owners; path activation is
false but that does not prove the user did not request logs.

## Frozen independent diagnostic

`independent-protocol.json` was written before the four public calls in
`independent-current.json`; no production edits were made.

A TouchReader method reads event.touches[0] and updates state; ConsoleSink logs a
synthetic touch-interaction failure, and AuditPage really calls that sink.
- The generic Chinese source query returns TouchReader + AuditPage, strictly red.
- Explicit TouchReader.onTouch returns TouchReader alone.
- Real console logging query returns ConsoleSink alone.
- Explicit two-target query retains TouchReader and ConsoleSink, but also AuditPage;
  the strict precision oracle remains red, not weakened to containment.

First relevant policy boundary: behavior markers are touchboundary+indexedread,
while `classify_target_scope` returns multiple/conjoined_evidence_cue.
`admitted_log_owners` therefore preserves log candidates at its scope guard before
examining complete method evidence. In addition raw wiki is a file projection,
not a callable carrying both requested markers. Compact callable ranking then
prefers ConsoleSink over the touch callable (whose file_structural_coverage is2).

This is not fixed by transferring file labels into a method or by removing
non-activated log paths. Those operations would not establish common ownership or
permission to override the existing multiple-target guard. The previously rejected
scope shortcuts and generic diagnostic-word translation are not revived here.
A future proposal needs independently valid query-role and method evidence contracts
that preserve real multiple source/log requests; neither can be assumed from these
four cases. Current source ranges exist, so no source extraction or budget defect
was established. No new code or relaxed oracle is accepted.
