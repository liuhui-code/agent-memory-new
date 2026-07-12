# Local Development Log

This repository is currently not a git repository. Use this file as a lightweight local change log so implementation work can be reviewed and manually rolled back.

## Entry Format

```md
## YYYY-MM-DD HH:mm - Short Change Title

Files changed:
- path/to/file

What changed:
- ...

Why:
- ...

Verification:
- Command: ...
- Result: ...

Rollback notes:
- ...
```

## 2026-07-12 - Add governance action limit

Files changed:
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory_runtime/governance.py`
- `tests/test_governance_action_budget.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/superpowers/plans/2026-07-12-governance-action-limit.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- Added `maintain-plan --action-limit N`.
- Wired the limit into `action_budget.top_actions` for both full and compact maintain-plan output.
- Documented small-batch review patterns for large archives and low-token sessions.

Why:
- Fixed-size top-action batches are still too large for some low-token maintenance sessions. A tunable output budget lets Agents inspect one or a few top actions without changing governance scoring or SQLite reads.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_governance_action_budget`
- Result: passes.

Rollback notes:
- Remove the parser flag, action-budget limit wiring, test, and docs if the extra knob proves unnecessary.

## 2026-07-12 - Add compact maintain-plan output

Files changed:
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory_runtime/governance.py`
- `tools/agent_memory_runtime/governance_action_budget.py`
- `tests/test_governance_action_budget.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/superpowers/plans/2026-07-12-maintain-plan-compact-output.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- Added `maintain-plan --compact --json`.
- Compact mode keeps `summary`, governance summaries, `action_budget`, compact top actions, and `health_overview`.
- Compact mode omits heavyweight full action payloads, quality record lists, graph details, memory tier details, and active-learning details.

Why:
- Large archives need a token-saving way to choose the first governance lane before loading full review templates and record details.
- This keeps the optimization output-only and avoids new persistent queues or heavier infrastructure.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_governance_action_budget`
- Result: passes.

Rollback notes:
- Remove the `--compact` parser flag, `compact_maintain_plan_payload`, compact test, and related docs if compact output proves confusing.

## 2026-07-12 - Add governance action budget

Files changed:
- `tools/agent_memory_runtime/governance_action_budget.py`
- `tools/agent_memory_runtime/governance.py`
- `tests/test_governance_action_budget.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/superpowers/plans/2026-07-12-governance-action-budget.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- Added a read-only `action_budget` summary to `maintain-plan`.
- Annotated every maintain action with deterministic `priority_score` and `priority_reasons`.
- Added bounded `top_actions`, counts by lane, and counts by risk so large governance plans can be reviewed in smaller batches.
- Documented that the budget is advisory and does not execute or mutate memory.

Why:
- As memory grows, `maintain-plan` can produce many valid review actions. A compact budget helps Agents spend tokens on the highest-impact actions first without adding persistent schedulers or heavier infrastructure.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_governance_action_budget`
- Result: passes.

Rollback notes:
- Remove `tools/agent_memory_runtime/governance_action_budget.py`, drop action-budget wiring from `governance.py`, and revert the docs/tests if the priority view becomes noisy.

## 2026-07-12 - Add memory tier governance

Files changed:
- `tools/agent_memory_runtime/memory_tiers.py`
- `tools/agent_memory_runtime/governance.py`
- `tests/test_memory_tiers.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/superpowers/plans/2026-07-12-memory-tier-governance.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- Added a read-only `memory_tiers` summary to `maintain-health` and `maintain-plan`.
- Classified recent semantic facts, reflections, and episodes into `hot`, `warm`, `cold`, and `archive_candidate` tiers using status, usage, freshness, confidence, and quality signals.
- Added `review_memory_tier` maintain-plan actions for cold and archive-candidate records.
- Documented the tier view as archive-pressure governance, not automatic deletion or ranking mutation.

Why:
- Large memory archives need a bounded way to separate active useful memory from stale, low-confidence, or unused records before adding heavier retrieval infrastructure.
- Maintenance should review archive pressure explicitly while keeping the four user-facing skills unchanged.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_memory_tiers`
- Result: passes.

Rollback notes:
- Remove `tools/agent_memory_runtime/memory_tiers.py`, drop memory-tier wiring from `governance.py`, and revert the tier docs/tests if the signal is too noisy.

## 2026-07-12 - Add active learning governance queue

Files changed:
- `tools/agent_memory_runtime/active_learning_queue.py`
- `tools/agent_memory_runtime/governance.py`
- `tests/test_active_learning_queue.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/superpowers/plans/2026-07-12-active-learning-governance-queue.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- Added a read-only `active_learning_queue` summary to `maintain-health` and `maintain-plan`.
- Ranked open query misses, weak graph/log anchors, experience usage outcomes, and low-quality memory records into one bounded queue.
- Added `review_active_learning_queue` actions that point to the underlying target without mutating memory.
- Updated docs and maintain skill guidance for consuming the queue.

Why:
- As memory grows, maintain output can contain many independent signals. The queue gives Agents a compact prioritization layer so optimization work starts with the highest expected payoff.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_active_learning_queue`
- Result: fails before `active_learning_queue` exists, then passes.

Rollback notes:
- Remove `active_learning_queue.py`, remove queue integration from `governance.py`, delete the focused test and plan doc, and revert the docs/skill/gitlog updates.

## 2026-07-12 - Add experience evidence log closed loop

Files changed:
- `tools/agent_memory.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory_runtime/storage.py`
- `tools/agent_memory_runtime/models.py`
- `tools/agent_memory_runtime/query.py`
- `tools/agent_memory_runtime/governance.py`
- `tools/agent_memory_runtime/runtime_logs.py`
- `tools/agent_memory_runtime/log_signal_quality.py`
- `tools/agent_memory_runtime/experience_usage.py`
- `tools/agent_memory_runtime/evidence_attribution.py`
- `tools/agent_memory_runtime/otel_lite.py`
- `tests/test_experience_usage.py`
- `tests/test_evidence_attribution.py`
- `tests/test_otel_lite.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/superpowers/plans/2026-07-12-experience-evidence-log-closed-loop.md`
- `skills/agent-memory-query/SKILL.md`
- `skills/agent-memory-maintain/SKILL.md`
- `skills/agent-memory-reflect/SKILL.md`
- `gitlog.md`

What changed:
- Added `experience-usage` to record whether retrieved semantic/reflection records were used, helpful, ignored, misleading, or superseded.
- Added query-time `usage_feedback_bonus`, `usage_feedback_penalty`, and usage reasons for future similar queries.
- Added `maintain-health` and `maintain-plan` visibility for misleading/helpful usage outcomes.
- Added `eval-evidence-attribution` to check whether answer claims are grounded in returned context.
- Added OTel-lite event projection to runtime log analysis output and log signal scoring.
- Updated docs and skills while keeping the fixed four user-facing skills.

Why:
- Experience quality needs a closed loop after retrieval. This lets the system learn which memories actually helped or misled tasks, while keeping raw temporary logs out of durable storage and giving LLMs structured evidence fields that save tokens.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_usage tests.test_evidence_attribution tests.test_otel_lite`
- Result: fails before new commands/modules exist, then passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_log_signal_quality tests.test_retrieval_feedback tests.test_experience_query_quality tests.test_retrieval_eval tests.test_calibration_eval`
- Result: passes.

Rollback notes:
- Remove the three new runtime modules and tests, remove CLI command wiring, remove the `experience_usage_events` table from new schema creation, and revert query/governance/runtime-log/docs/skill changes.

## 2026-05-31 - Add semantic coverage feedback to learn-business

Files changed:
- `tools/agent_memory_runtime/code_wiki.py`
- `skills/agent-memory-learn/SKILL.md`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `tests/test_agent_memory.py`
- `gitlog.md`

What changed:
- Added `semantic_stats` and `semantic_gaps` to `learn-business --json` output.
- Counted file, symbol, and log business coverage for `business_summary` and `business_terms`.
- Listed missing business meaning with stable anchors such as `file_path::symbol` and `file_path::message_template`.
- Wrote the latest learn-business result to `runtime/last_learn_business.json`.
- Updated learn/runtime/usage docs so Agents know to read code first, write structured business meaning, and inspect coverage gaps after learning.

Why:
- Query quality depends on whether learned code has usable business semantics, not just whether files and symbols were indexed. The new feedback gives the Agent a direct way to see what still needs semantic enrichment.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_learn_business_reports_semantic_stats_and_gaps`
- Result: fails before `semantic_stats` exists, then passes.

Rollback notes:
- Remove `semantic_stats` and `semantic_gaps` from `learn-business`, stop writing `last_learn_business.json`, remove the new test, and revert the learn/runtime/usage doc updates.

## 2026-05-31 - Surface semantic gap targets in maintain-plan

Files changed:
- `tools/agent_memory_runtime/governance.py`
- `skills/agent-memory-maintain/SKILL.md`
- `docs/guided-memory-review-workflow.md`
- `tests/test_agent_memory.py`
- `gitlog.md`

What changed:
- Added `semantic_gap_targets` to `maintain-plan` output so query-miss review can point at concrete files, symbols, and logs that still lack business summaries or business terms.
- Added a standalone low-risk `add_business_terms` governance action when learned code memory has semantic gaps.
- Updated maintain workflow docs so Agents use these targets as a narrow enrichment queue for `learn-business`.

Why:
- Governance should not just say "add business terms". It should tell the Agent exactly what to enrich, so query quality can improve without broad re-learning.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_maintain_plan_includes_open_query_miss_actions`
- Result: fails before `semantic_gap_targets` exists, then passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_maintain_plan_adds_business_term_enrichment_action`
- Result: fails before the standalone `add_business_terms` action exists, then passes.

Rollback notes:
- Remove `build_semantic_gap_targets`, remove `semantic_gap_targets` and the `add_business_terms` action from `maintain-plan`, and revert the maintain workflow docs and tests.

## 2026-06-01 - Add learn-business payload templates to maintain-plan

Files changed:
- `tools/agent_memory_runtime/governance.py`
- `skills/agent-memory-maintain/SKILL.md`
- `docs/guided-memory-review-workflow.md`
- `docs/templates/memory-query-answer-skill-template.md`
- `tests/test_agent_memory.py`
- `gitlog.md`

What changed:
- Added `learn_business_payload_template` and `command_template` to low-risk semantic enrichment actions in `maintain-plan`.
- Built the template from existing code wiki rows so files, symbols, and logs are pre-anchored for targeted enrichment.
- Updated maintain and query template docs so Agents reuse the provided template instead of inventing a new payload shape.

Why:
- The Agent should be able to move from governance output to a focused `learn-business` write with minimal manual reconstruction.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_maintain_plan_adds_business_term_enrichment_action`
- Result: fails before `command_template` and `learn_business_payload_template` exist, then passes.

Rollback notes:
- Remove `build_learn_business_payload_template`, remove `command_template` and `learn_business_payload_template` from maintain-plan actions, and revert the doc and test updates.

## 2026-06-01 - Add semantic enrichment workflow steps to maintain-plan

Files changed:
- `tools/agent_memory_runtime/governance.py`
- `skills/agent-memory-maintain/SKILL.md`
- `docs/guided-memory-review-workflow.md`
- `docs/templates/memory-query-answer-skill-template.md`
- `tests/test_agent_memory.py`
- `gitlog.md`

What changed:
- Added `workflow_steps` to semantic enrichment actions in `maintain-plan`.
- Documented that local Agent CLI integrations can follow the returned steps directly when consuming `learn_business_payload_template`.

Why:
- The runtime should give the Agent not just data, but a stable execution order for targeted semantic enrichment.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_maintain_plan_adds_business_term_enrichment_action`
- Result: fails before `workflow_steps` exists, then passes.

Rollback notes:
- Remove `semantic_enrichment_workflow_steps`, remove `workflow_steps` from maintain-plan actions, and revert the related doc and test updates.

## 2026-06-01 - Add learn-business follow-up templates

Files changed:
- `tools/agent_memory_runtime/code_wiki.py`
- `skills/agent-memory-learn/SKILL.md`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `tests/test_agent_memory.py`
- `gitlog.md`

What changed:
- Added `semantic_followup` to `learn-business --json` when semantic gaps remain.
- Included a second-pass `followup_payload_template`, a stable `command_template`, and ordered `workflow_steps`.
- Updated learn/runtime/usage docs so Agents can run targeted follow-up enrichment directly from learn output.

Why:
- Learn should be able to self-correct incomplete business semantics without requiring a separate maintain pass first.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_learn_business_reports_semantic_stats_and_gaps`
- Result: fails before `semantic_followup` exists, then passes.

Rollback notes:
- Remove `semantic_followup_workflow_steps`, `semantic_followup_template`, and `semantic_followup` from `learn-business`, then revert the doc and test updates.

## 2026-06-01 - Return semantic follow-up from learn-entry and learn-path

Files changed:
- `tools/agent_memory_runtime/code_wiki.py`
- `skills/agent-memory-learn/SKILL.md`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `tests/test_agent_memory.py`
- `gitlog.md`

What changed:
- Added `semantic_followup` to `learn-entry --json` and `learn-path --json` when the just-indexed files still lack business semantics.
- Scoped the follow-up template to the files learned by the command, including missing symbol and log business fields.
- Fixed path deduplication in the follow-up builder to preserve case-sensitive file paths.

Why:
- Structural learning should be able to hand off directly to semantic enrichment for the same files without requiring a separate maintain step.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_learn_entry_returns_parse_stats tests.test_agent_memory.AgentMemoryRuntimeTests.test_learn_path_json_returns_parse_stats_for_harmonyos_config`
- Result: fails before `semantic_followup` exists, then passes.

Rollback notes:
- Remove `semantic_followup_from_db`, stop adding `semantic_followup` to `learn-entry` and `learn-path`, and revert the doc and test updates.

## 2026-06-01 - Make learn-business partial updates safe

Files changed:
- `tools/agent_memory_runtime/code_wiki.py`
- `skills/agent-memory-learn/SKILL.md`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `tests/test_agent_memory.py`
- `gitlog.md`

What changed:
- Replaced file-level symbol/log deletion in `learn-business` with object-level merge updates.
- Merged `business_terms` instead of replacing them.
- Preserved existing non-empty `business_summary` values and returned `semantic_conflicts` when incoming non-empty summaries disagreed.

Why:
- Partial semantic enrichment must not delete unmentioned records or silently overwrite existing business meaning.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_learn_business_partial_update_keeps_unmentioned_symbols_and_logs tests.test_agent_memory.AgentMemoryRuntimeTests.test_learn_business_preserves_existing_non_empty_summary_and_reports_conflict`
- Result: fails before object-level merge behavior exists, then passes.

Rollback notes:
- Restore file-level symbol/log rewrite behavior in `learn_business`, remove `semantic_conflicts`, and revert the doc and test updates.

## 2026-06-01 - Surface semantic conflicts in maintain-plan

Files changed:
- `tools/agent_memory_runtime/governance.py`
- `tools/agent_memory_runtime/code_wiki.py`
- `skills/agent-memory-maintain/SKILL.md`
- `docs/guided-memory-review-workflow.md`
- `docs/runtime.md`
- `tests/test_agent_memory.py`
- `gitlog.md`

What changed:
- Added `source_command` and `observed_at` metadata to `semantic_conflicts` emitted by `learn-business`.
- Added `review_semantic_conflict` actions and `summary.semantic_conflicts` to `maintain-plan` by reading the most recent learn-business runtime output.
- Updated maintain/runtime docs so semantic conflicts are treated as review-only governance items.

Why:
- Repeated learning on the same project needs an explicit governance path for conflicting semantic summaries instead of burying conflicts in raw learn output.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_maintain_plan_surfaces_recent_semantic_conflicts tests.test_agent_memory.AgentMemoryRuntimeTests.test_learn_business_preserves_existing_non_empty_summary_and_reports_conflict`
- Result: fails before maintain-plan reads semantic conflicts, then passes.

Rollback notes:
- Remove conflict metadata from `learn_business`, remove `build_recent_semantic_conflicts` and `review_semantic_conflict` actions from `maintain-plan`, and revert the doc and test updates.

## 2026-05-29 - Start experience candidate loop

Files changed:
- `docs/experience-system-plan.md`
- `docs/guided-memory-review-workflow.md`
- `docs/reflection-quality-loop.md`
- `docs/runtime.md`
- `docs/mvp-implementation-plan.md`
- `docs/phase-2-memory-governance-plan.md`
- `references/schema.md`
- `references/obsidian-vault.md`
- `skills/agent-memory-maintain/SKILL.md`
- `skills/agent-memory-reflect/SKILL.md`
- `skills/agent-memory-query/SKILL.md`
- `docs/usage-guide.md`
- `tools/agent_memory.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory_runtime/models.py`
- `tools/agent_memory_runtime/storage.py`
- `tools/agent_memory_runtime/records.py`
- `tools/agent_memory_runtime/query.py`
- `tools/agent_memory_runtime/governance.py`
- `tools/agent_memory_runtime/vault.py`
- `tests/test_agent_memory.py`
- `gitlog.md`

What changed:
- Added the experience system plan and defined Phase One as the `Experience Candidate Loop`.
- Extended structured reflections with `hidden_assumptions`, `negative_preconditions`, `verification_method`, `reuse_feedback`, `source_cases`, and `skill_candidate`.
- Made the new fields persist in the existing `reflections` table through schema migration columns.
- Included the new fields in reflection query matching and reflection quality review.
- Updated reflect/query skill instructions so Agents treat reflections as experience candidates and verify them against current evidence.
- Added `promote_experience_candidate` maintain-plan actions for complete structured reflections.
- Added `suggested_fixes` to query miss review actions: learn missing scope, add business terms, rewrite reflection, or ignore noise.
- Added generated Obsidian review output at `Governance/Experience Candidates.md` and linked it from the vault index.
- Added `reflection_reuse_events` to preserve auditable reuse feedback events behind aggregate reflection fields.
- Restricted `--reflection-outcome` to `helped`, `partial`, `misleading`, and `unused`.
- Added generated Obsidian review output at `Governance/Reflection Reuse.md`.

Why:
- The project distinguishes memory from experience. This change starts the experience layer without adding a new table or fifth skill.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_experience_phase_one_docs_define_candidate_protocol`
- Result: fails before `docs/experience-system-plan.md` exists, then passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_reflect_payload_writes_agent_structured_task_review`
- Result: fails before experience-candidate fields are persisted, then passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_maintain_plan_promotes_complete_experience_candidates`
- Result: fails before maintain-plan emits `promote_experience_candidate`, then passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_maintain_plan_includes_open_query_miss_actions`
- Result: fails before query miss actions include `suggested_fixes`, then passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_vault_export_writes_experience_candidates_dashboard`
- Result: fails before the vault writes `Governance/Experience Candidates.md`, then passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_reflect_records_reuse_feedback_events`
- Result: fails before `reflection_reuse_events` exists, then passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_vault_export_writes_reflection_reuse_dashboard`
- Result: fails before the vault writes `Governance/Reflection Reuse.md`, then passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 61 tests passed.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile install.py tools/agent_memory.py tools/agent_memory_runtime/__init__.py tools/agent_memory_runtime/cli.py tools/agent_memory_runtime/code_wiki.py tools/agent_memory_runtime/governance.py tools/agent_memory_runtime/models.py tools/agent_memory_runtime/query.py tools/agent_memory_runtime/records.py tools/agent_memory_runtime/storage.py tools/agent_memory_runtime/text.py tools/agent_memory_runtime/vault.py tests/test_agent_memory.py`
- Result: passes.
- Command: `git diff --check`
- Result: passes.

Rollback notes:
- Remove the added reflection columns from `GOVERNANCE_COLUMNS`, remove the extra reflection insert/query/review fields, remove the `reflection_reuse_events` table/listing/events, remove `promote_experience_candidate`, query miss `suggested_fixes`, `Experience Candidates.md`, and `Reflection Reuse.md` vault output, delete `docs/experience-system-plan.md`, and revert the skill/doc/test updates.

## 2026-05-31 - Bound search output and force UTF-8 query output

Files changed:
- `tools/agent_memory.py`
- `tools/agent_memory_runtime/query.py`
- `tests/test_agent_memory.py`
- `skills/agent-memory-query/SKILL.md`
- `docs/runtime.md`
- `gitlog.md`

What changed:
- Added bounded `search` output with `result_limits` so large archives do not return unbounded match sets.
- Kept `context` on the same shared limiting path to avoid drift between query commands.
- Reconfigured runtime `stdout` and `stderr` to UTF-8 with replacement mode at startup to reduce terminal-side Chinese garbling.
- Added regression tests for bounded `search` results and raw Chinese query output.

Why:
- Large result sets were causing downstream consumers to choke on oversized query payloads.
- Chinese output should be stable even when the host terminal locale is not configured cleanly.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_search_limits_large_result_sets`
- Result: fails before `search` is bounded, then passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_context_json_stdout_preserves_chinese_text`
- Result: passes and preserves raw Chinese output.

Rollback notes:
- Remove `limited_search`, `SEARCH_RESULT_LIMITS`, UTF-8 stream reconfiguration in `main()`, and the related docs/tests.

## 2026-05-29 - Split code wiki runtime module

Files changed:
- `tools/agent_memory.py`
- `tools/agent_memory_runtime/code_wiki.py`
- `tests/test_agent_memory.py`
- `gitlog.md`

What changed:
- Moved code learning, codebase wiki indexing/search, parse stats, code symbol/log extraction, ArkTS/HarmonyOS parsing, memory edge rebuilding, and entry import resolution into `tools/agent_memory_runtime/code_wiki.py`.
- Kept `tools/agent_memory.py` as the CLI entry point and command handler registry.
- Added a module import regression check for `language_for`.
- Preserved the all-Python-file public fingerprint rule for the new module.

Why:
- Code learning was the largest remaining cohesive domain block inside `tools/agent_memory.py`. Splitting it reduces the entry point to command orchestration and leaves code learning in a dedicated module.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_runtime_modules_expose_project_and_text_helpers`
- Result: fails before `tools/agent_memory_runtime/code_wiki.py` exists, then passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile install.py tools/agent_memory.py tools/agent_memory_runtime/__init__.py tools/agent_memory_runtime/cli.py tools/agent_memory_runtime/code_wiki.py tools/agent_memory_runtime/governance.py tools/agent_memory_runtime/models.py tools/agent_memory_runtime/query.py tools/agent_memory_runtime/records.py tools/agent_memory_runtime/storage.py tools/agent_memory_runtime/text.py tools/agent_memory_runtime/vault.py tests/test_agent_memory.py`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 56 tests passed.
- Command: `git diff --check`
- Result: passes.

Rollback notes:
- Move code learning and wiki helpers from `tools/agent_memory_runtime/code_wiki.py` back into `tools/agent_memory.py`, delete the code wiki module, and remove the code wiki module import assertion.

## 2026-05-29 - Split vault export runtime module

Files changed:
- `tools/agent_memory.py`
- `tools/agent_memory_runtime/vault.py`
- `tests/test_agent_memory.py`
- `gitlog.md`

What changed:
- Moved Obsidian vault initialization, Markdown rendering, vault export, generated governance dashboard export, and vault index generation into `tools/agent_memory_runtime/vault.py`.
- Kept `tools/agent_memory.py` as the CLI entry point and command handler registry.
- Added a module import regression check for `slugify`.
- Preserved the all-Python-file public fingerprint rule for the new module.

Why:
- Vault Markdown generation was a large template-heavy block in `tools/agent_memory.py`. Splitting it makes the runtime entry point smaller and gives vault rendering its own module boundary.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_runtime_modules_expose_project_and_text_helpers`
- Result: fails before `tools/agent_memory_runtime/vault.py` exists, then passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile install.py tools/agent_memory.py tools/agent_memory_runtime/__init__.py tools/agent_memory_runtime/cli.py tools/agent_memory_runtime/governance.py tools/agent_memory_runtime/models.py tools/agent_memory_runtime/query.py tools/agent_memory_runtime/records.py tools/agent_memory_runtime/storage.py tools/agent_memory_runtime/text.py tools/agent_memory_runtime/vault.py tests/test_agent_memory.py`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 56 tests passed.
- Command: `git diff --check`
- Result: passes.

Rollback notes:
- Move vault helpers and command handlers from `tools/agent_memory_runtime/vault.py` back into `tools/agent_memory.py`, delete the vault module, and remove the vault module import assertion.

## 2026-05-29 - Split governance runtime module

Files changed:
- `tools/agent_memory.py`
- `tools/agent_memory_runtime/governance.py`
- `tests/test_agent_memory.py`
- `gitlog.md`

What changed:
- Moved memory governance helpers and command handlers into `tools/agent_memory_runtime/governance.py`.
- The moved code includes stale marking, duplicate detection, memory health, maintain review/plan/status/merge/promote, reflection quality review, and query miss review data.
- Kept `tools/agent_memory.py` as the CLI entry point and command handler registry.
- Added a module import regression check for `reflection_quality_action`.

Why:
- Governance was another large cohesive domain block inside `tools/agent_memory.py`. Splitting it isolates review/maintenance behavior from the runtime entry point.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_runtime_modules_expose_project_and_text_helpers`
- Result: fails before `tools/agent_memory_runtime/governance.py` exists, then passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile install.py tools/agent_memory.py tools/agent_memory_runtime/__init__.py tools/agent_memory_runtime/cli.py tools/agent_memory_runtime/governance.py tools/agent_memory_runtime/models.py tools/agent_memory_runtime/query.py tools/agent_memory_runtime/records.py tools/agent_memory_runtime/storage.py tools/agent_memory_runtime/text.py tests/test_agent_memory.py`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 56 tests passed.
- Command: `git diff --check`
- Result: passes.

Rollback notes:
- Move governance helpers and command handlers from `tools/agent_memory_runtime/governance.py` back into `tools/agent_memory.py`, delete the governance module, and remove the governance module import assertion.

## 2026-05-29 - Split query runtime module

Files changed:
- `tools/agent_memory.py`
- `tools/agent_memory_runtime/query.py`
- `tests/test_agent_memory.py`
- `gitlog.md`

What changed:
- Moved search/context collection, bounded memory edge retrieval, evidence chain building, usage recording, and query miss recording into `tools/agent_memory_runtime/query.py`.
- Kept `search`, `context`, and `wiki-search` command handlers in `tools/agent_memory.py` while delegating query internals to the new module.
- Added a module import regression check for `network_limits`.
- Preserved the all-Python-file public fingerprint rule for the new module.

Why:
- Query logic was one of the largest cohesive blocks left in `tools/agent_memory.py`. Splitting it reduces the runtime entry point while preserving command behavior.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_runtime_modules_expose_project_and_text_helpers`
- Result: fails before `tools/agent_memory_runtime/query.py` exists, then passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile install.py tools/agent_memory.py tools/agent_memory_runtime/__init__.py tools/agent_memory_runtime/cli.py tools/agent_memory_runtime/models.py tools/agent_memory_runtime/query.py tools/agent_memory_runtime/records.py tools/agent_memory_runtime/storage.py tools/agent_memory_runtime/text.py tests/test_agent_memory.py`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 56 tests passed.

Rollback notes:
- Move query/context/miss helper functions from `tools/agent_memory_runtime/query.py` back into `tools/agent_memory.py`, delete the query module, and remove the query module import assertion.

## 2026-05-29 - Split CLI parser and enforce Python file fingerprints

Files changed:
- `install.py`
- `tools/agent_memory.py`
- `tools/agent_memory_runtime/__init__.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory_runtime/models.py`
- `tools/agent_memory_runtime/records.py`
- `tools/agent_memory_runtime/storage.py`
- `tools/agent_memory_runtime/text.py`
- `tests/test_agent_memory.py`
- `gitlog.md`

What changed:
- Added the public project fingerprint comment to every Python file.
- Added a regression test that fails if any project Python file lacks the public fingerprint hash.
- Moved argparse parser construction from `tools/agent_memory.py` into `tools/agent_memory_runtime/cli.py`.
- Moved record helpers for row conversion, output, table type resolution, memory warnings, and id parsing into `tools/agent_memory_runtime/records.py`.
- Kept `tools/agent_memory.py` as the only user-facing runtime entry point and injected command handlers into the CLI builder.

Why:
- The project default rule is that every Python source file carries the public watermark fingerprint.
- Splitting CLI construction continues reducing `tools/agent_memory.py` without changing runtime commands or skill-facing behavior.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_runtime_modules_expose_project_and_text_helpers tests.test_agent_memory.AgentMemoryRuntimeTests.test_all_project_python_files_include_public_fingerprint`
- Result: fails before `cli.py` and fingerprint headers are added, then passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile install.py tools/agent_memory.py tools/agent_memory_runtime/__init__.py tools/agent_memory_runtime/cli.py tools/agent_memory_runtime/models.py tools/agent_memory_runtime/records.py tools/agent_memory_runtime/storage.py tools/agent_memory_runtime/text.py tests/test_agent_memory.py`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 56 tests passed.

Rollback notes:
- Move parser construction and record helpers back into `tools/agent_memory.py`, remove `tools/agent_memory_runtime/cli.py` and `tools/agent_memory_runtime/records.py`, and remove the fingerprint enforcement test if the project no longer wants watermark checks on every Python file.

## 2026-05-28 - Split runtime models, storage, and text helpers

Files changed:
- `tools/agent_memory.py`
- `tools/agent_memory_runtime/__init__.py`
- `tools/agent_memory_runtime/models.py`
- `tools/agent_memory_runtime/storage.py`
- `tools/agent_memory_runtime/text.py`
- `tests/test_agent_memory.py`
- `gitlog.md`

What changed:
- Kept `tools/agent_memory.py` as the only user-facing runtime entry point.
- Added an internal `agent_memory_runtime` package for smaller implementation modules.
- Moved project dataclass, constants, schema governance constants, and runtime layout constants into `models.py`.
- Moved project resolution, memory-home handling, SQLite connection/schema/migration, config writing, and initialization helpers into `storage.py`.
- Moved tokenization, query expansion, JSON list helpers, code search term generation, and weighted scoring helpers into `text.py`.
- Added a regression test that imports the new modules and verifies query expansion still works.

Why:
- `tools/agent_memory.py` had grown past 3600 lines. Splitting stable helper layers reduces cognitive load while preserving the CLI contract required by the MVP.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_runtime_modules_expose_project_and_text_helpers`
- Result: fails before module creation, then passes after the refactor.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/models.py tools/agent_memory_runtime/storage.py tools/agent_memory_runtime/text.py tests/test_agent_memory.py`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 55 tests passed.

Rollback notes:
- Move the constants and helper functions from `tools/agent_memory_runtime/` back into `tools/agent_memory.py`, delete the package, and remove the module import regression test.

## 2026-05-28 - Rewrite experience system principles

Files changed:
- `docs/experience-system-principles.md`
- `gitlog.md`

What changed:
- Reframed memory as compressed facts and experience as higher-level abstraction over facts, hidden assumptions, reasoning, and validation.
- Added Memory / Reflection / Experience layer boundaries.
- Mapped Kolb experiential learning, Case-Based Reasoning, double-loop learning, SECI, MemGPT/Letta, Generative Agents, Zep, and Voyager ideas to this project.
- Documented project principles: reflection is only an experience candidate, experience requires preconditions and counterexamples, query should prefer experience before evidence drill-down, and validated experience may become a skill.

Why:
- The project needs a clearer distinction between the memory system and the higher-level experience system before adding more reflection or governance features.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py`
- Result: passes.
- Command: `git diff --check`
- Result: passes.

Rollback notes:
- Restore the previous `docs/experience-system-principles.md` content from git history if the project should return to the earlier reflection-focused principles.

## 2026-05-28 - Add local ownership fingerprint

Files changed:
- `tools/agent_memory.py`
- `.gitignore`
- `.fingerprint-salt` (local ignored file)
- `gitlog.md`

What changed:
- Added a public salted SHA256 fingerprint constant to the runtime script.
- Added `.fingerprint-salt` to `.gitignore`.
- Stored the private salt, owner/project inputs, and local verification method in `.fingerprint-salt`.

Why:
- Provide a lightweight authorship/provenance marker that survives direct code copying while keeping the proof material local and untracked.

Verification:
- Command: local fingerprint verification command
- Result: fingerprint verification ok.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py`
- Result: passes.
- Command: `git check-ignore -v .fingerprint-salt`
- Result: `.fingerprint-salt` is ignored by `.gitignore`.

Rollback notes:
- Remove `PROJECT_FINGERPRINT_SCHEME` and `PROJECT_FINGERPRINT` from `tools/agent_memory.py`, remove `.fingerprint-salt` from `.gitignore`, and delete the local `.fingerprint-salt` file if the watermark is no longer wanted.

## 2026-05-28 - Add Agent-structured reflection payloads

Files changed:
- `tools/agent_memory.py`
- `tests/test_agent_memory.py`
- `skills/agent-memory-reflect/SKILL.md`
- `README.md`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/mvp-implementation-plan.md`
- `docs/phase-2-memory-governance-plan.md`
- `references/schema.md`
- `gitlog.md`

What changed:
- Added `reflect --payload` and `reflect --payload-file` for Agent-authored task reviews.
- Added structured reflection fields for task type, outcome, problem, reasoning summary, context used, worked actions, and failed actions.
- Included those fields in reflection search/context scoring and Obsidian reflection export.
- Updated the reflection skill to make the local Agent CLI organize successful or failed diagnosis, design, execution, and workflow attempts before writing memory.

Why:
- Reflection should capture how an Agent located a problem, designed a fix, executed work, or failed, so future recursive query loops can reuse real evidence and reasoning rather than vague lessons.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tests/test_agent_memory.py install.py`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 54 tests passed.

Rollback notes:
- Remove the new reflection columns from `GOVERNANCE_COLUMNS`, remove payload parsing from `reflect`, and revert the skill/docs examples to argument-only reflection writes.

## 2026-05-28 - Separate learning source from memory archive

Files changed:
- `tools/agent_memory.py`
- `tests/test_agent_memory.py`
- `agent.md`
- `README.md`
- `docs/mvp-implementation-plan.md`
- `docs/usage-guide.md`
- `docs/runtime.md`
- `references/schema.md`
- `skills/agent-memory-learn/SKILL.md`
- `gitlog.md`

What changed:
- Added `--source` to `learn-entry`, `learn-path`, and `wiki-index`.
- Kept `--project` as the memory archive and query context.
- Allowed learning code from any external source root while archiving learned files into the current project memory.
- Kept stored code file paths relative to the learned source root.

Why:
- The project parameter should act as an archive/query context, while the learned source path may live anywhere on disk.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_learn_path_can_archive_external_source_into_current_project_memory tests.test_agent_memory.AgentMemoryRuntimeTests.test_learn_entry_follows_imports_inside_external_source_but_archives_current_project tests.test_agent_memory.AgentMemoryRuntimeTests.test_wiki_index_can_replace_archive_from_external_source`
- Result: passes after implementation.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 43 tests passed.
- Command: `python3 tools/agent_memory.py init --project . --memory-home /private/tmp/agent-memory-new-source-verify && python3 tools/agent_memory.py doctor --project . --memory-home /private/tmp/agent-memory-new-source-verify`
- Result: all checks report OK after initialization.

Rollback notes:
- Remove `--source`, `project_for_learning_source`, and external-source tests to return to requiring learned paths inside `--project`.

## 2026-05-28 - Add memory-aware answer skill template

Files changed:
- `docs/templates/memory-query-answer-skill-template.md`
- `README.md`
- `docs/usage-guide.md`
- `gitlog.md`

What changed:
- Added a copyable local Agent CLI skill template for using `context --json`.
- Documented query input shaping, returned field interpretation, recursive follow-up search, log-first querying, and final answer organization.
- Added the rule that final answers must be summarized conclusions, not raw memory result dumps.

Why:
- Users need a practical skill showing how to consume query results and turn memory hits, logs, wiki matches, and edges into a final answer.

Verification:
- Command: `python3 -m py_compile tools/agent_memory.py`
- Result: runtime still compiles; this change is documentation/template only.

Rollback notes:
- Remove `docs/templates/memory-query-answer-skill-template.md` and its links from README and usage guide.

## 2026-05-28 - Make ArkTS learning more knowledge-like

Files changed:
- `tools/agent_memory.py`
- `tests/test_agent_memory.py`
- `docs/code-log-statement-network.md`
- `references/schema.md`
- `references/codebase-wiki.md`
- `skills/agent-memory-learn/SKILL.md`
- `gitlog.md`

What changed:
- Added readable ArkTS file summaries with components, routes, and resources.
- Added readable ArkTS symbol summaries for components, routes, resources, functions, and classes.
- Added deterministic ArkTS network edges: `imports`, `routes_to`, and `uses_resource`.
- Allowed those ArkTS relations in bounded one-hop query context.

Why:
- ArkTS learning should behave more like a lightweight knowledge base and navigable network, not only a flat symbol dump.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_arkts_learning_writes_knowledge_summaries_for_files_and_symbols tests.test_agent_memory.AgentMemoryRuntimeTests.test_arkts_memory_edges_connect_imports_routes_and_resources`
- Result: passes after implementation.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 40 tests passed.

Rollback notes:
- Remove ArkTS summary generation, `insert_arkts_knowledge_edges`, and the new allowed edge relations if the graph needs to return to file/symbol/log-only behavior.

## 2026-05-28 - Move memory storage to global memory home

Files changed:
- `tools/agent_memory.py`
- `install.py`
- `tests/test_agent_memory.py`
- `agent.md`
- `README.md`
- `docs/mvp-implementation-plan.md`
- `docs/usage-guide.md`
- `docs/runtime.md`
- `docs/superpowers/specs/2026-05-28-global-memory-home-design.md`
- `docs/superpowers/plans/2026-05-28-global-memory-home.md`
- `references/schema.md`
- `references/obsidian-vault.md`
- `skills/agent-memory-learn/SKILL.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- Added configurable global memory home resolution: `--memory-home`, `AGENT_MEMORY_HOME`, then `~/.agent-memory`.
- Changed project storage to `projects/<project_id>/` under the memory home.
- Kept each project in its own SQLite database, runtime cache, and generated vault.
- Updated installer, docs, skills, and tests for the global layout.

Why:
- Learned projects should be source inputs only. Memory data should live in a shared user-configurable location.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_init_uses_configured_global_memory_home_without_project_local_state tests.test_agent_memory.AgentMemoryRuntimeTests.test_environment_memory_home_is_used_when_cli_option_is_absent tests.test_agent_memory.AgentMemoryRuntimeTests.test_global_memory_home_keeps_project_databases_isolated`
- Result: passes after implementation.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 38 tests passed.
- Command: `python3 tools/agent_memory.py doctor --project . --memory-home /private/tmp/agent-memory-new-verify-global`
- Result: all checks report OK.

Rollback notes:
- Revert the `resolve_project`/`--memory-home` changes and restore `memory_dir = root / ".agent-memory"` if project-local storage is needed again.
- Existing global memory directories can be deleted manually after exporting any needed vault files.

## 2026-05-26 - Add MVP planning documents

Files changed:
- `agent.md`
- `AGENTS.md`
- `README.md`
- `docs/mvp-implementation-plan.md`
- `gitlog.md`

What changed:
- Reframed the project around Skill-driven Memory Runtime.
- Documented SQLite as the source of truth and Obsidian as a generated mirror.
- Added the detailed MVP implementation plan.
- Added repository instructions for future coding agents.
- Added this local development log.

Why:
- Establish a stable implementation target before writing runtime code.
- Preserve the decisions from the design discussion in project files.

Verification:
- Command: `rg --files`
- Expected: all new documentation files are present.

Rollback notes:
- Restore the previous `agent.md` from editor history if needed.
- Delete `AGENTS.md`, `README.md`, `docs/mvp-implementation-plan.md`, and `gitlog.md` to return to the earlier minimal documentation state.

## 2026-05-26 - Implement MVP runtime, skills, and installer

Files changed:
- `.gitignore`
- `docs/mvp-implementation-plan.md`
- `tools/agent_memory.py`
- `install.py`
- `skills/agent-memory-init/SKILL.md`
- `skills/agent-memory-query/SKILL.md`
- `skills/agent-memory-update/SKILL.md`
- `skills/agent-memory-reflect/SKILL.md`
- `skills/agent-memory-wiki/SKILL.md`
- `skills/agent-memory-vault/SKILL.md`
- `references/schema.md`
- `references/skill-protocol.md`
- `references/obsidian-vault.md`
- `references/codebase-wiki.md`

What changed:
- Added the local Agent Memory runtime CLI.
- Added SQLite initialization, doctor checks, updates, search, context, reflection, vault export, and wiki indexing.
- Added six runtime-calling skills.
- Added an installer for project-local runtime and skill setup.
- Ignored generated runtime state and locally installed skills.
- Marked implementation plan checklist items complete after verification.

Why:
- Execute the documented MVP plan and make the project usable by local Agents through skills.

Verification:
- Command: `python3 tools/agent_memory.py init --project .`
- Result: initialized successfully.
- Command: `python3 tools/agent_memory.py doctor --project .`
- Result: all checks OK.
- Command: `python3 tools/agent_memory.py context --project . --query "如何对接本地 agent cli" --json`
- Result: returned the stored semantic fact.
- Command: `python3 tools/agent_memory.py vault-export --project .`
- Result: generated `.agent-memory/vault/index.md` and memory pages.
- Command: `python3 tools/agent_memory.py wiki-search --project . --query memory --json`
- Result: returned indexed files and symbols.

Rollback notes:
- Delete `.gitignore`, `tools/agent_memory.py`, `install.py`, `skills/`, `references/`, and generated `.agent-memory/` / `.agent-skills/` directories if reverting the runtime implementation.

## 2026-05-26 - Add skill-first usage guidance

Files changed:
- `docs/usage-guide.md`
- `README.md`
- `agent.md`
- `skills/agent-memory-wiki/SKILL.md`
- `gitlog.md`

What changed:
- Added user-facing guidance that normal use should start with natural language and skills.
- Documented current wiki usage and the planned `learn-entry` / `learn-path` direction for partial project memory.
- Updated project docs to preserve the design rule: LLM invokes skills, skills invoke deterministic runtime commands.

Why:
- Improve usability and lower the command memorization burden for users.

Verification:
- Command: `python3 tools/agent_memory.py doctor --project .`
- Expected: all checks OK.

Rollback notes:
- Remove `docs/usage-guide.md` and revert the README, agent, skill, and gitlog edits from this entry.

## 2026-05-26 - Simplify to four skills and add local learning commands

Files changed:
- `tools/agent_memory.py`
- `skills/agent-memory-learn/SKILL.md`
- `skills/agent-memory-maintain/SKILL.md`
- `skills/agent-memory-query/SKILL.md`
- `skills/agent-memory-reflect/SKILL.md`
- `README.md`
- `agent.md`
- `docs/usage-guide.md`
- `docs/mvp-implementation-plan.md`
- `gitlog.md`

What changed:
- Collapsed user-facing skills into Learn, Query, Maintain, and Reflect.
- Added `learn-entry` for entry-file-based local memory indexing.
- Added `learn-path` for directory-based local memory indexing.
- Updated usage docs so natural language maps to the four skills.

Why:
- Lower the user-facing skill count and make partial project memory easier to use.

Verification:
- Command: `python3 tools/agent_memory.py learn-entry --project . --entry tools/agent_memory.py --depth 1 --json`
- Expected: indexes the entry file and writes `last_learn_entry.json`.
- Command: `python3 tools/agent_memory.py learn-path --project . --path skills`
- Expected: indexes skill files and writes a learning episode.

Rollback notes:
- Revert `tools/agent_memory.py` parser and learning helpers.
- Restore removed skill directories if returning to the previous six-skill model.

## 2026-05-26 - Add recursive memory query integration templates

Files changed:
- `docs/templates/diagnosis-memory-query-template.md`
- `docs/templates/change-design-memory-query-template.md`
- `skills/agent-memory-query/SKILL.md`
- `docs/usage-guide.md`
- `README.md`
- `gitlog.md`

What changed:
- Added a recursive memory-query template for bug diagnosis skills.
- Added a recursive memory-query template for design/change planning skills.
- Kept `agent-memory-query` small and pointed complex workflows to reusable templates.

Why:
- Support recursive memory interaction without turning the query skill into a complex diagnosis or design skill.

Verification:
- Command: `python3 tools/agent_memory.py doctor --project .`
- Expected: all checks OK.

Rollback notes:
- Delete `docs/templates/` and revert the query skill, usage guide, README, and gitlog edits from this entry.

## 2026-05-27 - Add Phase 2 memory governance

Files changed:
- `tools/agent_memory.py`
- `.gitignore`
- `agent.md`
- `README.md`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/mvp-implementation-plan.md`
- `docs/phase-2-memory-governance-plan.md`
- `references/schema.md`
- `skills/agent-memory-learn/SKILL.md`
- `skills/agent-memory-maintain/SKILL.md`
- `skills/agent-memory-query/SKILL.md`
- `skills/agent-memory-reflect/SKILL.md`
- `gitlog.md`

What changed:
- Added schema migration for memory governance metadata: status, scope, evidence, usage, review, merge, stale reason, and episode promotion fields.
- Added `maintain-health`, `maintain-review`, `maintain-status`, `maintain-merge`, and `maintain-promote` runtime commands.
- Updated `context` and `search` output to include governance metadata and advisory warnings.
- Added generated Obsidian governance dashboard pages under `Governance/`.
- Updated skill and usage docs while preserving the four-skill interface.

Why:
- Keep memory clean as records grow, without slowing the normal query path or adding a new user-facing skill.

Verification:
- Command: `python3 tools/agent_memory.py doctor --project .`
- Expected: all checks OK and existing database migrates.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py`
- Expected: no syntax errors.
- Command: `python3 tools/agent_memory.py maintain-health --project . --json`
- Expected: JSON health summary with counts and recommended actions.
- Command: `python3 tools/agent_memory.py vault-export --project .`
- Expected: governance dashboard Markdown files are generated.

Rollback notes:
- Revert the runtime governance commands and schema migration additions.
- Revert skill/docs/gitlog edits from this entry.
- Existing SQLite files may retain extra nullable columns; they are backwards compatible with the earlier runtime unless older code assumes exact table shapes.

## 2026-05-27 - Make partial learning incremental by default

Files changed:
- `tools/agent_memory.py`
- `tests/test_agent_memory.py`
- `README.md`
- `agent.md`
- `docs/usage-guide.md`
- `docs/mvp-implementation-plan.md`
- `docs/phase-2-memory-governance-plan.md`
- `skills/agent-memory-learn/SKILL.md`
- `gitlog.md`

What changed:
- Added tests for default merge behavior and explicit replace behavior.
- Changed `learn-entry` and `learn-path` to merge learned files into the existing codebase wiki by default.
- Added `--replace` to `learn-entry` and `learn-path` for explicit reset/relearn workflows.
- Updated user-facing docs and the learn skill to explain incremental partial learning.

Why:
- Make "add part of a project to memory" behave naturally across multiple entry files or directories.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Expected: two tests pass.

Rollback notes:
- Revert `write_wiki_index` merge behavior and remove the `--replace` parser options.
- Remove `tests/test_agent_memory.py` if returning to manual verification only.

## 2026-05-27 - Add guided memory review workflow

Files changed:
- `tools/agent_memory.py`
- `tests/test_agent_memory.py`
- `skills/agent-memory-maintain/SKILL.md`
- `docs/guided-memory-review-workflow.md`
- `docs/usage-guide.md`
- `docs/runtime.md`
- `docs/phase-2-memory-governance-plan.md`
- `docs/mvp-implementation-plan.md`
- `README.md`
- `agent.md`
- `gitlog.md`

What changed:
- Added `maintain-plan`, a read-only command that converts review signals into confirmable action candidates.
- Added tests for stale exclusion, promote, merge, and maintain plan behavior.
- Updated the maintain skill to run doctor, health, plan, user confirmation, then confirmed governance actions.
- Documented the guided review workflow and confirmation boundary.

Why:
- Make memory governance usable through the skill layer instead of requiring users to interpret raw JSON manually.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Expected: six tests pass.

Rollback notes:
- Remove `maintain-plan` parser/function and the guided workflow docs.
- Revert the maintain skill and usage/runtime documentation updates from this entry.

## 2026-05-27 - Add reflection quality loop

Files changed:
- `tools/agent_memory.py`
- `tests/test_agent_memory.py`
- `skills/agent-memory-reflect/SKILL.md`
- `skills/agent-memory-maintain/SKILL.md`
- `skills/agent-memory-query/SKILL.md`
- `docs/reflection-quality-loop.md`
- `docs/usage-guide.md`
- `docs/runtime.md`
- `docs/guided-memory-review-workflow.md`
- `docs/phase-2-memory-governance-plan.md`
- `docs/mvp-implementation-plan.md`
- `references/schema.md`
- `README.md`
- `agent.md`
- `gitlog.md`

What changed:
- Added actionable reflection fields: trigger condition, anti-pattern, repair action, applies-to, and does-not-apply-to.
- Added reflection reuse feedback with used reflection ids and outcome tracking.
- Added `reflect-review`, a read-only reflection quality checker.
- Integrated reflection quality actions into `maintain-plan`.
- Extended `maintain-promote` to support `--reflection-id`.
- Added Reflection Quality vault dashboard output.

Why:
- Make reflections more actionable, reusable, and governable without adding a new user-facing skill.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Expected: thirteen tests pass.

Rollback notes:
- Remove reflection quality migration fields, parser args, `reflect-review`, and reflection promotion support.
- Revert reflection quality docs and skill updates from this entry.

## 2026-05-27 - Rewrite README in classic bilingual format

Files changed:
- `README.md`
- `gitlog.md`

What changed:
- Reworked README into a classic project structure: features, why use it, architecture, quick start, usage, commands, documentation, and roadmap.
- Added a full Chinese version with 特性、为何使用、快速开始、如何使用、常用命令、将来规划.
- Kept current runtime capabilities in the README, including query misses, reflection quality, and memory governance.

Why:
- Make the project easier to understand for first-time readers and Chinese users.

Verification:
- Command: checked README Markdown fence balance with a Python one-liner.
- Expected: balanced fences.

Rollback notes:
- Revert `README.md` and this gitlog entry.

## 2026-05-27 - Rewrite README in concise bilingual format

Files changed:
- `README.md`
- `gitlog.md`

What changed:
- Rewrote README again into a cleaner open-source style with English and Chinese sections.
- Kept the classic structure: features, why use it, architecture, quick start, usage, common commands, docs, and roadmap.
- Shortened repeated explanations while preserving current runtime capabilities.

Why:
- Improve readability and make the first page easier to scan.

Verification:
- Command: checked README Markdown fence balance with a Python one-liner.
- Expected: balanced fences.

Rollback notes:
- Revert `README.md` and this gitlog entry.

## 2026-05-27 - Add query miss feedback loop

Files changed:
- `tools/agent_memory.py`
- `tests/test_agent_memory.py`
- `skills/agent-memory-query/SKILL.md`
- `skills/agent-memory-maintain/SKILL.md`
- `docs/query-miss-feedback-loop.md`
- `docs/usage-guide.md`
- `docs/runtime.md`
- `docs/guided-memory-review-workflow.md`
- `docs/phase-2-memory-governance-plan.md`
- `docs/mvp-implementation-plan.md`
- `references/schema.md`
- `README.md`
- `agent.md`
- `gitlog.md`

What changed:
- Added `query_misses` storage for fully failed `context`, `search`, and `wiki-search` retrievals.
- Added `miss-list` and `miss-status` commands.
- Integrated open query misses into `maintain-plan` as `review_query_miss` actions.
- Added `Governance/Query Misses.md` vault dashboard output.
- Documented the feedback loop as an alternative to manual keyword maintenance.

Why:
- Improve retrieval over time by observing real misses, without adding manual keyword or alias maintenance burden.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Expected: query miss tests and existing runtime tests pass.

Rollback notes:
- Remove `query_misses` table creation, miss commands, miss recording hooks, and vault dashboard output.
- Revert query miss docs and skill updates from this entry.

## 2026-05-28 - Add code log statement network

Files changed:
- `tools/agent_memory.py`
- `tests/test_agent_memory.py`
- `agent.md`
- `README.md`
- `docs/code-log-statement-network.md`
- `docs/usage-guide.md`
- `docs/runtime.md`
- `docs/mvp-implementation-plan.md`
- `docs/templates/diagnosis-memory-query-template.md`
- `docs/templates/change-design-memory-query-template.md`
- `references/schema.md`
- `skills/agent-memory-learn/SKILL.md`
- `skills/agent-memory-query/SKILL.md`
- `skills/agent-memory-maintain/SKILL.md`
- `skills/agent-memory-reflect/SKILL.md`
- `gitlog.md`

What changed:
- Added `code_log_statements` and `memory_edges` tables.
- Added code learning extraction for Python, JavaScript/TypeScript, Dart, and Swift log-like statements.
- Rebuilds deterministic code wiki edges after learning: file contains symbol, file contains log statement, and symbol emits log.
- Added `code_log_matches` and `edge_matches` to query context, and log statement results to `wiki-search`.
- Added generated Obsidian pages for code log statements and memory edges.
- Documented the feature as part of the existing four-skill workflow.

Why:
- Let Agents diagnose from observed log/output strings and move toward related files/functions without adding a fifth user-facing skill.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 26 tests passed.

Rollback notes:
- Remove `code_log_statements` and `memory_edges` schema additions, extraction helpers, query/vault integrations, and list types.
- Revert the code log statement network docs and skill/readme updates from this entry.

## 2026-05-28 - Bound network query context

Files changed:
- `tools/agent_memory.py`
- `tests/test_agent_memory.py`
- `README.md`
- `docs/runtime.md`
- `docs/code-log-statement-network.md`
- `docs/phase-2-memory-governance-plan.md`
- `references/schema.md`
- `skills/agent-memory-query/SKILL.md`
- `gitlog.md`

What changed:
- Added hard query fast-path limits for network memory: one-hop depth, 10 edge matches, and 3 evidence chains.
- Added an allowed relation whitelist for query edge matches.
- Added `network_limits` and compact one-hop `evidence_chains` to `context` output.
- Documented that recursive investigation belongs to the LLM skill layer, not runtime graph traversal.

Why:
- Prevent network memory from becoming an expensive or looping graph traversal while still giving Agents useful evidence hints.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 28 tests passed.

Rollback notes:
- Remove `NETWORK_*` constants, relation filtering, evidence chain output, and related tests/docs.

## 2026-05-28 - Add HarmonyOS ArkTS code learning support

Files changed:
- `tools/agent_memory.py`
- `tests/test_agent_memory.py`
- `README.md`
- `docs/code-log-statement-network.md`
- `docs/usage-guide.md`
- `docs/mvp-implementation-plan.md`
- `references/schema.md`
- `references/codebase-wiki.md`
- `skills/agent-memory-learn/SKILL.md`
- `gitlog.md`

What changed:
- Added `.ets` language detection as ArkTS.
- Added lightweight ArkTS symbol extraction for `struct` components, classes, functions, and lifecycle/build methods.
- Added ArkTS log extraction for `console.*`, `logger.*`, and `hilog.*`, including hilog format-message detection.
- Added `learn-entry` import following for ArkTS relative imports.
- Updated user docs and skill guidance for HarmonyOS projects.

Why:
- Improve first-class usability for HarmonyOS/ArkTS developers while keeping the runtime deterministic and lightweight.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 30 tests passed.

Rollback notes:
- Remove `.ets` from `CODE_EXTENSIONS`, ArkTS extraction/import branches, ArkTS tests, and related docs.

## 2026-05-28 - Add HarmonyOS config, route, and resource learning

Files changed:
- `tools/agent_memory.py`
- `tests/test_agent_memory.py`
- `README.md`
- `docs/usage-guide.md`
- `docs/mvp-implementation-plan.md`
- `references/codebase-wiki.md`
- `skills/agent-memory-learn/SKILL.md`
- `gitlog.md`

What changed:
- Added `.json5` HarmonyOS config indexing.
- Extracted config symbols for abilities, permissions, dependencies, and page profiles.
- Extracted ArkTS `router.pushUrl` / `router.replaceUrl` targets as route symbols.
- Extracted ArkTS `$r(...)` references as resource symbols.
- Let `learn-entry` follow ArkTS router targets to related `.ets` pages.

Why:
- Make memory learning more useful for common HarmonyOS project layout, navigation, resource, permission, and dependency tasks.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 33 tests passed.

Rollback notes:
- Remove `.json5` from `CODE_EXTENSIONS`, HarmonyOS config extraction, ArkTS reference extraction, router target resolution, and related docs/tests.

## 2026-05-28 - Add code learning parse feedback

Files changed:
- `tools/agent_memory.py`
- `tests/test_agent_memory.py`
- `README.md`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/mvp-implementation-plan.md`
- `skills/agent-memory-learn/SKILL.md`
- `gitlog.md`

What changed:
- Added `parse_stats` output for `learn-entry --json` and `learn-path --json`.
- Added parse counts for indexed files, languages, symbols by type, code logs by level, and total memory edges.
- Added `learn-path --json`.
- Wrote `last_learn_path.json` with the same payload shape for Agent inspection.
- Updated learning docs to tell Agents to report low or surprising parse counts.

Why:
- Make learning feedback visible so users and Agents can tell whether the memory system actually parsed meaningful content.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 35 tests passed.

Rollback notes:
- Remove `parse_stats` generation, `learn-path --json`, `last_learn_path.json`, parse feedback tests, and related docs.

## 2026-05-28 - Improve natural-language query recall for ArkTS issues

Files changed:
- `tools/agent_memory.py`
- `tests/test_agent_memory.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-query/SKILL.md`
- `gitlog.md`

What changed:
- Added deterministic query expansion before memory scoring.
- Mapped common Chinese symptom descriptions to technical terms for routes, resources, logs, requests, permissions, and HarmonyOS/ArkTS concepts.
- Added tests showing Chinese problem queries can recall ArkTS route, resource, and hilog records.
- Updated query skill and runtime docs to explain natural-language query expansion and anchor-based follow-up searches.

Why:
- Reduce retrieval misses when the user's problem description uses symptom language instead of exact code keywords.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tests/test_agent_memory.py install.py`
- Result: passed.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 45 tests passed.
- Command: `git diff --check`
- Result: clean.

Rollback notes:
- Remove `QUERY_EXPANSION_RULES`, `query_tokens`, related tests, and query-expansion docs.

## 2026-05-28 - Maintain recurring query misses and export wiki page

Files changed:
- `tools/agent_memory.py`
- `tests/test_agent_memory.py`
- `docs/runtime.md`
- `docs/query-miss-feedback-loop.md`
- `references/schema.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- Added `normalized_query`, `miss_count`, and `last_seen_at` to query miss records.
- Merged repeated open misses by project, source, and normalized query instead of creating duplicate rows.
- Added miss recurrence fields to `maintain-plan` review actions.
- Exported query misses into both `Governance/Query Misses.md` and `Codebase Wiki/query-misses.md`.
- Added the query misses wiki page to the vault index.

Why:
- Keep real retrieval failures visible without letting repeated failed searches pollute the memory database.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tests/test_agent_memory.py install.py`
- Result: passed.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 47 tests passed.
- Command: `git diff --check`
- Result: clean.

Rollback notes:
- Remove query miss recurrence columns, upsert logic, wiki export page, index link, and related tests/docs.

## 2026-05-28 - Add search terms and match reasons for query results

Files changed:
- `tools/agent_memory.py`
- `tests/test_agent_memory.py`
- `docs/usage-guide.md`
- `docs/templates/memory-query-answer-skill-template.md`
- `skills/agent-memory-query/SKILL.md`
- `gitlog.md`

What changed:
- Added generated `search_terms` to code wiki and code log query results.
- Added `match_reasons` explaining exact file, exact symbol, exact log, expanded query, and field-level matches.
- Replaced flat text scoring with lightweight multi-field scoring for files, symbols, logs, facts, reflections, and episodes.
- Added reranking so exact file path matches outrank broader expanded summary matches.
- Updated query guidance so Agents use reasons and terms as recursive query anchors.

Why:
- Make search results more explainable and let Agents refine follow-up queries from high-signal anchors instead of guessing.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tests/test_agent_memory.py install.py`
- Result: passed.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 48 tests passed.
- Command: `git diff --check`
- Result: clean.

Rollback notes:
- Remove `code_search_terms`, `score_weighted_fields`, result `search_terms` / `match_reasons`, reranking tests, and related docs.

## 2026-05-28 - Store Agent-authored code business semantics

Files changed:
- `tools/agent_memory.py`
- `tests/test_agent_memory.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `references/schema.md`
- `skills/agent-memory-learn/SKILL.md`
- `gitlog.md`

What changed:
- Added `business_summary` and `business_terms` to `code_files`, `code_symbols`, and `code_log_statements`.
- Added `learn-business --payload` so an Agent can read source, organize business meaning, and persist it into existing code memory tables.
- Added business terms and summaries to query scoring and returned code/log matches.
- Exported business summaries and terms in existing Codebase Wiki files, symbols, and log pages.
- Added maintain-health counts for code records missing business terms.

Why:
- Improve business-level recall by storing real file, method, field, resource, route, and log meaning during learning instead of relying only on technical keywords.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tests/test_agent_memory.py install.py`
- Result: passed.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 51 tests passed.
- Command: `git diff --check`
- Result: clean.

Rollback notes:
- Remove code business columns, `learn-business`, business query scoring, business vault output, health counts, tests, and related docs.

## 2026-05-28 - Default memory home to workspace directory

Files changed:
- `tools/agent_memory.py`
- `tests/test_agent_memory.py`
- `README.md`
- `agent.md`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/mvp-implementation-plan.md`
- `references/schema.md`
- `references/obsidian-vault.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- Changed default memory-home resolution from the user home directory to the current workspace `.agent-memory/`.
- Kept explicit overrides through `--memory-home` and `AGENT_MEMORY_HOME`.
- Added a regression test proving default init writes to the current workspace and not `~/.agent-memory`.
- Updated docs to describe `.agent-memory/` as living next to `skills/` and `tools/`.

Why:
- Keep memory data beside the local Agent Memory project and installed skills instead of scattering runtime data under the user's home directory.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tests/test_agent_memory.py install.py`
- Result: passed.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 52 tests passed.
- Command: `git diff --check`
- Result: clean.

Rollback notes:
- Restore `resolve_memory_home()` fallback to `~/.agent-memory` and revert related docs/tests.

## 2026-06-01 - Prioritized learn follow-up, durable semantic conflicts, and batched search

Files changed:
- `docs/superpowers/plans/2026-06-01-memory-runtime-next-phase.md`
- `tools/agent_memory.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory_runtime/code_wiki.py`
- `tools/agent_memory_runtime/governance.py`
- `tools/agent_memory_runtime/models.py`
- `tools/agent_memory_runtime/query.py`
- `tools/agent_memory_runtime/storage.py`
- `tools/agent_memory_runtime/vault.py`
- `tests/test_agent_memory.py`
- `skills/agent-memory-learn/SKILL.md`
- `skills/agent-memory-query/SKILL.md`
- `skills/agent-memory-maintain/SKILL.md`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/guided-memory-review-workflow.md`
- `docs/templates/memory-query-answer-skill-template.md`
- `references/schema.md`
- `gitlog.md`

What changed:
- Added a next-phase implementation plan under `docs/superpowers/plans/`.
- Upgraded `semantic_followup` to return prioritized file work, capped batches, `recommended_next_action`, and explicit `truncated` / count metadata.
- Added durable SQLite `semantic_conflicts` storage and switched `maintain-plan` conflict review off `runtime/last_learn_business.json`.
- Exported semantic conflicts to a new vault governance page and linked it from the vault index.
- Added batched aggregated `search` retrieval with `--cursor`, `--per-type-limit`, `--aggregate-limit`, `truncated`, `next_cursor`, and returned/total counts by type.
- Updated learn/query/maintain docs so a local Agent CLI can consume the new follow-up, search, and governance outputs directly.

Why:
- Keep semantic enrichment focused on the highest-value file, symbol, and log gaps.
- Preserve semantic conflict review state across sessions instead of losing it with runtime cache turnover.
- Keep large-memory search bounded without forcing one-shot output dumps back into the Agent.
- Make the runtime outputs concrete enough that another local Agent CLI can follow them without ad hoc conventions.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 72 tests passed.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile install.py tools/agent_memory.py tools/agent_memory_runtime/__init__.py tools/agent_memory_runtime/cli.py tools/agent_memory_runtime/code_wiki.py tools/agent_memory_runtime/governance.py tools/agent_memory_runtime/models.py tools/agent_memory_runtime/query.py tools/agent_memory_runtime/records.py tools/agent_memory_runtime/storage.py tools/agent_memory_runtime/text.py tools/agent_memory_runtime/vault.py tests/test_agent_memory.py`
- Result: passed.
- Command: `git diff --check`
- Result: clean.

Rollback notes:
- Remove the `semantic_conflicts` table and its governance/vault consumers.
- Revert `semantic_followup` priority/truncation metadata if the batch protocol proves too rigid.
- Revert `search` cursor and aggregate metadata if downstream consumers require the old fixed-limit shape.

### Follow-up

- Added `semantic-conflict` listing and `conflict-status` to close reviewed conflict records with explicit resolution text.
- Added `conflict-apply` to replace a target `business_summary` with the reviewed incoming summary and mark the conflict `applied`.
- Tightened `conflict-apply` so symbol/log targets must resolve to exactly one row; ambiguous replacements now fail closed.
- Added `apply_command_template` to `maintain-plan` conflict actions and split vault health conflict counts by file, symbol, and log entity types.
- Added `decision_note` and `replacement_source` to semantic conflict closure/apply flows and vault export.
- Added `hint_terms` and `hint_context` to semantic follow-up payloads so second-pass `learn-business` writes can stay aligned with query anchors.
- Reused the same hint-bearing follow-up generation for `maintain-plan` semantic enrichment templates to keep miss repair and learn follow-up aligned.
- Added `suggested_followup_terms` to query outputs so recursive query skills can tighten the next search without inventing anchors.
- Added `suggested_query_terms`, `query_command_template`, and `query_workflow_steps` to `maintain-plan` query-miss actions so miss repair can recurse into query before broadening learn scope.
- Updated maintain/runtime/usage templates to treat query-miss repair and semantic enrichment as one loop driven by the same code-memory anchors.
- Tightened tests to check strong route/resource/log anchors appear at the front of recursive follow-up suggestions.
- Re-ranked `suggested_followup_terms` so exact ArkTS route/resource anchors and matched log templates/functions are returned before broader file-path and summary-derived terms.
- Made `suggested_followup_terms` scene-aware so route, resource, log, and HarmonyOS config queries bias their next-step anchors differently instead of sharing one flat priority order.
- Reused the same scene-aware follow-up ranking inside `maintain-plan` query-miss repair and exposed `followup_focus` in query and maintain outputs so local Agent recursion can branch without re-inferring the scene.
- Updated recursive query templates to branch directly on `followup_focus`, and added a regression check that plain semantic-fact search leaves `followup_focus` empty instead of inventing a scene.
- Updated the diagnosis and change-design query templates so local Agent skills explicitly branch on `followup_focus` and compose the next query from `suggested_followup_terms` before broader anchors.
- Added `docs/experience-layer-typing-plan.md` to split the future experience layer into `procedure_experience` and `correction_experience`, while explicitly keeping the user-facing interface fixed at four skills.
- Introduced `experience_type` at the reflect/maintain protocol layer so reflections can already separate reusable procedure experiences from semantic-correction experiences without adding a new skill.
- Added `docs/trace-case-and-skill-pattern-plan.md` to define the missing middle layers between single-task reflections and future skill candidates: compressed trace cases and aggregated skill patterns.
- Extended the reflect protocol with compressed trace-case fields (`query_rounds`, `trajectory_summary`, `useful_followup_focus`, `useful_followup_terms`, `misleading_followup_terms`, `inspection_targets`, `final_verification_path`, `related_cases`) and surfaced them through experience-candidate maintain actions instead of storing raw task transcripts.
- Added a read-only skill-pattern clustering step in `maintain-plan` so repeated `procedure_experience` reflections that share the same `skill_candidate` can produce `review_skill_pattern_candidate` actions with shared anchors, cases, and verification cues.
- Extended `review_skill_pattern_candidate` actions with `draft_path` and `draft_markdown` so the runtime can hand a first-pass `docs/skill-candidates/*.md` draft to the local Agent CLI without touching the formal `skills/` directory.
- Exported grouped skill-pattern candidates into `Governance/Skill Pattern Candidates.md` so Obsidian review mirrors can show the same draft path and Markdown preview that `maintain-plan` returns.
- Enriched skill-pattern aggregation with `common_stop_conditions`, `expected_outputs`, and `failure_modes` so repeated procedure experiences produce a more skill-like draft instead of a loose case summary.
- Added heuristic `common_steps` generation from repeated focus, query anchors, inspection targets, and verification paths so clustered procedure experiences now read more like an executable workflow draft.
- Added `maintain-skill-draft` so reviewed skill-pattern candidates can be written into `docs/skill-candidates/`, including an `all` mode to export every currently clustered draft in one pass without touching the formal `skills/` directory.
- Added `maintain-skill-package` so a reviewed draft can be staged into `skills/_candidates/<pattern>/SKILL.md` as a candidate package while still keeping formal `skills/<name>/` promotion as a separate human-reviewed step.
- Added `docs/skill-promotion-rules.md` to lock down the final manual promotion boundary between `docs/skill-candidates/`, `skills/_candidates/`, and formal `skills/`.
- Added stable YAML frontmatter to generated `docs/skill-candidates/*.md` drafts so review metadata such as `artifact_type`, `promotion_status`, `supporting_reflection_ids`, `common_followup_focus`, and `supporting_cases` can be read without reparsing the Markdown body.
- Added stable YAML frontmatter to generated `skills/_candidates/*/SKILL.md` packages so the candidate stage now records `promotion_status: candidate` and `source_draft` alongside the aggregated support metadata.
- Updated runtime, usage, maintain-skill, and promotion-rule docs to treat draft/package frontmatter as part of the audited promotion chain instead of an incidental file-format detail.
- Added explicit `draft_status`, `package_status`, `package_path`, and `promotion_stage` fields to skill-pattern candidate review outputs so maintain-plan and vault reviewers can see whether a pattern is only clustered, already written as a draft, or already staged as a candidate package.
- Added minimal human-review metadata placeholders (`review_status`, `reviewer`, `review_notes`) to generated skill candidate drafts and candidate packages so review state can live inside the same artifact that later promotion consumes.
- Made skill-pattern artifact status inspection read existing frontmatter back into runtime outputs (`draft_review_status`, `package_review_status`) and added `review_guidance` so maintain-plan and vault reviewers can see the next recommended human step.
- Hardened `maintain-skill-draft` and `maintain-skill-package` so they preserve existing artifacts once human review metadata is present, returning `write_action` and `warning` instead of silently overwriting reviewed draft/package files.
- Completed the first correction-experience governance loop by turning `review_correction_experience` into a real learn-repair bundle with `correction_targets`, `learning_rule_draft`, a targeted `learn_business_payload_template`, and correction-specific workflow steps.
- Updated the vault skill-pattern dashboard to mirror reviewer metadata and the reviewed-artifact preservation policy, so Obsidian review now shows the same promotion guardrails as runtime JSON.
- Added a generated `skills/_candidates/<pattern>/PROMOTION.md` manual checklist so candidate packages now ship with a concrete human promotion template instead of pointing only to a general rules document.
- Added first-pass quality gates for skill patterns (`promotion_readiness`, `quality_score`, `quality_reasons`) so repeated procedure experiences now report whether they merely cluster, deserve review, or are close to manual promotion consideration.

## 2026-06-02 - Add refreshable learn scopes and structural retirement

Files changed:

- `tools/agent_memory.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory_runtime/code_wiki.py`
- `tools/agent_memory_runtime/models.py`
- `tools/agent_memory_runtime/records.py`
- `tools/agent_memory_runtime/storage.py`
- `tests/test_agent_memory.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/memory-refresh-and-retirement-plan.md`
- `skills/agent-memory-maintain/SKILL.md`
- `references/schema.md`
- `gitlog.md`

What changed:

- Added durable SQLite `learn_scopes` manifests so `wiki-index`, `learn-path`, and `learn-entry` record refreshable learned scopes instead of leaving scope replay implicit.
- Added `maintain-refresh-scope` as the low-risk codebase drift path for projects that keep changing.
- Implemented scope replay from stored manifests, structural refresh for current files, and retirement of removed-file `code_files`, `code_symbols`, `code_log_statements`, and derived `memory_edges`.
- Added semantic drift output (`semantic_review_targets`) so changed or newly added files can flow back into focused `learn-business` review instead of forcing broad relearns.
- Added runtime, schema, usage, and maintain-skill documentation for project refresh and stale-structure retirement.

Why:

- Keep the code wiki aligned with the current codebase without wiping accumulated business semantics or experience review history.
- Let maintain refresh only what was previously learned, instead of making the user restate scope boundaries every time the project updates.
- Separate safe structural retirement from human-reviewed semantic or experience retirement.

Verification:

- Command: `python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_learn_path_records_persistent_learn_scope_manifest tests.test_agent_memory.AgentMemoryRuntimeTests.test_maintain_refresh_scope_updates_structure_and_reports_drift`
- Result: passed.

Rollback notes:

- Remove the `learn_scopes` table and `maintain-refresh-scope` command.
- Remove manifest recording from `wiki-index`, `learn-path`, and `learn-entry`.
- Revert the refresh/retirement docs if we decide to postpone project-drift handling.

### Follow-up

- Added `build_recent_refresh_drifts` so `maintain-plan` consumes recent learn-scope refresh summaries instead of leaving drift only in runtime JSON.
- Added `review_semantic_drift` actions with targeted `learn_business_payload_template` output for changed or newly added files in refreshed scopes.
- Added `mark_experience_stale_if_anchor_removed` advisory actions when active reflections still reference files removed during scope refresh.
- Updated runtime, usage, and maintain-skill docs so refresh is now explicitly part of the maintain governance chain instead of a standalone maintenance command.
- Added scope health aggregation so `maintain-health` reports learned-scope counts, drift counts, missing-source scopes, and a sorted scope-health summary.
- Added vault dashboards for `Governance/Learned Scopes.md` and `Governance/Refresh Drift.md`, and linked them from the vault index and review queue.
- Strengthened skill-pattern quality signals with reuse counts and anchor freshness (`helped_reuse_count`, `partial_reuse_count`, `misleading_reuse_count`, `anchor_health`, `missing_anchor_paths`).
- Added `review_skill_pattern_staleness` so removed-file drift can warn when a clustered skill pattern still depends on stale anchors.
- Added `maintain-skill-promotion-status` as a read-only final gate that reports promotion blockers, review metadata, checklist status, anchor freshness, and formal target path before any manual promotion.

## 2026-06-02 - 500k-scale query/update hardening

Files touched:

- `tools/agent_memory_runtime/models.py`
- `tools/agent_memory_runtime/storage.py`
- `tools/agent_memory_runtime/query.py`
- `tools/agent_memory_runtime/code_wiki.py`
- `tools/agent_memory_runtime/governance.py`
- `tests/test_agent_memory.py`
- `gitlog.md`

What changed:

- Added SQLite FTS5 side indexes for `semantic_facts`, `reflections`, `episodes`, `code_files`, `code_symbols`, and `code_log_statements`, with trigger-based sync on insert/update/delete.
- Changed query recall from whole-table row loading to SQLite candidate recall first, followed by the existing Python rerank logic.
- Added a bounded SQL `LIKE` fallback for Chinese and low-hit scenes so route/resource/log/config queries still recall useful candidates when FTS tokenization is weak.
- Added missing hot-path indexes for code-symbol, code-log, and status/staleness filtering paths.
- Changed scoped `learn-path` / `learn-entry` refresh from full-project `memory_edges` rebuilds to affected-scope edge deletion and incremental edge rebuild.
- Bounded duplicate-review work to a recent review pool instead of unbounded O(n²) comparison over all active memory rows.
- Changed `maintain-health` and `maintain-review` to rely on SQL counts/filters and only load bounded active windows where pairwise review logic is still needed.

Why:

- Keep query latency from scaling linearly with total row volume as the memory archive approaches hundreds of thousands of rows.
- Make local relearn and refresh cost proportional to the touched scope instead of proportional to all learned files and edges in the project.
- Prevent maintain workflows from turning into large in-memory scans or quadratic comparisons as durable memory accumulates.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: `99 tests OK`.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passed.
- Command: `git diff --check`
- Result: clean.

Rollback notes:

- Remove the FTS5 side indexes and triggers if we want to fall back to the old full-scan query behavior.
- Restore full-project edge rebuilds if scoped edge invalidation proves too conservative or too complex to maintain.
- Remove the bounded duplicate-review pool if exact all-history duplicate detection becomes more important than bounded maintain cost.

### Follow-up

- Changed `vault-export` to generate bounded human-readable summaries for large aggregate pages instead of trying to mirror every record into Markdown.
- Limited per-record vault note export to a recent bounded set for episodes and reflections, while keeping SQLite as the complete source of truth.
- Added truncation notices to generated vault pages so reviewers can tell when they are looking at a summarized mirror rather than the full archive.

## 2026-06-03 - Goal-oriented temporary runtime log analysis

Files touched:

- `tools/agent_memory.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory_runtime/query.py`
- `tools/agent_memory_runtime/runtime_logs.py`
- `tests/test_agent_memory.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-query/SKILL.md`
- `gitlog.md`

What changed:

- Added `log_search_plan` to `context` and `search` so problem-oriented queries now return candidate code-log events, search terms, logger/tag hints, file/function hints, and an inspection order.
- Added `analyze-runtime-log` as a bounded diagnosis command that keeps raw user logs temporary, normalizes them into lightweight runtime events, scores them against current code-log memory, and returns scored slices plus a `runtime_episode_candidate`.
- Wrote runtime analysis snapshots only to `runtime/last_runtime_log_analysis.json` instead of persisting raw log lines into SQLite.
- Updated query documentation and skill guidance so agents can bridge from user problem descriptions to code-log anchors, then to temporary runtime-log evidence.

Why:

- Let the memory system use existing code-log knowledge to guide diagnosis of real user-provided runtime logs without turning temporary raw logs into long-term memory.
- Give LLMs bounded, code-linked evidence slices instead of requiring them to inspect large raw log dumps directly.
- Keep the current four-skill model intact while adding a practical first step toward Goal-Oriented Log Analysis.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_context_includes_goal_oriented_log_search_plan tests.test_agent_memory.AgentMemoryRuntimeTests.test_analyze_runtime_log_builds_bounded_slices_and_episode_candidate`
- Result: passed.

Rollback notes:

- Remove `log_search_plan` from query payloads and delete `analyze-runtime-log` plus `runtime_logs.py`.
- Revert the usage/query skill docs if we decide not to support temporary raw-log analysis yet.

### Follow-up

- Extended `code_log_statements` semantics with `business_event`, `trigger_stage`, `symptom_terms`, `likely_causes`, `process_hint`, and `neighbor_terms`, while keeping the same table and FTS path.
- Changed `learn-business` so log semantics merge into the existing code-log records instead of creating a separate log-knowledge store.
- Upgraded `log_search_plan` to consume those new log semantics and expose `process_hints` plus stronger root-cause-oriented search terms.
- Added lightweight `session_candidates` and `reflect_payload_template` to `analyze-runtime-log`, so temporary runtime-log evidence can flow directly into `reflect` without persisting raw logs.

## 2026-06-03 - Runtime log evidence deepening

Files touched:

- `tools/agent_memory_runtime/runtime_logs.py`
- `tests/test_agent_memory.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-query/SKILL.md`
- `gitlog.md`

What changed:

- Strengthened runtime log parsing so temporary evidence extraction now recognizes optional `pid`/`tid` prefixes and lightweight structured fields such as `error_code`, `route`, `request_id`, `session_id`, `reason`, and `request_path`.
- Added a compact `candidate_chain` plus `chain_confidence` to `runtime_episode_candidate`, giving diagnosis and reflection code a bounded failure-sequence summary without introducing a full causal-graph subsystem.
- Made `reflect_payload_template` more correction-aware by adding `old_hypothesis` and non-empty `what_failed` guidance when the query is clearly revising an earlier diagnosis.
- Added `log_improvement_suggestions` so the runtime can recommend a few high-value start, branch, or correlation logs when the temporary evidence was usable but fragile.

Why:

- Improve the quality of LLM-facing runtime evidence without persisting raw logs.
- Make log-driven diagnosis results more reusable as `procedure_experience` or `correction_experience`.
- Turn brittle temporary log analysis into actionable feedback for improving future source-code logging.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_analyze_runtime_log_extracts_structured_fields_and_chain tests.test_agent_memory.AgentMemoryRuntimeTests.test_analyze_runtime_log_can_recommend_correction_experience`
- Result: passed.

Rollback notes:

- Revert `runtime_logs.py` to the lighter parser if the extra runtime field extraction proves too format-specific.
- Remove `candidate_chain`, `chain_confidence`, and `log_improvement_suggestions` if we decide to keep runtime log analysis strictly slice-based.

## 2026-06-03 - Goal-oriented incident diagnosis strategy library

Files touched:

- `tools/agent_memory.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory_runtime/governance.py`
- `tools/agent_memory_runtime/vault.py`
- `tests/test_agent_memory.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/guided-memory-review-workflow.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:

- Added a new governance path that clusters repeated runtime-log-backed `procedure_experience` reflections into `review_incident_strategy_candidate` actions.
- Added `maintain-incident-strategy-draft`, which writes reviewed strategy drafts into `docs/incident-strategies/<strategy>.md`.
- Added `Governance/Incident Strategy Candidates.md` to the vault mirror so recurring incident diagnosis strategies can be reviewed without reopening raw logs.
- Framed these strategy drafts as reusable diagnosis policies that sit between repeated incidents and later skill evolution, without adding a fifth user-facing skill.

Why:

- Turn repeated runtime-log diagnosis work into reusable Goal-Oriented Incident Diagnosis strategies.
- Keep the output reviewable and lightweight before any future promotion into broader skill artifacts.
- Reuse the existing maintain / reflect / vault governance loop instead of inventing a separate log platform.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_maintain_plan_clusters_runtime_incidents_into_strategy_candidate tests.test_agent_memory.AgentMemoryRuntimeTests.test_maintain_incident_strategy_draft_writes_markdown_file tests.test_agent_memory.AgentMemoryRuntimeTests.test_vault_export_writes_incident_strategy_candidates_dashboard`
- Result: passed.

Rollback notes:

- Remove `maintain-incident-strategy-draft` and the `review_incident_strategy_candidate` action if we decide to keep runtime-log governance limited to skill patterns only.
- Remove `Governance/Incident Strategy Candidates.md` from the vault mirror if the extra review surface becomes too noisy.

## 2026-06-07 - Log feedback loop and log design governance

Files touched:

- `tools/agent_memory_runtime/runtime_logs.py`
- `tools/agent_memory_runtime/governance.py`
- `tests/test_agent_memory.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-maintain/SKILL.md`
- `skills/agent-memory-reflect/SKILL.md`
- `gitlog.md`

What changed:

- Deepened `reflect_payload_template` for runtime-log diagnosis by carrying bounded `evidence`, `misleading_followup_terms`, and a concrete `repair_action` instead of only summary text.
- Made the runtime evidence feedback more human-readable by prioritizing dominant matched log messages in `what_worked`, so repeated diagnosis cases preserve the signals that actually helped.
- Added `review_log_design_gap` to `maintain-plan` as a narrow governance action for repeated runtime-log-backed diagnosis flows that point to the same logging weakness.
- Kept the new log-design review lightweight: it groups `goal_area`, `goal_symptoms`, `high_value_log_anchor_targets`, `suggested_log_kinds`, and `log_design_feedback` without persisting raw runtime history.

Why:

- Improve the quality of `procedure_experience` and `correction_experience` generated from temporary runtime-log evidence.
- Turn repeated diagnosis pain points into actionable logging improvements without adding a heavier runtime-incident storage layer.
- Preserve the current “raw logs are temporary, reflections are durable” boundary while making the durable layer more useful.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_analyze_runtime_log_can_recommend_correction_experience tests.test_agent_memory.AgentMemoryRuntimeTests.test_analyze_runtime_log_reflect_template_carries_runtime_evidence_feedback tests.test_agent_memory.AgentMemoryRuntimeTests.test_maintain_plan_surfaces_log_design_gap_review`
- Result: passed.

Rollback notes:

- Revert the new `reflect_payload_template` fields if we decide runtime-log reflections should stay summary-only.
- Remove `review_log_design_gap` if log-design review should remain an informal suggestion rather than a first-class maintain action.

## 2026-06-08 - Governance summaries and recurring incident fingerprints

Files touched:

- `tools/agent_memory_runtime/governance.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory.py`
- `tools/agent_memory_runtime/vault.py`
- `tests/test_agent_memory.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-maintain/SKILL.md`
- `skills/agent-memory-reflect/SKILL.md`
- `gitlog.md`

What changed:

- Added `runtime_feedback_summary` to `reflect-review` so runtime-log-backed reflections expose effective signals, misleading signals, and verification checkpoints without storing raw logs.
- Added `governance_summary` and `learn_governance_summary` to `maintain-plan`, grouping work by governance lane and keeping correction/drift follow-up narrow.
- Added lightweight recurring incident fingerprint candidates plus `maintain-incident-fingerprint-draft`, which writes bounded review drafts into `docs/incident-fingerprints/`.
- Added `Governance/Recurring Incident Fingerprints.md` to the vault mirror.

Why:

- Strengthen the reflection/experience feedback loop without introducing a larger runtime-history layer.
- Make learn correction and semantic drift follow-up more systematic and easier for maintain to route.
- Preserve repeated runtime incident signatures as compact summaries before any heavier incident-clustering work.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_reflect_review_surfaces_runtime_feedback_summary tests.test_agent_memory.AgentMemoryRuntimeTests.test_maintain_plan_includes_learn_and_governance_summaries tests.test_agent_memory.AgentMemoryRuntimeTests.test_maintain_plan_surfaces_recurring_incident_fingerprint_and_can_write_draft`
- Result: passed.

Rollback notes:

- Remove recurring incident fingerprint drafting if we decide repeated runtime incidents should stay only inside incident strategies.
- Drop `runtime_feedback_summary` from `reflect-review` if the extra runtime evidence summary proves too noisy for review workflows.

## 2026-06-08 - Automatic runtime usage summaries for reflection

Files touched:

- `tools/agent_memory_runtime/usage_samples.py`
- `tools/agent_memory.py`
- `tools/agent_memory_runtime/governance.py`
- `tests/test_agent_memory.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-reflect/SKILL.md`
- `gitlog.md`

What changed:

- Added a runtime-only `last_usage_sample.json` helper that collects bounded usage facts from `context`, `search`, `analyze-runtime-log`, and `maintain-plan`.
- Kept the usage sample out of SQLite: it stores only recent command flow, query rounds, followup focus, suggested terms, dominant runtime signals, candidate chain, and governance lanes.
- Made `reflect` auto-merge missing structured fields from the latest usage sample and any bounded `reflect_payload_template` captured during runtime-log analysis.
- Closed the usage sample after writing a reflection so a later unrelated task starts from a fresh runtime summary instead of inheriting stale context.

Why:

- Reduce manual reflection overhead during real usage without creating a heavier telemetry table.
- Preserve the “automatic facts, minimal human judgment” approach by capturing process data automatically and letting the user decide final quality feedback separately.
- Keep rollback and storage cost low by confining the summary to runtime files instead of long-term database rows.

Verification:

- Command: `python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_usage_sample_auto_records_query_runtime_and_governance_steps tests.test_agent_memory.AgentMemoryRuntimeTests.test_reflect_auto_merges_recent_usage_sample`
- Result: passed.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: `115 tests OK`.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passed.
- Command: `git diff --check`
- Result: clean.

Rollback notes:

- Remove `usage_samples.py` and the runtime-file auto-merge path if we decide reflection authorship should remain fully manual.
- Keep the existing `last_context.json`, `last_runtime_log_analysis.json`, and `last_reflection.json` snapshots even if the rolling usage sample is removed.

## 2026-06-08 - README rewrite for product framing

Files touched:

- `README.md`
- `docs/assets/agent-memory-overview.png`
- `gitlog.md`

What changed:

- Rewrote the README front section to explain the weakness of current coding agents, why a local memory system is needed, and what concrete problems this project solves.
- Added a lightweight project feature illustration instead of a complex architecture-only diagram.
- Added concise sections for memory design, experience design, governance, and the four user-facing skills while keeping quick start and command references in place.

Why:

- Make the repository easier to understand for first-time readers.
- Shift the README from an internal runtime summary toward a clearer product and system introduction.
- Highlight the project-specific strengths: code-aware memory, goal-oriented log diagnosis, experience and skill evolution, and governed refresh/drift review.

Verification:

- Checked the updated README structure locally.
- Kept the image path repository-relative so it can render in GitHub and local markdown viewers.
- Command: `git diff --check`
- Result: clean.

Rollback notes:

- Restore the previous README if we want a more runtime-command-heavy homepage.
- Replace the generated illustration with a text-only overview if image maintenance becomes undesirable.

## 2026-06-16 - Memory query firewall for experience interference

Files touched:

- `tools/agent_memory.py`
- `tools/agent_memory_runtime/models.py`
- `tools/agent_memory_runtime/query.py`
- `tools/agent_memory_runtime/governance.py`
- `tests/test_agent_memory.py`
- `references/schema.md`
- `docs/experience-system-plan.md`
- `docs/phase-2-memory-governance-plan.md`
- `skills/agent-memory-learn/SKILL.md`
- `skills/agent-memory-query/SKILL.md`
- `skills/agent-memory-maintain/SKILL.md`
- `skills/agent-memory-reflect/SKILL.md`
- `gitlog.md`

What changed:

- Added `semantic_patch_experience` as a third reflection experience type for anchored code business-semantic corrections.
- Added reflection fields for semantic patches and retrieval interference governance: `anchor_type`, `anchor_key`, `semantic_field`, `existing_value`, `proposed_value`, `patch_reason`, `applies_to_current_code`, `superseded_by`, and `misleading_score`.
- Added reflection payload validation so procedure, correction, and semantic patch experiences carry the minimum structure needed for safe reuse.
- Added query intent routing and a memory query firewall that separates main reflections, correction guards, semantic patch notes, blocked memories, and matching semantic conflicts.
- Extended `maintain-plan` with `review_semantic_patch` and `review_retrieval_interference` actions.
- Updated skill and design docs so the four-skill interface stays fixed while internal experience governance becomes type-aware.

Why:

- Prevent recent weakly related experiences from steering unrelated queries.
- Keep correction experiences as guardrails instead of letting them become the main execution path.
- Let business-semantic corrections repair code wiki meaning through focused `learn-business` review rather than normal experience recall.

Verification:

- Command: `python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_reflect_payload_writes_semantic_patch_experience tests.test_agent_memory.AgentMemoryRuntimeTests.test_reflect_rejects_semantic_patch_without_anchor tests.test_agent_memory.AgentMemoryRuntimeTests.test_context_firewall_separates_experience_lanes tests.test_agent_memory.AgentMemoryRuntimeTests.test_maintain_plan_surfaces_semantic_patch_and_retrieval_interference_reviews`
- Result: passed.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: `119 tests OK`.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passed.
- Command: `git diff --check`
- Result: clean.

Rollback notes:

- Remove `semantic_patch_experience` validation and fields if code-business semantic repair should stay solely in `learn-business`.
- Remove the memory query firewall output fields if downstream agents need the previous flat reflection retrieval behavior.

## 2026-06-16 - Semantic patch reflection examples

Files touched:

- `skills/agent-memory-reflect/SKILL.md`
- `docs/runtime.md`
- `gitlog.md`

What changed:

- Added a copy-paste `semantic_patch_experience` payload example to the reflect skill docs.
- Documented that `reflect` stores semantic patch corrections in `reflections` first and that maintain and `learn-business` apply them later.
- Added the follow-up flow: `reflect` -> `maintain-plan` -> `review_semantic_patch` -> `learn-business`.

Why:

- The new semantic patch lane was implemented, but the docs still made users infer the payload shape from field names alone.
- This closes the gap between the runtime behavior and the operator guidance.

Verification:

- Command: `git diff --check`
- Result: clean.

Rollback notes:

- Remove the example block if we later move semantic patch authoring into a separate helper command.

## 2026-06-16 - Detect conflicting old and new experiences

Files touched:

- `tools/agent_memory_runtime/governance.py`
- `tests/test_agent_memory.py`
- `docs/experience-system-plan.md`
- `skills/agent-memory-maintain/SKILL.md`
- `docs/runtime.md`
- `gitlog.md`

What changed:

- Added `review_experience_conflict` candidates to `maintain-plan` for two cases:
  - newer `procedure_experience` / `correction_experience` records that change workflow guidance for the same trigger and scope
  - multiple `semantic_patch_experience` records that target the same anchor and semantic field with different proposed values
- Added `summary.experience_conflict_reviews` and `governance_summary.experience_conflict_reviews`.
- Added regression tests for both procedure-guidance conflicts and semantic-patch conflicts.
- Documented how maintain should handle these review-only conflict actions.

Why:

- Experience typing and retrieval firewall reduced cross-lane interference, but active old and new experience records could still coexist and quietly disagree.
- The maintain step needs an explicit queue for “same problem, different answer” so the conflict is resolved before query relies on both.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests.test_maintain_plan_surfaces_new_old_procedure_experience_conflict tests.test_agent_memory.AgentMemoryRuntimeTests.test_maintain_plan_surfaces_new_old_semantic_patch_conflict`
- Result: passed.

Rollback notes:

- Remove `build_experience_conflict_candidates`, drop `review_experience_conflict` from `maintain-plan`, and revert the targeted doc and test updates if this review lane proves too noisy.

## 2026-06-22 - Add execution-discipline memory note

Files touched:

- `memory.md`
- `gitlog.md`

What changed:

- Added a new project-local `memory.md` note that records execution mistakes observed during ArkLine verification work.
- Captured the main failure modes:
  - running heavyweight verification too early
  - parallelizing lock-competing commands
  - running Rust tests before dependent generated worker artifacts were definitely rebuilt
- Recorded concrete operating rules for future sessions, including a preferred verification order and explicit anti-patterns to avoid.

Why:

- These mistakes did not reflect one broken feature; they reflected poor verification discipline.
- A local memory note makes the lesson reusable and reduces the chance of repeating "looks hung" execution patterns in later work.

Verification:

- Command: `ls -la memory.md`
- Result: file created.

Rollback notes:

- Remove `memory.md` if the project later centralizes this kind of execution guidance into the SQLite-backed memory runtime or a dedicated docs location.

## 2026-06-24 - Add Chinese README focused on ArkTS and lightweight retrieval

Files touched:

- `README.md`
- `README.zh-CN.md`
- `gitlog.md`

What changed:

- Added a top-level Chinese README entry link in `README.md`.
- Added `README.zh-CN.md` as a concise Chinese overview for local readers.
- Focused the Chinese copy on:
  - ArkTS / HarmonyOS usage
  - SQLite + FTS5 lightweight retrieval
  - code log extraction and lightweight code graph via `memory_edges`
  - reduced token cost through bounded context and structured memory

Why:

- The existing README already explained the system in English, but it did not quickly signal the project's practical strengths for Chinese readers.
- This version makes the current positioning clearer: ArkTS-oriented, lightweight, log-aware, and designed to reduce repeated retrieval and token waste.

Verification:

- Command: `git diff --check`
- Result: passes after implementation and documentation updates.

Rollback notes:

- Remove `README.zh-CN.md` and the README link if the project later consolidates documentation back into a single-language README.

## 2026-07-11 - Plan ArkTS incident trace implementation

Files touched:

- `docs/superpowers/plans/2026-07-11-arkts-incident-trace.md`
- `gitlog.md`

What changed:

- Added a detailed implementation plan for a small ArkTS Incident Trace layer.
- The plan keeps the existing four-skill interface and `tools/agent_memory.py` runtime boundary.
- It defines a lightweight SQLite schema for `incident_traces` and `incident_trace_links`.
- It splits implementation across focused files so new incident trace modules and tests stay under 500 lines.
- It includes staged TDD tasks for schema, trace building, CLI commands, query integration, maintain governance, vault export, docs, and verification.

Why:

- The project already has code log anchors, memory edges, runtime-log-backed reflections, incident strategy candidates, and recurring fingerprints.
- The missing layer is a compact incident trace that preserves useful diagnosis evidence without storing raw user log streams.
- The plan gives future implementers a bounded path that supports long-term evolution without turning the runtime into a heavy log platform.

Verification:

- Command: `git diff --check`
- Result: pending

Rollback notes:

- Remove the plan document if ArkTS incident trace work is deferred or replaced by a broader incident diagnosis design.

## 2026-07-11 - Implement ArkTS incident traces

Files touched:

- `tools/agent_memory.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory_runtime/storage.py`
- `tools/agent_memory_runtime/records.py`
- `tools/agent_memory_runtime/query.py`
- `tools/agent_memory_runtime/governance.py`
- `tools/agent_memory_runtime/vault.py`
- `tools/agent_memory_runtime/incident_trace_models.py`
- `tools/agent_memory_runtime/incident_trace_schema.py`
- `tools/agent_memory_runtime/incident_trace_builder.py`
- `tools/agent_memory_runtime/incident_trace.py`
- `tools/agent_memory_runtime/incident_trace_query.py`
- `tools/agent_memory_runtime/incident_trace_governance.py`
- `tests/test_incident_trace.py`
- `references/schema.md`
- `docs/code-log-statement-network.md`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-query/SKILL.md`
- `skills/agent-memory-maintain/SKILL.md`
- `skills/agent-memory-reflect/SKILL.md`
- `gitlog.md`

What changed:

- Added `incident_traces` and `incident_trace_links` with FTS support.
- Added `incident-trace` and `incident-trace-status` runtime commands.
- Added deterministic ArkTS scene classification and compact trace draft building from symptom plus bounded log text.
- Added `incident_trace_matches` to query/context output.
- Added maintain-plan trace actions for promotion review and log-anchor gaps.
- Added vault pages for incident traces and trace review.

Why:

- ArkTS issue diagnosis often starts from user symptoms and temporary runtime logs.
- The runtime now preserves useful diagnosis evidence without storing full raw logs or adding a fifth skill.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_incident_trace`
- Result: 10 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests`
- Result: 121 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passes.
- Command: `wc -l tools/agent_memory_runtime/incident_trace*.py tests/test_incident_trace.py`
- Result: all new incident trace implementation and test files stay below 500 lines.

Rollback notes:

- Remove incident trace modules, schema hook, CLI registration, query lane, maintain actions, vault pages, and docs if trace storage proves too noisy.

## 2026-07-11 - Add quality and performance scoring plan

Files touched:

- `docs/superpowers/plans/2026-07-11-quality-performance-scoring.md`
- `tools/agent_memory_runtime/scoring_models.py`
- `tools/agent_memory_runtime/quality_scoring.py`
- `tools/agent_memory_runtime/performance_scoring.py`
- `tools/agent_memory.py`
- `tools/agent_memory_runtime/governance.py`
- `tests/test_quality_performance_scoring.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `references/schema.md`
- `skills/agent-memory-maintain/SKILL.md`
- `skills/agent-memory-query/SKILL.md`
- `gitlog.md`

What changed:

- Added a detailed implementation plan for deterministic quality and performance scoring.
- Added explainable quality scoring for semantic facts, reflections/experiences, and incident traces.
- Added bounded JSONL runtime performance samples with p50/p95 health summaries.
- Exposed `quality_summary`, `low_quality_records`, and `high_value_records` in `maintain-plan`.
- Exposed `runtime_performance` in `maintain-health`.
- Recorded lightweight performance samples for `context`, `search`, `maintain-plan`, and `maintain-health`.

Why:

- Memory retrieval needs a visible quality signal so weakly related or stale experiences do not dominate Agent context.
- Maintenance needs lightweight performance signals before large archives make query, maintain, or export work expensive.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_performance_scoring`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_incident_trace`
- Result: 131 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passes.

Rollback notes:

- Remove the scoring modules, maintain output fields, performance sample writes, tests, and doc updates if the scoring layer becomes noisy.

## 2026-07-11 - Use quality score for memory reranking

Files touched:

- `tools/agent_memory_runtime/query.py`
- `tests/test_quality_performance_scoring.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-query/SKILL.md`
- `gitlog.md`

What changed:

- Added `quality_score`, `quality_band`, and `quality_reasons` to semantic and reflection query matches.
- Added a soft `rerank_score` for main-lane reflections after the existing memory-intent gate.
- Added regression coverage showing a verified, evidence-backed ArkTS route diagnosis outranks broad misleading advice for the same query.

Why:

- Recency or shallow lexical overlap should not let weak experience dominate the Agent's direction when stronger verified experience exists.
- The rerank stays behind the lane firewall so correction guards and semantic patches do not bypass their intended roles.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_performance_scoring.QualityPerformanceScoringTests.test_context_reranks_reflections_by_quality_signal`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_performance_scoring`
- Result: 6 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_incident_trace`
- Result: 131 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passes.

Rollback notes:

- Remove quality fields and `rerank_score` from `query.py`, revert the query skill/runtime docs, and keep scoring limited to maintain outputs if query reranking proves too opinionated.

## 2026-07-11 - Add quality-driven maintain actions

Files touched:

- `docs/superpowers/plans/2026-07-11-quality-governance-actions.md`
- `tools/agent_memory_runtime/quality_scoring.py`
- `tools/agent_memory_runtime/governance.py`
- `tests/test_quality_performance_scoring.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:

- Added a bounded implementation plan for quality-score-driven governance actions.
- Added `review_low_quality_memory` actions for low-quality semantic, reflection, and incident trace records.
- Added `review_high_value_experience` actions for high-quality reflection/experience records.
- Added maintain-plan summary counters for low-quality memory reviews and high-value experience reviews.
- Treated `manual` and `unknown` semantic fact sources as weak evidence unless an explicit evidence field is present.

Why:

- Quality scoring should drive review order and governance decisions, not just appear as passive metadata.
- Weak memory needs an explicit path toward verification, confidence reduction, stale marking, or merge review.
- Strong experience needs a clear path toward reuse, skill-pattern review, or semantic-repair review without automatic promotion.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_performance_scoring.QualityPerformanceScoringTests.test_maintain_plan_adds_low_quality_memory_review_action tests.test_quality_performance_scoring.QualityPerformanceScoringTests.test_maintain_plan_adds_high_value_experience_review_action`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_performance_scoring`
- Result: 8 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_incident_trace`
- Result: 131 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passes.

Rollback notes:

- Remove `build_quality_governance_actions`, drop the maintain-plan counters, revert the scoring evidence tweak, and remove the action docs/tests if these actions become noisy.

## 2026-07-11 - Add retrieval golden-set evaluation

Files touched:

- `docs/superpowers/plans/2026-07-11-memory-retrieval-eval.md`
- `tools/agent_memory_runtime/retrieval_eval.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory.py`
- `tests/test_retrieval_eval.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-query/SKILL.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:

- Added an executable plan for a lightweight golden-query retrieval eval workflow.
- Added `eval-retrieval --cases <file> --json`.
- The eval command reads JSON cases, runs the same `context` path Agents consume, and reports expected hits, missed anchors, blocked bad matches, and unexpected bad matches.
- Added deterministic match specs by result type, id, text, and optional field.

Why:

- Retrieval quality, experience reranking, code graph extraction, and log graph extraction need a stable regression check before further tuning.
- Golden cases make weak-related or misleading memory interference measurable instead of anecdotal.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_retrieval_eval`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_retrieval_eval tests.test_quality_performance_scoring`
- Result: 10 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_incident_trace`
- Result: 131 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passes.

Rollback notes:

- Remove `retrieval_eval.py`, the `eval-retrieval` CLI wiring, tests, and docs if golden-set evaluation proves too rigid for early iteration.

## 2026-07-11 - Add evidence chain quality scoring

Files touched:

- `docs/superpowers/plans/2026-07-11-evidence-chain-quality.md`
- `tools/agent_memory_runtime/evidence_chain_quality.py`
- `tools/agent_memory_runtime/quality_scoring.py`
- `tools/agent_memory_runtime/governance.py`
- `tests/test_quality_performance_scoring.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:

- Added an implementation plan for evidence-chain quality.
- Added reflection evidence-chain enrichment from `source_cases` entries such as `incident_trace:<id>`.
- Resolved incident trace ids to `incident_traces` and `incident_trace_links` to compute `evidence_chain_score`.
- Added evidence-chain fields to quality scored records and maintain-plan output.
- Added `evidence_chain_summary` and `review_weak_evidence_chain` maintain action.

Why:

- Experience quality should distinguish field-complete advice from advice grounded in incident traces and code/log anchors.
- Weak evidence chains should trigger focused review without automatically discarding useful experience.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_performance_scoring.QualityPerformanceScoringTests.test_quality_report_rewards_resolved_incident_trace_evidence_chain tests.test_quality_performance_scoring.QualityPerformanceScoringTests.test_maintain_plan_reviews_weak_evidence_chain_for_high_value_experience`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_performance_scoring tests.test_retrieval_eval`
- Result: 12 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_incident_trace`
- Result: 131 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passes.

Rollback notes:

- Remove `evidence_chain_quality.py`, drop evidence-chain fields and weak-chain actions from maintain-plan, and revert the scoring/docs/tests if this creates noisy review output.

## 2026-07-11 - Add graph quality health checks

Files touched:

- `docs/superpowers/plans/2026-07-11-graph-quality-health.md`
- `tools/agent_memory_runtime/graph_quality.py`
- `tools/agent_memory_runtime/governance.py`
- `tests/test_graph_quality.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:

- Added a plan for lightweight code/log graph health metrics.
- Added `graph_quality` to `maintain-health` and `maintain-plan`.
- Added metrics for orphan code symbols, orphan code logs, stale edges, low-confidence edges, and symbol/log anchor coverage.
- Added `review_graph_quality` maintain-plan action when graph health is not ok.

Why:

- Query quality depends on whether learned code/log anchors are connected and current, not just whether rows exist.
- Graph health should flag stale or orphan anchors before Agents rely on weak code/log evidence.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_graph_quality`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_graph_quality tests.test_quality_performance_scoring tests.test_retrieval_eval`
- Result: 14 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_incident_trace`
- Result: 131 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passes.

Rollback notes:

- Remove `graph_quality.py`, drop graph quality output/action integration, and revert docs/tests if the health signal becomes noisy.

## 2026-07-11 - Add retrieval feedback loop

Files touched:

- `docs/superpowers/plans/2026-07-11-retrieval-feedback-loop.md`
- `tools/agent_memory_runtime/retrieval_feedback.py`
- `tools/agent_memory_runtime/storage.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory_runtime/query.py`
- `tools/agent_memory_runtime/governance.py`
- `tools/agent_memory.py`
- `tests/test_retrieval_feedback.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-query/SKILL.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:

- Added a plan for targeted negative retrieval feedback.
- Added `retrieval_feedback` SQLite storage and `retrieval-feedback` CLI command.
- Added query-similarity feedback penalties for semantic facts and reflections.
- Added `feedback_penalty`, `feedback_reasons`, and `feedback_ids` to penalized query results.
- Added `review_retrieval_feedback` maintain-plan action and summary output.

Why:

- Weak-related or misleading records should be down-ranked for similar future queries without deleting useful memory globally.
- Feedback makes retrieval interference measurable and governable.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_retrieval_feedback`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_retrieval_feedback tests.test_graph_quality tests.test_quality_performance_scoring tests.test_retrieval_eval`
- Result: 17 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_incident_trace`
- Result: 131 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passes.

Rollback notes:

- Remove `retrieval_feedback.py`, schema/table wiring, CLI command, query penalties, maintain actions, tests, and docs if query-specific feedback becomes noisy.

## 2026-07-11 - Add runtime SLO governance

Files touched:

- `docs/superpowers/plans/2026-07-11-runtime-slo-governance.md`
- `tools/agent_memory_runtime/performance_scoring.py`
- `tools/agent_memory_runtime/governance.py`
- `tests/test_quality_performance_scoring.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `gitlog.md`

What changed:

- Added a plan for runtime SLO and token-budget governance.
- Added per-operation target latency and token-budget fields to `runtime_performance`.
- Added `review_runtime_performance_budget` maintain-plan actions for latency, token, status, or performance-band breaches.
- Added `runtime_performance_reviews` to governance summary output.

Why:

- Performance samples were visible in health output, but maintain-plan could not yet turn budget breaches into reviewable maintenance work.
- Local memory systems need lightweight SLO signals before large archives make query and maintain paths expensive.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_performance_scoring.QualityPerformanceScoringTests.test_maintain_plan_reviews_runtime_performance_budget`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_performance_scoring tests.test_retrieval_feedback tests.test_graph_quality tests.test_retrieval_eval`
- Result: 18 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_incident_trace`
- Result: 131 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passes.
- Command: `git diff --check`
- Result: passes.

Rollback notes:

- Remove `build_runtime_performance_actions`, drop runtime performance action wiring from maintain-plan, and revert docs/tests if the SLO signal becomes noisy.

## 2026-07-11 - Add memory calibration layer

Files touched:

- `docs/superpowers/specs/2026-07-11-memory-calibration-layer-design.md`
- `docs/superpowers/plans/2026-07-11-memory-calibration-layer.md`
- `tools/agent_memory_runtime/memory_calibration.py`
- `tools/agent_memory_runtime/query.py`
- `tests/test_memory_calibration.py`
- `skills/agent-memory-query/SKILL.md`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `gitlog.md`

What changed:

- Added a design and implementation plan for answer-time memory calibration.
- Added per-record `trust_level`, `trust_score`, `trust_reasons`, and `retrieval_explanation` annotations to query results.
- Added top-level `memory_use_policy` to `context` and `search` output.
- Updated query skill guidance to use trust levels before injecting memory into answers.

Why:

- Retrieval relevance alone is not enough; Agents need to know whether a record is evidence, verified experience, a weak hint, stale context, or a conflict warning.
- Calibration reduces interference from recent but weakly related memories without adding a new storage system.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_memory_calibration`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_memory_calibration tests.test_retrieval_feedback tests.test_quality_performance_scoring tests.test_retrieval_eval`
- Result: 19 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_incident_trace`
- Result: 131 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passes.
- Command: `git diff --check`
- Result: passes.

Rollback notes:

- Remove `memory_calibration.py`, drop `calibrate_payload` calls, and revert docs/tests if trust labels become noisy.

## 2026-07-11 - Add calibration feedback loop

Files touched:

- `docs/superpowers/specs/2026-07-11-calibration-feedback-loop-design.md`
- `docs/superpowers/plans/2026-07-11-calibration-feedback-loop.md`
- `tools/agent_memory_runtime/retrieval_feedback.py`
- `tools/agent_memory_runtime/query.py`
- `tools/agent_memory_runtime/memory_calibration.py`
- `tools/agent_memory_runtime/governance.py`
- `tools/agent_memory_runtime/cli.py`
- `tests/test_calibration_feedback.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-query/SKILL.md`
- `gitlog.md`

What changed:

- Added a design and implementation plan for calibration feedback.
- Added feedback reasons: `useful`, `verified_useful`, `undertrusted`, and `overtrusted`.
- Added query-time `calibration_feedback_bonus`, `calibration_feedback_penalty`, `calibration_feedback_reasons`, and `calibration_feedback_ids`.
- Updated trust scoring to consume calibration feedback.
- Added `review_overtrusted_memory` and `review_undertrusted_memory` maintain-plan actions.

Why:

- Static trust labels need real usage feedback to become more reliable.
- Positive and negative calibration feedback should adjust answer-time trust without automatically mutating stored memory.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_calibration_feedback`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_calibration_feedback tests.test_memory_calibration tests.test_retrieval_feedback tests.test_quality_performance_scoring`
- Result: 19 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_incident_trace tests.test_retrieval_eval`
- Result: 133 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passes.
- Command: `git diff --check`
- Result: passes.

Rollback notes:

- Remove calibration feedback reason handling, query fields, trust-score integration, governance actions, docs, and tests if the feedback loop becomes noisy.

## 2026-07-11 - Add calibration evaluation suite

Files touched:

- `docs/superpowers/plans/2026-07-11-calibration-evaluation-suite.md`
- `tools/agent_memory_runtime/calibration_eval.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory.py`
- `tests/test_calibration_eval.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-query/SKILL.md`
- `gitlog.md`

What changed:

- Added `eval-calibration --cases <file> --json`.
- Added JSON calibration cases with `expected_trust` and `must_not_trust` specs.
- Added expected trust rate and blocked-overtrust rate reporting.
- Documented when to run calibration evaluation.

Why:

- Trust labels and calibration feedback need a stable regression suite before ranking, feedback, or policy changes.
- The suite turns "memory did not interfere" into a measurable local quality gate.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_calibration_eval`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_calibration_eval tests.test_calibration_feedback tests.test_memory_calibration tests.test_retrieval_eval tests.test_retrieval_feedback`
- Result: 12 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_performance_scoring tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_incident_trace`
- Result: 142 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passes.
- Command: `git diff --check`
- Result: passes.

Rollback notes:

- Remove `calibration_eval.py`, CLI wiring, docs, and tests if the evaluation model proves too rigid.

## 2026-07-11 - Plan experience maturity and log signal quality

Files touched:

- `docs/superpowers/plans/2026-07-11-experience-maturity-and-log-signal-quality.md`
- `gitlog.md`

What changed:

- Added a detailed staged implementation plan for Experience Maturity Level + Counter Evidence.
- Added a detailed staged implementation plan for Log Signal Quality + Log Design Gap.
- Included target files, phased tasks, test strategy, maintain-plan action design, skill updates, verification matrix, and rollback strategy.

Why:

- Experience quality needs maturity and counter-evidence signals before records can safely evolve toward reusable skills.
- Log diagnosis quality needs explicit signal scoring and design-gap governance so runtime logs help locate issues faster without preserving raw logs.

Verification:

- Command: `rg -n "TBD|TODO|implement later|fill in|placeholder|Similar to" docs/superpowers/plans/2026-07-11-experience-maturity-and-log-signal-quality.md`
- Result: no matches.
- Command: `git diff --check`
- Result: passes.

Rollback notes:

- Remove the plan document and this gitlog entry if the project chooses a different next-stage direction.

## 2026-07-11 - Add experience maturity scoring

Files touched:

- `tools/agent_memory_runtime/experience_maturity.py`
- `tools/agent_memory_runtime/query.py`
- `tools/agent_memory_runtime/memory_calibration.py`
- `tests/test_experience_maturity.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-query/SKILL.md`
- `gitlog.md`

What changed:

- Added derived experience maturity levels for reflection query results.
- Added counter-evidence summaries from `negative_preconditions`, `does_not_apply_to`, `what_failed`, `anti_pattern`, and `misleading_followup_terms`.
- Attached maturity fields to `context` and `search` reflection results.
- Updated trust calibration to consume maturity and counter-evidence signals.

Why:

- Experience records need a maturity signal before Agents treat them as reusable procedures or future skill candidates.
- Counter-evidence helps prevent broad experiences from becoming over-trusted rules.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_maturity`
- Result: 8 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_maturity tests.test_memory_calibration tests.test_calibration_feedback tests.test_calibration_eval`
- Result: 15 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_maturity tests.test_memory_calibration tests.test_calibration_feedback tests.test_calibration_eval tests.test_quality_performance_scoring`
- Result: 26 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_incident_trace tests.test_retrieval_eval tests.test_retrieval_feedback`
- Result: 136 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passes.
- Command: `git diff --check`
- Result: passes.

Rollback notes:

- Remove `experience_maturity.py`, remove query/calibration maturity fields, and revert tests/docs if the derived maturity labels become noisy.

## 2026-07-11 - Add counter-evidence governance

Files touched:

- `tools/agent_memory_runtime/experience_maturity.py`
- `tools/agent_memory_runtime/governance.py`
- `tests/test_experience_maturity.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:

- Fixed empty JSON-list counter-evidence detection.
- Added `review_missing_counter_evidence` maintain-plan action for mature experiences that lack negative applicability boundaries.
- Added `review_immature_experience` and `review_maturity_regression` action builders for high-confidence raw observations and deprecated reusable experiences.
- Added governance summary counters for maturity review actions.

Why:

- Mature-looking experiences should not become reusable rules until the system knows where they do not apply.
- Regressed or misleading reusable experiences need review before they can influence future skill evolution.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_maturity`
- Result: 9 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_maturity tests.test_quality_performance_scoring tests.test_memory_calibration tests.test_calibration_feedback`
- Result: 25 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_incident_trace tests.test_retrieval_eval tests.test_retrieval_feedback tests.test_calibration_eval`
- Result: 138 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passes.
- Command: `git diff --check`
- Result: passes.

Rollback notes:

- Remove maturity governance action wiring and counters, and revert docs/tests if counter-evidence review becomes noisy.

## 2026-07-11 - Plan experience quality and graph signal roadmap

Files touched:

- `docs/superpowers/plans/2026-07-11-experience-quality-and-graph-signal-roadmap.md`
- `gitlog.md`

What changed:

- Added a detailed executable roadmap for the combined `1 + 5` direction.
- Split the work into experience query hardening, procedure/correction recording shape, log signal quality, graph signal governance, evaluation gates, skill guidance, and final regression phases.
- Defined expected data contracts for experience trust fields, log signal fields, and graph signal quality fields.
- Included concrete files, test commands, acceptance criteria, commit points, and rollback strategy for staged execution.

Why:

- The next improvements need to reduce experience interference while also making code/log graph anchors more useful for diagnosis.
- A staged document lets later implementation proceed without re-opening the design discussion each time.

Verification:

- Command: `git diff --check`
- Result: passes.

Rollback notes:

- Remove the roadmap document and this gitlog entry if the project chooses a different execution sequence for `1 + 5`.

## 2026-07-11 - Harden experience query trust

Files touched:

- `tools/agent_memory_runtime/experience_query_quality.py`
- `tools/agent_memory_runtime/memory_calibration.py`
- `tests/test_experience_query_quality.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-query/SKILL.md`
- `docs/superpowers/plans/2026-07-11-experience-quality-and-graph-signal-roadmap.md`
- `gitlog.md`

What changed:

- Added query-facing experience trust explanations with `query_risk_flags`, `trust_cap`, and `trust_cap_reasons`.
- Capped stale, misleading, deprecated, and raw-observation experiences so confidence or quality cannot make them dominate query direction.
- Added a soft cap and risk flag for verified procedure experiences that still lack counter-evidence.
- Allowed positive calibration feedback to raise trust past the missing-counter-evidence soft cap while preserving the risk flag.
- Added regression tests for misleading experience caps, missing counter-evidence flags, and correction-guard guidance versus broad procedure experience.

Why:

- Recent or broadly related experience can interfere with the user's actual query unless trust explains risk and applies hard bounds for misleading or stale records.
- Procedure experience without negative applicability boundaries should remain useful but visibly risky.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_query_quality`
- Result: 3 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_query_quality tests.test_experience_maturity tests.test_memory_calibration tests.test_calibration_feedback`
- Result: 17 tests pass.
- Command: `git diff --check`
- Result: passes.

Rollback notes:

- Remove `experience_query_quality.py`, remove query-risk fields from calibration output, and revert the new tests/docs if trust caps prove too strict.

## 2026-07-11 - Clarify experience recording shapes

Files touched:

- `tools/agent_memory.py`
- `tests/test_experience_query_quality.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-reflect/SKILL.md`
- `docs/superpowers/plans/2026-07-11-experience-quality-and-graph-signal-roadmap.md`
- `gitlog.md`

What changed:

- Added regression coverage that procedure experience and correction experience preserve distinct runtime fields.
- Added validation that rejects `skill_candidate` on `correction_experience`.
- Documented that correction experience should route to guardrail or semantic-repair governance instead of direct skill evolution.

Why:

- Skill candidates should emerge from verified and reused procedure patterns, not from a single business-semantic correction.
- Keeping correction records distinct prevents semantic repair notes from becoming broad task procedures.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_query_quality`
- Result: 5 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_maturity tests.test_memory_calibration tests.test_calibration_feedback`
- Result: 14 tests pass.
- Command: `git diff --check`
- Result: passes.

Rollback notes:

- Remove the `skill_candidate` validation for correction experience and revert the Phase 2 tests/docs if correction records need to temporarily carry promotion hints.

## 2026-07-11 - Add log signal quality scoring

Files touched:

- `tools/agent_memory_runtime/log_signal_quality.py`
- `tools/agent_memory_runtime/runtime_logs.py`
- `tools/agent_memory_runtime/query.py`
- `tests/test_log_signal_quality.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-query/SKILL.md`
- `docs/superpowers/plans/2026-07-11-experience-quality-and-graph-signal-roadmap.md`
- `gitlog.md`

What changed:

- Added deterministic log signal scoring for runtime events and learned code log matches.
- Added `log_signal_score`, `log_signal_band`, `present_signals`, `missing_signals`, and `suggested_log_fields`.
- Added `log_signal_summary` and `low_signal_events` to `analyze-runtime-log` output without persisting raw runtime logs to SQLite.
- Enriched `code_log_matches` from `context` and `search` with log signal quality fields.

Why:

- Goal-oriented incident diagnosis needs to distinguish useful log evidence from generic matching text.
- Low-signal logs should become narrow logging improvement guidance instead of misleading the Agent into over-reading weak evidence.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_log_signal_quality`
- Result: 5 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_log_signal_quality tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_incident_trace`
- Result: 141 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_query_quality tests.test_experience_maturity tests.test_memory_calibration tests.test_calibration_feedback`
- Result: 19 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passes.
- Command: `git diff --check`
- Result: passes.

Rollback notes:

- Remove `log_signal_quality.py`, stop enriching runtime events and code log matches with signal fields, and revert related tests/docs if the signal scoring proves too noisy.

## 2026-07-11 - Add graph signal quality governance

Files touched:

- `tools/agent_memory_runtime/graph_quality.py`
- `tools/agent_memory_runtime/governance.py`
- `tests/test_graph_quality.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-maintain/SKILL.md`
- `docs/superpowers/plans/2026-07-11-experience-quality-and-graph-signal-roadmap.md`
- `gitlog.md`

What changed:

- Added `graph_signal_quality` to maintain-health and maintain-plan outputs.
- Scored whether learned graph anchors are useful for retrieval and diagnosis, not only whether they are structurally connected.
- Added concrete `top_repair_targets` for weak code-log and symbol anchors.
- Added `review_graph_signal_quality` maintain-plan action with narrow suggested repairs.

Why:

- A graph can be structurally healthy while still failing to guide diagnosis if anchors lack business semantics or diagnostic log fields.
- Maintenance should tell the Agent exactly which log or symbol to enrich instead of recommending broad relearning.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_graph_quality`
- Result: 4 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_graph_quality tests.test_quality_performance_scoring tests.test_log_signal_quality tests.test_retrieval_feedback`
- Result: 23 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_incident_trace`
- Result: 131 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passes.
- Command: `git diff --check`
- Result: passes.

Rollback notes:

- Remove graph signal helpers/action wiring and revert tests/docs if the extra maintain-plan action becomes noisy.

## 2026-07-11 - Add retrieval and diagnosis quality gates

Files touched:

- `tools/agent_memory_runtime/retrieval_eval.py`
- `tools/agent_memory_runtime/log_signal_eval.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory.py`
- `tests/test_retrieval_eval.py`
- `tests/test_log_signal_quality.py`
- `tests/test_calibration_eval.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/superpowers/plans/2026-07-11-experience-quality-and-graph-signal-roadmap.md`
- `gitlog.md`

What changed:

- Extended `eval-retrieval` with `expected_top`, exact anchor rank, expected-top hit rate, `noise`, and experience noise rate.
- Added `eval-log-signal` for temporary log-line quality gates.
- Added log signal eval metrics: good signal rate and low signal event rate.
- Updated calibration eval fixture data so verified procedure experience includes counter-evidence under the current trust model.

Why:

- Query improvements need regression gates that catch exact-anchor demotion and high-trust experience noise.
- Log diagnosis improvements need a small measurable gate before changing parsers, scoring, or runtime-log output.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_retrieval_eval`
- Result: 3 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_log_signal_quality tests.test_retrieval_eval tests.test_calibration_eval`
- Result: 11 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passes.
- Command: `git diff --check`
- Result: passes.

Rollback notes:

- Remove `eval-log-signal`, remove retrieval eval top/noise metrics, and revert tests/docs if the additional gates are too strict.

## 2026-07-11 - Update skills for quality-guided memory use

Files touched:

- `skills/agent-memory-learn/SKILL.md`
- `skills/agent-memory-maintain/SKILL.md`
- `README.md`
- `docs/superpowers/plans/2026-07-11-experience-quality-and-graph-signal-roadmap.md`
- `gitlog.md`

What changed:

- Updated learn skill guidance to inspect semantic, graph, and graph-signal quality after learning.
- Updated maintain workflow order to run health, signal review, eval gates, maintain-plan, and then confirmed mutations.
- Added README summary of retrieval, trust, log signal, and graph signal gates.

Why:

- The four public skills need to consume the new quality signals consistently without adding a fifth user-facing skill.
- Operators need a clear order for quality checks so maintenance stays narrow and evidence-driven.

Verification:

- Command: `rg -n "experience_maturity|counter_evidence|log_signal|graph_signal" skills docs README.md`
- Result: matches expected skill and documentation guidance.
- Command: `git diff --check`
- Result: passes.

Rollback notes:

- Revert these docs/skill edits if the operator workflow needs a different ordering.

## 2026-07-11 - Complete experience and graph signal quality roadmap

Files touched:

- `docs/superpowers/plans/2026-07-11-experience-quality-and-graph-signal-roadmap.md`
- `gitlog.md`

What changed:

- Marked the final roadmap verification phase complete.
- Recorded final regression, compile, formatting, skill count, and runtime entrypoint evidence.

Why:

- The roadmap is now implemented through all planned phases and needs a durable local completion record.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_maturity tests.test_experience_query_quality tests.test_log_signal_quality tests.test_graph_quality`
- Result: 24 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests tests.test_incident_trace tests.test_retrieval_eval tests.test_retrieval_feedback tests.test_calibration_eval tests.test_quality_performance_scoring`
- Result: 150 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py`
- Result: passes.
- Command: `git diff --check`
- Result: passes.
- Command: `ls -1 skills`
- Result: exactly `agent-memory-learn`, `agent-memory-maintain`, `agent-memory-query`, and `agent-memory-reflect`.
- Command: `rg -n "argparse|subparsers|add_parser" tools/agent_memory.py tools/agent_memory_runtime/cli.py`
- Result: parser wiring remains under `tools/agent_memory.py` and `tools/agent_memory_runtime/cli.py`; no new user-facing skill was added.

Rollback notes:

- Revert the roadmap completion marker and this gitlog entry only if the final verification evidence needs to be rerun.
