# Runtime SLO Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote runtime performance samples from passive health telemetry into maintain-plan governance actions when local SLOs or token budgets are breached.

**Architecture:** Keep telemetry disposable in `runtime/performance_samples.jsonl`, summarize it through the existing performance scoring module, and let `maintain-plan` emit confirmable review actions without mutating memory. This keeps SQLite as source of truth for memory while treating performance samples as local operational evidence.

**Tech Stack:** Python 3.9, unittest, JSONL runtime telemetry, existing SQLite-backed runtime.

---

### Task 1: Runtime SLO Review Actions

**Files:**
- Modify: `tools/agent_memory_runtime/performance_scoring.py`
- Modify: `tools/agent_memory_runtime/governance.py`
- Modify: `tests/test_quality_performance_scoring.py`
- Modify: `docs/runtime.md`
- Modify: `docs/usage-guide.md`
- Modify: `gitlog.md`

- [ ] **Step 1: Write the failing test**

Add a test that appends a slow `context` performance sample, runs `maintain-plan --json`, and expects a `review_runtime_performance_budget` action plus a governance summary counter.

- [ ] **Step 2: Verify the test fails**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_performance_scoring.QualityPerformanceScoringTests.test_maintain_plan_reviews_runtime_performance_budget
```

Expected: fail because the action is not emitted yet.

- [ ] **Step 3: Implement minimal governance helper**

Add `build_runtime_performance_actions(summary)` to `performance_scoring.py`. The helper should inspect per-operation p95 latency, average score band, latest status, and token budget signals already captured in samples.

- [ ] **Step 4: Wire maintain-plan**

Call the helper from `maintain_plan`, extend actions, add `runtime_performance` output, and add `runtime_performance_reviews` to `governance_summary`.

- [ ] **Step 5: Document runtime SLO governance**

Update runtime and usage docs to explain that performance samples stay disposable, while maintain-plan can surface SLO review actions.

- [ ] **Step 6: Verify focused and regression tests**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_performance_scoring tests.test_retrieval_feedback tests.test_graph_quality tests.test_retrieval_eval
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_incident_trace
PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py
git diff --check
```

Expected: all commands exit 0.
