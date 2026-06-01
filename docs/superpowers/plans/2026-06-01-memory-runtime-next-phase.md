# Memory Runtime Next Phase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the next four runtime priorities: semantic follow-up prioritization, durable semantic conflict governance, batched aggregated query retrieval, and a concrete Agent CLI integration guide.

**Architecture:** Keep `tools/agent_memory.py` as the only entry point and SQLite as the source of truth. Extend the existing runtime modules in place: `code_wiki.py` owns semantic follow-up generation, `governance.py` owns durable review state, `query.py` owns bounded retrieval, and docs/skills explain how a local Agent CLI should consume the new outputs.

**Tech Stack:** Python 3.9+, SQLite, unittest, Markdown docs.

---

## File Map

- Modify: `tools/agent_memory_runtime/code_wiki.py`
  - Add semantic follow-up prioritization, batch limits, and next-action guidance.
- Modify: `tools/agent_memory_runtime/governance.py`
  - Persist semantic conflicts into governance state and expose review actions across sessions.
- Modify: `tools/agent_memory_runtime/query.py`
  - Add per-type batched retrieval, aggregated truncation metadata, and cursor support.
- Modify: `tools/agent_memory_runtime/storage.py`
  - Add the durable semantic conflict table and migration.
- Modify: `tools/agent_memory_runtime/cli.py`
  - Add cursor and limit flags for query commands only if needed by the runtime implementation.
- Modify: `tools/agent_memory_runtime/vault.py`
  - Export durable semantic conflict review pages.
- Modify: `tests/test_agent_memory.py`
  - Add failing tests first for each behavior change.
- Modify: `skills/agent-memory-learn/SKILL.md`
- Modify: `skills/agent-memory-query/SKILL.md`
- Modify: `skills/agent-memory-maintain/SKILL.md`
- Modify: `docs/runtime.md`
- Modify: `docs/usage-guide.md`
- Modify: `docs/guided-memory-review-workflow.md`
- Modify: `docs/templates/memory-query-answer-skill-template.md`
- Modify: `gitlog.md`

## Task 1: Prioritize and cap semantic follow-up

**Files:**
- Modify: `tests/test_agent_memory.py`
- Modify: `tools/agent_memory_runtime/code_wiki.py`
- Modify: `skills/agent-memory-learn/SKILL.md`
- Modify: `docs/runtime.md`
- Modify: `docs/usage-guide.md`

- [ ] **Step 1: Write the failing tests for semantic follow-up ordering and truncation**
- [ ] **Step 2: Run the targeted tests and confirm they fail for the missing fields**
- [ ] **Step 3: Implement priority scoring, capped batches, and `recommended_next_action` in `code_wiki.py`**
- [ ] **Step 4: Run the targeted tests and confirm they pass**
- [ ] **Step 5: Update learn docs to explain priority, truncation, and next-action semantics**

## Task 2: Persist semantic conflicts durably

**Files:**
- Modify: `tests/test_agent_memory.py`
- Modify: `tools/agent_memory_runtime/storage.py`
- Modify: `tools/agent_memory_runtime/governance.py`
- Modify: `tools/agent_memory_runtime/code_wiki.py`
- Modify: `tools/agent_memory_runtime/vault.py`
- Modify: `skills/agent-memory-maintain/SKILL.md`
- Modify: `docs/guided-memory-review-workflow.md`
- Modify: `docs/runtime.md`

- [ ] **Step 1: Write the failing tests for durable conflict persistence, maintain-plan review actions, and vault export**
- [ ] **Step 2: Run the targeted tests and confirm they fail**
- [ ] **Step 3: Add a persistent semantic conflict table and migration in `storage.py`**
- [ ] **Step 4: Write conflicts into SQLite from `learn-business` and read them from `governance.py`**
- [ ] **Step 5: Export the durable conflict review page in `vault.py`**
- [ ] **Step 6: Run the targeted tests and confirm they pass**
- [ ] **Step 7: Update governance docs and skill guidance**

## Task 3: Upgrade query to batched aggregated retrieval

**Files:**
- Modify: `tests/test_agent_memory.py`
- Modify: `tools/agent_memory_runtime/query.py`
- Modify: `tools/agent_memory_runtime/cli.py`
- Modify: `skills/agent-memory-query/SKILL.md`
- Modify: `docs/runtime.md`
- Modify: `docs/templates/memory-query-answer-skill-template.md`

- [ ] **Step 1: Write the failing tests for batched search metadata, cursor pagination, and per-type counts**
- [ ] **Step 2: Run the targeted tests and confirm they fail**
- [ ] **Step 3: Implement per-type retrieval windows, aggregated truncation metadata, and cursor handling in `query.py`**
- [ ] **Step 4: Add CLI flags only if the runtime design requires explicit overrides**
- [ ] **Step 5: Run the targeted tests and confirm they pass**
- [ ] **Step 6: Update query docs and Agent query-answer template**

## Task 4: Tighten Agent CLI integration guidance

**Files:**
- Modify: `tests/test_agent_memory.py`
- Modify: `skills/agent-memory-learn/SKILL.md`
- Modify: `skills/agent-memory-query/SKILL.md`
- Modify: `skills/agent-memory-maintain/SKILL.md`
- Modify: `docs/usage-guide.md`
- Modify: `docs/templates/memory-query-answer-skill-template.md`
- Modify: `gitlog.md`

- [ ] **Step 1: Add or update tests only if the docs depend on concrete JSON shapes changed in Tasks 1-3**
- [ ] **Step 2: Document the end-to-end local Agent CLI loop: learn -> learn-business -> query -> maintain-plan -> reflect**
- [ ] **Step 3: Record the implementation milestone in `gitlog.md`**

## Task 5: Full verification

**Files:**
- Modify: `gitlog.md`

- [ ] **Step 1: Run targeted tests for the new learn/governance/query behaviors**
- [ ] **Step 2: Run the full suite**
- [ ] **Step 3: Run `py_compile` for all Python entrypoints and runtime modules**
- [ ] **Step 4: Run `git diff --check`**
- [ ] **Step 5: Update `gitlog.md` with the final verification summary**
