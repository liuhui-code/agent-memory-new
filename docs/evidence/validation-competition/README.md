# Validation first-loss fixed experiment: stopped without runtime changes

Production baseline 8ce567b, protocol frozen at 419fcdc before the 18 queries (three fresh cohorts × six unchanged queries), each with raw and compact public CLI output. Non-mutating profiling captures full stage inputs/outputs. No full suite, original oracle edits or serving candidate.

## Actual result

Of 18 cohort/query cells, 10 applicable required-source controls pass, one fails, four are N/A because their requested source is not in that cohort, and three generic mechanism requests are deliberately unscored/ambiguous. These are source-retention results, not whole-response precision, full-body or overall gate passes.

English profile target survives all three cohorts. Explicit order and both-owner controls survive whenever sources exist; literal logging control retains the real logger when present. Generic guard/dispatch with competing owners focuses PurchaseCoordinator first via structural selection but later returns both real owners; no exclusive oracle is asserted.

The sole retention failure is profile-zh after adding StatusSink. This query has no activated behavior markers. Raw retains ProfileEditor and focus does not narrow. Callable localization ranks StatusSink.error bounded (20.705) over ProfileEditor.saveProfile (17.205) and ProfileGateway.updateProfile (16.205); compact keeps only StatusSink.error. Its reasons are expanded symbol/summary/method/string evidence. This is a genuine independent localization precision loss, but NOT the original Chinese structural-focus loss. Do not use it to justify a structural fix, error-token change, ranking adjustment, or rejected non-erasure veto.

## Original layer comparison

Sibling directory validation-first-loss preserves original three-variant raw/compact and stage traces. Original English first variant focuses the correct AccountSettingsPage, then salient preservation restores JobDispatchPage and DispatchProfileService. Correct full source remains; this is precision failure. Original Chinese has OrderCommitCoordinator at focus input 13 and AccountSettingsPage at 14, both score 6.0; focus retains only OrderCommitCoordinator. It is not FTS failure. Their file summaries share actiondispatch/validationguard; Order also advertises persistencewrite/asyncboundary. Existing strongest_structural_candidates greedily selects new marker coverage in stable input order. The old trace omits match_reasons/coverage internals, so exact selected helper is code-supported inference rather than newly captured helper-return proof.

The independent English family enters strongest_method_evidence_candidates and preserves the target, while generic goes through structural selection. Thus the fixed experiment does not reproduce target-specific activated structural loss or original salient over-inclusion. No rewording/noise addition is attempted to manufacture such a red.

## Boundary / next missing evidence

Both real owners perform guard/UI feedback/dispatch. Neither shared markers nor UI toast establish which field-domain the user means. Current hints are retrieval clues, not field-to-action binding or unique-owner certificates. This run supplies no safe minimal serving change. A future change requires an independent target-specific activated-query reproduction of the same loss and an existing identity/evidence contract that can distinguish it; otherwise it would require explicit new field/action binding evidence, not marker counts. Previous lexical/operator repairs remain valid producer fixes but do not resolve original validation 1/3.
