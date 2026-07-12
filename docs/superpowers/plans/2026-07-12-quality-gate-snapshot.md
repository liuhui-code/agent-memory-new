# Quality Gate Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist the latest `eval-quality` result as a runtime-only snapshot and expose it through `maintain-health`.

**Architecture:** Write the aggregate quality-gate payload to `runtime/last_quality_gate.json` after each `eval-quality` run. `maintain-health` reads that disposable runtime file and surfaces a compact `last_quality_gate` block plus a recommended action when the latest gate failed. No SQLite schema, daemon, or fifth skill is added.

**Tech Stack:** Python 3.9+, JSON runtime files, existing maintain-health and unittest CLI tests.

---

## Tasks

### Task 1: Test Health Visibility

**Files:**
- Modify: `tests/test_quality_gate_eval.py`

- [ ] Add a test that runs a failing `eval-quality`, then runs `maintain-health --json`, and asserts:
  - `last_quality_gate.quality_gate == "fail"`
  - `last_quality_gate.summary.failed_gate_names == ["log_signal"]`
  - `recommended_actions` includes quality gate review guidance

### Task 2: Runtime Snapshot Helpers

**Files:**
- Modify: `tools/agent_memory_runtime/quality_gate_eval.py`
- Modify: `tools/agent_memory_runtime/governance.py`

- [ ] Add `QUALITY_GATE_SAMPLE_FILE = "last_quality_gate.json"`.
- [ ] Add `quality_gate_snapshot_path(project)`.
- [ ] Add `save_quality_gate_snapshot(project, data)`.
- [ ] Add `load_quality_gate_snapshot(project)`.
- [ ] Call `save_quality_gate_snapshot` from `eval_quality_command` after evaluating and before output.
- [ ] Import `load_quality_gate_snapshot` in governance and include `last_quality_gate` in `maintain_health`.
- [ ] Append a recommended action when `last_quality_gate.quality_gate == "fail"`.

### Task 3: Docs

**Files:**
- Modify: `docs/runtime.md`
- Modify: `docs/usage-guide.md`
- Modify: `skills/agent-memory-maintain/SKILL.md`
- Modify: `gitlog.md`

- [ ] Document `runtime/last_quality_gate.json` as runtime-only telemetry.
- [ ] Document that `maintain-health` reports `last_quality_gate`.

### Task 4: Verification And Commit

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_gate_eval tests.test_eval_case_seed
PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory_runtime/quality_gate_eval.py tools/agent_memory_runtime/governance.py
git diff --check
ls -1 skills
```

Expected: tests pass, compile exits 0, diff check exits 0, and the official skill list remains four skills.

Commit:

```bash
git add docs/runtime.md docs/usage-guide.md gitlog.md skills/agent-memory-maintain/SKILL.md tools/agent_memory_runtime/quality_gate_eval.py tools/agent_memory_runtime/governance.py tests/test_quality_gate_eval.py docs/superpowers/plans/2026-07-12-quality-gate-snapshot.md
git commit -m "Expose latest quality gate health"
git push
```

## Self-Review

- Spec coverage: snapshot write, snapshot read, maintain-health output, recommendation, docs, tests, and verification are covered.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: snapshot helpers use existing `Project` and JSON payload conventions.
