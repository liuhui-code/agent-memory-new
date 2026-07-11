# Graph Quality Health Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add lightweight health metrics for the code graph and log graph so maintain commands can detect orphan anchors and stale edges.

**Architecture:** Compute graph quality from existing `code_files`, `code_symbols`, `code_log_statements`, and `memory_edges`. Keep it read-only and bounded; do not add graph traversal, a graph database, or new storage tables.

**Tech Stack:** Python 3.9+, SQLite, unittest, existing maintain-health/maintain-plan.

---

## Scope

Build:

- `graph_quality` summary in `maintain-health --json`
- `review_graph_quality` action in `maintain-plan --json`
- Metrics for orphan code symbols, orphan code logs, stale edges, low-confidence edges, and anchor coverage

Do not build:

- Recursive graph traversal
- Persistent graph metrics table
- Hot subgraph ranking
- Automatic edge repair

## Metrics

- `code_files`
- `code_symbols`
- `code_log_statements`
- `memory_edges`
- `orphan_code_symbols`
- `orphan_code_logs`
- `stale_edges`
- `low_confidence_edges`
- `symbol_anchor_coverage`
- `log_anchor_coverage`
- `health_status`: `ok`, `watch`, or `poor`

## Tasks

- [x] **Step 1: Add failing tests**
  - Test `maintain-health` reports orphan logs and stale edges.
  - Test `maintain-plan` emits `review_graph_quality`.

- [x] **Step 2: Implement graph quality module**
  - Add `tools/agent_memory_runtime/graph_quality.py`.
  - Compute counts and coverage from SQLite.

- [x] **Step 3: Integrate maintain commands**
  - Add `graph_quality` to `maintain-health`.
  - Add `review_graph_quality` action and summary count to `maintain-plan`.

- [x] **Step 4: Update docs and gitlog**

- [x] **Step 5: Verify and commit**
