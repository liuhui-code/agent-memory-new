# Quality Gate Delta Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lightweight previous-run comparison to `eval-quality` so agents can see whether the latest gate improved, regressed, or stayed the same.

**Architecture:** Read `runtime/last_quality_gate.json` before evaluating the current run, compute a compact delta, then save the new snapshot with that delta included. Compare only aggregate `quality_gate` and failed gate names; do not store history or write to SQLite.

**Tech Stack:** Python 3.9+, JSON runtime snapshots, existing eval-quality tests.

---

## Tasks

### Task 1: Tests

**Files:**
- Modify: `tests/test_quality_gate_eval.py`

- [ ] Add a test that runs a failing `eval-quality`, then edits the same log-signal case to pass, runs `eval-quality` again, and asserts:
  - `quality_gate == "pass"`
  - `quality_gate_delta.previous_quality_gate == "fail"`
  - `quality_gate_delta.status_change == "resolved_failure"`
  - `quality_gate_delta.resolved_failed_gates == ["log_signal"]`

### Task 2: Delta Implementation

**Files:**
- Modify: `tools/agent_memory_runtime/quality_gate_eval.py`

- [ ] Read the previous compact snapshot before evaluating.
- [ ] Add `build_quality_gate_delta(previous, current)`.
- [ ] Add `quality_gate_delta` to current output before saving.
- [ ] Keep first-run behavior explicit with `status_change: "no_previous"`.

### Task 3: Docs And Verification

**Files:**
- Modify: `docs/runtime.md`
- Modify: `docs/usage-guide.md`
- Modify: `skills/agent-memory-maintain/SKILL.md`
- Modify: `gitlog.md`

- [ ] Document `quality_gate_delta`.
- [ ] Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_gate_eval tests.test_eval_case_seed
PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory_runtime/quality_gate_eval.py
git diff --check
ls -1 skills
```

Expected: tests pass, compile exits 0, diff check exits 0, and the official skill list remains four skills.

Commit:

```bash
git add docs/runtime.md docs/usage-guide.md gitlog.md skills/agent-memory-maintain/SKILL.md tools/agent_memory_runtime/quality_gate_eval.py tests/test_quality_gate_eval.py docs/superpowers/plans/2026-07-12-quality-gate-delta.md
git commit -m "Add quality gate delta summary"
git push
```

## Self-Review

- Spec coverage: previous snapshot read, delta calculation, first-run behavior, docs, tests, and verification are covered.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: delta fields use existing `quality_gate` and `summary.failed_gate_names` names.
