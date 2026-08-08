# Product-Faithful Selective Query Skill Evaluation v3

## Decision

External Agent evaluation now supports two explicit treatment modes:

- `preloaded-context`: the v2 experiment that isolates the value of one fixed Context
  payload.
- `selective-query-skill`: the v3 experiment that measures the product workflow in
  which the Agent decides whether, when, and how often to invoke the existing
  `agent-memory-query` Skill.

v3 is an evaluation adapter behind `tools/agent_memory.py`; it does not add a fifth
Skill, a new Runtime entry point, or Runtime diagnosis behavior.

## Problem

v2 answers a narrow causal question: does a fixed preloaded Context projection improve
the same investigation? It does not reproduce normal Agent CLI use because:

1. the Runner chooses the query before the Agent sees the task;
2. every Memory sample pays for Context, including tasks solvable directly from source;
3. the Agent cannot refine a query after inspecting source;
4. activation, routing, and retrieval losses are collapsed into one payload outcome.

Replacing v2 would destroy a useful controlled experiment. v3 therefore adds a second,
product-faithful question instead of changing the meaning of historical v2 evidence.

## Contract

### Arms

| Property | Baseline | Memory |
|---|---|---|
| Frozen source workspace | yes | yes |
| Investigation prompt and limits | same | same |
| Preloaded Memory payload | none | none |
| Query Skill installed | no | yes |
| Maximum Skill calls | 0 | 3, further bounded per case |
| Oracle visible to Runner or Agent | no | no |

The Memory arm receives the repository's real `skills/agent-memory-query` Skill in an
isolated temporary `HOME`. Its benchmark binding points only to the frozen workspace and
isolated Memory Home. Baseline has no Memory Skill or `memory_access` request field.

### Source integrity

Codex requires `workspace-write` so the Skill can run through its normal tool path.
The Runner hashes repository-owned workspace files before and after each Agent call and
rejects any mutation. `.git` and the generated `.agent-memory-benchmark` directory are
excluded from this source digest.

### Selective levels

Cases may preregister hidden `oracle.query_skill_expectation` metadata:

```json
{
  "activation": "required | forbidden | optional",
  "max_queries": 0
}
```

- L0: a direct named source owner should not activate Memory.
- L1: one focused lookup should recover a log owner or relevant context.
- L2: at most two focused lookups may separate competing candidates.

The field is hidden from the public case and Agent. Unknown activation values or query
budgets outside `0..3` fail case validation rather than silently becoming optional.

## Measurement

`agent-benchmark-treatment/v3` records:

- treatment mode and shared investigation-contract digest;
- whether the query Skill was available and its stable contract digest;
- query limit and absence of preloaded Context;
- measured query count, success/error counts, output bytes, estimated output tokens;
- command kinds, SHA-256 query digests, returned anchor paths and primary anchor paths.

Raw query text, command text, tool output, source content, and model reasoning are never
persisted. The protocol rejects response fields that attempt to include raw query terms
or outputs.

End-to-end latency and token cost include Agent-selected Memory calls. Per-query maximum
Context remains bounded by 1,500 estimated tokens. Zero Context tokens are valid only
when the measured query count is zero.

## First Observable Loss

v3 reports the earliest contract failure it can directly observe:

1. `treatment_isolation`
2. `telemetry_accounting`
3. `query_budget`
4. `skill_execution`
5. `skill_activation`
6. `selective_routing`
7. `context_retrieval`

This taxonomy does not infer hidden model reasoning. A downstream wrong answer does not
prove that activation or retrieval failed, and v3 does not claim ownership of general
Agent diagnosis quality.

## Calibration

The repository contains three generated ArkTS protocol cases and six deterministic
observations:

- `docs/eval/selective-query-skill-v3-calibration-cases.json`
- `docs/eval/selective-query-skill-v3-calibration-responses.json`
- `docs/eval/selective-query-skill-v3-calibration-result.json`

They verify L0/L1/L2 activation, isolation, accounting, privacy, routing and replay. They
are generated protocol calibration, contain no real incident evidence, use no model and
cannot support a capability, efficiency, generalization, or promotion claim.

## Execution

```bash
python tools/agent_memory.py eval-agent-benchmark \
  --project . \
  --cases /path/to/validated-cases.json \
  --source /path/to/frozen-source \
  --runner examples/codex-agent-benchmark-runner.py \
  --treatment-mode selective-query-skill \
  --trials 3 \
  --json
```

Recorded observations can be replayed with the same `--treatment-mode`. The mode is also
detected from `agent-benchmark-treatment/v3` metadata so stored results remain auditable.

## Promotion path

1. Keep v2 results under their original fixed-payload interpretation.
2. Use generated calibration only to validate the v3 instrument.
3. Preregister a new, unconsumed Development campaign with real symptom provenance,
   hidden activation expectations, mechanism assertions, balanced order and full cost
   telemetry.
4. Diagnose failures by the first observable loss; do not change Runtime serving from
   an evaluation-only defect.
5. Require an independent Development reproduction in actual `query_handoff` before any
   serving change.
6. Use one new sealed source family only after Context and v3 Development gates pass.

## Acceptance status

- [x] v2 remains the default and historical replay is unchanged.
- [x] v3 uses the real query Skill in an isolated Agent home.
- [x] Baseline has no Memory access and neither arm receives preloaded Context.
- [x] Agent-selected calls are capped, measured and included in end-to-end cost.
- [x] Raw query text and output are absent from persisted telemetry.
- [x] Generated L0/L1/L2 calibration passes the v3 protocol gate.
- [x] Public CLI, fake Codex Runner and source-immutability paths have regression tests.
- [ ] Real external Agent capability and efficiency remain unproven pending a new
  preregistered Development campaign.

## References

- SWE-bench: <https://arxiv.org/abs/2310.06770>
- ReAct: <https://arxiv.org/abs/2210.03629>
- Toolformer: <https://arxiv.org/abs/2302.04761>
- TREC evaluation guidance: <https://trec.nist.gov/howto.html>
- Repository policy: `docs/evaluation-and-change-policy.md`
- v2 contract: `docs/superpowers/plans/2026-08-03-agent-ab-measurement-contract-v2.md`
