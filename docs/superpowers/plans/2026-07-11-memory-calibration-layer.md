# Memory Calibration Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add trust-level and retrieval-explanation annotations to memory query results so Agents can safely decide how much to rely on each record.

**Architecture:** A new `memory_calibration.py` module computes advisory annotations from existing query result fields. Query assembly calls the module after ranking/gating and before returning JSON. Skills and docs explain how to consume the annotations.

**Tech Stack:** Python 3.9, SQLite-backed existing runtime, unittest.

---

### Task 1: Calibration Model

**Files:**
- Create: `tools/agent_memory_runtime/memory_calibration.py`
- Test: `tests/test_memory_calibration.py`

- [ ] Write tests for semantic facts, verified reflections, weak hints, stale records, and retrieval explanations.
- [ ] Run the focused tests and verify they fail because the module is missing.
- [ ] Implement `calibrate_record`, `calibrate_result_group`, and `memory_use_policy`.
- [ ] Run the focused tests and verify they pass.

### Task 2: Query Integration

**Files:**
- Modify: `tools/agent_memory_runtime/query.py`
- Test: `tests/test_memory_calibration.py`

- [ ] Add a CLI-level test that `context --json` returns `memory_use_policy` and annotated result rows.
- [ ] Run the test and verify it fails before query integration.
- [ ] Annotate context and search payloads after gating/limiting.
- [ ] Run the focused tests and verify they pass.

### Task 3: Skill and Docs

**Files:**
- Modify: `skills/agent-memory-query/SKILL.md`
- Modify: `docs/runtime.md`
- Modify: `docs/usage-guide.md`
- Modify: `gitlog.md`

- [ ] Document trust levels and answer-time memory policy.
- [ ] Run regression tests, py_compile, and diff check.
- [ ] Commit the completed stage.
