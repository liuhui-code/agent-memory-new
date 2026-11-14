# Requested multi-caller diversity repair

Baseline14663ac. Independent Development and one original Development scenario;
no full gate, holdout, remote write or claim of global caller completeness.

## Actual first loss

The unchanged fixed query `Find both actual callers of ModalBridge.finish and
ModalBridge.reset.` resolves two different callee IDs and collects two genuine
caller rows, ResetPanel.onClick ID9 and ConfirmPanel.onClick ID3, each6–8 with
current digest/key. The return-only trace shows focus returns both. Diversity then
drops ConfirmPanel as textually similar to ResetPanel: path/method token Jaccard
is over the existing0.3 threshold, and the focused branch does not refill deferred
items. `caller_owner` deliberately counts as a direct graph override, so it does
not receive the ordinary reserved graph lane. The loss precedes raw handoff, not
compact source reading. Traced/clean raw anchors agree.

## Minimal contract and implementation

A multiple request's already admitted distinct typed callers are not the same
requested source merely because their display words overlap. Preserve them through
that similarity decision only. The existing four-seed/two-caller, total result and
per-file limits, ordering, scores, target identity lookup, relation filters and
source-reading rules remain. No callee, log or other context is deleted.

Qualification requires all recognized target references to resolve uniquely and
the exact target-ID set to equal the existing SQL filter's set. The strict check
uses the old separator grammar, rejects unknown first targets, dangling separators,
no-space comma, unsupported conjunctions and unconsumed suffix/task text. Default
legacy target parsing/collection remains unchanged. This is NOT a full natural-
language request parse, all-project caller proof or authorization to force two
files when one actual caller invokes both targets.

Only multiple requests attempt the extra qualification; ordinary single requests
have no additional target-resolution lookup. Complete source identity means
positive typed symbol ID, path, stable symbol key, valid full range and SHA256
source digest. Conflicting same-ID rows or missing/legacy fields do not qualify.
Duplicates, capacity and per-file constraints still apply.

Collector-local ResolvedCallerItem carries a private query/identity binding. Intent
projection correctly makes ordinary dict copies, so the initial subclass-only
candidate lost eligibility and its public test FAILED. That log is preserved.
The final change does not alter any general copy/serialization behavior: within the
same limited_context call, the pre-gate collector computes a query-bound frozenset
of identities and passes it privately through limited_matches to diversity. The
post-gate identity and caller-direction reasons must still match. Changed queries,
list/JSON-shaped bindings and plain dict/JSON copies cannot independently grant it.
No private binding is published as a JSON field.

## Actual results and tradeoffs

|fixed query|before compact paths|accepted compact paths|tokens before→after|
|---|---|---|---|
|finish|ConfirmPanel, ModalBridge|unchanged|1316→1316|
|reset|ResetPanel, ModalBridge|unchanged|1317→1317|
|both|ResetPanel, ModalBridge|ResetPanel, ConfirmPanel, ModalBridge|1337→1458|
|broad|ResetPanel, ModalBridge|unchanged|1305→1305|

The repaired invariant is both admitted callers retained:1/2→2/2 in actual raw and
compact. Both callback bodies6–8 are covered by complete excerpts1–10, and the
callee1–4 remains complete. All remain≤1500. The both output's overall truncated
flag changes false→true as existing budget compression acts on the larger payload;
no claim of lossless whole-payload preservation is made. Its source excerpts are
all explicitly truncated=false.

All four OLD strict path-set equality probes remain false because callee context
is retained; `Find actual caller` never contained an explicit `only`. This change
does not silently reinterpret or relax that oracle. The original42 scenario's
three unchanged variants remain1/3 on fresh baseline and final candidate. Thus the
cumulative repaired original count remains20. No new aggregate score is inferred.

Nine new focused tests plus32 related tests:40 pass,1 pre-existing expected failure.
Controls include single/generic/ordinary graph policy, source/ID conflicts,
projection/query mismatch, total/per-file caps, duplicates, unknown/ambiguous and
partial target grammar, exact SQL-target equality, one caller for two methods,
real log output and project-wide callee ambiguity. Fingerprint1 pass, changed files
compile and diff-check clean; runtime files remain251/479/457 lines (≤500).

## Retained development corrections

- The trace wrapper first failed before main import because tools was absent from
  sys.path; no context ran on that attempt. Corrected setup is documented.
- The initial direct private-subclass transport failed the public test at intent's
  dict-copy boundary; no attempt was made to broadly preserve private authority.
- Internal test factories were supplemented with real query-binding qualification
  after the original red freeze; their bytes are not claimed unchanged. The fixed
  independent sources/queries and original scenario remained unchanged throughout.
- Independent review found partial-target grammar holes, and a no-space comma
  parser could have certified more targets than SQL actually filtered. Both were
  closed conservatively without changing default parsing; intermediate logs remain.

Source commit013ef95; preceding freeze af0f529 and public red4cc4a4a. Final evidence
is accepted-public.json, accepted-original.json and accepted-related.txt; earlier
candidate outputs are retained under their original filenames, not overwritten.
