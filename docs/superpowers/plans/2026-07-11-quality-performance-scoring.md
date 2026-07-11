# Quality and Performance Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explainable quality scoring model for memory records and a lightweight performance scoring model for runtime operations.

**Architecture:** Keep `tools/agent_memory.py` as the only runtime entry point. Add focused scoring modules that produce deterministic, explainable JSON consumed by `maintain-plan` and `maintain-health`; do not add vector storage, daemon telemetry, or a fifth skill.

**Tech Stack:** Python 3.9+, SQLite, JSONL runtime samples, unittest, existing FTS5-backed runtime.

---

## File Structure

- Create `tools/agent_memory_runtime/scoring_models.py`
  - Shared constants, clamping helpers, score band labels, weighted-score helpers.
- Create `tools/agent_memory_runtime/quality_scoring.py`
  - Score semantic facts, reflections/experiences, and incident traces.
  - Return explainable `score_parts`, `reasons`, and `recommended_action`.
- Create `tools/agent_memory_runtime/performance_scoring.py`
  - Store bounded runtime performance samples in `runtime/performance_samples.jsonl`.
  - Summarize operation latency, token pressure, storage pressure, and score bands.
- Modify `tools/agent_memory_runtime/governance.py`
  - Add `quality_summary`, `low_quality_records`, `high_value_records`, and `runtime_performance` to maintain output.
  - Append lightweight performance samples for `maintain-plan` and `maintain-health`.
- Modify `tools/agent_memory_runtime/query.py`
  - Append lightweight performance samples for `context` and `search` output paths if practical.
- Modify docs and skills
  - Document scoring fields in runtime, schema, maintain, and query guidance.
- Add tests
  - Extend `tests/test_agent_memory.py` or add focused scoring tests if the file would stay manageable.

## Task 1: Quality Scoring Model

**Files:**
- Create: `tools/agent_memory_runtime/scoring_models.py`
- Create: `tools/agent_memory_runtime/quality_scoring.py`
- Test: `tests/test_quality_performance_scoring.py`

- [x] **Step 1: Write failing tests**

```python
def test_quality_scoring_rewards_structured_verified_experience(self) -> None:
    row = {
        "id": 1,
        "experience_type": "procedure_experience",
        "confidence": 0.9,
        "status": "active",
        "verification_method": "ran targeted unit test",
        "source_cases": '["incident_trace:1"]',
        "trigger_condition": "ArkTS route blank screen",
        "repair_action": "inspect router.pushUrl target",
        "reuse_feedback": "reused successfully",
    }
    score = score_reflection_quality(row)
    self.assertGreaterEqual(score["quality_score"], 0.75)
    self.assertEqual(score["quality_band"], "good")
```

- [x] **Step 2: Run test to verify failure**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_performance_scoring
```

Expected: import failure because scoring modules do not exist.

- [x] **Step 3: Implement scoring helpers**

Create deterministic helpers:

```python
def clamp_score(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)

def score_band(score: float) -> str:
    if score >= 0.8:
        return "excellent"
    if score >= 0.65:
        return "good"
    if score >= 0.45:
        return "watch"
    return "poor"
```

- [x] **Step 4: Implement reflection, semantic, and incident trace scoring**

Use weighted parts:

```text
retrieval_relevance      0.20
evidence_strength        0.25
freshness                0.20
conflict_safety          0.15
reuse_success            0.10
governance_completeness  0.10
```

- [x] **Step 5: Run tests to verify pass**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_performance_scoring
```

Expected: quality scoring tests pass.

## Task 2: Maintain-Plan Quality Summary

**Files:**
- Modify: `tools/agent_memory_runtime/governance.py`
- Test: `tests/test_quality_performance_scoring.py`

- [x] **Step 1: Write failing integration test**

Expected `maintain-plan --json` includes:

```json
{
  "quality_summary": {
    "scored_records": 1,
    "low_quality_records": 0,
    "high_value_records": 1
  }
}
```

- [x] **Step 2: Implement maintain-plan integration**

Fetch active semantic facts, active reflections, and recent incident traces. Add:

```python
quality_report = build_quality_report(project, semantic_rows, reflection_rows, incident_trace_rows)
data["quality_summary"] = quality_report["summary"]
data["low_quality_records"] = quality_report["low_quality_records"]
data["high_value_records"] = quality_report["high_value_records"]
```

- [x] **Step 3: Run integration test**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_performance_scoring
```

Expected: maintain-plan quality fields are present and explainable.

## Task 3: Performance Scoring Model

**Files:**
- Create: `tools/agent_memory_runtime/performance_scoring.py`
- Modify: `tools/agent_memory_runtime/governance.py`
- Test: `tests/test_quality_performance_scoring.py`

- [x] **Step 1: Write failing tests**

Expected:

```python
sample = build_performance_sample(project, "context", 25.0, {"semantic_facts": 2}, 900, "ok")
self.assertEqual(sample["operation"], "context")
self.assertGreater(sample["performance_score"], 0.8)
```

- [x] **Step 2: Implement sample writer and summary**

Use JSONL in `project.runtime_dir / "performance_samples.jsonl"` with bounded tail retention.

- [x] **Step 3: Integrate maintain-health**

`maintain-health --json` should include:

```json
{
  "runtime_performance": {
    "sample_count": 3,
    "operations": {
      "maintain-plan": {
        "p95_elapsed_ms": 42.0,
        "performance_band": "excellent"
      }
    }
  }
}
```

- [x] **Step 4: Run tests**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_performance_scoring
```

Expected: performance samples and maintain-health summary pass.

## Task 4: Documentation and Verification

**Files:**
- Modify: `docs/runtime.md`
- Modify: `docs/usage-guide.md`
- Modify: `references/schema.md`
- Modify: `skills/agent-memory-maintain/SKILL.md`
- Modify: `skills/agent-memory-query/SKILL.md`
- Modify: `gitlog.md`

- [x] **Step 1: Document scoring outputs**

Document:

- `quality_summary`
- `low_quality_records`
- `high_value_records`
- `runtime_performance`
- JSONL performance sample path

- [x] **Step 2: Run targeted and full tests**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_performance_scoring
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests
PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py
git diff --check
```

Expected: all pass.

- [x] **Step 3: Update gitlog**

Add a dated entry summarizing scoring model, maintain integration, performance samples, and verification commands.

## Self-Review

- Spec coverage: quality scoring, performance scoring, maintain output, docs, tests, and verification are covered.
- Placeholder scan: no implementation placeholders remain; later query-ranking integration is intentionally out of scope for this first scoring layer.
- Scope check: this is one bounded implementation plan. It does not add embeddings, daemon metrics, LLM judges, or a fifth skill.
