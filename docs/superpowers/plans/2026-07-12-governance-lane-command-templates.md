# Governance Lane Command Templates Implementation Plan

> **For agentic workers:** Keep this as compact navigation metadata. Do not execute commands automatically.

**Goal:** Add `next_command_template` to each `action_budget.recommended_lanes` entry so Agents can jump directly from a lane recommendation to a focused compact maintain-plan run.

**Architecture:** Reuse existing command-template construction and attach one focused compact command per recommended lane. This is output-only and does not change scoring or persistence.

**Tech Stack:** Python 3.9+, JSON CLI output, unittest.

## Scope

Build:

- `recommended_lanes[*].next_command_template`.
- Tests and docs.

Do not build:

- Automatic command execution.
- Persistent lane selection.
- New scoring rules.

## Tasks

- [x] **Step 1: Write failing test**
  - Expect each recommended lane to include a command template.
  - Expect the command to include the lane name.

- [x] **Step 2: Implement**
  - Attach focused compact command templates to lane recommendations.

- [x] **Step 3: Document and verify**
  - Update runtime, usage, maintain skill, and gitlog.
  - Run targeted tests and static checks.
