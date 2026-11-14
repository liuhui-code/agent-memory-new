# Disposable CLI overlay review: not ready for production

Read-only review of listener-cli-compat/docs/evidence/listener-cli-compat-experiment
install_overlay.py, overlay_support.py, model_checks.py, indexed-controls.json,
model-results.json, run.txt, old-reader.txt and EXECUTION.md. No experiment rerun,
new counterexample execution, runtime edit or frozen data modification by reviewer.
The initial import-path failure and corrected second attempt remain recorded.

## Actually measured evidence

Saved CLI control result: 19/20, not full success. Native has zero persisted
witnesses instead of two; Relay and the other fixed controls match expectations.
The Native rows retain operation details call:listener.onready/onfailure, while
attach constructs its join key from case-preserving onReady/onFailure. Therefore
the existing textual record join cannot find these Native facts. This is visible
in the saved actual rows and code, not a new measurement. Case-insensitive matching
alone must not certify identity: distinct case-sensitive members need protection.

Eleven saved model checks pass: new roundtrip; legacy record without new field;
old reader explicit schema rejection; bad version; boolean coordinate; bad nested
range; wrong key; wrong snapshot digest; oversized witness; receiver mismatch;
atomic whole-record byte-cap omission. These tests establish their stated cases,
not complete validation or backward-compatible evidence retention. Old-reader.txt
shows intentional rejection, not an old reader transparently accepting new schema.

## Static, NOT executed counterexamples / missing checks

1. from_dict unconditionally changes semantic-index/v1 to the experimental schema.
   A v1-labelled object already containing typed_invocation_witness follows the
   new validation path. The legacy test removed this field and does not cover
   contaminated old-version input. A formal protocol must reject or explicitly
   discard unsupported payloads; it must not authenticate them by relabelling.
2. validate checks a formal index is in 0..15 but does not compare that index,
   name or declared_type with the entity signature. A modified type or another
   in-range index is not rejected by these checks. The construction-time source
   validator is not repeated by batch decoding and cannot supply that guarantee.
3. Nested object schemas are not exact. Argument-call receiver/member and source
   coordinate_unit are not checked. Inner ranges are mutually nested and below
   32768, but not source-sliced or offset-bound to the outer entity at decoding.
   Source key/digest equality links a claimed snapshot; it does not independently
   prove arbitrary inner bytes or binding semantics. Validation must name which
   facts require trusted producer provenance or later source verification.
4. The existing 4096-byte mechanism serialization stops at the first oversized
   candidate. Enlarging an existing operation record may drop that entire legacy
   record and every following record, including original search terms. The cap
   test proves atomic omission only. It does not establish unchanged old evidence,
   and grafting into the same record does not by itself preserve retrieval.

These are code-path observations requiring separately frozen tests if pursued;
none has been silently added to or used to rewrite the original 20 or 11 checks.

## Decision and bounded next step

Do not integrate this overlay as the formal producer/model implementation. Keep
it as a useful local experiment identifying a real model/transport boundary, not
as evidence that the entire project is blocked or that structured facts are
inherently impossible. No selector or original failure improvement is approved.

A finite next proposal must define: exact optional field/version dispatch; v1
contamination behavior; signature/formal and snapshot joins; strict nested shape
and coordinate-unit contract; which source facts are producer-attested rather
than independently decoded; case-sensitive graft identity with ambiguity refusal;
and overflow behavior preserving old evidence rather than simply breaking earlier.
Freeze new malicious/malformed/ambiguous/cap controls before execution. Retain the
existing failed Native result and all old inputs/oracles; do not erase 19/20 by
retroactively modifying this experiment. Any model-only improvement still needs
public learn/list, install-only versus merge, legacy terms/order and unchanged
query protection before production review. Consumer intent/member permissions
remain a separate task.
