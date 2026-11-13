# Lifecycle callback cleanup: Development repair

## Frozen experiment and plan

Baseline: local 2d48e9c (integrated remote f8c3b53). Independent clone, no shared
runtime changes. A frozen four-class fixture distinguishes direct lifecycle+cleanup,
lifecycle-only, cleanup-only and split-method ownership. Identical TS and ETS sources
run six frozen queries in raw/compact modes (24 calls per code version).

Before code modification, public English paraphrase returned the split owner and
cleanup-only neighbor. TS Chinese query returned no anchor. This identifies the same
missing method-evidence layer, without using the existing scenario to tune the fix.
Existing scenario baseline was separately measured: 1/3, both English variants failing.

Plan: reuse bounded callable evidence and existing cleanup recognition, verify non-code
and nested-scope negatives, replay frozen public queries, then only the existing focused
scenario and necessary related regressions. No full gate, consumed holdout or remote write.

## Minimal change

Add lifecycleboundary for existing recognized lifecycle method names and callbackcleanup
for the existing cleanup-call pattern, inside the established conservative method-local
scope guard. No new query vocabulary, score, file-level weight, evaluator or architecture.
Strings, comments, regex literals, nested callbacks/functions/object methods/accessors
cannot add cleanup labels. Registration alone does not count as cleanup. Java is unchanged.

The conservative guard may miss valid callbacks or methods mixing direct and nested work;
it does not claim nested callbacks execute during the enclosing lifecycle.

## Intermediate regression and compact repair

The initial 76-test related run had one failure: an explicitly requested second owner
was present in raw anchors but removed by compact callable focus. The same dual-target
control passes on 2d48e9c (the baseline public test file has only the expected three
semantic subcase failures). This is a real candidate regression, not an existing failure.
An attempted early-selection protection did not fix the compact loss and was reverted.

Compact focus now declines to narrow when at least two exact requested callable targets
from primary/alternatives have valid ranges wholly contained in already supplied anchors
in different files. It returns the original anchors; it does not create a source anchor,
project a cross-file portfolio, or grant private certification. Existing certificate
branches execute first. Seven tests bound single/missing targets, out-of-range spans,
identifier prefixes, same-file scope and untrusted portfolio behavior.

## Result

- All 24 candidate public calls exited successfully; all 12 compact anchor controls match
  their frozen expected owners. Raw named controls may retain related alternatives.
- Explicit two-owner public requests without paths preserve both requested sources in TS
  and ETS. Seven new scope/registration unit controls pass.
- Final necessary regression run: 123 tests pass, including compact focus/certification,
  prior collection-owner, salience, lifecycle, behavior-marker and same-owner controls.
- Existing lifecycle callback cleanup scenario: 1/3 -> 3/3. Both English failures fixed;
  Chinese remains passing. Final targeted cleanup + adjacent-owner run is 6/6.
  Original source/oracles/queries unchanged.
- Compilation, diff check and changed runtime file line bound pass.

This is a focused Development result, not a new 231-case total or external promotion.
The independent callable_evidence.primary consistency limitation from the prior stage
is not addressed. Existing archives require normal reindexing to materialize new hints;
no source digest or freshness bypass is introduced.

The tracked observation projection contains raw-output SHA-256 values and both anchors
and callable primary; full raw outputs remain beside the independent workspace. The
run.py copy documents the original experiment layout, not a repository-root invocation.
