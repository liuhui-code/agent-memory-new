# Memory Tier Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add read-only hot/warm/cold memory tier governance so large archives can identify high-value records, neglected records, and archive candidates without changing query behavior.

**Architecture:** Compute tiers on demand from existing SQLite fields and quality scores. `maintain-health` exposes compact tier counts; `maintain-plan` exposes bounded `review_memory_tier` actions. No new table, daemon, vector store, or fifth skill is added.

**Tech Stack:** Python 3.9+, SQLite, deterministic scoring, JSON CLI output, unittest.

---

## Scope

Build:

- `tools/agent_memory_runtime/memory_tiers.py`.
- Tier summary for semantic facts, reflections, and episodes.
- Maintain-health output:
  - counts by tier
  - hot records
  - cold candidates
  - archive candidates
- Maintain-plan actions:
  - `review_memory_tier`
  - governance summary count
- Docs and maintain skill guidance.

Do not build:

- Automatic archiving.
- Query ranking changes.
- Persistent tier table.
- Background compaction.

## Task 1: Tier Builder

**Files:**

- Create: `tools/agent_memory_runtime/memory_tiers.py`
- Test: `tests/test_memory_tiers.py`

- [x] **Step 1: Write failing tests**

Create temporary records:

- a hot reflection with `use_count >= 3`
- a cold semantic fact with low confidence and no use
- a stale reflection with `status = stale`

Expected:

- `maintain-health --json` includes `memory_tiers`
- hot/cold/stale counts are present
- `maintain-plan --json` emits `review_memory_tier`

- [x] **Step 2: Implement tier classification**

Tier rules:

- `hot`: active and `use_count >= 3` or recent `last_used_at`
- `warm`: active and not hot/cold
- `cold`: active with no use and low confidence or low quality
- `archive_candidate`: stale, archived, rejected, or cold stale-like records

Keep result bounded:

- scan latest 500 rows per memory table
- return top 10 tier review targets

## Task 2: Maintain Integration

**Files:**

- Modify: `tools/agent_memory_runtime/governance.py`
- Test: `tests/test_memory_tiers.py`

- [x] **Step 1: Add health output**

`maintain-health --json` should include:

```json
"memory_tiers": {
  "counts": {"hot": 1, "warm": 0, "cold": 1, "archive_candidate": 1},
  "review_targets": [...]
}
```

- [x] **Step 2: Add maintain-plan actions**

Add `review_memory_tier` actions with:

- `tier`
- `target_type`
- `target_id`
- `reason`
- `suggested_actions`

Do not mutate memory.

## Task 3: Docs, Verification, Commit

**Files:**

- Modify: `docs/runtime.md`
- Modify: `docs/usage-guide.md`
- Modify: `skills/agent-memory-maintain/SKILL.md`
- Modify: `gitlog.md`

- [x] **Step 1: Document tier governance**

Explain that tiers are advisory, bounded, and designed for large archives.

- [x] **Step 2: Verify**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest \
  tests.test_memory_tiers \
  tests.test_active_learning_queue \
  tests.test_quality_performance_scoring \
  tests.test_agent_memory.AgentMemoryRuntimeTests
PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py
git diff --check
```

- [x] **Step 3: Commit**

```bash
git add tools tests docs skills gitlog.md
git commit -m "Add memory tier governance"
```
