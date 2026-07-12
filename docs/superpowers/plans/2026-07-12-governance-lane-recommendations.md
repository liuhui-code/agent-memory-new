# Governance Lane Recommendations Implementation Plan

> **For agentic workers:** Keep this as derived action-budget metadata. Do not change action scoring or persistence.

**Goal:** Add `recommended_lanes` to `action_budget` so Agents can choose the most useful governance lane before loading full action details.

**Architecture:** Group already-scored actions by `governance_lane`, compute count, max priority, average priority, and top action, then sort lanes by max priority and count. This is output-only and uses no new SQLite reads.

**Tech Stack:** Python 3.9+, JSON CLI output, unittest.

## Scope

Build:

- `recommended_lanes` in `action_budget`.
- Tests and docs.

Do not build:

- New scoring rules.
- Persistent lane preferences.
- New governance lanes.
- Automatic action execution.

## Tasks

- [x] **Step 1: Write failing test**
  - Run compact maintain-plan.
  - Expect recommended lanes with priority fields and sorted order.

- [x] **Step 2: Implement lane aggregation**
  - Group by `governance_lane`.
  - Include lane count, max priority, average priority, and top action.
  - Sort by max priority descending.

- [x] **Step 3: Document and verify**
  - Update runtime, usage, maintain skill, and gitlog.
  - Run targeted tests and static checks.
