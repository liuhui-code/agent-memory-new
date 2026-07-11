# Calibration Feedback Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make memory trust labels respond to targeted positive and negative calibration feedback.

**Architecture:** Extend existing retrieval feedback reason codes and query-time feedback collection. Feed calibration bonus/penalty fields into `memory_calibration.py`, and emit dedicated maintain-plan review actions for overtrusted and undertrusted records.

**Tech Stack:** Python 3.9, SQLite, unittest.

---

### Task 1: Feedback Reason Expansion

**Files:**
- Modify: `tools/agent_memory_runtime/retrieval_feedback.py`
- Test: `tests/test_calibration_feedback.py`

- [ ] Add failing tests for `verified_useful` feedback raising trust and `overtrusted` feedback lowering trust.
- [ ] Extend feedback reason validation.
- [ ] Add calibration feedback collection fields.

### Task 2: Trust Integration

**Files:**
- Modify: `tools/agent_memory_runtime/query.py`
- Modify: `tools/agent_memory_runtime/memory_calibration.py`
- Test: `tests/test_calibration_feedback.py`

- [ ] Apply calibration feedback to semantic facts and reflections before calibration.
- [ ] Update trust scoring to use bonus/penalty fields.
- [ ] Verify context output exposes calibration feedback fields.

### Task 3: Maintain Governance

**Files:**
- Modify: `tools/agent_memory_runtime/governance.py`
- Modify: `docs/runtime.md`
- Modify: `docs/usage-guide.md`
- Modify: `skills/agent-memory-query/SKILL.md`
- Modify: `gitlog.md`

- [ ] Add `review_overtrusted_memory` and `review_undertrusted_memory` actions.
- [ ] Document the feedback loop.
- [ ] Run regression tests, py_compile, and diff check.
