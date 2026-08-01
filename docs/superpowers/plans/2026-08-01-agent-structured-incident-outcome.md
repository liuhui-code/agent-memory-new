# Agent-Structured Incident Outcome Convergence Plan

**Status:** Implemented

**Goal:** Converge Incident memory on a durable evidence contract: the local
Agent CLI analyzes temporary logs and current source; Runtime stores and serves
only a bounded, attributable diagnosis outcome.

## Problem

The original `incident-trace` path accepted raw log text or files and derived
events, paths, and root-cause candidates inside Runtime. That conflicts with the
project boundary in `docs/context-provider-boundary.md` and
`docs/evaluation-and-change-policy.md`:

- temporary user logs are not project memory;
- static graph reachability is not observed runtime causality;
- Runtime supplies evidence context while the local Agent owns diagnosis;
- historical artifacts must not silently gain authority after a contract change.

The defect is architectural rather than a ranking issue: it affects both data
ownership and causal authority. A serving filter alone would leave the write
path wrong; a parser removal alone would leave legacy rows trusted.

## Target Contract

```text
temporary logs + user symptom
  -> Agent CLI reads and analyzes locally
  -> context --compact supplies code/log/experience/path evidence
  -> Agent compares alternatives against current source and log order
  -> Agent verifies intervention and outcome
  -> incident-trace accepts structured fields only
  -> SQLite stores attributable outcome + current-index anchors
  -> Context serves sanitized Agent-structured records
  -> Maintain reviews closure, legacy quarantine, or reflection promotion
```

The four user-facing Skills remain fixed. `tools/agent_memory.py` remains the
only Runtime entry point. No daemon, vector database, or graph database is
introduced.

## Data Contract

Every new Incident uses `schema_version=agent-incident-record/v2` and:

- `capture_mode=agent_structured`;
- `symptom`, `arkts_scene`, and required `diagnosis_summary`;
- bounded `observed_events` supplied by the Agent;
- bounded `agent_causal_steps` supplied by the Agent;
- explicit `code_anchor` values resolved against the current learned index;
- optional `resolution`, `intervention`, and `verification_evidence`;
- no raw log text, Runtime-generated span graph, inferred root cause, or
  Runtime-generated causal chain.

Evidence states are monotonic in authority, not necessarily in time:

| State | Required evidence | Maximum confidence |
|---|---|---:|
| `legacy_unverified` | old Runtime-derived row | 0.25 |
| `reported` | Agent report without a current resolved anchor | 0.45 |
| `supported` | Agent report with a current resolved anchor | 0.70 |
| `verified` | anchor + resolution + intervention + verification | 0.95 |

Status and evidence state are independent. `resolved` without causal closure is
not `verified`.

## Serving And Governance

1. Context and FTS select only `capture_mode=agent_structured`.
2. Query output removes legacy raw, inferred-root-cause, span, and
   Runtime-generated causal fields.
3. Maintain may promote only a resolved `verified` record with a current anchor.
4. `reported` and `supported` records receive a completion action.
5. Legacy rows receive `review_legacy_incident_trace` and cannot be promoted.
6. Existing legacy data is quarantined rather than destructively deleted; a
   separate reviewed migration may redact or archive it later.

## Implementation Phases

- [x] Define migration columns, evidence states, and confidence caps.
- [x] Replace raw-log CLI arguments with structured Agent fields.
- [x] Resolve Agent code anchors against current files and symbols.
- [x] Remove Runtime event/path/root-cause generation from Incident writes.
- [x] Filter and sanitize Incident serving results.
- [x] Gate quality scoring and Maintain promotion on evidence state.
- [x] Quarantine legacy rows and expose a review action.
- [x] Update Vault mirror, Runtime docs, usage guide, and fixed Skills.
- [x] Add focused migration, boundary, query, governance, and Vault tests.

## Verification

- Focused Incident tests cover structured writes, raw-argument rejection,
  unresolved anchors, verified closure, sanitized query output, legacy
  quarantine, Maintain promotion, and Vault projection.
- Semantic, causal-boundary, log-signal, OTel-lite, quality, and evidence-fabric
  tests verify that evaluation-only log parsing remains available while no
  production Incident path reads temporary logs.
- The full suite passes 801 non-socket tests; all three Ollama runner tests pass
  separately with local loopback binding enabled.
- All changed Python files remain below 500 lines.

## Stop Conditions

- Do not reintroduce Runtime diagnosis under a different command name.
- Do not infer `verified` from status, confidence, recurrence, or static graph
  reachability.
- Do not delete quarantined legacy rows without an explicit reviewed retention
  policy.
- Do not evolve the fixed four-Skill user interface for this storage contract.
