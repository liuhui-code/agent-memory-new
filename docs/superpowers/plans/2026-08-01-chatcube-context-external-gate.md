# ChatCube Context External Gate Plan

## Objective

Validate RC `80431d1` on a previously unused ArkTS project before any further
retrieval or ranking change. The gate evaluates Context supply only. It does not
claim Agent diagnosis quality and does not authorize tuning from a consumed
result.

## Source Isolation

- Repository: `LongLiveY96/chatcube`
- License: MIT
- Repository is not a fork and was not present in existing development,
  calibration, performance, or holdout sources.
- The five cases were selected after RC freeze from real Git fixes.
- Every case uses its pre-fix revision; after revision, commit message, and
  Oracle remain hidden from the evaluated Runtime query.
- No Context command may run before the reviewed pack is sealed.

## Reviewed Portfolio

1. Hosted-search insertion splits an unfinished reasoning part.
2. Long-screenshot stitching swaps red and blue channels.
3. Provider backup metadata omits local icon resources.
4. A rapid settings-sheet open is immediately dismissed.
5. Consecutive image sends reuse attachment payloads across request history.

Together the cases cover file, callable, and expression localization across
page, component, viewmodel, service, store, and adapter roles. Mechanisms cover
UI state, event binding, navigation, platform API boundaries, resource I/O,
async control, persistence, and error contracts.

## Execution Protocol

1. Freeze current implementation as RC `80431d1`.
2. Clone complete source history and verify every before/after revision.
3. Review each diff and pre-fix source range without running Context.
4. Create and seal the five-case Holdout pack.
5. Execute `eval-context-capability` exactly once against the sealed pack.
6. Record the immutable result without changing the pack, Oracle, task wording,
   ranking, thresholds, or Runtime implementation.
7. Continue to Agent A/B only if `system_context_gate=pass` and promotion policy
   names paired Agent A/B as the next gate.

## Failure Handling

- A failed sealed case becomes an immutable observation.
- Do not rerun, edit, or tune from the consumed pack.
- Reproduce any candidate, callable, range, projection, compactness, or
  abstention failure in at least two independent editable development fixtures
  before considering an architecture change.
- If the failing layer cannot be identified, record the gap and stop.

## Agent A/B Boundary

If the Context gate passes, first run one paired smoke with the actual target
Agent CLI. Full source excerpts require an explicit trusted-source delivery
mode; excerpt bodies remain non-persistent and benchmark artifacts retain only
paths, aggregate telemetry, and structured outcomes. Expand to three cases and
three trials only after the smoke passes both quality and efficiency gates.

## Completed Outcome

- RC `80431d1` was evaluated without a serving-code change.
- The five-case pack was sealed with digest
  `6db8be056b5ec2f22e9ba5df3c25d99ab0d142bb7d3769723c6fda49cc194ceb`.
- One complete Context run was executed on 2026-08-01. The gate failed `0/5`;
  calibration passed, compactness passed, and promotion remained ineligible.
- Candidate-file recall at 20 was `0.8`, but final anchor recall was `0.2`,
  callable recall was `0.2`, and required source-span recall was `0.0`.
- Agent A/B was not executed because its prerequisite failed.
- The consumed pack and result are immutable. Follow-up is limited to independent
  development reproductions and a future new external holdout.

See `docs/eval/chatcube-context-external-holdout-report.md` for the evidence
boundary and `docs/eval/chatcube-context-external-holdout-result.json` for the
complete observation.
