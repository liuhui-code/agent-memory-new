# Quality Governance Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn quality scoring into maintain-plan governance actions for low-quality memory review and high-value experience review.

**Architecture:** Reuse the existing deterministic quality scoring layer. Keep `maintain-plan` read-only: it proposes `review_low_quality_memory` and `review_high_value_experience` actions, but does not mutate records or promote skills automatically.

**Tech Stack:** Python 3.9+, SQLite, unittest, existing Agent Memory runtime.

---

## Scope

Build:

- Low-quality review actions for records below the quality threshold.
- High-value experience review actions for reflection records above the high-value threshold.
- Governance summary counters for both action types.
- Docs and skill guidance.

Do not build:

- Automatic stale marking.
- Automatic confidence lowering.
- Automatic skill promotion.
- New CLI commands.
- Vault pages.

## Action Contract

`review_low_quality_memory`:

- Trigger: `quality_score < 0.45`.
- Applies to semantic facts, reflections, and incident traces.
- Suggested actions: `verify_against_source`, `tighten_trigger_condition`, `lower_confidence`, `mark_stale`, `merge_duplicate`.
- Requires confirmation.
- Governance lane: `memory_quality`.

`review_high_value_experience`:

- Trigger: reflection quality score `>= 0.75`.
- Applies only to reflections/experience candidates.
- Suggested actions: `reuse_as_primary_context`, `review_for_skill_pattern`, `review_for_promotion`, `keep_active`.
- Requires confirmation.
- Governance lane: `skill_evolution` for procedure experience, `learn_semantic_repair` for correction/semantic patch experience.

## Tasks

- [x] **Step 1: Add failing tests**
  - Add a low-quality maintain-plan test.
  - Add a high-value maintain-plan test.

- [x] **Step 2: Enrich quality payloads**
  - Include `experience_type`, `confidence`, and `status` when available so governance actions do not need to refetch records.

- [x] **Step 3: Build quality governance actions**
  - Add a helper that converts `quality_report` into action dictionaries.
  - Deduplicate action identity by `(action, type, id)`.

- [x] **Step 4: Integrate maintain-plan**
  - Extend `actions`.
  - Add summary counters: `low_quality_memory_reviews`, `high_value_experience_reviews`.

- [x] **Step 5: Update docs and skills**
  - Document action semantics in runtime, usage guide, maintain skill, and gitlog.

- [x] **Step 6: Verify**
  - Run targeted quality tests.
  - Run main regression.
  - Run py_compile.
  - Run `git diff --check`.
