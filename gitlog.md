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
