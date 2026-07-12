# Active Learning Governance Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only active learning queue that ranks the next best memory/code/log improvement targets from existing query misses, graph signal gaps, and experience usage outcomes.

**Architecture:** Keep the queue computed on demand from existing SQLite/runtime summaries. `maintain-health` exposes a compact summary, and `maintain-plan` exposes ranked queue items plus confirmation-required review actions. No new table, daemon, vector index, or user-facing skill is added.

**Tech Stack:** Python 3.9+, SQLite, deterministic scoring, JSON CLI output, unittest.

---

## Scope

Build:

- `tools/agent_memory_runtime/active_learning_queue.py`.
- Queue items from:
  - open `query_misses`
  - `graph_signal_quality.top_repair_targets`
  - misleading/superseded/helpful `experience_usage` records
  - low-quality memory records from the existing quality report
- `maintain-health --json` summary for queue pressure.
- `maintain-plan --json` top queue items and `review_active_learning_queue` actions.
- Docs and skill guidance explaining how to consume the queue.

Do not build:

- Automatic mutation.
- Persistent queue table.
- Scheduling or background refresh.
- A fifth user-facing skill.

## Task 1: Active Learning Queue Builder

**Files:**

- Create: `tools/agent_memory_runtime/active_learning_queue.py`
- Test: `tests/test_active_learning_queue.py`

- [x] **Step 1: Write failing tests**

Test queue ranking for:

- repeated query miss
- weak graph-signal code-log target
- misleading experience usage

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_active_learning_queue
```

Expected before implementation: module or output missing.

- [x] **Step 2: Implement queue builder**

Implement:

```python
def build_active_learning_queue(project, graph_signal_quality=None, experience_usage=None, quality_report=None, limit=10) -> dict
def build_active_learning_actions(queue) -> list[dict]
```

Queue item fields:

- `queue_id`
- `priority_score`
- `lane`
- `target_type`
- `target_id`
- `title`
- `reason`
- `suggested_action`
- `source_signals`

Scoring:

- repeated query miss: `50 + min(miss_count, 10) * 4`
- graph signal target: `45 + missing_signals * 3`
- misleading/superseded usage: `65 + negative_count * 5`
- low-quality memory: `40 + (1 - quality_score) * 20`

## Task 2: Maintain Integration

**Files:**

- Modify: `tools/agent_memory_runtime/governance.py`
- Test: `tests/test_active_learning_queue.py`

- [x] **Step 1: Add queue to health**

`maintain-health --json` should include:

```json
"active_learning_queue": {
  "queue_count": 3,
  "top_priority_score": 70,
  "lanes": {"experience_usage": 1, "query_miss": 1, "graph_signal": 1},
  "top_items": [...]
}
```

- [x] **Step 2: Add queue to maintain-plan**

`maintain-plan --json` should include:

- top-level `active_learning_queue`
- `governance_summary.active_learning_queue_items`
- `review_active_learning_queue` actions

Actions remain read-only with `command: null`.

## Task 3: Docs And Verification

**Files:**

- Modify: `docs/runtime.md`
- Modify: `docs/usage-guide.md`
- Modify: `skills/agent-memory-maintain/SKILL.md`
- Modify: `gitlog.md`

- [x] **Step 1: Document queue behavior**

Explain:

- the queue is computed on demand
- it ranks already-known signals
- it is a triage aid, not an automatic mutation path
- it helps keep optimization focused at larger data volumes

- [x] **Step 2: Run verification**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest \
  tests.test_active_learning_queue \
  tests.test_graph_quality \
  tests.test_experience_usage \
  tests.test_agent_memory.AgentMemoryRuntimeTests
PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py
git diff --check
```

Expected: all pass.

- [x] **Step 3: Commit**

Run:

```bash
git add tools tests docs skills gitlog.md
git commit -m "Add active learning governance queue"
```
