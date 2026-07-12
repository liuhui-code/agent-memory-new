# Governance Action Budget Implementation Plan

> **For agentic workers:** Implement this as a small read-only governance layer. Keep the four user-facing skills unchanged.

**Goal:** Add a compact action-budget view to `maintain-plan` so large archives can show which governance actions deserve attention first without asking the LLM to inspect every action equally.

**Architecture:** Score already-built maintain actions in memory, attach deterministic priority fields, and return a bounded `action_budget` summary. Do not add a table, daemon, vector store, or new skill.

**Tech Stack:** Python 3.9+, existing JSON CLI output, unittest.

## Scope

Build:

- `tools/agent_memory_runtime/governance_action_budget.py`.
- `action_budget` in `maintain-plan --json`.
- `priority_score` and `priority_reasons` on maintain actions.
- Documentation and maintain-skill guidance.

Do not build:

- Automatic execution.
- Action deletion.
- Query ranking changes.
- Persistent action scheduling.

## Task 1: Budget Model

**Files:**

- Create: `tools/agent_memory_runtime/governance_action_budget.py`
- Test: `tests/test_governance_action_budget.py`

- [x] **Step 1: Write failing test**
  - Seed mixed maintain-plan actions.
  - Expect top-level `action_budget`.
  - Expect each action to include `priority_score` and `priority_reasons`.

- [x] **Step 2: Implement deterministic scoring**
  - Use risk, confirmation requirement, governance lane, action type, existing action priority, and repeated miss/use signals.
  - Keep the score explainable and bounded.

## Task 2: Maintain Integration

**Files:**

- Modify: `tools/agent_memory_runtime/governance.py`

- [x] **Step 1: Annotate actions**
  - After all actions have `governance_lane`, attach priority fields.

- [x] **Step 2: Add compact budget output**
  - Include counts by lane and risk.
  - Include top bounded actions.
  - Mirror the budget in `governance_summary` for fast inspection.

## Task 3: Docs, Verification, Commit

**Files:**

- Modify: `docs/runtime.md`
- Modify: `docs/usage-guide.md`
- Modify: `skills/agent-memory-maintain/SKILL.md`
- Modify: `gitlog.md`

- [x] **Step 1: Document**
  - Explain that action budget is advisory and read-only.

- [x] **Step 2: Verify**
  - Run targeted tests.
  - Run relevant regression tests.
  - Run py_compile and diff checks.

- [x] **Step 3: Commit**
  - Commit as `Add governance action budget`.
