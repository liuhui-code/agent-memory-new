# Python File Line Limit Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring every Python code file in the repository under 500 lines without changing the four user-facing skills or runtime CLI behavior.

**Architecture:** Keep existing public modules as facades where compatibility matters, and extract cohesive helpers into focused submodules. Split large tests by behavior area first so later runtime refactors have a reliable regression net.

**Tech Stack:** Python 3.9+, unittest, SQLite-backed runtime, local file-system tooling.

---

## Current Violations

- `tests/test_agent_memory.py`
- `tools/agent_memory_runtime/governance.py`
- `tools/agent_memory_runtime/code_wiki.py`
- `tools/agent_memory_runtime/query.py`
- `tools/agent_memory.py`
- `tools/agent_memory_runtime/vault.py`
- `tools/agent_memory_runtime/storage.py`
- `tools/agent_memory_runtime/runtime_logs.py`

## Execution Tasks

### Task 1: Add a Line Limit Gate

**Files:**
- Create: `tools/check_line_limits.py`

- [x] Add a repository-local checker that scans `install.py`, `tools/**/*.py`, and `tests/**/*.py`.
- [x] Make it fail with exit code 1 when any Python file exceeds 500 lines.
- [x] Exclude `.pycache` and generated runtime memory folders.
- [x] Verify with `python3 tools/check_line_limits.py`.

### Task 2: Split `tests/test_agent_memory.py`

**Files:**
- Create: `tests/agent_memory_test_base.py`
- Create: `tests/test_agent_memory_part_*.py`
- Replace: `tests/test_agent_memory.py`

- [x] Move shared constants and helper methods to `AgentMemoryTestBase`.
- [x] Move test methods into numbered part files, each under 500 lines.
- [x] Keep test method bodies unchanged.
- [x] Verify with `python3 -m unittest discover tests`.

### Task 3: Thin `tools/agent_memory.py`

**Files:**
- Modify: `tools/agent_memory.py`
- Create: focused runtime entry helpers as needed.

- [x] Preserve `tools/agent_memory.py` as the stable executable entry point.
- [x] Move implementation detail into runtime modules.
- [x] Verify key CLI commands: `doctor`, `context`, `maintain-plan`, `learn-path`.

### Task 4: Split Medium Runtime Modules

**Files:**
- Modify: `tools/agent_memory_runtime/runtime_logs.py`
- Modify: `tools/agent_memory_runtime/storage.py`
- Modify: `tools/agent_memory_runtime/vault.py`

- [x] Extract pure parser and summarizer helpers from runtime log analysis.
- [x] Extract schema groups and migration helpers from storage.
- [x] Extract vault dashboard writers by page group.
- [x] Verify with related unit tests and full discovery.

### Task 5: Split Core Runtime Modules

**Files:**
- Modify: `tools/agent_memory_runtime/query.py`
- Modify: `tools/agent_memory_runtime/code_wiki.py`
- Modify: `tools/agent_memory_runtime/governance.py`

- [x] Split query intent, lane retrieval, edge evidence, and output formatting.
- [x] Split code wiki extraction, writing, scope refresh, business semantics, and edge building.
- [x] Split governance health, semantic conflicts, quality gates, experience review, and action budgeting.
- [x] Preserve public imports used by tests and skills.

### Task 6: Final Verification

- [x] `python3 tools/check_line_limits.py`
- [x] `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest discover tests`
- [x] `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py tests/*.py`
- [x] `git diff --check`
- [x] Confirm `memory.md` remains untracked and unstaged.
