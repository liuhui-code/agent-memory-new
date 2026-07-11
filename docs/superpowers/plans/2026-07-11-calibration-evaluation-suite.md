# Calibration Evaluation Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local golden-case evaluator for trust calibration behavior so query trust changes can be regression-tested.

**Architecture:** Create a read-only `calibration_eval.py` module mirroring `retrieval_eval.py`. It loads JSON cases, runs the normal `limited_context` path, checks expected trust levels/score bounds and forbidden trust levels, then reports pass/fail summary metrics. Wire it through `tools/agent_memory.py` and the existing CLI parser.

**Tech Stack:** Python 3.9, JSON golden cases, SQLite-backed runtime, unittest.

---

### Task 1: Eval Module and CLI

**Files:**
- Create: `tools/agent_memory_runtime/calibration_eval.py`
- Modify: `tools/agent_memory.py`
- Modify: `tools/agent_memory_runtime/cli.py`
- Test: `tests/test_calibration_eval.py`

- [ ] Write failing tests for `eval-calibration --cases <file> --json`.
- [ ] Implement JSON case loading and per-case context evaluation.
- [ ] Add CLI parser and runtime command import.
- [ ] Run focused tests until green.

### Task 2: Trust Case Semantics

**Files:**
- Modify: `tools/agent_memory_runtime/calibration_eval.py`
- Test: `tests/test_calibration_eval.py`

- [ ] Support `expected_trust` specs with `type`, `id`, `trust_level`, `min_trust_score`, and optional text/field matching.
- [ ] Support `must_not_trust` specs to catch over-trusted weak/stale/conflict records.
- [ ] Report `expected_trust_rate`, `blocked_overtrust_rate`, missed specs, and unexpected trusted specs.

### Task 3: Docs and Verification

**Files:**
- Modify: `docs/runtime.md`
- Modify: `docs/usage-guide.md`
- Modify: `skills/agent-memory-query/SKILL.md`
- Modify: `gitlog.md`

- [ ] Document the eval command and case shape.
- [ ] Run focused tests, query-related regression tests, full runtime regression, py_compile, and diff check.
- [ ] Commit the completed stage.
