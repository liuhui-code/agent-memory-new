# Agent A/B Measurement Calibration Campaign

## Objective

Calibrate the paired Agent A/B measurement chain before another external holdout.
The campaign separates three questions that previous gates conflated:

1. Does the deterministic scorer order controlled answers correctly?
2. Does Runtime Context retrieve the evidence required by a known case?
3. Does that Context improve a fixed local Agent over source-only diagnosis?

Runtime remains an evidence provider. The Codex runner remains responsible for
diagnosis, causal synthesis, and the final answer.

## Frozen Protocol

- Split: repeatable Development; this is not a holdout or promotion gate.
- Cases: one construct-known Mutation and two reviewed real Git fixes from two
  projects.
- Agent: `codex-cli 0.142.0`, one fixed model and reasoning setting recorded by
  the runner.
- Trials: three paired trials per case, 18 independent Agent calls total.
- Variants: source-only Baseline versus source plus Runtime Context.
- Order: `alternating_case_trial_parity/v1`. The Youtube pack has 1-based case
  positions 1 and 2; the Dimina pack has position 1. Across all nine pairs this yields five
  Baseline-first and four Memory-first pairs.
- Isolation: every observation gets a fresh frozen Git workspace. Different
  repositories are never combined in one workspace.
- Leakage: Oracle, after revision, fix message, and mutation original are hidden
  from the runner.
- Raw source and private reasoning are not persisted. Only structured answers,
  file names, aggregate tool telemetry, and model token counts are retained.

## Preregistered Cases

| Case | Evidence class | Frozen revision | Expected owner |
|---|---|---|---|
| `mutation-e94b869b178b` | construct-known route mutation | `f925981b8a5c4483be371bfd672722526b4986cf` | `entry/src/main/ets/component/Album.ets` |
| `youtube-media-page-array-merge` | reviewed real Git fix | `6e6cd7681688eb3bedaf0fd7833c166554ede8b6` | `entry/src/main/ets/component/MediaComponent.ets` |
| `dimina-harmony-tabbar-height` | reviewed real Git fix | `f162f4737d154261f1b0363ec3a050952170865b` | `harmony/dimina/src/main/ets/Components/DMPTabBar.ets` |

The Mutation calibrates protocol behavior only. It must never be reported as
real-incident accuracy. The two real fixes have commit-level before/after
evidence; neither has a dedicated regression test, so conclusions remain
Development evidence rather than external validity claims.

## Decision Matrix

Interpret Context capability and Agent uplift independently:

| Context gate | Agent uplift | Interpretation |
|---|---|---|
| pass | positive | preliminary support that useful evidence improves the Agent |
| pass | zero/negative | Context interference, presentation, or stopping-policy defect |
| fail | positive | Context gate may be stricter than actual Agent utility |
| fail | zero/negative | retrieval supply is the leading measured deficiency |

No serving-path change is justified by this campaign alone. A production change
requires reproduction in independent Development fixtures for at least two
defect classes under `docs/evaluation-and-change-policy.md`.

## Execution And Stop Rules

1. Validate JSON, revisions, source digests, and scorer calibration tests.
2. Run `eval-context-capability` for each source pack and retain both results.
3. Run exactly three paired trials for every case with the fixed Codex runner.
4. Stop on protocol errors, source checkout failure, model identity drift,
   incomplete pairs, or execution-order audit failure. Do not select best trials.
5. Re-score only from the recorded response bundles; do not rerun calls to tune
   the evaluator.
6. Publish per-provenance results and the two-dimensional matrix conclusion,
   including negative or inconclusive findings.

## Verification

- Focused A/B protocol and scoring tests.
- Full Python unit suite.
- JSON parse check for every new pack and result.
- Four-Skill invariant and runtime-entry check.
- Python compile check and repository-wide 500-line source limit.
- Existing query performance and million-row scale gates; this campaign must not
  regress the serving path.

## Completion

The campaign completed on 2026-08-03. The authoritative matrix and governance
decision are recorded in `docs/eval/agent-ab-measurement-calibration-report.md`;
the machine-readable aggregate is
`docs/eval/agent-ab-measurement-calibration-summary.json`.
