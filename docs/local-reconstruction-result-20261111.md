# Verified local reconstruction result, 2026-11-11

## Recovered state and actual outcome

The input is the complete locally verified `verified-repair-resumed.bundle`,
SHA-256 `cdd773da5cb62c148338f8754894d226a45f7049623cbe9b29107d9b113efcf0`.
An independent checkout starts at `25ae6ba` on
`repair/reconstruct-local-20261111`. Its baseline tracked files exactly match the
untouched original. No remote push occurred, and this branch has no remote.

Fresh unchanged Development evaluation: **157/231 pass, 74 fail**. After the
source-backed sink repair, the same unchanged evaluation remains **157/231 pass,
74 fail**. There are no new failing checks, recall/precision/MRR decreases, or
budget failures. This is not recovery of any previously reported 170, 177 or
194 passing state. Five later historical commit objects were not found locally.

## Narrow repair and independent proof

`df3f9df` changes only runtime `log_effects.py`. A caller's business argument no
longer overwrites a fixed or simple-template log message when the complete
canonical ECMAScript sink message expression is proven against the existing
indexed source statement. Earlier arguments must also satisfy conservative
positional checks. Empty literals are preserved explicitly. Proof is cached per
sink; no extra source reads, schema, graph/ranking algorithm or budget changes.

Five new minimal TypeScript sources were frozen before execution. Actual source
execution and both public raw/compact outputs identify three wrong-message cases
on the baseline. The repair fixes the fixed and simple-template cases; both
working controls stay correct. Correct messages improve from 2/5 to 4/5 in each
mode. The second-message-parameter binding case remains wrong and is recorded as
unresolved. All five static path controls and complete source bodies remain
exactly unchanged. Unknown aliases, complex expressions and dynamic binding
retain their old behavior; existing archives need normal relearning.

Two existing tests expected caller text despite fixed sink source. Only those
source-false expectations and exact function selection were corrected. Original
queries, ownership/range/count/path assertions and sink-ID refresh checks remain.
New frozen-source tests and red output precede the runtime commit.

## Verification

- Focused related regression: 18 tests pass.
- Complete suite: 1304 tests in 588.570 seconds, OK with 3 existing optional skips
  (ArkAnalyzer and two explicit-opt-in real host/model checks).
- CI scale: 100,000 searchable entities / 300,000 edges, all gates pass, 10.740 s.
- Million scale: 1,000,000 searchable entities / 3,000,000 edges, all gates pass,
  99.769 s. Both scales pass latency, query-plan and incremental-maintenance gates.
- Original 2001-caller fan-in: 7 successful public commands. Incremental and fresh
  rebuilds contain each expected pair exactly once, no missing/duplicate/extra
  pairs, and unchanged source/runtime.
- Python 500-line and diff checks pass; runtime file remains 388 lines.
- Evaluation policy, case pack, queries, Oracle and budgets are unchanged. No
  consumed holdout or external-generalization claim is made.

The first full run is retained: 1304 tests, 1 failure, 3 skips. Two original
frozen investigation scripts lacked the repository fingerprint. Their exact
bytes are now archived as `.py.txt`, with every original frozen hash verified
through an explicit filename mapping. `freeze.json` and all fixture source/query
bytes are unchanged. After this archive-only correction (`ffe628b`), the complete
suite was rerun successfully, rather than reporting only a selective rerun.

## Actual source bodies and the public path exception

All 21 changed Development records were independently replayed with the exact
sources and queries: 42 raw and 42 compact results. All 42 non-time scored records
and token estimates exactly reproduce the saved evaluations. All 84 returned
source excerpts exactly match their declared source lines. Target excerpts have
zero lost characters or lines, and there are no new forbidden code anchors.

This does **not** mean complete bodies were supplied. Of 21 required source spans,
only 7 are complete; the same 14 are incomplete on both sides (8 partial and 6
absent). Eight changed cases alter non-target source context. The 1498-to-1500
case trims log keywords, not source text.

There is one real public-context exception. For the English query requesting
`.ets` receipt-export implementation, an unrelated JobDispatch wrapped static
path is replaced by a WrappedProfileService log anchor in raw and compact.
The JobDispatch chain is genuine, but its old `nightly` log message was false.
Its indexed path, locations, raw call, depth, evidence, digest and generation
remain intact; its public wrapped path is no longer returned for that query.
The ReceiptExportCoordinator target body and metrics remain unchanged. The other
six queries previously returning `nightly` retain that wrapped path with the
correct template. Do not claim that every old public static path is unchanged.

This does not change the pre-frozen acceptance contract: existing source/path
controls and indexed fields survive, and the unchanged Development checks and
metrics do not regress. The contract did not freeze every non-target public log
anchor. No ranking or Oracle changes were made to hide or reverse this exception.

## Negative findings and remaining work

Two locator investigations and one source-window investigation did not reproduce
their predeclared target-body displacement. They remain negative evidence and
produce no runtime patch. Broader callback, conjunction or identity relaxations
were not introduced. The 74 baseline failures and existing incomplete-body
coverage still need separate source-backed investigation; this stage fixes a
proven source-accuracy defect, not that entire backlog.

The companion evidence contains frozen inputs, actual public stdout/stderr,
failed and successful runs, body comparisons and scale/fan-in results. Generated
SQLite databases are omitted from the delivery archive and can be rebuilt from
the included sources and recorded commands. The Git bundle is authoritative for
commit recovery; the small patch series is an alternative for a clean 25ae6ba.
