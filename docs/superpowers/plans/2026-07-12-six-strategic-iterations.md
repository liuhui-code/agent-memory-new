# Six Strategic Iterations Execution Plan

> **Goal:** Turn the next six important Agent Memory iterations into a staged, testable roadmap. Keep the user-facing interface fixed at four skills: `agent-memory-learn`, `agent-memory-maintain`, `agent-memory-query`, and `agent-memory-reflect`.

## Direction

The system now has memory storage, reflection, code/log graph learning, incident trace support, quality scoring, evidence profile, query calibration, active learning, memory tiers, and aggregate quality gates. The next work should not add broad new surfaces. It should make the loop more automatic, less noisy, easier to evaluate, and safer at larger scale.

## Phase 1: Automatic Recording And Auto-Summary Loop

**Problem:** High-quality memories still depend on the Agent remembering to call `reflect` manually after useful work.

**Target outcome:** After query, context, runtime-log analysis, and maintain-plan usage, the runtime can prepare a bounded reflection candidate that the Agent can accept, edit, or reject.

**Implementation slices:**

1. Add a `runtime/last_task_trace.json` projection.
   - Inputs: `last_context.json`, `last_runtime_log_analysis.json`, `last_usage_sample.json`, last maintain action batch.
   - Output: compact task trace with `query`, `intent`, `context_used`, `code/log anchors`, `actions_seen`, and `candidate_evidence`.
   - Constraint: do not store raw logs; preserve only compact structured evidence.

2. Add `reflect --from-last-task`.
   - Builds a payload template from the runtime trace.
   - Requires explicit task and lesson if the template is incomplete.
   - Does not auto-write without the existing `reflect` command path.

3. Add auto-summary fields to the payload template.
   - `experience_type` suggestion.
   - `trigger_condition`.
   - `repair_action`.
   - `verification_method`.
   - `source_cases`.
   - `negative_preconditions` / `does_not_apply_to` placeholders when missing.

4. Add maintain actions.
   - `review_unreflected_task_trace`.
   - `review_low_evidence_auto_summary`.

**Acceptance criteria:**

- A task using `context` and `analyze-runtime-log` can produce a reflection payload template without retyping evidence.
- `reflect --from-last-task --json` writes a normal reflection through the existing schema.
- `eval-experience-evidence` catches incomplete auto summaries.
- Raw runtime logs remain outside SQLite.

**Tests:**

- `tests/test_auto_reflection_summary.py`
- `tests/test_experience_evidence_eval.py`
- Existing `tests.test_agent_memory` reflection tests.

**Risks:**

- Auto summaries may overstate evidence. Mitigation: mark all generated templates as candidates and require verification fields before high trust.

## Phase 2: Query Anti-Interference V2

**Problem:** Current intent routing and interference penalties reduce broad experience noise, but intent classes are still coarse.

**Target outcome:** Query returns cleaner context by routing to the right evidence lane before ranking.

**Implementation slices:**

1. Split `memory_intent` into finer intents.
   - `code_location`.
   - `code_business_semantics`.
   - `runtime_log_diagnosis`.
   - `procedure_reuse`.
   - `semantic_correction`.
   - `memory_maintenance`.
   - `general_context`.

2. Add lane budgets per intent.
   - Example: `code_location` prefers wiki/code-log/edge and allows at most one procedure reflection.
   - Example: `semantic_correction` prefers semantic patches and correction guards.

3. Add stricter broad-experience checks.
   - Penalize procedure memories without `negative_preconditions`.
   - Penalize low token overlap unless the query explicitly asks for workflow/procedure.
   - Cap trust when `source_cases` are old or non-source-like.

4. Extend retrieval eval.
   - `expected_memory_intent`.
   - `required_preferred_lanes`.
   - `max_reflection_count`.
   - `must_not_trust`.

**Acceptance criteria:**

- Current-code queries return code/wiki/log anchors before broad experiences.
- Correction queries surface correction guards without turning them into main procedure advice.
- Retrieval golden cases can fail if weak related reflections leak into high-trust context.

**Tests:**

- `tests/test_experience_query_quality.py`
- `tests/test_retrieval_eval.py`
- `tests/test_memory_calibration.py`

**Risks:**

- Over-filtering useful old experience. Mitigation: keep blocked memory notes visible and explainable.

**Implementation status: 2026-07-12 first slice**

Implemented:

- Added compatible `memory_intent_v2` with `code_location`, `code_business_semantics`, `runtime_log_diagnosis`, `semantic_correction`, `memory_maintenance`, `procedure_reuse`, and `general_context`.
- Kept legacy `memory_intent` aliases for existing skill/user compatibility.
- Added per-intent main reflection budgets in `retrieval_lanes.lane_budgets`.
- Strengthened procedure-experience interference penalties for code-location, business-semantics, semantic-correction, missing negative preconditions, and low-overlap non-procedure queries.
- Extended retrieval eval cases with `expected_memory_intent_v2`.
- Added source-case quality profiling and trust caps for weak historical or non-source-like `source_cases`.
- Added retrieval eval support for `max_reflection_count` and `must_not_trust`.

Deferred:

- More nuanced source-case freshness with timestamps and source existence checks.
- Intent-specific lane budgets for non-reflection lanes.

## Phase 3: Experience To Strategy To Skill Candidate Layer

**Problem:** A single reflection cannot safely become a skill. The system needs a middle layer for repeated patterns.

**Target outcome:** Multiple verified experiences can form strategy candidates and later skill candidates without changing the four user-facing skills.

**Implementation slices:**

1. Normalize existing candidate concepts.
   - `skill_pattern_candidate`.
   - `incident_strategy_candidate`.
   - `recurring_incident_fingerprint`.
   - Add a shared candidate summary shape.

2. Add `strategy_candidate` review payload.
   - Supporting reflection ids.
   - Common trigger.
   - Common steps.
   - Common stop conditions.
   - Counter examples.
   - Verification tasks.
   - Suggested skill draft path.

3. Add candidate quality scoring.
   - Support count.
   - Evidence profile completeness.
   - Reuse success.
   - Conflict safety.
   - Evaluation coverage.

4. Add draft-only artifact generation.
   - `maintain-strategy-draft`.
   - Writes Markdown under `docs/strategy-candidates/`.
   - Does not install a new skill.

**Acceptance criteria:**

- At least two verified procedure reflections can produce one strategy candidate.
- A correction experience can influence a strategy but cannot directly become a skill candidate.
- Generated strategy drafts include frontmatter for later promotion review.

**Tests:**

- `tests/test_strategy_candidates.py`
- Existing skill pattern and incident strategy tests.

**Risks:**

- Candidate sprawl. Mitigation: require support count and evidence score before drafting.

## Phase 4: Incremental Code And Log Graph Refresh

**Problem:** Learned projects change over time; old anchors and semantics can become stale.

**Target outcome:** Memory can refresh changed scopes, retire removed structural anchors, and preserve business semantics safely.

**Implementation slices:**

1. Expand learn scope manifest.
   - Store source root, path, command kind, last file hash summary, and refresh timestamp.

2. Add changed-file refresh.
   - Detect changed files in learned scopes.
   - Re-index only changed files.
   - Rebuild edges for changed file ids.

3. Add removed-anchor review.
   - Retire removed code files/symbols/logs structurally.
   - Emit review actions for reflections or semantic patches anchored to removed files.

4. Add semantic conflict refresh.
   - Do not overwrite business summaries automatically.
   - Route divergent current code/business meaning into `semantic_conflicts`.

**Acceptance criteria:**

- `maintain-refresh-scope --changed-only` refreshes changed files without broad relearn.
- Removed code anchors are not returned as source truth.
- Business semantics are preserved or conflict-reviewed, never silently replaced.

**Tests:**

- `tests/test_refresh_scope.py`
- `tests/test_graph_quality.py`
- `tests/test_agent_memory.py` focused learn-business cases.

**Risks:**

- Hashing or scope scans may become expensive. Mitigation: bounded manifests and explicit scope commands.

**Implementation status: 2026-07-13 first slice**

Implemented:

- `learn_scopes` already stores source root, target path or entry path, mode, file snapshot, file count, and refresh timestamps.
- Added `maintain-refresh-scope --changed-only`.
- Changed-only refresh re-indexes only added or changed files and retires removed structural file/symbol/log anchors.
- Refresh output reports `changed_only`, `refreshed_files`, drift lists, and semantic review targets.

**Implementation status: 2026-07-13 second slice**

Implemented:

- Added refresh-time business semantic snapshot and restore for exact-match file, symbol, and log anchors when structural wiki refresh runs in merge mode.
- Added `maintain-refresh-scope` semantic conflict recording for changed files that keep an existing `business_summary`.
- Refresh output now includes `semantic_conflicts`, and the conflicts are durable rows for `maintain-plan` / `list --type semantic-conflict`.

**Implementation status: 2026-07-13 third slice**

Implemented:

- Added `parse_stats.edge_rebuild` for wiki refresh runs.
- Edge rebuild metrics report scoped files, before/after node counts, before/after relation counts, deleted/inserted estimates, and edge delta.
- Changed-only refresh tests now assert that only changed/added files appear in the edge rebuild scope.

**Implementation status: 2026-07-13 fourth slice**

Implemented:

- Added refresh-time structural semantic snapshots for changed files.
- `maintain-refresh-scope` semantic conflicts now describe summary drift and log templates added or removed in `incoming`.
- Refresh tests now assert durable semantic conflicts include log-template drift evidence.

Deferred:

- LLM-assisted semantic divergence comparison against current code intent and user-provided semantic patches.

## Phase 5: Golden Eval Quality Dashboard

**Problem:** Quality gates exist, but trend and failure triage are still manual.

**Target outcome:** The runtime can show recent quality history and convert repeated failures into maintain actions.

**Implementation slices:**

1. Add `eval-quality --history`.
   - Reads bounded JSONL snapshots from `runtime/quality_gate_history.jsonl`.
   - Does not require durable memory tables.

2. Append compact history after each eval-quality run.
   - Timestamp.
   - Selected gates.
   - Pass/fail.
   - Failed gate names.
   - Summary metrics.

3. Add `eval-quality --history --gate <name>`.
   - Filter trend by lane.
   - Show recent status changes and recurring failures.

4. Add maintain action integration.
   - `review_recurring_quality_gate_failure`.
   - Link to latest failed command templates.

5. Add golden-case draft generation from misses.
   - Query misses -> retrieval case draft.
   - Low signal logs -> log signal case draft.
   - Weak evidence claims -> evidence attribution case draft.

**Implementation status: 2026-07-13 first slice**

Implemented:

- `eval-quality` appends compact runtime-only history to `runtime/quality_gate_history.jsonl`.
- `eval-quality --history` returns recent trend, failed gate counts, latest status, and recurring failed gates.
- `eval-quality --history --gate <name>` filters the history to one or more gates.
- `maintain-plan` emits `review_recurring_quality_gate_failure` when a gate fails repeatedly in recent history.
- `eval-draft-cases` writes review-only `.draft.json` cases from open query misses, low-signal runtime logs, and weak evidence task traces.

Deferred:

- Better draft enrichment from concrete failed eval case details, once failed case snapshots are persisted.

**Acceptance criteria:**

- Agents can see whether quality is improving or regressing over the last N runs.
- Recurring failing gates show up in `maintain-plan`.
- Draft cases are generated but not automatically activated.

**Tests:**

- `tests/test_quality_gate_history.py`
- `tests/test_eval_case_seed.py`
- `tests/test_quality_gate_eval.py`

**Risks:**

- History could grow. Mitigation: JSONL bounded compaction or last-N reads only.

## Phase 6: Large-Scale Data Governance

**Problem:** At 500k records, query quality and speed depend on default narrowing, not just indexes.

**Target outcome:** Hot/warm/cold/archive tiers influence query scope, compact summaries reduce token load, and FTS5 stays the default retrieval engine.

**Implementation slices:**

1. Make memory tiers query-aware.
   - Default query uses hot/warm active records.
   - Cold records require explicit history/archive intent or follow-up widening.
   - Archive candidates stay out of normal context.

2. Add compact per-record projections.
   - Short `retrieval_summary`.
   - `evidence_profile_summary`.
   - `business_anchor_summary`.
   - Used in context output before full record expansion.

3. Add lane-specific FTS queries.
   - Query semantic, reflection, code, log, incident lanes separately.
   - Apply per-lane budgets before merge.

4. Add maintain compaction actions.
   - `review_compact_projection_missing`.
   - `review_archive_pressure`.
   - `review_cold_record_noise`.

5. Add performance budgets to quality gates.
   - Query p95 threshold.
   - Token estimate threshold.
   - Result count threshold.

**Acceptance criteria:**

- Normal query stays bounded even with large archives.
- Cold/archive-candidate records do not enter high-trust context by default.
- Maintain compact mode can triage large archives without full payload expansion.

**Tests:**

- `tests/test_memory_tiers.py`
- `tests/test_performance_scoring.py`
- Synthetic fixture with thousands of rows, not 500k full fixture.

**Risks:**

- Query-aware tiers may hide useful old records. Mitigation: explicit widening path and blocked/cold hints.

## Execution Order

1. Phase 1: automatic recording and summary.
2. Phase 2: query anti-interference v2.
3. Phase 5: quality dashboard, because it protects later changes.
4. Phase 4: incremental graph refresh.
5. Phase 3: strategy-to-skill candidate layer.
6. Phase 6: large-scale governance hardening.

This order favors feedback loops first, then correctness, then scale.

## Cross-Phase Invariants

- Keep the four user-facing skills fixed.
- Keep SQLite and FTS5 as the source of truth and retrieval base.
- Keep raw logs temporary.
- Keep generated drafts review-only.
- Keep query fast; heavier work belongs in maintain.
- Every new quality-sensitive behavior needs an eval case or maintain action.

## First Implementation Recommendation

Start with Phase 1 Slice 1-2:

- `runtime/last_task_trace.json`
- `reflect --from-last-task`
- Tests for context/log-analysis-to-reflection payload generation

This creates better raw material for every later phase.

## Implementation Status

### 2026-07-12 Phase 1 Minimal Loop

Implemented:

- `runtime/last_task_trace.json` is generated from the rolling usage sample.
- `reflect --from-last-task` starts from the trace's `reflection_payload_template`.
- `reflect --json` returns the written reflection payload for automation.
- `maintain-plan` emits `review_unreflected_task_trace` when the latest task trace has useful evidence but no reflection has closed it.
- `last_task_trace.json` includes `auto_summary_quality` and `reflection_payload_placeholders` for missing verification, repair, and counter-evidence fields.
- `maintain-plan` emits `review_low_evidence_auto_summary` for weak open trace summaries.
- Tests cover context-to-task-trace and task-trace-to-reflection writes.
- Tests cover maintain-plan detection and suppression after reflection closure.

Deferred:

- Richer domain-specific negative-precondition suggestions beyond generic placeholders.
