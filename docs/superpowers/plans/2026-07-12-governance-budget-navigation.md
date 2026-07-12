# Governance Budget Navigation Implementation Plan

> **For agentic workers:** Keep this as compact-output metadata. Do not add action execution or persistent scheduling.

**Goal:** Make compact `action_budget.top_actions` easier to follow up by adding stable review keys, source hints, and next command templates.

**Architecture:** Enrich compact action rendering only. Full maintain actions remain unchanged except for existing priority fields. The new metadata is derived from existing action fields.

**Tech Stack:** Python 3.9+, JSON CLI output, unittest.

## Scope

Build:

- `review_key` on compact top actions.
- `source_hint` on compact top actions.
- `next_command_templates` on `action_budget`.
- Docs and maintain skill guidance.

Do not build:

- Action execution.
- Persistent action queues.
- New tables.
- Query ranking changes.

## Tasks

- [x] **Step 1: Write failing navigation test**
  - Run compact maintain-plan with one top action.
  - Expect `review_key`, `source_hint`, and next command templates.

- [x] **Step 2: Implement compact metadata**
  - Build review keys from action name, type, id, lane, or rank fallback.
  - Build source hints from action reason plus lane/type/id.
  - Add full and compact command templates to the budget.

- [x] **Step 3: Document and verify**
  - Update runtime, usage, maintain skill, and gitlog.
  - Run targeted tests and static checks.
