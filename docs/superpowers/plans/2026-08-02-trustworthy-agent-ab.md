# Trustworthy ArkTS Agent A/B

## Goal

Produce one governed Agent A/B result that separates Runtime context supply from
Agent reasoning without reusing or tuning a consumed holdout.

## Preconditions

- Use a previously unused external ArkTS fix with source, revision, symptom, and
  regression-test provenance.
- Freeze the case before Context evaluation.
- Atomically reserve every classified sealed holdout run before source access,
  Runner execution, or Oracle scoring.
- Treat interrupted and failed runs as consumed.
- Permit Agent A/B only after the same seal has a completed passing Context run.

## Execution

1. Add the SQLite evaluation run ledger and enforce its state machine in both
   evaluation facades.
2. Verify duplicate, failed, concurrent, and predecessor behavior with isolated
   contract tests.
3. Review and seal the wPlayer PiP startup/disposal race at the pre-fix revision.
4. Execute the Context gate exactly once and persist its result and digest.
5. If and only if the Context gate passes, run one fixed Agent Runner for three
   paired source-only/source-plus-context trials.
6. Record quality, stability, Token, elapsed-time, and governance conclusions.

## Stop Rules

- A failed Context gate ends this holdout path; do not edit or rerun the case.
- A Runner failure consumes the Agent run; do not select the best trial or retry.
- Do not change serving behavior from this single holdout. Any observed defect
  must be reproduced in an independent development fixture and public handoff.

## Status

- Evaluation run ledger: implemented; focused contract tests pass.
- External source review: complete.
- Holdout seal: complete; digest `42e8ce9655fcd48e2b71fa544705d58c5d31984bfda1975f74c4b10e70daf340`.
- Context gate: completed and failed. Both query variants found the only expected
  file at rank one with 1.0 recall and precision, but source-span recall was
  0.3333 and 0.0. The first proven loss is callable/passage selection.
- Agent A/B: not executed; Agent call count is zero because the predecessor gate
  did not pass. The sealed case is consumed and must not be edited or rerun.
- Independent development closure: complete. Four editable packs prove callable
  portfolios, artifact roles, definition identity, and object-literal evidence
  continuity through the public handoff. The full capability pack improved from
  154/231 to 158/231 with zero pass-to-fail regression.
- External portfolios: v1-v4 are consumed and immutable. Their Context results are
  7/10, 9/10, 9/10, and 9/10. The v4 seal is
  `dc3c0abd4799223d2db73709fe1373d8d1bb83bdd8f6e33d0b48bc3e4b48d1c4`;
  its only loss occurs after file localization at primary-evidence selection.
- Campaign conclusion: blocked before Agent A/B. All four portfolios come from the
  same wPlayer source family, so selecting v5 would be optional stopping rather than
  independent validation. The next valid campaign requires a new ArkTS source family,
  a preregistered fixed portfolio, and a one-shot passing Context predecessor.
- A new preregistered RNOH campaign used exactly 10 source-reviewed fixes with
  repository-owned regression tests. Seal
  `d594346a45832eb120d7267fcf6755dedd11818c49644c485702a69d2f4584f6`
  was consumed once and produced a 2/10 Context result. Agent calls remained zero.
  RNOH is now also consumed; its failures may form development hypotheses only.
