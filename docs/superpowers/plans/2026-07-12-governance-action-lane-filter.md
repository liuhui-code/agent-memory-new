# Governance Action Lane Filter Implementation Plan

> **For agentic workers:** Keep this as output filtering for the action budget. Do not drop underlying maintain-plan action generation.

**Goal:** Add `maintain-plan --action-lane <lane>` so Agents can review one governance lane at a time in compact or full maintain-plan output.

**Architecture:** Generate all actions as before, then filter only the action-budget candidate set before selecting `top_actions`. Keep counts by lane over the full action set so Agents can see other available lanes.

**Tech Stack:** Python 3.9+, argparse, JSON CLI output, unittest.

## Scope

Build:

- `--action-lane` flag for `maintain-plan`.
- Budget filtering by `governance_lane`.
- Budget fields `selected_lane` and `candidate_actions`.
- Tests and docs.

Do not build:

- Persistent queues.
- Different action scoring.
- Different SQLite query behavior.
- Deleting or hiding full maintain-plan actions.

## Tasks

- [x] **Step 1: Write failing test**
  - Run `maintain-plan --compact --action-lane memory_tiers --json`.
  - Expect budget top actions only from `memory_tiers`.

- [x] **Step 2: Implement lane filtering**
  - Parse `--action-lane`.
  - Filter only action-budget candidates.
  - Preserve full action counts.

- [x] **Step 3: Document and verify**
  - Update runtime, usage, maintain skill, and gitlog.
  - Run targeted and regression checks.
