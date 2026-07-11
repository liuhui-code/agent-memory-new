# Experience Maturity and Log Signal Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve experience quality and log-diagnosis quality by adding experience maturity/counter-evidence scoring and log signal quality/log design gap governance.

**Architecture:** Keep the first implementation read-mostly and SQLite-compatible. Compute maturity and log-signal scores from existing reflection, incident trace, code log, runtime-log, calibration-feedback, and memory-edge data; surface the result through query calibration and maintain-plan review actions. Add persistence only where it avoids repeated expensive work or is needed for explicit human review.

**Tech Stack:** Python 3.9, SQLite, existing `tools/agent_memory.py` CLI, `unittest`, existing four user-facing skills.

---

## Scope

This plan covers two priority tracks:

1. **Experience Maturity Level + Counter Evidence**
   - Classify reflections/experiences by maturity.
   - Reward verified reuse and evidence chains.
   - Penalize stale, misleading, overtrusted, weakly anchored, or missing counter-evidence records.
   - Make `does_not_apply_to`, `negative_preconditions`, `what_failed`, `anti_pattern`, calibration feedback, and failed reuse first-class quality signals.

2. **Log Signal Quality + Log Design Gap**
   - Score learned code logs and runtime log evidence for diagnosis usefulness.
   - Detect missing correlation, stage, business event, error code, route/resource/session/request identifiers.
   - Convert repeated diagnosis pain into narrow `review_log_design_gap` actions tied to files/functions/log anchors.

Out of scope for this plan:

- Vector database.
- Graph database.
- Raw user runtime-log persistence.
- New user-facing skill.
- Automatic mutation of source memory without maintain action confirmation.

---

## Target Files and Responsibilities

- Create `tools/agent_memory_runtime/experience_maturity.py`
  - Pure scoring/classification helpers for reflection rows.
  - Outputs maturity level, score, reasons, counter-evidence summary, and suggested governance action.

- Create `tools/agent_memory_runtime/log_signal_quality.py`
  - Pure scoring helpers for code log rows, runtime incident evidence, and log design gaps.
  - Outputs log signal score, missing signal fields, and narrow log improvement suggestions.

- Modify `tools/agent_memory_runtime/query.py`
  - Attach `experience_maturity`, `experience_maturity_score`, and counter-evidence summary to reflection results before calibration.
  - Optionally expose log signal quality on `code_log_matches`.

- Modify `tools/agent_memory_runtime/memory_calibration.py`
  - Consume maturity and counter-evidence signals in trust scoring.
  - Prevent mature-looking but overtrusted/misleading experiences from becoming strong conclusions.

- Modify `tools/agent_memory_runtime/governance.py`
  - Add maintain-plan actions:
    - `review_immature_experience`
    - `review_missing_counter_evidence`
    - `review_maturity_regression`
    - `review_low_log_signal_quality`
    - refined `review_log_design_gap`

- Modify `tools/agent_memory_runtime/runtime_logs.py`
  - Add log signal summaries to `analyze-runtime-log` output without storing raw logs.
  - Feed signal gaps into `reflect_payload_template`.

- Modify `tools/agent_memory_runtime/code_wiki.py`
  - If needed, enrich extracted code log rows with deterministic signal fields already available from message templates.
  - Keep changes localized to extraction and returned parse stats.

- Modify `skills/agent-memory-reflect/SKILL.md`
  - Instruct Agents to include counter-evidence and maturity-supporting fields when reflecting.

- Modify `skills/agent-memory-query/SKILL.md`
  - Instruct Agents to use maturity and log-signal fields before applying experiences.

- Modify `skills/agent-memory-maintain/SKILL.md`
  - Document maintain-plan maturity and log signal review actions.

- Modify docs:
  - `docs/runtime.md`
  - `docs/usage-guide.md`
  - `gitlog.md`

- Add tests:
  - `tests/test_experience_maturity.py`
  - `tests/test_log_signal_quality.py`

File-size guardrail:

- Keep new modules under 500 lines each.
- If `governance.py` integration grows, extract action builders into a new focused module instead of adding a large block.

---

## Phase 1: Experience Maturity Scoring

### Task 1.1: Define Maturity Levels

**Files:**
- Create: `tools/agent_memory_runtime/experience_maturity.py`
- Create: `tests/test_experience_maturity.py`

Maturity levels:

- `raw_observation`
  - A reflection exists but lacks verification, source cases, reuse history, or concrete repair action.

- `structured_candidate`
  - Has trigger, repair action, scope, and at least one useful structured field.

- `verified_case`
  - Has verification method plus source case, evidence, incident trace, code/log anchor, or final verification path.

- `reused_pattern`
  - Has positive reuse feedback, `applied_count > 0`, `last_outcome != misleading`, or positive calibration feedback.

- `skill_candidate`
  - Is a mature procedure experience with repeated support, skill candidate field, or clustered skill-pattern evidence.

- `deprecated_pattern`
  - Stale, superseded, misleading, overtrusted, rejected, archived, or contradicted by current code/conflict feedback.

- [ ] **Step 1: Write focused unit tests**

Test cases:

- Raw reflection with only task/lesson returns `raw_observation`.
- Procedure reflection with trigger and repair but no verification returns `structured_candidate`.
- Reflection with `verification_method` and `source_cases=["incident_trace:1"]` returns `verified_case`.
- Reflection with `applied_count=2` and `last_outcome="helped"` returns `reused_pattern`.
- Reflection with `skill_candidate` plus verification and reuse returns `skill_candidate`.
- Reflection with `status="stale"` or `last_outcome="misleading"` returns `deprecated_pattern`.

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_maturity
```

Expected before implementation: fail because the module does not exist.

- [ ] **Step 2: Implement minimal scoring helper**

Required public functions:

```python
def score_experience_maturity(row: dict[str, Any]) -> dict[str, Any]:
    ...

def build_counter_evidence_summary(row: dict[str, Any]) -> dict[str, Any]:
    ...
```

Required output:

```json
{
  "experience_maturity": "verified_case",
  "experience_maturity_score": 0.78,
  "maturity_reasons": ["has verification_method", "has source_cases"],
  "counter_evidence": {
    "has_counter_evidence": true,
    "fields": ["negative_preconditions", "does_not_apply_to"],
    "missing_fields": []
  },
  "recommended_maturity_action": "keep_active"
}
```

- [ ] **Step 3: Verify focused tests**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_maturity
```

Expected: all tests pass.

### Task 1.2: Attach Maturity to Query Results

**Files:**
- Modify: `tools/agent_memory_runtime/query.py`
- Modify: `tools/agent_memory_runtime/memory_calibration.py`
- Test: `tests/test_experience_maturity.py`

- [ ] **Step 1: Add context/search integration test**

Seed one verified reflection and one raw reflection. Run:

```bash
python tools/agent_memory.py context --project <tmp> --query "ArkTS route blank screen" --json
```

Assert returned reflections include:

- `experience_maturity`
- `experience_maturity_score`
- `maturity_reasons`
- `counter_evidence`

Assert the verified reflection has higher `trust_score` than the raw reflection when both are in the same lane.

- [ ] **Step 2: Implement query annotation**

Call `score_experience_maturity` for reflection matches before `calibrate_payload`.

- [ ] **Step 3: Update calibration scoring**

Rules:

- Add a small trust bonus for `verified_case`, `reused_pattern`, and `skill_candidate`.
- Add a trust penalty for `raw_observation` and `deprecated_pattern`.
- Add a penalty when counter-evidence is absent for otherwise high-quality procedure experiences.
- Never let maturity bypass lane gates, stale status, explicit conflict, or current-source authority.

- [ ] **Step 4: Verify**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_maturity tests.test_memory_calibration tests.test_calibration_feedback
```

Expected: all tests pass.

---

## Phase 2: Counter Evidence Governance

### Task 2.1: Maintain Actions for Missing Counter Evidence

**Files:**
- Modify: `tools/agent_memory_runtime/governance.py`
- Test: `tests/test_experience_maturity.py`

- [ ] **Step 1: Add maintain-plan test**

Seed a high-confidence procedure reflection with:

- trigger condition
- repair action
- verification method
- no `negative_preconditions`
- no `does_not_apply_to`
- no `what_failed`
- no `anti_pattern`

Run:

```bash
python tools/agent_memory.py maintain-plan --project <tmp> --json
```

Assert action:

```json
{
  "action": "review_missing_counter_evidence",
  "type": "reflection",
  "id": 1,
  "governance_lane": "memory_quality"
}
```

- [ ] **Step 2: Add action builder**

Action should include:

- `experience_maturity`
- `experience_maturity_score`
- `missing_counter_evidence_fields`
- `suggested_actions`

Suggested actions:

- `add_negative_preconditions`
- `add_does_not_apply_to`
- `add_counter_example`
- `lower_confidence_until_verified`
- `keep_if_context_specific`

- [ ] **Step 3: Add summary counters**

Add to `governance_summary`:

- `immature_experience_reviews`
- `missing_counter_evidence_reviews`
- `maturity_regression_reviews`

- [ ] **Step 4: Verify**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_maturity tests.test_quality_performance_scoring
```

Expected: all tests pass.

### Task 2.2: Reflect Skill Guidance

**Files:**
- Modify: `skills/agent-memory-reflect/SKILL.md`
- Modify: `docs/usage-guide.md`

- [ ] Add a short section that asks Agents to record counter-evidence after non-trivial tasks:

Required reflection fields when available:

- `negative_preconditions`
- `does_not_apply_to`
- `what_failed`
- `anti_pattern`
- `hidden_assumptions`
- `source_cases`
- `verification_method`

- [ ] Explain that missing counter-evidence keeps the experience useful but not mature.

- [ ] Verify docs with:

```bash
git diff --check
```

---

## Phase 3: Log Signal Quality Scoring

### Task 3.1: Score Runtime Log Events

**Files:**
- Create: `tools/agent_memory_runtime/log_signal_quality.py`
- Create: `tests/test_log_signal_quality.py`
- Modify: `tools/agent_memory_runtime/runtime_logs.py`

Log signal dimensions:

- `has_timestamp`
- `has_process`
- `has_level`
- `has_logger`
- `has_event_type`
- `has_stage`
- `has_business_event`
- `has_error_code`
- `has_reason`
- `has_route_or_resource`
- `has_request_or_session_id`
- `has_entity_id_or_key`
- `has_action_result`
- `has_neighbor_context`

- [ ] **Step 1: Write unit tests**

Test:

- Rich log line with request/session/error/route/reason receives `good`.
- Generic log line like `failed` receives `poor`.
- Route log without target route reports missing `route_or_resource`.
- Error log without reason/error code reports missing diagnostic fields.

Expected public function:

```python
def score_log_signal(event: dict[str, Any]) -> dict[str, Any]:
    ...
```

Required output:

```json
{
  "log_signal_score": 0.82,
  "log_signal_band": "good",
  "present_signals": ["timestamp", "level", "logger", "route", "reason"],
  "missing_signals": ["request_id", "session_id"],
  "suggested_log_fields": ["request_id", "session_id"]
}
```

- [ ] **Step 2: Implement scorer**

Use deterministic scoring only. Do not call LLMs.

- [ ] **Step 3: Attach to `analyze-runtime-log` output**

Add:

- per-event `log_signal_score`
- top-level `log_signal_summary`
- top-level `low_signal_events`

- [ ] **Step 4: Verify**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_log_signal_quality tests.test_agent_memory.AgentMemoryRuntimeTests
```

Expected: all tests pass.

### Task 3.2: Score Learned Code Log Statements

**Files:**
- Modify: `tools/agent_memory_runtime/code_wiki.py`
- Modify: `tools/agent_memory_runtime/query.py`
- Test: `tests/test_log_signal_quality.py`

- [ ] Add a test that learns a source file with two logs:

Good log:

```text
[Router] pushUrl target=pages/Profile request_id=${requestId} result=started
```

Weak log:

```text
failed
```

Assert:

- `list --type code-log --json` or `context --json` exposes log signal quality fields.
- Good log scores higher than weak log.

- [ ] Implement deterministic extraction from `message_template`, `raw_statement`, `business_event`, `trigger_stage`, `symptom_terms`, `likely_causes`, and `process_hint`.

- [ ] Verify:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_log_signal_quality tests.test_agent_memory.AgentMemoryRuntimeTests
```

Expected: all tests pass.

---

## Phase 4: Log Design Gap Governance

### Task 4.1: Maintain Actions for Low Log Signal Quality

**Files:**
- Modify: `tools/agent_memory_runtime/governance.py`
- Test: `tests/test_log_signal_quality.py`

- [ ] Add maintain-plan test:

Seed or learn code logs where repeated matched logs are low-signal. Run:

```bash
python tools/agent_memory.py maintain-plan --project <tmp> --json
```

Assert action:

```json
{
  "action": "review_low_log_signal_quality",
  "type": "code_log_statement",
  "governance_lane": "log_diagnosis"
}
```

- [ ] Action should include:

  - `file_path`
  - `function`
  - `message_template`
  - `log_signal_score`
  - `missing_signals`
  - `suggested_log_fields`
  - `suggested_log_template`

- [ ] Suggested template examples:

Route:

```text
[Route] stage=<start|success|failure> target=<page> request_id=<id> result=<result> reason=<reason>
```

Resource:

```text
[Resource] stage=<resolve|render|failure> key=<resource> page=<page> result=<result> reason=<reason>
```

Network/session:

```text
[Request] stage=<start|success|failure> request_id=<id> path=<path> code=<code> reason=<reason>
```

- [ ] Add summary counter:

```json
"low_log_signal_reviews": 1
```

### Task 4.2: Refine Existing `review_log_design_gap`

**Files:**
- Modify: `tools/agent_memory_runtime/governance.py`
- Test: `tests/test_log_signal_quality.py`

- [ ] Extend existing `build_log_design_gap_candidates` output with:

  - `gap_type`
  - `missing_signals`
  - `supporting_reflection_ids`
  - `supporting_log_ids`
  - `suggested_log_template`
  - `expected_diagnosis_benefit`

- [ ] Keep existing action name `review_log_design_gap` for repeated diagnosis gaps.

- [ ] Verify:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_log_signal_quality tests.test_incident_trace
```

Expected: all tests pass.

---

## Phase 5: Evaluation and Regression Gates

### Task 5.1: Experience Maturity Eval

**Files:**
- Create: `tools/agent_memory_runtime/maturity_eval.py`
- Modify: `tools/agent_memory_runtime/cli.py`
- Modify: `tools/agent_memory.py`
- Test: `tests/test_experience_maturity.py`

- [ ] Add optional CLI:

```bash
python tools/agent_memory.py eval-maturity --project . --cases docs/eval/golden-maturity.json --json
```

- [ ] Case shape:

```json
[
  {
    "name": "route-experience-maturity",
    "query": "ArkTS route blank screen",
    "expected_maturity": [
      {"type": "reflections", "id": 1, "experience_maturity": "verified_case", "min_score": 0.7}
    ],
    "must_not_mature": [
      {"type": "reflections", "id": 2, "levels": ["verified_case", "reused_pattern", "skill_candidate"]}
    ]
  }
]
```

- [ ] Report:

  - `expected_maturity_rate`
  - `blocked_false_maturity_rate`
  - `missed_expected_maturity`
  - `unexpected_mature_matches`

### Task 5.2: Log Signal Eval

**Files:**
- Create: `tools/agent_memory_runtime/log_signal_eval.py`
- Modify: `tools/agent_memory_runtime/cli.py`
- Modify: `tools/agent_memory.py`
- Test: `tests/test_log_signal_quality.py`

- [ ] Add optional CLI:

```bash
python tools/agent_memory.py eval-log-signal --project . --cases docs/eval/golden-log-signal.json --json
```

- [ ] Case shape:

```json
[
  {
    "name": "route-logs-have-correlation",
    "query": "route blank screen",
    "expected_log_signal": [
      {"type": "code_log_matches", "text": "pushUrl", "min_log_signal_score": 0.7}
    ],
    "must_not_low_signal": [
      {"type": "code_log_matches", "text": "failed", "max_log_signal_score": 0.4}
    ]
  }
]
```

- [ ] Report:

  - `expected_log_signal_rate`
  - `blocked_low_signal_rate`
  - `missed_expected_log_signal`
  - `unexpected_low_signal_matches`

### Task 5.3: Maintain-Plan Summary Integration

**Files:**
- Modify: `tools/agent_memory_runtime/governance.py`
- Test: `tests/test_experience_maturity.py`
- Test: `tests/test_log_signal_quality.py`

- [ ] If eval files exist under `docs/eval/`, `maintain-plan` may include read-only summaries:

  - `maturity_eval_summary`
  - `log_signal_eval_summary`

- [ ] If quality gate fails, add actions:

  - `review_maturity_regression`
  - `review_log_signal_regression`

- [ ] Do not fail `maintain-plan`; it remains advisory.

---

## Phase 6: Documentation and Skill Protocol

### Task 6.1: Runtime and Usage Docs

**Files:**
- Modify: `docs/runtime.md`
- Modify: `docs/usage-guide.md`

- [ ] Document maturity levels.
- [ ] Document counter-evidence fields.
- [ ] Document log signal dimensions.
- [ ] Document maintain-plan actions.
- [ ] Document eval commands if implemented.

### Task 6.2: Skill Updates

**Files:**
- Modify: `skills/agent-memory-reflect/SKILL.md`
- Modify: `skills/agent-memory-query/SKILL.md`
- Modify: `skills/agent-memory-maintain/SKILL.md`

- [ ] Reflect skill:
  - Require counter-evidence when recording reusable procedure experience.
  - Encourage `does_not_apply_to`, `negative_preconditions`, and `what_failed`.

- [ ] Query skill:
  - Use `experience_maturity` before applying experience as a rule.
  - Treat `raw_observation` as a hint only.
  - Treat `deprecated_pattern` as warning/counter-evidence.

- [ ] Maintain skill:
  - Explain how to review maturity and low-log-signal actions.

### Task 6.3: Gitlog

**Files:**
- Modify: `gitlog.md`

- [ ] Add one dated entry per implemented phase, including:

  - files touched
  - behavior changed
  - verification commands
  - rollback notes

---

## Recommended Execution Order

1. Phase 1: Experience maturity scoring.
2. Phase 2: Counter-evidence governance.
3. Phase 3: Runtime/code log signal scoring.
4. Phase 4: Log design gap governance.
5. Phase 6 docs for the implemented pieces.
6. Phase 5 eval commands only after the first scoring and governance behavior stabilizes.

Reasoning:

- Maturity and counter-evidence immediately improve experience quality and query safety.
- Log signal quality has the next highest diagnostic impact.
- Eval commands are valuable, but they need stable output fields first.

---

## Verification Matrix

Run focused tests after each phase:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_maturity
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_log_signal_quality
```

Run related regression tests before each commit:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_memory_calibration tests.test_calibration_feedback tests.test_calibration_eval
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_performance_scoring tests.test_retrieval_feedback tests.test_retrieval_eval
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_incident_trace
PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py
git diff --check
```

Expected final state:

- All focused tests pass.
- Existing retrieval, calibration, incident trace, and quality tests pass.
- `maintain-plan --json` remains advisory and does not mutate memory.
- Four user-facing skills remain unchanged in number.
- New modules stay under 500 lines.

---

## Rollback Strategy

Rollback by phase:

- Phase 1 rollback:
  - Remove `experience_maturity.py`.
  - Remove query/calibration maturity fields.
  - Remove `tests/test_experience_maturity.py`.

- Phase 2 rollback:
  - Remove maturity governance action builders and summary counters.
  - Revert reflect/query/maintain skill additions.

- Phase 3 rollback:
  - Remove `log_signal_quality.py`.
  - Remove runtime/code log signal output fields.
  - Remove `tests/test_log_signal_quality.py`.

- Phase 4 rollback:
  - Remove low-log-signal maintain actions and refined gap fields.

- Phase 5 rollback:
  - Remove eval commands, parser wiring, and eval tests.

Each rollback should leave stored SQLite data readable. Avoid schema changes unless a later implementation phase explicitly proves derived scoring is too expensive.
