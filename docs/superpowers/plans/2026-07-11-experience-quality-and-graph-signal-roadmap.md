# Experience Quality and Graph Signal Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the combined `1 + 5` direction: improve experience recording/query quality, and improve code graph plus log graph quality so Agent Memory can retrieve less noise, stronger anchors, and better diagnosis context.

**Architecture:** Keep the public interface fixed to the existing four skills. Add deterministic scoring, governance actions, and bounded evaluation around existing SQLite tables before introducing any heavier storage. Current source files, current runtime logs, and user feedback remain more authoritative than historical memory.

**Tech Stack:** Python 3.9+, SQLite, FTS5, existing `tools/agent_memory.py` CLI, existing `unittest` suite, existing four user-facing skills.

---

## Interpretation of `1 + 5`

This plan treats `1 + 5` as two high-leverage tracks from the current mainline:

- **Track 1: Experience quality for recording and query**
  - Improve how reflections/experiences are captured.
  - Separate successful procedure experience from business-semantic correction experience.
  - Reduce interference from weakly related, stale, immature, or contradicted experience.
  - Make experience maturity, counter-evidence, evidence chains, usage feedback, and conflict state influence query trust.

- **Track 5: Code graph and log graph quality**
  - Improve whether learned code/log anchors can guide the Agent to the right file, function, route, resource, and failure signal.
  - Score code graph and log graph health.
  - Detect stale/orphan anchors and low-signal logs.
  - Feed graph/log gaps into maintain actions and future learn-business enrichment.

The two tracks should converge only at query and governance outputs. Do not merge them into one large data model.

---

## Current Foundation

Already available in the project:

- SQLite as source of truth.
- FTS5-backed candidate recall for memory and code/wiki records.
- `code_files`, `code_symbols`, `code_log_statements`, and `memory_edges`.
- `incident_traces` and temporary runtime log analysis.
- Quality scoring, calibration feedback, retrieval evals, graph quality health, evidence chain quality.
- Experience maturity and counter-evidence scoring.
- Four user-facing skills:
  - `agent-memory-learn`
  - `agent-memory-query`
  - `agent-memory-reflect`
  - `agent-memory-maintain`

Non-goals:

- No fifth user-facing skill.
- No vector database in this phase.
- No graph database in this phase.
- No raw user runtime-log persistence.
- No automatic skill generation without human approval.
- No background daemon or watcher.

---

## Target Outcomes

After this roadmap is executed, the runtime should provide:

1. Experience records that can be classified as raw observation, structured candidate, verified case, reused pattern, skill candidate, correction experience, or deprecated pattern.
2. Query results that explain why an experience is trusted, down-weighted, or blocked.
3. Maintain actions that identify exactly which experiences need counter-evidence, verification, merge, deprecation, or promotion review.
4. Code graph quality signals that expose orphan symbols/logs, stale edges, weak anchors, and missing business semantics.
5. Log graph quality signals that expose low-signal log statements, missing correlation fields, missing stage/result/reason fields, and weak incident diagnosis anchors.
6. Evaluation gates that prevent query quality, graph quality, or log diagnosis quality from regressing silently.

---

## File Map

Expected new files:

- `tools/agent_memory_runtime/log_signal_quality.py`
  - Scores runtime log events and learned code log statements.
  - Returns signal score, band, present/missing fields, and suggested logging fields.

- `tools/agent_memory_runtime/experience_query_quality.py`
  - Optional focused helper if query/calibration integration grows too large.
  - Computes query-facing trust explanations from maturity, evidence, feedback, conflict, and counter-evidence fields.

- `tools/agent_memory_runtime/graph_signal_quality.py`
  - Optional focused helper if existing `graph_quality.py` becomes too broad.
  - Scores anchor usefulness, not just structural graph health.

- `tests/test_log_signal_quality.py`
  - Unit and integration tests for log signal scoring.

- `tests/test_experience_query_quality.py`
  - Focused tests for experience trust, suppression, and conflict behavior if current test files become too crowded.

Expected modified files:

- `tools/agent_memory_runtime/query.py`
  - Attach trust reasons and graph/log signal fields to query payloads.

- `tools/agent_memory_runtime/memory_calibration.py`
  - Consume maturity, evidence chain, counter-evidence, feedback, and conflict signals.

- `tools/agent_memory_runtime/governance.py`
  - Add or refine maintain actions for weak experience quality, weak graph anchors, and weak log signal.

- `tools/agent_memory_runtime/runtime_logs.py`
  - Attach log signal quality to temporary runtime log analysis output.

- `tools/agent_memory_runtime/code_wiki.py`
  - Add bounded log/code semantic enrichment only when needed.

- `skills/agent-memory-reflect/SKILL.md`
  - Clarify how to record procedure experience versus business-semantic correction.

- `skills/agent-memory-query/SKILL.md`
  - Clarify how to consume trust, maturity, counter-evidence, and graph/log anchors.

- `skills/agent-memory-maintain/SKILL.md`
  - Clarify review actions and staged maintenance workflow.

- `docs/runtime.md`
  - Runtime field contracts.

- `docs/usage-guide.md`
  - Operator workflow.

- `gitlog.md`
  - Local change record after each completed phase.

File-size guardrail:

- Keep new modules under 500 lines.
- If `query.py`, `governance.py`, or `runtime_logs.py` additions exceed a thin adapter, extract helper modules instead.

---

## Data Contracts

### Experience Query Quality Fields

Each reflection/experience query result should eventually include:

```json
{
  "experience_type": "procedure_experience",
  "experience_maturity": "verified_case",
  "experience_maturity_score": 0.78,
  "evidence_chain_score": 0.8,
  "counter_evidence": {
    "has_counter_evidence": true,
    "fields": ["negative_preconditions", "does_not_apply_to"],
    "missing_fields": []
  },
  "trust_score": 0.72,
  "trust_band": "use_with_care",
  "trust_reasons": [
    "verified incident trace evidence",
    "has negative applicability boundaries",
    "current anchor still exists"
  ],
  "query_risk_flags": []
}
```

Required query behavior:

- `deprecated_pattern`, stale status, conflict, or misleading feedback must cap trust.
- Missing counter-evidence should reduce trust for broadly reusable procedure experience.
- Correction experience should be routed as semantic repair guidance, not as a generic procedure.
- A recent but weakly related experience must not outrank an older exact file/log/source anchor.

### Log Signal Quality Fields

Each runtime log event or learned code log candidate should eventually include:

```json
{
  "log_signal_score": 0.82,
  "log_signal_band": "good",
  "present_signals": ["timestamp", "level", "logger", "route_or_resource", "reason"],
  "missing_signals": ["request_or_session_id"],
  "suggested_log_fields": ["request_id", "session_id"]
}
```

Signal dimensions:

- `timestamp`
- `process`
- `level`
- `logger`
- `event_type`
- `stage`
- `business_event`
- `error_code`
- `reason`
- `route_or_resource`
- `request_or_session_id`
- `entity_id_or_key`
- `action_result`
- `neighbor_context`

Required log behavior:

- Runtime raw logs remain temporary.
- Store durable learnings only as bounded reflections, incident traces, or code-log metadata.
- Low-signal logs should become maintain actions, not automatic source edits.

### Graph Signal Quality Fields

Each graph health report should continue to include structural health and should add anchor usefulness where needed:

```json
{
  "graph_quality": {
    "health_status": "watch",
    "orphan_code_symbols": 2,
    "orphan_code_logs": 1,
    "stale_edges": 0,
    "symbol_anchor_coverage": 0.91,
    "log_anchor_coverage": 0.76
  },
  "graph_signal_quality": {
    "weak_anchor_count": 3,
    "missing_business_semantics": 4,
    "missing_log_signal_fields": 2,
    "top_repair_targets": []
  }
}
```

Required graph behavior:

- Treat `memory_edges` as bounded hints, not full call graph truth.
- Prefer exact source/log/file anchors over fuzzy graph expansion.
- Governance should produce narrow repair targets.

---

## Phase 1: Experience Query Quality Hardening

**Goal:** Make query trust explainable and resistant to irrelevant recent experiences.

**Files:**

- Modify: `tools/agent_memory_runtime/query.py`
- Modify: `tools/agent_memory_runtime/memory_calibration.py`
- Optional create: `tools/agent_memory_runtime/experience_query_quality.py`
- Test: `tests/test_experience_query_quality.py` or `tests/test_experience_maturity.py`

- [x] **Step 1: Add query interference tests**

Create tests with three reflections:

- exact ArkTS route/log correction with current source anchor
- recent but broad procedure experience
- stale or misleading experience with overlapping keywords

Expected:

- exact correction ranks above broad procedure
- stale/misleading record has capped `trust_score`
- result includes `trust_reasons`
- result includes `query_risk_flags` for misleading or missing counter-evidence records

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_query_quality
```

Expected before implementation: fail because query trust reasons are incomplete or module does not exist.

- [x] **Step 2: Implement trust explanation helper**

Create `experience_query_quality.py` only if keeping this inside `memory_calibration.py` would make it bulky.

Required helper signature:

```python
def explain_experience_trust(row: dict[str, Any]) -> dict[str, Any]:
    ...
```

Required output:

```json
{
  "trust_reasons": ["verified evidence chain", "has counter-evidence"],
  "query_risk_flags": ["missing_counter_evidence"],
  "trust_cap": 0.65
}
```

Rules:

- `status in stale, archived, rejected` caps trust at `0.35`.
- `last_outcome == misleading` caps trust at `0.25`.
- `experience_maturity == raw_observation` caps trust at `0.55`.
- `experience_maturity == deprecated_pattern` caps trust at `0.25`.
- missing counter-evidence on `procedure_experience` adds `missing_counter_evidence`.
- correction experience adds `semantic_correction_guidance`, not `procedure_rule`.

- [x] **Step 3: Integrate calibration**

Attach `trust_reasons` and `query_risk_flags` after maturity/evidence scoring and before final payload shaping.

Do not let this bypass existing lane gates or current-source authority.

- [x] **Step 4: Verify focused and regression tests**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_query_quality tests.test_experience_maturity tests.test_memory_calibration tests.test_calibration_feedback
```

Expected: all tests pass.

- [x] **Step 5: Update docs and commit**

Update:

- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-query/SKILL.md`
- `gitlog.md`

Commit:

```bash
git add tools/agent_memory_runtime/query.py tools/agent_memory_runtime/memory_calibration.py tools/agent_memory_runtime/experience_query_quality.py tests/test_experience_query_quality.py docs/runtime.md docs/usage-guide.md skills/agent-memory-query/SKILL.md gitlog.md
git commit -m "Harden experience query trust"
```

---

## Phase 2: Procedure Experience vs Correction Experience Recording

**Goal:** Ensure `reflect` records different experience types in different shapes so future query and skill evolution are not confused.

**Files:**

- Modify: `skills/agent-memory-reflect/SKILL.md`
- Modify: `tools/agent_memory_runtime/reflection.py` or the current reflect handler module
- Modify: `tools/agent_memory_runtime/usage_capture.py` if automatic summary data is used
- Test: `tests/test_agent_memory.py` or `tests/test_experience_query_quality.py`

- [ ] **Step 1: Add reflect shape tests**

Create tests for:

- procedure experience with trigger, preconditions, repair action, verification method
- correction experience with wrong old meaning, corrected meaning, source anchor, evidence

Expected:

- procedure experience gets `experience_type == procedure_experience`
- correction experience gets `experience_type == correction_experience`
- correction experience does not get promoted as a skill candidate from one case
- both include counter-evidence fields when provided

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests
```

- [ ] **Step 2: Refine reflect payload contract**

Minimum procedure fields:

```json
{
  "experience_type": "procedure_experience",
  "trigger_condition": "...",
  "negative_preconditions": ["..."],
  "repair_action": "...",
  "verification_method": "...",
  "source_cases": ["incident_trace:1"]
}
```

Minimum correction fields:

```json
{
  "experience_type": "correction_experience",
  "wrong_assumption": "...",
  "corrected_semantic": "...",
  "applies_to": ["file_or_symbol"],
  "does_not_apply_to": ["..."],
  "evidence": ["current source line", "test output"]
}
```

- [ ] **Step 3: Update skill instructions**

In `agent-memory-reflect`, instruct Agents:

- Use `procedure_experience` only for reusable execution patterns.
- Use `correction_experience` for business/code semantic corrections.
- Always include where the lesson does not apply when the lesson could affect future query direction.
- Use automatic usage summaries as raw material, not as final truth.

- [ ] **Step 4: Verify**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_experience_maturity
```

- [ ] **Step 5: Commit**

```bash
git add tools/agent_memory_runtime skills/agent-memory-reflect/SKILL.md tests gitlog.md
git commit -m "Clarify experience recording shapes"
```

---

## Phase 3: Log Signal Quality Scoring

**Goal:** Score whether logs contain enough fields for goal-oriented incident diagnosis.

**Files:**

- Create: `tools/agent_memory_runtime/log_signal_quality.py`
- Modify: `tools/agent_memory_runtime/runtime_logs.py`
- Modify: `tools/agent_memory_runtime/query.py`
- Test: `tests/test_log_signal_quality.py`

- [ ] **Step 1: Add unit tests for log signal scoring**

Test cases:

- rich route failure log with timestamp, process, level, logger, route, request id, session id, reason, and result returns `good`.
- generic `failed` log returns `poor`.
- route log without route/resource reports missing `route_or_resource`.
- error log without reason/error code reports missing diagnostic fields.

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_log_signal_quality
```

Expected before implementation: fail because module does not exist.

- [ ] **Step 2: Implement `score_log_signal`**

Required public function:

```python
def score_log_signal(event: dict[str, Any]) -> dict[str, Any]:
    ...
```

Return:

```json
{
  "log_signal_score": 0.82,
  "log_signal_band": "good",
  "present_signals": ["timestamp", "level", "logger"],
  "missing_signals": ["request_or_session_id"],
  "suggested_log_fields": ["request_id", "session_id"]
}
```

Band thresholds:

- `good`: `>= 0.75`
- `watch`: `>= 0.55 and < 0.75`
- `poor`: `< 0.55`

- [ ] **Step 3: Attach to `analyze-runtime-log`**

Output additions:

- per-event `log_signal_score`
- per-event `log_signal_band`
- top-level `log_signal_summary`
- top-level `low_signal_events`

Raw logs must still not be persisted to SQLite.

- [ ] **Step 4: Attach to code log matches**

For `context/search` output, enrich `code_log_matches` with log signal fields derived from learned code-log metadata and message templates.

- [ ] **Step 5: Verify**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_log_signal_quality tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_incident_trace
```

- [ ] **Step 6: Docs and commit**

Update:

- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-query/SKILL.md`
- `gitlog.md`

Commit:

```bash
git add tools/agent_memory_runtime/log_signal_quality.py tools/agent_memory_runtime/runtime_logs.py tools/agent_memory_runtime/query.py tests/test_log_signal_quality.py docs/runtime.md docs/usage-guide.md skills/agent-memory-query/SKILL.md gitlog.md
git commit -m "Add log signal quality scoring"
```

---

## Phase 4: Graph Signal Quality Governance

**Goal:** Move beyond structural graph health into usefulness: can the graph actually guide diagnosis and code understanding?

**Files:**

- Modify: `tools/agent_memory_runtime/graph_quality.py`
- Optional create: `tools/agent_memory_runtime/graph_signal_quality.py`
- Modify: `tools/agent_memory_runtime/governance.py`
- Test: `tests/test_graph_quality.py`

- [ ] **Step 1: Add graph signal tests**

Test cases:

- code log with no symbol/file edge is reported as weak anchor.
- symbol with no business summary and no useful query terms is reported as missing semantic anchor.
- maintain-plan returns narrow `review_graph_signal_quality` action with file/log/symbol targets.

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_graph_quality
```

- [ ] **Step 2: Implement anchor usefulness scoring**

Compute:

- `weak_anchor_count`
- `missing_business_semantics`
- `missing_log_signal_fields`
- `top_repair_targets`

Suggested repair target shape:

```json
{
  "target_type": "code_log_statement",
  "target_id": 12,
  "file_path": "entry/src/main/ets/pages/Index.ets",
  "function_name": "aboutToAppear",
  "reason": "log lacks request/session correlation",
  "suggested_fields": ["request_id", "route", "reason"]
}
```

- [ ] **Step 3: Add maintain action**

Add `review_graph_signal_quality` only when targets are concrete.

Do not emit broad actions like "improve graph".

- [ ] **Step 4: Verify**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_graph_quality tests.test_quality_performance_scoring tests.test_retrieval_feedback
```

- [ ] **Step 5: Docs and commit**

Update:

- `docs/runtime.md`
- `docs/code-log-statement-network.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

Commit:

```bash
git add tools/agent_memory_runtime/graph_quality.py tools/agent_memory_runtime/graph_signal_quality.py tools/agent_memory_runtime/governance.py tests/test_graph_quality.py docs/runtime.md docs/code-log-statement-network.md skills/agent-memory-maintain/SKILL.md gitlog.md
git commit -m "Add graph signal quality governance"
```

---

## Phase 5: Retrieval and Diagnosis Evaluation Gates

**Goal:** Make quality improvements measurable so later changes do not quietly increase noise.

**Files:**

- Modify: `tools/agent_memory_runtime/retrieval_eval.py`
- Modify: `tools/agent_memory_runtime/calibration_eval.py`
- Optional create: `tools/agent_memory_runtime/log_signal_eval.py`
- Modify: `tools/agent_memory.py` CLI wiring if adding a command
- Test: `tests/test_retrieval_eval.py`
- Test: `tests/test_calibration_eval.py`
- Test: `tests/test_log_signal_quality.py`

- [ ] **Step 1: Add golden cases**

Create fixtures or inline tests for:

- exact code/log anchor should outrank broad experience.
- stale/misleading experience should be blocked or down-weighted.
- correction experience should appear as semantic repair guidance.
- runtime log with route/resource/request fields should produce higher diagnosis confidence than generic logs.

- [ ] **Step 2: Add metrics**

Minimum metrics:

- `expected_hit_rate`
- `bad_hit_block_rate`
- `exact_anchor_rank`
- `experience_noise_rate`
- `log_signal_good_rate`
- `low_signal_event_rate`

Gate example:

```json
{
  "quality_gate": "pass",
  "expected_hit_rate": 0.9,
  "experience_noise_rate": 0.05,
  "exact_anchor_rank": 1
}
```

- [ ] **Step 3: Wire eval command only if needed**

Prefer extending existing eval commands before adding new commands.

Acceptable command if the current eval modules cannot express log signal:

```bash
python tools/agent_memory.py eval-log-signal --project . --json
```

- [ ] **Step 4: Verify**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_retrieval_eval tests.test_calibration_eval tests.test_log_signal_quality
```

- [ ] **Step 5: Docs and commit**

Update:

- `docs/runtime.md`
- `docs/usage-guide.md`
- `gitlog.md`

Commit:

```bash
git add tools/agent_memory.py tools/agent_memory_runtime tests docs/runtime.md docs/usage-guide.md gitlog.md
git commit -m "Add retrieval and diagnosis quality gates"
```

---

## Phase 6: Skill Guidance and Operator Workflow

**Goal:** Ensure Agents use the new quality signals correctly without exposing a fifth skill to users.

**Files:**

- Modify: `skills/agent-memory-learn/SKILL.md`
- Modify: `skills/agent-memory-query/SKILL.md`
- Modify: `skills/agent-memory-reflect/SKILL.md`
- Modify: `skills/agent-memory-maintain/SKILL.md`
- Modify: `docs/usage-guide.md`
- Modify: `README.md`
- Modify: `gitlog.md`

- [ ] **Step 1: Update learn skill**

Add guidance:

- After learning, inspect parse stats, semantic gaps, graph quality, and low-signal code logs.
- Prefer targeted `learn-business` enrichment over broad re-learning.
- Preserve existing business semantics unless explicitly correcting them.

- [ ] **Step 2: Update query skill**

Add guidance:

- Treat memory as advisory.
- Prefer current source/log/test evidence.
- Use `trust_reasons`, `query_risk_flags`, `experience_maturity`, and `counter_evidence` before applying experience.
- Use code/log/edge anchors as inspection targets, not as proof.

- [ ] **Step 3: Update reflect skill**

Add guidance:

- Record procedure experience and correction experience differently.
- Include counter-evidence and negative preconditions.
- Use runtime usage summaries as input but require explicit final judgment.

- [ ] **Step 4: Update maintain skill**

Add guidance:

- Run quality/governance review in this order:
  1. health and graph quality
  2. retrieval eval
  3. maturity/counter-evidence review
  4. log signal review
  5. merge/stale/archive actions

- [ ] **Step 5: Verify docs**

Run:

```bash
rg -n "fifth skill|new user-facing skill" skills docs README.md
rg -n "experience_maturity|counter_evidence|log_signal|graph_signal" skills docs README.md
git diff --check
```

- [ ] **Step 6: Commit**

```bash
git add skills docs README.md gitlog.md
git commit -m "Update skills for quality-guided memory use"
```

---

## Phase 7: Final Regression and Release Check

**Goal:** Verify the full roadmap does not break the stable runtime entry point or main workflows.

- [ ] **Step 1: Run focused suites**

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_maturity tests.test_experience_query_quality tests.test_log_signal_quality tests.test_graph_quality
```

- [ ] **Step 2: Run main regression**

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_incident_trace tests.test_retrieval_eval tests.test_retrieval_feedback tests.test_calibration_eval tests.test_quality_performance_scoring
```

- [ ] **Step 3: Compile runtime modules**

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py
```

- [ ] **Step 4: Check formatting whitespace**

```bash
git diff --check
```

- [ ] **Step 5: Inspect runtime entry point**

Confirm no new user-facing skill was added and `tools/agent_memory.py` remains the only runtime entry point.

```bash
ls -1 skills
rg -n "argparse|subparsers|add_parser" tools/agent_memory.py tools/agent_memory_runtime/cli.py
```

- [ ] **Step 6: Final commit or push**

Commit any remaining docs or verification updates:

```bash
git add .
git commit -m "Complete experience and graph signal quality roadmap"
```

Push only when requested:

```bash
git push
```

---

## Execution Order Recommendation

Recommended order:

1. Phase 1: Experience Query Quality Hardening
2. Phase 2: Procedure vs Correction Experience Recording
3. Phase 3: Log Signal Quality Scoring
4. Phase 4: Graph Signal Quality Governance
5. Phase 5: Retrieval and Diagnosis Evaluation Gates
6. Phase 6: Skill Guidance and Operator Workflow
7. Phase 7: Final Regression and Release Check

Reasoning:

- Query hardening reduces immediate interference risk.
- Recording shape fixes prevent new low-quality experience from entering the system.
- Log and graph quality then improve diagnosis anchors.
- Evaluation gates come after signals exist.
- Skill docs come last so instructions match implemented behavior.

---

## Acceptance Criteria

- Existing four user-facing skills remain the public interface.
- Query results expose why experience is trusted or down-weighted.
- Procedure experience and correction experience have distinct recording guidance and runtime behavior.
- Low-signal logs are visible in `analyze-runtime-log` and query code-log output.
- Maintain-plan emits narrow actions for experience, log, and graph quality problems.
- Evaluation gates include at least one case that catches irrelevant experience interference.
- Runtime raw logs are not persisted.
- No new persistent graph/vector store is introduced.
- Main regression suites pass.

---

## Rollback Strategy

Rollback by phase:

- Phase 1: remove trust explanation helper and revert query/calibration field additions.
- Phase 2: revert reflect contract changes and skill guidance.
- Phase 3: remove `log_signal_quality.py` and remove log signal fields from runtime/query output.
- Phase 4: remove graph signal helper and maintain action wiring.
- Phase 5: remove eval metric additions or the optional eval command.
- Phase 6: revert skill and docs edits.

Do not roll back unrelated prior work such as FTS5, incident traces, quality scoring, graph health, or experience maturity unless explicitly requested.
