# Agent A/B Measurement Contract v2

## Goal

Make Context the only treatment variable in external Agent A/B evaluation, account for
end-to-end serving cost, and separate localization evidence from verified mechanism
evidence without changing Runtime serving behavior or consumed Oracles.

## Proven Defects

1. The legacy Memory arm received both Context and a stricter investigation protocol.
2. Memory retrieval completed before elapsed-time measurement started.
3. The deterministic score accepted Agent-reported causal level without mechanism proof.
4. Mutation and reviewed Git fixes were combined in the headline aggregate.
5. Pooled cost ratios could be dominated by one expensive case.

## Completed Work

- [x] Introduce `agent-benchmark-treatment/v2` with one shared investigation contract.
- [x] Give Baseline a null payload and Memory the external metadata-only projection.
- [x] Enforce exploration limits on both v2 arms.
- [x] Record treatment, Context exposure, and full protocol component digests.
- [x] Include Memory retrieval and Context assembly in end-to-end elapsed time.
- [x] Report Agent and retrieval latency as separate attribution fields.
- [x] Add optional Oracle mechanism assertions and Agent source-span evidence.
- [x] Use mechanism grounding instead of self-reported causal level when assertions exist.
- [x] Split protocol calibration from real-case evidence.
- [x] Add paired mean, median, and worst-case cost effects.
- [x] Preserve legacy response replay without upgrading its evidence claims.

## Acceptance

- Both variants contain the same investigation and runner instructions.
- v2 treatment audit fails on missing Context, Baseline Context, or contract mismatch.
- Context capability exposes both full-gate and external-Agent projection manifests.
- End-to-end latency is greater than or equal to Agent latency.
- Wrong source spans cannot receive mechanism causal credit.
- Mutation and real cases appear in separate result segments.
- Focused tests, full tests, compile, JSON, diff, four-Skill and 500-line gates pass.

## Stop Boundary

Do not rerun the consumed 18-call calibration as v2 evidence. A new Development campaign
must use symptom-only cases, an even per-case trial count, predeclared mechanism assertions,
and the v2 Runner before any new sealed holdout is consumed.
