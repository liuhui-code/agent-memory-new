# Experience Evidence Log Closed Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lightweight closed loop for experience usage outcomes, evidence attribution evaluation, and OTel-lite log normalization without changing the fixed four user-facing skills.

**Architecture:** Keep `tools/agent_memory.py` as the only runtime entry point and SQLite as source of truth. Add small focused runtime modules for outcome aggregation, evidence attribution, and OTel-lite event projection; query and maintain consume bounded summaries instead of scanning unbounded history.

**Tech Stack:** Python 3.9+, SQLite, FTS5, deterministic keyword scoring, JSON CLI output, unittest.

---

## Scope

This plan implements the next stage after the experience maturity, conflict, graph quality, and log signal work.

Build:

- Explicit experience usage outcome recording for retrieved semantic/reflection records.
- Query-time positive/negative adjustment based on usage outcomes.
- Maintain-health/maintain-plan visibility for misleading, ignored, and highly helpful experience.
- Evidence attribution evaluation command for checking whether answer claims are grounded in retrieved context.
- OTel-lite normalized event projection for runtime logs and code-log matches.

Do not build:

- A vector database.
- A daemon or background watcher.
- A new user-facing skill.
- Persistent raw user log storage.
- LLM-based grading inside the runtime.

## File Map

- Create `tools/agent_memory_runtime/experience_usage.py`
  - Owns `experience_usage_events` writes, bounded aggregation, query adjustment, and governance action builders.
- Create `tools/agent_memory_runtime/evidence_attribution.py`
  - Owns deterministic claim-to-context attribution evaluation.
- Create `tools/agent_memory_runtime/otel_lite.py`
  - Owns normalized event projection inspired by OpenTelemetry fields while staying local and lightweight.
- Modify `tools/agent_memory_runtime/storage.py`
  - Adds the usage event table and indexes.
- Modify `tools/agent_memory_runtime/models.py`
  - Adds `experience_usage_events` to required tables.
- Modify `tools/agent_memory_runtime/cli.py`
  - Adds `experience-usage` and `eval-evidence-attribution`.
- Modify `tools/agent_memory.py`
  - Wires new commands.
- Modify `tools/agent_memory_runtime/query.py`
  - Applies bounded experience usage adjustments to semantic facts and reflections.
- Modify `tools/agent_memory_runtime/governance.py`
  - Adds usage outcome summary and review actions.
- Modify `tools/agent_memory_runtime/runtime_logs.py`
  - Adds OTel-lite event projection to normalized runtime analysis output.
- Modify `tools/agent_memory_runtime/log_signal_quality.py`
  - Uses OTel-lite normalized fields as additional signal evidence where available.
- Add tests:
  - `tests/test_experience_usage.py`
  - `tests/test_evidence_attribution.py`
  - `tests/test_otel_lite.py`
- Update docs:
  - `docs/runtime.md`
  - `docs/usage-guide.md`
  - `skills/agent-memory-query/SKILL.md`
  - `skills/agent-memory-maintain/SKILL.md`
  - `skills/agent-memory-reflect/SKILL.md`
  - `gitlog.md`

## Task 1: Experience Usage Outcome Loop

**Goal:** Let Agents explicitly record whether a retrieved memory was used, helpful, ignored, or misleading, and make future queries consume that signal.

**Files:**

- Create: `tools/agent_memory_runtime/experience_usage.py`
- Modify: `tools/agent_memory_runtime/storage.py`
- Modify: `tools/agent_memory_runtime/models.py`
- Modify: `tools/agent_memory_runtime/cli.py`
- Modify: `tools/agent_memory.py`
- Modify: `tools/agent_memory_runtime/query.py`
- Modify: `tools/agent_memory_runtime/governance.py`
- Test: `tests/test_experience_usage.py`

- [x] **Step 1: Write tests for CLI write, query adjustment, and maintain actions**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_usage
```

Expected before implementation: import or command failure.

- [x] **Step 2: Add SQLite table and required table entry**

Schema:

```sql
CREATE TABLE IF NOT EXISTS experience_usage_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL,
  query TEXT NOT NULL,
  normalized_query TEXT NOT NULL,
  record_type TEXT NOT NULL,
  record_id INTEGER NOT NULL,
  outcome TEXT NOT NULL,
  note TEXT,
  evidence TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_experience_usage_project_record
ON experience_usage_events(project_id, record_type, record_id, created_at);

CREATE INDEX IF NOT EXISTS idx_experience_usage_project_query
ON experience_usage_events(project_id, normalized_query, outcome, created_at);
```

Allowed record types: `semantic`, `reflection`.

Allowed outcomes: `used`, `helpful`, `ignored`, `misleading`, `superseded`.

- [x] **Step 3: Add runtime helper**

Implement:

```python
def write_experience_usage(project, query, record_type, record_id, outcome, note=None, evidence=None) -> dict
def collect_usage_adjustments(project, query, record_type) -> dict[int, dict]
def fetch_experience_usage_summary(project, limit=10) -> dict
def build_experience_usage_actions(summary) -> list[dict]
```

Rules:

- Positive outcomes add at most `+0.18` trust bonus.
- Negative outcomes add at most `0.35` trust penalty.
- Query overlap gates transfer so unrelated usage does not leak.
- `misleading` and `superseded` are stronger than `ignored`.
- Aggregation scans at most the latest 200 events per record type.

- [x] **Step 4: Add CLI command**

Command:

```bash
python tools/agent_memory.py experience-usage \
  --project . \
  --query "ArkTS route blank screen" \
  --type reflection \
  --id 12 \
  --outcome misleading \
  --note "Recent but broad experience sent diagnosis toward wrong route layer" \
  --json
```

- [x] **Step 5: Apply usage adjustments in query**

For semantic facts and reflections:

- Add `usage_feedback_bonus`.
- Add `usage_feedback_penalty`.
- Add `usage_feedback_reasons`.
- Reduce `rerank_score` or trust where existing ranking supports it.
- Keep output explainable without hiding the record unless existing gates already block it.

- [x] **Step 6: Add maintain-health and maintain-plan visibility**

Maintain output should include:

```json
"experience_usage": {
  "event_count": 3,
  "misleading_records": 1,
  "helpful_records": 1
}
```

Maintain actions should include `review_experience_usage` for misleading or superseded records.

- [x] **Step 7: Verify focused tests**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_usage tests.test_retrieval_feedback tests.test_experience_query_quality
```

Expected: all pass.

## Task 2: Evidence Attribution Evaluation

**Goal:** Add a deterministic eval command that checks whether important answer claims can be grounded in current query/context evidence.

**Files:**

- Create: `tools/agent_memory_runtime/evidence_attribution.py`
- Modify: `tools/agent_memory_runtime/cli.py`
- Modify: `tools/agent_memory.py`
- Test: `tests/test_evidence_attribution.py`

- [x] **Step 1: Write tests for grounded and ungrounded claims**

Use JSON cases shaped as:

```json
[
  {
    "name": "route claim grounded",
    "query": "ArkTS route blank screen",
    "claims": [
      "router.pushUrl target pages/Profile should match page registration",
      "payment timeout is the root cause"
    ],
    "min_grounded_rate": 0.5,
    "max_unsupported_claims": 1
  }
]
```

- [x] **Step 2: Implement deterministic attribution**

Implement:

```python
def evaluate_evidence_attribution(project, cases) -> dict
def evaluate_case(project, case) -> dict
def claim_support_score(claim, context) -> dict
```

Scoring:

- Token overlap with current source/context fields.
- Bonus for exact file path, symbol, log message, or error code matches.
- Support bands: `grounded >= 0.45`, `weak >= 0.25`, else `unsupported`.

- [x] **Step 3: Add CLI command**

Command:

```bash
python tools/agent_memory.py eval-evidence-attribution \
  --project . \
  --cases /tmp/evidence-cases.json \
  --json
```

Output includes `quality_gate`, summary rates, and per-claim support evidence.

- [x] **Step 4: Verify focused tests**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_evidence_attribution tests.test_retrieval_eval tests.test_calibration_eval
```

Expected: all pass.

## Task 3: OTel-Lite Log Event Adapter

**Goal:** Normalize runtime/code log events into stable fields that make log analysis and future diagnosis easier for LLMs.

**Files:**

- Create: `tools/agent_memory_runtime/otel_lite.py`
- Modify: `tools/agent_memory_runtime/runtime_logs.py`
- Modify: `tools/agent_memory_runtime/log_signal_quality.py`
- Test: `tests/test_otel_lite.py`
- Test: `tests/test_log_signal_quality.py`

- [x] **Step 1: Write tests for runtime and code-log projection**

Expected normalized fields:

```json
{
  "time_unix_nano": null,
  "severity_text": "ERROR",
  "body": "load profile failed ...",
  "resource": {"process.name": "EntryAbility"},
  "attributes": {
    "logger.name": "ProfilePage",
    "event.name": "profile_load_failed",
    "request.id": "req-1",
    "session.id": "sess-1",
    "error.code": "401",
    "error.reason": "session_invalid"
  }
}
```

- [x] **Step 2: Implement OTel-lite helper**

Implement:

```python
def runtime_event_to_otel_lite(event: dict[str, Any]) -> dict[str, Any]
def code_log_to_otel_lite(row: dict[str, Any]) -> dict[str, Any]
def attach_otel_lite(event: dict[str, Any]) -> dict[str, Any]
```

Rules:

- Do not persist raw temporary logs.
- Keep projection bounded inside analysis/query outputs.
- Use OpenTelemetry-style names where obvious, but do not require OTel dependencies.

- [x] **Step 3: Attach projection to log analysis**

`analyze-runtime-log --json` should include `otel_lite` on matched events and low-signal examples where available.

- [x] **Step 4: Use projection for signal scoring**

`score_log_signal` should treat OTel-lite attributes as valid evidence for request/session/error/reason/event fields.

- [x] **Step 5: Verify focused tests**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_otel_lite tests.test_log_signal_quality
```

Expected: all pass.

## Task 4: Docs, Skills, and Regression

**Goal:** Make the new loop visible to users and future Agents while preserving the fixed four-skill surface.

**Files:**

- Modify: `docs/runtime.md`
- Modify: `docs/usage-guide.md`
- Modify: `skills/agent-memory-query/SKILL.md`
- Modify: `skills/agent-memory-maintain/SKILL.md`
- Modify: `skills/agent-memory-reflect/SKILL.md`
- Modify: `gitlog.md`

- [x] **Step 1: Update docs**

Document:

- When to call `experience-usage`.
- How `eval-evidence-attribution` differs from retrieval eval.
- Why OTel-lite projection is temporary output rather than raw log persistence.
- How this saves tokens by sending structured, bounded evidence to LLMs.

- [x] **Step 2: Update skill guidance**

Keep exactly four user-facing skills:

```bash
ls -1 skills
```

Expected:

```text
agent-memory-learn
agent-memory-maintain
agent-memory-query
agent-memory-reflect
```

- [x] **Step 3: Run regression**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest \
  tests.test_experience_usage \
  tests.test_evidence_attribution \
  tests.test_otel_lite \
  tests.test_log_signal_quality \
  tests.test_retrieval_feedback \
  tests.test_experience_query_quality \
  tests.test_retrieval_eval \
  tests.test_calibration_eval \
  tests.test_agent_memory.AgentMemoryRuntimeTests
```

Expected: all pass.

- [x] **Step 4: Run syntax and whitespace checks**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py
git diff --check
```

Expected: no output or success.

- [x] **Step 5: Commit**

Run:

```bash
git add tools tests docs skills gitlog.md
git commit -m "Add experience evidence log closed loop"
```

Expected: commit succeeds.
