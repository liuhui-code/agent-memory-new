# Experience, Query, Code Graph, and Log Graph Quality Closed Loop Plan

> **For agentic workers:** Keep the public interface fixed to the four existing skills. Implement thin, deterministic layers on top of the current SQLite runtime. Do not add vector databases, daemons, or heavy graph stores.

**Goal:** Complete five quality-enhancement tracks:

1. Query Explain / Rerank Audit
2. Experience Effectiveness Metrics
3. Golden Governance Eval
4. ArkTS Local Code Graph Enhancement
5. Log Observability Gap

**Architecture:** Reuse current query calibration, usage feedback, eval, code wiki, log signal, and maintain-plan infrastructure. Add explainable summaries and narrow eval/governance hooks before adding storage-heavy features.

## Track 1: Query Explain / Rerank Audit

**Purpose:** Make retrieval ranking debuggable when historical experience interferes with current task direction.

Implementation:

- Add a `query_audit` summary to `context` and `search`.
- Count candidates by result type.
- Report top compact explanations per result type:
  - `id`
  - `score`
  - `rerank_score`
  - `quality_score`
  - `trust_score`
  - `trust_level`
  - `retrieval_explanation`
  - feedback adjustment fields
- Keep this output bounded and read-only.

Verification:

- Query tests assert `query_audit` exists and explains at least one result.

## Track 2: Experience Effectiveness Metrics

**Purpose:** Move from static experience quality to task-outcome quality.

Implementation:

- Extend `fetch_experience_usage_summary` records with:
  - `total_count`
  - `success_count`
  - `failure_count`
  - `success_rate`
  - `misleading_rate`
  - `effectiveness_band`
- Extend `review_experience_usage` actions with these fields.
- Keep using existing `experience_usage_events`; no schema change.

Verification:

- Usage tests assert helpful/used outcomes produce strong effectiveness and misleading/superseded outcomes produce weak effectiveness.

## Track 3: Golden Governance Eval

**Purpose:** Make maintain-plan governance measurable, not just manually inspected.

Implementation:

- Add `eval-governance --cases <json> --json`.
- Case format:

```json
[
  {
    "name": "memory tier review",
    "expected_actions": [{"action": "review_memory_tier", "governance_lane": "memory_tiers"}],
    "must_not_actions": [{"action": "promote_experience_candidate"}]
  }
]
```

- Evaluation runs `maintain-plan` in memory and checks action specs.
- Report:
  - expected action hit rate
  - blocked bad action rate
  - quality gate
  - missed / unexpected actions

Verification:

- New governance eval test uses seeded memory-tier actions.

## Track 4: ArkTS Local Code Graph Enhancement

**Purpose:** Improve diagnosis paths without building full CPG.

Implementation:

- Add ArkTS state variable extraction for `@State`, `@Prop`, `@Link`, and `@Provide`.
- Store state references as `code_symbols` with kind `state`.
- Add deterministic `code_file --defines_state--> code_symbol` edges.
- Keep route/resource/log edges unchanged.

Verification:

- Code wiki test learns an ArkTS file with `@State profileLoaded` and asserts a state symbol plus edge exists.

## Track 5: Log Observability Gap

**Purpose:** Tell Agents what log fields are missing before they over-trust runtime logs.

Implementation:

- Add `observability_gaps` to log signal summaries.
- Derive gaps from missing timestamp/process/logger/event/stage/reason/route/correlation/result fields.
- Add `review_log_observability_gap` maintain-plan action only when concrete gaps exist.
- Keep raw user logs temporary; persist only compact reflections or incident traces when explicitly generated.

Verification:

- Log signal tests assert low-signal events expose missing observability fields.

## Execution Order

1. Query audit, because it directly reduces experience interference.
2. Experience effectiveness, because it strengthens the feedback loop.
3. Governance eval, because it makes future maintain-plan changes measurable.
4. ArkTS local graph enhancement, because it improves code anchors without heavy graph infrastructure.
5. Log observability gaps, because it improves diagnosis quality without persisting raw logs.

## Regression Matrix

Run targeted tests:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest \
  tests.test_experience_usage \
  tests.test_retrieval_eval \
  tests.test_graph_quality \
  tests.test_log_signal_quality \
  tests.test_governance_action_budget
```

Run static checks:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py
git diff --check
ls -1 skills
```

## Rollback

- Query audit: remove `query_audit` builders and docs.
- Experience effectiveness: remove derived fields/actions; keep usage events.
- Governance eval: remove command, parser, module, and tests.
- ArkTS state graph: remove state extractor and edge insertion.
- Log observability: remove gap summary/action fields.
