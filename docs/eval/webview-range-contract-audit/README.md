# WebView range/recovery contract: read-only exact-field audit

Audit base235fb51. NO new queries, source probes or production changes. Public
observations are the historical accepted multi-source recovery stage at a6c1d93:
`docs/evidence/multi-source-recovery/{original-public,original-after}.json`.
Do not call these current-baseline executions. Color full2..12/1460 recovery is
already accepted and is not the remaining issue here.

## Exact mismatches in existing public outputs

| Variant | callable_evidence.primary | SecureDocumentBrowser anchor | Actual excerpt | Meaning |
|---|---|---|---|---|
| original (remaining precision failure) | DocumentBrowserSettingsPage.build3–8, NOT SecureDocumentBrowser | typed symbol record504, build8–18, role primary | Column9–13, truncated true; final1496/1500 | Display role primary is not selected callable ownership. Recovery does not target this reader/body at all; symbol/start mismatch is an additional independent refusal condition. |
| en-paraphrase (historically passing oracle) | SecureDocumentBrowser.build8–18 | component SecureDocumentBrowser4–19 | Column9–12, truncated true | Selected method identity differs from retained component source range and actual nested snippet. Passing overlap oracle is not full body delivery. |
| zh-noise (historically passing oracle) | SecureDocumentBrowser.onLoadIntercept mechanism window12–14 | build8–18 | Column9–17, truncated false | Complete chosen nested snippet, not claimed complete method/component. No partial-prefix recovery needed for this excerpt. |

Original raw indeed contains the correct build8–18 typed symbol. No source ID is
silently renamed to Column: Column is the excerpt selection label, while anchor
retains its original typed record/range. These are deliberately different fields,
not by themselves evidence of an identity corruption.

Source: `docs/eval/fixtures/system-capability/src/web/SecureDocumentBrowser.ets`.
Actual build is8–18; Column9–17 contains Web10, fileAccess(false)11,
onLoadIntercept12–16, URL normalization13, blocked schemes14 and return15.
The original excerpt genuinely misses14–16, including the blocking decision.
This is not resolved merely by having the right range metadata.

## Consumer chain explains why this is allowed and recovery refuses

`context_source_excerpt.selected_ranges` merges source-bound mechanism ranges
with anchor ranges, orders by query/source mechanism overlap then shorter span,
and avoids overlapping duplicates. `mechanism_callable_ranges` delegates ArkTS
range extraction; it does not promise excerpt symbol/range equals the anchor.
Existing tests explicitly prefer nested onTouch/onKeyEvent over generic build
(`tests/test_context_source_focus.py`). Removing this behavior globally to force
outer method identity would violate an intentional source-focus contract.

`recover_partial_primary` supports completing an already selected **same** interval,
not substituting an enclosing one. For multi-anchor output it first requires one
anchor matching callable primary file/symbol/exact range. The original primary is
DocumentBrowserSettingsPage, so SecureDocumentBrowser cannot receive this privilege.
Even if considered independently, build8–18 vs Column9–13 fails same symbol/start.
For English the retained component4–19 also differs from build8–18; a single display
anchor is not permission to relabel it. Chinese has no truncated chosen excerpt.

Further guards require raw record kind/ID/path/symbol/full range, unique digest,
unchanged existing prefix and hard source/total/token caps. A private projection
receipt cannot be inferred from public role labels or a JSON range overlap.
The existing multi-source recovery stage already added safe multiple-anchor
matching; these shapes are explicitly outside that accepted contract.

## No demonstrated existing identity violation

The missing lines are real, but current evidence establishes intentional nested
source selection plus budgeted truncation, not a silently skipped same-identity
recovery permission. Historical final1496 tokens also does not establish that a
complete nested or outer interval would fit. We did not perform an append/cap
experiment or modify output. Original owner precision is separately unresolved;
full source restoration alone would not remove its extra owners.

The saved public traces did not instrument all excerpt allocation and trimming
steps. Therefore this audit cannot assert whether the first tail loss happened in
char allocation or final token trimming. That gap does not authorize relaxed range
matching, enlarged budgets, or deleting other retained evidence.

## Independent before feasibility / next gate

Existing `multi-source-recovery` independent length-matrix reds prove only the
already-fixed exact single-range prefix case; class/multiple-range probes were
intentionally rejected. Existing nested-source unit positives establish selection,
not a public failing identity contract. No matching independent public red currently
proves an unhandled identity corruption here.

There is no justified new before to execute solely on this evidence. A future
approved request could freeze a real nested-operation source and assert typed anchor
identity remains stable while its nested excerpt is accurately labeled and bounded;
that would test an existing contract and may already pass. Demanding enclosing/full
body regardless of budget would instead require a new allocation/projection contract,
not an identity repair. Do not manufacture a red by changing expected scope.

Disposition: preserve the three exact mismatches and stop this implementation
candidate. No runtime edit, original score update, new oracle, new fixture or claim
that all possible WebView improvements are blocked.
