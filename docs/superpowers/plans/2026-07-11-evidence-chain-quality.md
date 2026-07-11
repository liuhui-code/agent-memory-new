# Evidence Chain Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve experience quality by scoring whether a reflection can be grounded through source cases, incident traces, and code/log anchors.

**Architecture:** Add a lightweight read-only evidence chain scorer. It consumes existing reflection `source_cases`, `incident_traces`, and `incident_trace_links`; it does not add tables, perform graph traversal, or mutate memory.

**Tech Stack:** Python 3.9+, SQLite, existing quality scoring, unittest.

---

## Scope

Build:

- Reflection evidence chain enrichment for `maintain-plan`
- `evidence_chain_score` and `evidence_chain_reasons`
- `evidence_chain_summary`
- `review_weak_evidence_chain` action for otherwise useful reflections that lack grounded evidence

Do not build:

- Recursive graph traversal
- New persistent tables
- LLM judge scoring
- Automatic stale marking or promotion

## Evidence Chain Rules

Signals:

- `source_cases` contains `incident_trace:<id>`
- incident trace exists and belongs to the project
- incident trace has linked code/log anchors through `incident_trace_links`
- incident trace status is `resolved` or `diagnosed`

Scoring:

```text
0.00 no source cases
0.35 source case present but not resolvable
0.60 incident trace exists
0.80 incident trace has linked anchors
1.00 incident trace has linked anchors and resolved/diagnosed status
```

## Tasks

- [x] **Step 1: Add failing tests**
  - A reflection linked to a resolved incident trace with code/log links gets high evidence chain score.
  - A high-value reflection with no resolvable evidence chain triggers `review_weak_evidence_chain`.

- [x] **Step 2: Implement evidence chain helpers**
  - Parse `source_cases`.
  - Fetch linked incident traces and links.
  - Return score, reasons, trace ids, and anchor count.

- [x] **Step 3: Integrate quality report**
  - Attach evidence chain fields to reflection scored records.
  - Include chain score in reflection evidence strength.

- [x] **Step 4: Integrate maintain-plan**
  - Add `evidence_chain_summary`.
  - Add `review_weak_evidence_chain` actions.

- [x] **Step 5: Update docs and gitlog**

- [x] **Step 6: Verify and commit**
