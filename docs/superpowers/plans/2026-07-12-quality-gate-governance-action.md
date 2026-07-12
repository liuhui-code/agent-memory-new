# Quality Gate Governance Action Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn a failed latest `eval-quality` snapshot into a first-class `maintain-plan` review action.

**Architecture:** Reuse `runtime/last_quality_gate.json` and keep it runtime-only. Add a small action builder beside the quality-gate snapshot helpers, then let `maintain-plan` include the action in normal governance budgeting and lane filtering.

**Tech Stack:** Python 3.9+, JSON runtime snapshots, existing maintain-plan/action-budget pipeline, unittest.

---

## Tasks

### Task 1: Test Maintain-Plan Action

**Files:**
- Modify: `tests/test_quality_gate_eval.py`

- [ ] Add a test that runs a failing `eval-quality`, then runs `maintain-plan --json`, and asserts:
  - `review_quality_gate_failure` appears in `actions`
  - action lane is `quality_gate`
  - action includes `failed_gate_names`
  - action includes the failed gate's `next_command_templates`
  - `governance_summary.quality_gate_failure_reviews == 1`

### Task 2: Action Builder

**Files:**
- Modify: `tools/agent_memory_runtime/quality_gate_eval.py`

- [ ] Add `build_quality_gate_failure_actions(snapshot)`.
- [ ] Return no actions unless `snapshot.quality_gate == "fail"`.
- [ ] Include:
  - `action: review_quality_gate_failure`
  - `governance_lane: quality_gate`
  - `type: quality_gate`
  - `risk: medium`
  - `requires_confirmation: False`
  - `failed_gate_names`
  - `next_command_templates`
  - compact snapshot

### Task 3: Maintain-Plan Integration

**Files:**
- Modify: `tools/agent_memory_runtime/governance.py`
- Modify: `tools/agent_memory_runtime/governance_action_budget.py`

- [ ] Import `build_quality_gate_failure_actions`.
- [ ] Load the latest quality snapshot once in `maintain_plan`.
- [ ] Extend actions with quality gate failure actions.
- [ ] Add `quality_gate_failure_reviews` to `governance_summary`.
- [ ] Include `last_quality_gate` in full maintain-plan output.
- [ ] Add lane/action priority weights for `quality_gate` and `review_quality_gate_failure`.
- [ ] Add `quality_gate` to `infer_governance_lane`.
- [ ] Include `last_quality_gate_status` in compact `health_overview`.

### Task 4: Docs And Verification

**Files:**
- Modify: `docs/runtime.md`
- Modify: `docs/usage-guide.md`
- Modify: `skills/agent-memory-maintain/SKILL.md`
- Modify: `gitlog.md`

- [ ] Document `review_quality_gate_failure`.
- [ ] Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_gate_eval tests.test_eval_case_seed
PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory_runtime/quality_gate_eval.py tools/agent_memory_runtime/governance.py tools/agent_memory_runtime/governance_action_budget.py
git diff --check
ls -1 skills
```

Expected: tests pass, compile exits 0, diff check exits 0, and the official skill list remains four skills.

Commit:

```bash
git add docs/runtime.md docs/usage-guide.md gitlog.md skills/agent-memory-maintain/SKILL.md tools/agent_memory_runtime/quality_gate_eval.py tools/agent_memory_runtime/governance.py tools/agent_memory_runtime/governance_action_budget.py tests/test_quality_gate_eval.py docs/superpowers/plans/2026-07-12-quality-gate-governance-action.md
git commit -m "Add quality gate governance action"
git push
```

## Self-Review

- Spec coverage: action creation, maintain-plan integration, prioritization, docs, tests, and verification are covered.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: action fields match existing governance action conventions.
