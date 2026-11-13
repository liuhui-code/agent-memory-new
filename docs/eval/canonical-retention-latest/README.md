# Remaining canonical English variant: current single-query audit

Runtime base 3a7aea5. Prior snapshot: docs/eval/canonical-current/README.md at
623981f. Protocol and trace runner frozen in 9878a06 before execution. Governance
is development/editable/project_neutral; no consumed holdout or full suite was run.
Only the unchanged en-paraphrase was executed once through public context raw and
compact after init/learn in the existing scenario materialized workspace.

Query: "Locate the canonical quota recovery click handler that enables retry and
updates the notice; exclude generated build artifacts."

## Current observed boundary

public.json contains all four CLI results; trace-2.json is raw selection tracing.
The fixed remaining variant still has extra owners, independently of any overall
scoring claim. Compact paths are QuotaRecoveryPage, ParcelRetryPage and
AccountSettingsPage. The correct primary is applyQuotaRecovery, with actual
retryEnabled/recoveryNotice writes visible at lines 8–9 in its returned 7–19
excerpt. The frozen oracle interval begins at line 6 (a blank line); no evaluator
was rerun and no interval or oracle changed here. Do not report a new 2/3 aggregate
or complete interval acceptance from this single raw/compact observation.

First undesired supplement is unchanged:
1. filter_query_role_candidates contains no generated preview result.
2. focus_code_candidates retains only QuotaRecoveryPage applyQuotaRecovery,
   onClick and build. Structural preservation returns the same three methods.
3. preserve_salient_evidence_candidates adds ParcelRetryPage.onClick, a direct
   source-locatable salient candidate, and AccountSettingsPage.saveAccount, with
   graph_neighbor plus graph_relation:imports. Both redundant_source_supplement
   checks return false. This is the first expansion beyond the focused owner.
4. Compact retains these three paths. Raw also has AccountUpdateService log emitter
   and DownloadsPage wrapped caller, but they are NOT the final precision extras.

## Actual source versus artifact/class labels

All source paths are under docs/eval/fixtures/system-capability/:
- src/pages/QuotaRecoveryPage.ets has actual writes retryEnabled=true and
  recoveryNotice='quota recovery ready'; onClick calls applyQuotaRecovery.
- src/pages/ParcelRetryPage.ets has a genuine parcel retry async operation,
  retryPending guard/reset, a Retry parcel button and its own enabled/click/text
  behavior. It is maintained source, not a generated quota preview.
- src/pages/AccountSettingsPage.ets imports AccountUpdateService, validates
  displayName and calls dispatchUpdate. It is maintained source, with retrieved
  import graph provenance; lack of quota writes is not proof of no diagnostic
  relationship in all tasks.
- The forbidden .preview/default/cache/src/pages/QuotaRecoveryPage.ets is absent
  from both public outputs. This is not an artifact-filter bypass or same-name
  preview identity corruption. Component/class labels alone prove none of these
  behavioral distinctions; the statements above are from the source bodies.

## Existing contract assessment

filter_query_role_candidates applies generated-path filtering before language and
excluded-example handling. These extras are neither generated nor examples, so
extending that exclusion to them would change its meaning. The earlier positive
structural-query exclusion repair remains intact: no extra is introduced at the
structural stage. Do not revive native/build trigger special cases.

The existing salient redundancy contract protects multiple-target classification
and graph provenance. The fixed query's conjoined actions meet the former existing
boundary; AccountSettings independently has the latter protection. Bounded callable
selection does not grant exclusive owner authority over all source evidence, and
canonical source kind does not mean only one maintained implementation may survive.
No typed identity certificate requiring these extra candidates to be excluded was
found. No skipped artifact/source-kind or typed-ID consumer permission is shown.

## Minimum next evidence, not another tuning series

The existing independent canonical-current fixture is already frozen: generic red,
explicit pair green, and strict extras in other controls are retained. It reaches
a different initial focus (notice exact-symbol candidates), not this original's
three-method focus. It therefore cannot justify simply bypassing the multiple/graph
veto here. Re-running it or changing its words to force focus is not this stage.

A safe consumer proposal would need an independently demonstrated request-bound
identity/role distinction between a quota implementation and genuine other retry
or update implementations, plus actual requested graph/dual-owner controls. There
is currently no such exclusion authority. Even a proven redundant direct supplement
would not authorize dropping the graph supplement. Keep these lanes separate;
no score, broad semantic veto, source-kind reclassification or unique-owner claim.

Result: current first expansion is precisely known and still policy-protected;
this audit establishes no narrow existing-contract misuse. No production change,
new variant, original repair credit, external validation or architecture proposal.
