# Global Memory Home Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move persisted memory data from the learned project directory to a configurable global memory home.

**Architecture:** `--project` identifies the source project. `--memory-home`, `AGENT_MEMORY_HOME`, or `~/.agent-memory` identifies the storage root. Each project keeps its own SQLite database, runtime cache, and vault under `projects/<project_id>/`.

**Tech Stack:** Python 3.9+, argparse, pathlib, SQLite, unittest.

---

### Task 1: Runtime Path Resolution

**Files:**
- Modify: `tools/agent_memory.py`
- Test: `tests/test_agent_memory.py`

- [x] Write tests proving `init` stores data under `--memory-home`, does not create project-local `.agent-memory`, and honors `AGENT_MEMORY_HOME`.
- [x] Run the focused tests and confirm they fail before implementation.
- [x] Add global memory home resolution to the runtime parser and project resolver.
- [x] Run the focused tests and confirm they pass.

### Task 2: Installer and Documentation

**Files:**
- Modify: `install.py`
- Modify: `README.md`
- Modify: `agent.md`
- Modify: `docs/mvp-implementation-plan.md`
- Modify: `docs/usage-guide.md`
- Modify: `docs/runtime.md`
- Modify: `references/schema.md`
- Modify: `references/obsidian-vault.md`
- Modify: `skills/agent-memory-maintain/SKILL.md`
- Modify: `gitlog.md`

- [x] Add `--memory-home` to the installer and pass it through to runtime init and doctor.
- [x] Update docs and skill instructions to describe global memory home storage.
- [x] Record the change and rollback notes in `gitlog.md`.

### Task 3: Verification

- [x] Run Python compile checks.
- [x] Run the full unittest suite.
- [x] Run `doctor` with a temporary memory home.
- [x] Review `git diff`.
- [ ] Commit and push the completed change.
