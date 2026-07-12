# Maintain Plan Compact Output Implementation Plan

> **For agentic workers:** Keep this feature read-only and output-only. Do not add persistent scheduling or a fifth skill.

**Goal:** Add `maintain-plan --compact --json` so Agents can inspect governance budgets and top actions without paying the token cost of the full maintain-plan payload.

**Architecture:** Reuse the full `maintain-plan` computation, then shrink the output at the final boundary. Preserve summaries, `action_budget`, and compact top actions. Omit heavyweight sections such as full actions, quality records, graph details, memory tiers, and active-learning details.

**Tech Stack:** Python 3.9+, existing argparse CLI, JSON output, unittest.

## Scope

Build:

- `--compact` flag for `maintain-plan`.
- Compact payload helper in `governance_action_budget.py`.
- Compact output tests.
- Runtime, usage, maintain-skill, and gitlog docs.

Do not build:

- Persistent action queues.
- Automatic action execution.
- Different governance scoring.
- Different SQLite queries.

## Tasks

- [x] **Step 1: Write failing compact-output test**
  - Run `maintain-plan --compact --json`.
  - Expect `compact: true`, `action_budget`, `health_overview`, and compact `actions`.
  - Expect heavyweight full-output sections to be omitted.

- [x] **Step 2: Add CLI flag**
  - Add `--compact` to the `maintain-plan` parser.

- [x] **Step 3: Add compact payload helper**
  - Keep `summary`, governance summaries, action budget, and top actions.
  - Add `health_overview` counts/statuses.
  - Add explicit `omitted_sections`.

- [x] **Step 4: Wire maintain-plan output**
  - Apply compacting immediately before usage recording, performance sampling, and output.

- [x] **Step 5: Verify**
  - Run targeted tests.
  - Run relevant regression tests.
  - Run py_compile and diff checks.

- [x] **Step 6: Commit**
  - Commit as `Add compact maintain plan output`.
