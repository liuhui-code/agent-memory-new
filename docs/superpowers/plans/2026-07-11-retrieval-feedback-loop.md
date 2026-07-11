# Retrieval Feedback Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lightweight negative retrieval feedback loop so weak-related or misleading records can be penalized for similar future queries and reviewed by maintain.

**Architecture:** Store explicit feedback in SQLite, apply a bounded deterministic penalty during query reranking, and expose maintain review actions. Feedback is advisory; it does not delete, stale, or rewrite memory automatically.

**Tech Stack:** Python 3.9+, SQLite, existing FTS/query runtime, unittest.

---

## Scope

Build:

- `retrieval-feedback` CLI command
- `retrieval_feedback` SQLite table
- Query penalty for matching feedback on reflections and semantic facts
- `review_retrieval_feedback` maintain-plan action
- Docs and tests

Do not build:

- Automatic memory mutation
- LLM judge feedback
- New user-facing skill
- Feedback for every result type in the first version

## Feedback Shape

```bash
python tools/agent_memory.py retrieval-feedback \
  --project . \
  --query "ArkTS route blank screen" \
  --type reflection \
  --id 2 \
  --reason weak_related \
  --replacement-type reflection \
  --replacement-id 1 \
  --json
```

Reasons:

- `weak_related`
- `stale`
- `wrong_domain`
- `too_broad`
- `misleading`

## Tasks

- [x] **Step 1: Add failing tests**
  - Feedback command writes a row.
  - Query rerank penalizes the feedbacked record for similar query text.
  - Maintain-plan emits `review_retrieval_feedback`.

- [x] **Step 2: Add schema**
  - Create `retrieval_feedback`.
  - Add indexes by project/type/id and project/status.

- [x] **Step 3: Implement command and module**
  - Add feedback writer.
  - Add feedback collector for query rerank.

- [x] **Step 4: Integrate query and maintain**
  - Attach feedback penalty fields to results.
  - Add maintain action and summary counter.

- [x] **Step 5: Update docs and gitlog**

- [x] **Step 6: Verify and commit**
