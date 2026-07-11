# Memory Retrieval Eval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lightweight golden-query evaluation workflow for Agent Memory retrieval quality.

**Architecture:** Keep evaluation inside `tools/agent_memory.py` as a read-only runtime command. The command reads a JSON golden set, runs the existing `context` retrieval path, and computes deterministic hit/block metrics without adding LLM judges, vector databases, or a fifth skill.

**Tech Stack:** Python 3.9+, JSON, SQLite-backed runtime, unittest.

---

## Scope

Build:

- `eval-retrieval --cases <file> --json`
- Golden case schema with `query`, `expected`, and `must_not_include`
- Per-case expected hits, missed expected anchors, blocked bad matches, and unexpected bad matches
- Summary metrics: `case_count`, `expected_hit_rate`, `blocked_bad_rate`, `quality_gate`
- Docs and maintain/query skill guidance

Do not build:

- LLM-as-judge scoring
- Synthetic test generation
- Persistent eval tables
- Vector or embedding evaluation
- New user-facing skill

## Golden Case Shape

```json
[
  {
    "name": "arkts-route-blank-screen",
    "query": "ArkTS 页面跳转后白屏如何定位",
    "expected": [
      {"type": "reflections", "id": 1},
      {"type": "semantic_facts", "text": "router.pushUrl"}
    ],
    "must_not_include": [
      {"type": "reflections", "id": 2}
    ]
  }
]
```

Matchers support:

- `type`: context result list name
- `id`: exact record id
- `text`: substring searched across the candidate JSON
- `field`: optional exact field name for text matching

## Tasks

- [x] **Step 1: Add failing tests**
  - Test expected hit and bad-block metrics.
  - Test CLI output includes summary and per-case details.

- [x] **Step 2: Implement eval module**
  - Add `tools/agent_memory_runtime/retrieval_eval.py`.
  - Load JSON cases.
  - Run `limited_context`.
  - Match expected and must-not-include specs.
  - Return summary and case results.

- [x] **Step 3: Wire CLI**
  - Add parser command `eval-retrieval`.
  - Add runtime command map entry.

- [x] **Step 4: Update docs**
  - Explain golden query sets in runtime and usage guide.
  - Add maintain/query skill guidance.
  - Update `gitlog.md`.

- [x] **Step 5: Verify**
  - Run targeted eval tests.
  - Run quality/performance tests.
  - Run main regression and incident trace tests.
  - Run py_compile and `git diff --check`.
