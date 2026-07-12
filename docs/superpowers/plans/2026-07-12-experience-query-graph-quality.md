# Experience Query Graph Quality Implementation Plan

> **For agentic workers:** execute this plan in small verified slices. Keep the four user-facing skills unchanged.

**Goal:** Improve experience quality, query quality, and code/log graph quality without adding a new database engine or user-facing skill.

**Architecture:** Reuse existing reflection fields, query gating, calibration, quality scoring, graph quality, and graph signal quality. Add deterministic derived profiles and scorecards that are cheap to compute and explainable to the Agent.

**Scope:**
- No new tables.
- No vector database.
- No raw runtime log persistence.
- No fifth skill.

## Phase 1: Experience Evidence Profile

Files:
- `tools/agent_memory_runtime/quality_scoring.py`
- `tools/agent_memory_runtime/memory_calibration.py`
- `tools/agent_memory_runtime/query.py`
- `tests/test_memory_calibration.py`

Tasks:
- Add a deterministic `experience_evidence_profile(row)` helper.
- Include claim, evidence, applicability, counter-evidence, verification, and source-case status.
- Attach the profile to reflection quality payloads.
- Expose the profile through calibrated query rows and retrieval explanations.
- Add tests that verified experience rows include the profile and missing counter-evidence is visible.

## Phase 2: Intent-Aware Query Interference Control

Files:
- `tools/agent_memory_runtime/query.py`
- `tests/test_experience_query_quality.py`
- `docs/runtime.md`
- `skills/agent-memory-query/SKILL.md`

Tasks:
- Add `query_intent_profile(query)` with preferred evidence lanes.
- Add intent-aware penalties for reflections that do not match the query's primary evidence need.
- Keep correction and semantic patch experiences in guardrail lanes unless the query asks for them.
- Add `intent_alignment`, `interference_penalty`, and `interference_reasons` to reflection rows.
- Include the intent profile in `retrieval_lanes`.
- Add a regression test where a code-current query does not let broad procedure experience outrank source-like evidence.

## Phase 3: Code/Log Coverage Scorecard

Files:
- `tools/agent_memory_runtime/graph_quality.py`
- `tools/agent_memory_runtime/governance.py`
- `tests/test_quality_performance_scoring.py`
- `docs/runtime.md`
- `skills/agent-memory-maintain/SKILL.md`

Tasks:
- Add a compact `coverage_scorecard` to `graph_signal_quality`.
- Score business semantic coverage and log diagnostic coverage separately.
- Include missing file/symbol/log business coverage and weak log signal counts.
- Return a combined `coverage_score` and status.
- Add maintain-health and maintain-plan consumers through the existing graph signal quality payload.
- Add tests that weak learned symbols/logs produce a watch/poor scorecard and concrete repair targets.

## Verification

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_memory_calibration tests.test_experience_query_quality tests.test_quality_performance_scoring
PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory_runtime/query.py tools/agent_memory_runtime/quality_scoring.py tools/agent_memory_runtime/memory_calibration.py tools/agent_memory_runtime/graph_quality.py tools/agent_memory_runtime/governance.py
git diff --check
ls -1 skills
```

Expected:
- Tests pass.
- Compile succeeds.
- Diff check succeeds.
- Official skill list remains exactly four skills.

## Follow-Up: Retrieval Quality Gate Coverage

Add query-quality regression hooks to the existing retrieval eval instead of creating a new command:

- Optional `expected_memory_intent` verifies the query router.
- Optional `required_preferred_lanes` verifies the intent profile exposes the expected evidence lanes.
- Optional `max_blocked_memory_notes` verifies broad or weak memories stay bounded.

This keeps the new experience/query/graph quality work inside the existing `eval-retrieval` and `eval-quality --gate retrieval` path.

## Follow-Up: Graph Signal Quality Gate

Add `eval-graph-signal` for code/log graph coverage regression:

- Evaluate `graph_signal_quality.coverage_scorecard`.
- Check `min_coverage_score`, `allowed_coverage_statuses`, `max_repair_targets`, and `required_repair_targets`.
- Register `graph_signal` inside `eval-quality`.

This keeps graph/log quality measurable without storing raw logs or adding a new user-facing skill.

## Follow-Up: Experience Evidence Quality Gate

Add `eval-experience-evidence` for reflection evidence-profile regression:

- Match active reflections by id or text.
- Evaluate the derived `experience_evidence_profile` directly from stored fields.
- Check `min_profile_score`, `expected_verification_status`, and `required_true`.
- Register `experience_evidence` inside `eval-quality`.

This makes experience recording quality measurable independently of query ranking.

## Follow-Up: Quality Gate Registry

Add `eval-quality --list-gates` for low-cost discovery:

- Return all gate names, case files, direct commands, and aggregate rerun commands.
- Do not execute cases.
- Do not write `runtime/last_quality_gate.json`.

This helps Agents and scripts choose the correct `--gate` after the registry grows.
