# RNOH ArkTS Agent A/B Campaign

## Goal

Run one preregistered, one-shot external Context gate on a previously unused ArkTS
source family and, only if it passes, run a fixed paired Agent A/B without changing
the case pack, query behavior, Oracle, runner, model, thresholds, or trial count.

## Frozen Campaign Definition

- Source repository: `https://github.com/ohosgg/rnoh.git`.
- Local source: `/private/tmp/agent-memory-ab-rnoh-full`.
- Case pack: `docs/eval/rnoh-agent-ab-cases.json`.
- Case count: exactly 10; no `--limit` and no `--case-id` execution.
- Context attempts: exactly one after sealing.
- Agent runner: `examples/codex-agent-benchmark-runner.py`.
- Agent model: `gpt-5.5`.
- Reasoning effort: `low`.
- Trials: exactly three paired baseline/memory trials per case.
- Runner timeout: 900 seconds per call.
- Source boundary: read-only frozen pre-fix workspaces; no Git history access.
- Memory delivery: Runner-preloaded compact Context with external source bodies redacted.

The ten case ids and their order are fixed before sealing:

1. `rnoh-paragraph-ellipsis-padding`
2. `rnoh-paragraph-text-align-padding`
3. `rnoh-image-invalid-source-switch`
4. `rnoh-text-input-font-color`
5. `rnoh-transformed-touch-coordinates`
6. `rnoh-virtualized-list-initial-index`
7. `rnoh-pan-responder-scroll-lock`
8. `rnoh-trimmed-inline-view-crash`
9. `rnoh-inline-text-vertical-alignment`
10. `rnoh-text-measurement-float-rounding`

Every case has a full parent revision, fix revision, reviewed changed-file set, issue or
commit symptom, and a repository-owned tester or Jest regression case. All cases share
the RNOH repository lineage and count as one source-family observation.

## Execution Contract

1. Validate JSON and audit all declared revisions and files through `eval-seal-cases`.
2. Preserve the generated seal digest and never modify or regenerate the sealed pack.
3. Run the complete sealed pack once through `eval-context-capability` using the same
   project archive that owns the append-only evaluation ledger.
4. Persist the Context result and verify one completed ledger row for the seal.
5. If `promotion_policy.eligible` is false, stop with zero Agent calls.
6. If it is true, run the complete seal once through `eval-agent-benchmark` with the
   fixed Runner, model, reasoning effort, timeout, and three trials.
7. Persist the A/B result, response telemetry, quality, Token, elapsed-time, source-read,
   and governance conclusions. Do not retry failed Runner calls or select trials.

## Stop Rules

- Any seal, revision, file-audit, Context, Runner, or ledger failure consumes the
  corresponding classified run and stops the campaign.
- The case pack and Oracle are never changed after sealing.
- No serving-path change is allowed from this holdout result. A defect must first be
  reproduced in independent development data and the public handoff.
- There is no second RNOH portfolio. Another external campaign requires a new source
  family and a new preregistration.

## Status

- Source and diff review: complete.
- Campaign and case order preregistered: complete.
- Seal: complete; digest
  `d594346a45832eb120d7267fcf6755dedd11818c49644c485702a69d2f4584f6`.
- Context gate: completed once and failed at 2/10. Candidate-file recall@20 is
  0.9, hierarchical file recall is 0.5, anchor recall is 0.4, and average compact
  size is 1,425.7 tokens. The seal is consumed and must not be rerun.
- Agent A/B: not executed. The predecessor is ineligible and the ledger contains
  zero `agent_benchmark` rows for this seal.
- Campaign conclusion: stopped as preregistered. The result is preserved at
  `docs/eval/rnoh-agent-ab-context-result.json`; no second RNOH portfolio is allowed.
