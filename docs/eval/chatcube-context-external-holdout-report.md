# ChatCube Context External Holdout Report

## Classification

- Source: `LongLiveY96/chatcube` (MIT, non-fork, previously unused by this repository)
- Frozen RC: `80431d1`
- Evaluation: classified external holdout, case-explicit lineage, sealed change policy
- Case count: 5 real pre-fix revisions selected from reviewed Git fixes
- Seal digest: `6db8be056b5ec2f22e9ba5df3c25d99ab0d142bb7d3769723c6fda49cc194ceb`
- Sealed file SHA-256: `207a619d052da40f689e409c7a28e44f842bb582ed54442fca7258cea3a6f5a4`
- Result file SHA-256: `18c2759aae48e3364c78baeb026b7a30c6301e35f4bcb6682bc83f95b1a71a09`
- Execution: exactly one complete `eval-context-capability` run; no case filters or limits

The sealed pack is consumed. It must not be edited, rerun, or used for tuning.

## Result

The formal Context gate failed `0/5`; calibration passed and promotion is not
eligible. Agent A/B was not started because the predeclared Context prerequisite
failed.

| Capability | Result |
| --- | ---: |
| Candidate-file recall at 20 | 0.8 |
| Hierarchical file recall | 0.7 |
| Callable recall | 0.2 |
| Range recall | 0.2 |
| Final anchor recall | 0.2 |
| Final anchor precision | 0.0667 |
| Source excerpt recall | 0.2 |
| Required source-span recall | 0.0 |
| Average compact Context | 1,431.4 / 1,500 estimated tokens |

The first observable loss was `callable` in two cases, `localizer_file` in two,
and `candidate_file` in one. Four cases placed at least one expected file in the
top-20 candidate pool, but only the screenshot case preserved its target callable
and range through hierarchical localization. That case still failed because the
compact result retained three anchors (precision `0.3333`) and its returned excerpt
did not cover the required source lines.

## Interpretation

Proved:

- The RC can build isolated indexes for all five real pre-fix snapshots and return
  compact Context within budget.
- Candidate generation is not the only bottleneck. File localization, callable
  localization, ranking precision, and query-focused source-window selection all
  lose evidence before the final Agent-visible handoff.
- The current RC does not meet its external Context supply contract on this source.

Not proved:

- The holdout does not identify a single implementation defect or authorize a
  ranking, threshold, parser, graph, or compact-projection change.
- It does not measure Agent diagnosis quality because Agent A/B was correctly skipped.
- Informational funnel and evidence-set outputs are hypotheses, not promotion evidence.

## Stop Decision

No serving code is changed from this result. Any follow-up must reproduce a public
`query_handoff` failure in independent editable development fixtures. Architecture
work additionally requires at least two independent defect classes to demonstrate
the same missing contract. A future promotion claim requires a newly selected and
newly sealed external source.
