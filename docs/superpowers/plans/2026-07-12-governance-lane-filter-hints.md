# Governance Lane Filter Hints Implementation Plan

> **For agentic workers:** Keep this as advisory JSON metadata. Do not fail the command for unknown lanes.

**Goal:** Make `maintain-plan --action-lane <lane>` safer by reporting whether the selected lane matched any actions and listing available lanes when it does not.

**Architecture:** Reuse existing `counts_by_lane` from all generated actions. Add `lane_filter_status` and `available_lanes` to `action_budget`. Do not change action generation, scoring, or SQLite reads.

**Tech Stack:** Python 3.9+, JSON CLI output, unittest.

## Scope

Build:

- `lane_filter_status` in `action_budget`.
- `available_lanes` in `action_budget`.
- Tests and docs.

Do not build:

- CLI failure for unknown lanes.
- Fuzzy matching.
- Persistent lane preferences.
- New governance lanes.

## Tasks

- [x] **Step 1: Write failing test**
  - Run compact maintain-plan with an unknown lane.
  - Expect `lane_filter_status: no_matches`, empty top actions, and available lane hints.

- [x] **Step 2: Implement hint metadata**
  - Derive available lanes from full action counts.
  - Report `all_lanes`, `matched`, or `no_matches`.

- [x] **Step 3: Document and verify**
  - Update runtime, usage, maintain skill, and gitlog.
  - Run targeted tests and static checks.
