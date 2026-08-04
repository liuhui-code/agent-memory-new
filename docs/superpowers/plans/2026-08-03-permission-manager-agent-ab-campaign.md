# Permission Manager ArkTS Agent A/B Campaign

## Goal

Run one preregistered, one-shot external Context gate on the previously unused
OpenHarmony Permission Manager source family. Only a passing gate may start the fixed
paired Agent A/B. The campaign measures whether compact Runtime context helps the same
local Agent diagnose frozen pre-fix source with less search, lower cost, or better
Oracle alignment.

## Frozen Campaign Definition

- Source repository: `https://github.com/openharmony/applications_permission_manager`.
- Local source: `/private/tmp/agent-memory-ab-permission-manager`.
- Source revision at acquisition: `9fd6f1e3a65b342d12b9dc04b7d9492d5d5bfb63`.
- Case pack: `docs/eval/permission-manager-agent-ab-cases.json`.
- Case count: exactly 10 in the order below; no `--limit` or `--case-id`.
- Context attempts: exactly one after sealing.
- Agent runner: `examples/codex-agent-benchmark-runner.py`.
- Agent model: `gpt-5.5`; reasoning effort: `low`.
- Trials: exactly three paired source-only/Context trials per case.
- Runner timeout: 900 seconds per Agent call.
- Source boundary: read-only temporary checkouts of each pre-fix revision with no Git
  metadata available to the Agent.
- Context delivery: Runner-preloaded compact Context; hidden Oracle, post-fix source,
  commit subject, and source bodies outside the checkout are excluded.

Fixed case order:

1. `permission-app-label-await`
2. `permission-dialog-cancel-result`
3. `permission-wearable-swipe-cleanup`
4. `permission-global-switch-result-contract`
5. `permission-toast-api-exception-boundary`
6. `permission-toast-font-range-fallback`
7. `permission-precise-location-grant-revoke`
8. `permission-wearable-isolated-page-guard`
9. `permission-floating-session-content-cleanup`
10. `permission-language-refresh-clone-label`

## Method

The campaign follows staged ranking and paired controlled evaluation rather than
tuning on a consumed external set:

1. Audit every declared parent/fix revision and changed path from the local clone.
2. Seal the complete reviewed case pack once and record its SHA-256 digest.
3. Reserve and consume one Context capability run through the append-only SQLite
   evaluation ledger.
4. Require all ten cases to satisfy anchor, source excerpt, precision, and compact
   Token-budget checks.
5. Stop with zero Agent calls if the Context predecessor is ineligible.
6. Otherwise run all 60 fixed Agent calls: 10 cases x 2 variants x 3 paired trials.
7. Compare deterministic file/category/causal scores, exploration telemetry, input and
   output Tokens, elapsed time, and trial stability. Do not use an LLM judge.

Relevant foundations are late-interaction retrieval and staged ranking
([ColBERTv2](https://aclanthology.org/2022.naacl-main.272/),
[Vespa phased ranking](https://docs.vespa.ai/en/phased-ranking.html)), bounded diversity
([MMR](https://doi.org/10.1145/290941.291025)), and position-aware evidence delivery
([Lost in the Middle](https://arxiv.org/abs/2307.03172)). These sources motivate the
generic Runtime architecture; they do not validate any case Oracle or campaign result.

## Stop Rules

- A seal, revision audit, Context, Runner, ledger, or response-protocol failure consumes
  that classified attempt and stops its successor stage.
- Never edit, regenerate, tune on, or rerun the consumed sealed pack.
- Never retry failed Agent calls or select favorable trials.
- This source family yields one external observation, not ten independent projects.
- A failed case may form a hypothesis only. Production behavior changes require an
  independent development reproduction and an actual `query_handoff` defect.
- The Runtime supplies evidence context only; the Agent owns diagnosis and verification.

## Status

- Source acquisition: complete.
- Commit and diff review: complete.
- Campaign and case order preregistered: complete.
- Seal: complete; digest
  `bc330f138584991aa230d53f026505b52a0c8b5b1ffe70d2d17bbf918333d9ce`.
- Context gate: completed exactly once and failed at 2/10. Candidate-file recall@20 is
  0.95, hierarchical file recall is 0.5333, final anchor and source excerpt recall are
  0.35, anchor precision is 0.2333, MRR is 0.5, and average Context is 1,466.5 tokens.
- Agent A/B: not executed. The Context predecessor is ineligible and the ledger has no
  `agent_benchmark` row for this seal, so Agent call count is zero.
- Governance conclusion: the seal is consumed and immutable. Six cases first lose an
  expected file at `localizer_file`, one at `candidate_file`, and three reach the
  primary-evidence boundary before compact projection. These are external hypotheses,
  not tuning evidence; any repair requires independent development reproductions.
