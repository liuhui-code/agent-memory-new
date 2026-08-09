# Campaign Input Provenance Plan

## Goal

Make `prospective_real_tasks` cohorts prove a verified, user-controlled campaign
source at creation time. The stored cohort must retain only a canonical digest
and minimal verification status. It must never persist raw tasks, logs,
reasoning, absolute paths, owners, or source descriptions.

## Boundary

- Reuse the existing `eval-cohort-create`, `eval-cohort-enroll`,
  `eval-cohort-complete`, `eval-cohort-report`, and `eval-cohort-finalize`
  commands.
- Keep SQLite and the existing protocol JSON as the only persistence surface.
- Keep diagnosis and design reasoning in the local Agent CLI. Runtime only
  validates and supplies evidence context.
- Generated protocol calibration remains usable without a campaign manifest.

## Contract

1. A confirmed `campaign-source-manifest/v1` binds a real cohort to the active
   project root, Memory Home, fixed task count, exclusions, fixed stopping,
   clean-source policy, verification method, custody declaration, and
   feasibility-only claim boundary.
2. The binding stored in `protocol_json` contains only `status`, schema version,
   manifest digest, and campaign-id digest.
3. Creation of a real cohort without a verified binding fails closed.
4. Enrollment, completion, and finalization of an old real cohort without the
   binding fail closed before mutation. Report remains read-only and labels it
   `unverified_campaign_input`; it cannot imply efficiency or promotion.

## Verification

1. Red tests establish the absent internal contract module.
2. Unit tests verify real-cohort rejection and redaction of binding data.
3. CLI tests verify creation requires the manifest, generated calibration is
   unaffected, and legacy lifecycle commands are blocked while reporting is
   safely labeled.
4. Run focused tests, full unit discovery, line limits, compile checks, and
   whitespace checks.

## Result

Implemented in this change. The contract is intentionally a lifecycle and
provenance guard, not an evaluator, retrieval tuner, or diagnostic engine.
