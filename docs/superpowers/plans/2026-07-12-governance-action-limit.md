# Governance Action Limit Implementation Plan

> **For agentic workers:** Keep this as an output-budget control. Do not change governance scoring or memory state.

**Goal:** Add `maintain-plan --action-limit N` so Agents can tune how many budgeted top actions are returned in both full and compact maintain-plan output.

**Architecture:** Thread a CLI integer into the existing `build_governance_action_budget(..., limit=N)` helper. Clamp the value to at least one. Keep all maintain-plan action generation unchanged.

**Tech Stack:** Python 3.9+, argparse, unittest.

## Scope

Build:

- `--action-limit` flag for `maintain-plan`.
- Budget top action limit wiring.
- Tests and docs.

Do not build:

- New persistent queues.
- New action scheduling commands.
- Different action scoring.
- Different SQLite query behavior.

## Tasks

- [x] **Step 1: Write failing test**
  - Run `maintain-plan --compact --action-limit 1 --json`.
  - Expect `action_budget.top_limit == 1`.
  - Expect one compact action.

- [x] **Step 2: Add CLI flag and wiring**
  - Parse `--action-limit`.
  - Clamp to at least 1.
  - Pass into `build_governance_action_budget`.

- [x] **Step 3: Document and verify**
  - Update runtime, usage, maintain skill, and gitlog.
  - Run targeted and regression checks.
