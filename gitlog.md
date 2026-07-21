# Local Development Log

This repository is currently not a git repository. Use this file as a lightweight local change log so implementation work can be reviewed and manually rolled back.

## 2026-07-17 - Bound Agent source expansion and stopping

Files changed:
- Compact context, Query Skill, Agent benchmark protocol/evaluator, Codex Runner,
  tests, and usage/benchmark docs.

What changed:
- Added `anchor_first_gap_driven_v1` as a shared deterministic exploration
  contract without moving diagnosis into Runtime.
- Marked up to three compact code anchors as `primary` and two as `expansion`.
- Required named evidence-gap reasons before expansion, bounded source files,
  searches, expansion rounds, and files per round, and explicit stop reasons.
- Added Runner-computed primary-anchor/non-anchor counts and a compatible
  benchmark budget gate for newly reporting Runners.
- Separated causal/repair-owner `predicted_files` from inspected
  `supporting_files` while retaining both in the investigation trail.
- Reduced the repeated compact exploration contract from about 175 estimated
  tokens to 28 by keeping only its policy id and numeric limits.
- Upgraded the current policy to `anchor_first_gap_driven_v2`: natural-language
  retrieval filters English noise and low-discrimination code metawords, and
  FTS5 prefix recall maps domain words such as `sticker` to compound identifiers
  such as `StickerView`.
- Added `evidence_basis` and `mechanism_evidence_files`; a supported stop now
  requires direct mechanism evidence from an inspected causal file.
- Upgraded the current protocol to `anchor_first_gap_driven_v3`: the Agent emits
  `expansion_trace` items and the Runner derives round/reason totals, allowing
  two bounded new files per round without inconsistent parallel counters.
- Allowed direct mechanism evidence to span an inspected supporting boundary
  while still requiring at least one predicted causal owner, and clarified
  async/state classification for in-flight concurrency and duplicate effects.

Why:
- The three-trial Gramony run improved quality consistently but Memory inspected
  more files and averaged 50,983 more model tokens than Baseline.

Verification:
- Focused compact-context, Runner, protocol, and benchmark tests pass.
- Existing 18-observation Gramony response pack rescored with all historical
  gates passing; missing exploration fields remain explicitly unreported.
- All 403 tests passed in 298.909 seconds after the file-role and compact
  contract refinement.
- The repository still contains exactly four Skills, and every Python file
  remains below 500 lines.
- The authorized post-optimization three-case, three-trial Gramony A/B completed
  18 external calls with all quality, stability, context, and exploration gates
  passing.
- Compared with the pre-optimization Memory batch, model tokens fell by 2,722
  (1.9%), Agent elapsed time by 2.29 seconds (3.3%), and inspected files by 0.33
  (7.7%). Outcome score fell from 1.0 to 0.9833 because split-view navigation
  included one supporting file in addition to the expected causal file.
- File-role and compact-contract refinements pass focused protocol tests; their
  external post-refinement A/B completed all 18 calls but failed the quality
  gate.
- Local frozen Gramony queries measured 490, 456, and 564 context tokens after
  refinement, about 147 fewer per case than the first gap-driven payloads.
- Both saved 18-observation Gramony packs retain their original scores and pass
  every gate when rescored through the compatible `supporting_files` protocol.
- The refined batch restored split-view predicted-file precision by moving
  `Index.ets` to `supporting_files`, and averaged 5,172 fewer tokens than its
  same-batch Baseline.
- One of three WebM Memory trials missed `MessageBubble.ets`, reducing the batch
  score to 0.9000 versus Baseline 0.9556. The reconstructed frozen query showed
  only generic chat anchors, exposing a retrieval-recall and premature-stop
  defect. The exact failed batch is retained for regression testing.
- A frozen local WebM query now returns `MessageBubble.ets / StickerOnlyView` as
  a primary anchor instead of omitting the owner. Its compact context is about
  541 estimated tokens.
- The new retrieval and stop-contract tests pass, as do all 119 runtime part
  tests.
- All 406 repository tests passed in 327.039 seconds after the v2 retrieval,
  protocol, Skill, and documentation changes.
- The authorized v2 three-case, three-trial Gramony A/B completed all 18 calls.
  Aggregate outcome, root-cause accuracy, file recall, and file precision were
  equal to Baseline, but the batch failed per-case and source-exploration gates.
- WebM recovered fully: all three Memory trials selected `media` and
  `MessageBubble.ets`, inspected only the two primary anchors, and used no
  non-anchor expansion.
- One login Memory trial labeled the correctly described parallel async
  mechanism as `state`, and v2 evidence reporting exposed supporting-file and
  expansion-audit violations. The exact failed batch is retained for offline
  regression testing.
- V3 focused protocol, Runner, compact-context, and benchmark tests pass. The
  frozen WebM query still returns `MessageBubble.ets` as a primary anchor at
  about 541 context tokens.
- The saved v2 pack rescored unchanged at 0.9556 with the same per-case and
  exploration gate failures; v3 does not rewrite historical observations.
- All 409 repository tests passed in 359.785 seconds after the v3 exploration
  audit and category-boundary refinement.

## 2026-07-17 - Add repeated Agent trials and retrieval discipline

Files changed:
- Agent benchmark CLI, protocol, evaluator, Codex Runner, tests, and docs.

What changed:
- Added bounded `--trials 1..10` with independently paired Baseline/Memory runs.
- Added trial indices, per-case trial details, non-regression rate, root-cause
  consistency, and predicted-file consistency.
- Added Runner-computed source file count and Memory anchor hit count/rate.
- Added `anchor_first_bounded_v1` instructions to limit context-driven expansion.
- Required two-thirds trial non-regression and root-cause agreement for stability.

Why:
- A single model run can misclassify a correct source conclusion or choose a
  different tool path. Aggregate case scores also cannot establish repeatability.

Verification:
- Focused benchmark and Runner tests cover trial pairing, stability gates,
  trial bounds, prompt discipline, and computed anchor hits.
- Existing single-trial Gramony responses remain compatible and report
  `stability_evaluated=false`; the known WebM per-case regression remains visible.
- The authorized three-case, three-trial Gramony A/B completed 18 external
  Agent calls with all quality and stability gates passing.
- Memory improved outcome score from 0.8667 to 1.0 and root-cause accuracy from
  0.6667 to 1.0, with every case non-regressing in all three trials.
- Memory averaged 50,983 more model tokens, 27.9 seconds more elapsed time, and
  a 0.6815 code-anchor hit rate, so Agent expansion cost remains the next target.
- All 394 tests passed in 624.003 seconds.
- The repository still contains exactly four Skills, and every Python file
  remains below 500 lines.

## 2026-07-17 - Bound benchmark Memory context

Files changed:
- Benchmark Memory command, protocol, evaluation, Codex Runner, tests, and Gramony records.

What changed:
- Switched diagnosis benchmark retrieval from full `context` to `context --compact`.
- Added per-observation Memory payload byte and estimated-token metrics.
- Added a 1,500-token Memory context quality gate for reporting Runners.
- Preserved compatibility for third-party response packs that do not report context metrics.

Verification:
- Three frozen Gramony revisions reduced Runner payload bytes by 95.55% to 96.79%.
- Compact payload estimates were 444, 414, and 508 tokens.
- All 387 tests passed in 448.891 seconds.
- The explicitly approved compact external A/B had equal aggregate quality but
  failed the new per-case gate because WebM regressed by 0.4.
- Compact Memory averaged 455 context tokens but increased total model usage by
  34,473 tokens, so payload size alone does not explain the remaining cost.

## 2026-07-16 - Reproducible Gramony Agent benchmark

Files changed:
- Agent benchmark runtime, Codex Runner, tests, and Gramony benchmark records.

What changed:
- Added exact `--case-id` selection and persisted runner configuration metadata.
- Preloaded isolated Memory context before the read-only Codex session.
- Isolated Codex from user Skills, Plugins, rules, history, and memory.
- Added three pinned Gramony development A/B pairs.
- Capped source-only diagnosis at supported causality with unknown verification.

Verification:
- Pinned three-case run passed with `gpt-5.5`, low reasoning, and isolated user context.
- Memory outcome score was 1.0 versus 0.8667, with 66,424 more average tokens.
- All 382 tests passed in 558.096 seconds.
- Focused benchmark tests passed and Python files remain below 500 lines.

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

## 2026-07-15 - Design log-anchored call path reconstruction

Files changed:
- `docs/log-anchored-call-path-design.md`
- `docs/context-provider-boundary.md`
- `README.zh-CN.md`

What changed:
- Designed a single public `context` facade with an internal path-context facade instead of adding another diagnosis command.
- Defined language-neutral Protocol boundaries for log-anchor resolution, graph access, entry classification, bounded path search, and explainable ranking.
- Isolated log-anchor, program-path, semantic-correction, and experience lanes so advisory memory cannot change path seeds, graph edges, or structural ranking.
- Specified revision-bound Top-K path candidates, Agent-owned temporary-log alignment, ArkTS entry adapters, bounded SQL/query behavior, degradation rules, phased implementation, and A/B quality gates.
- Preserved primary references to SherLog, CodeQL path queries, dynamic slicing, process-model alignment, OpenTelemetry, W3C Trace Context, and Dapper.

Why:
- The next implementation needs an easy facade while keeping storage, language semantics, graph algorithms, and ranking replaceable. Static candidate paths must remain project context rather than Runtime-selected diagnoses.

Verification:
- `git diff --check` passed.
- Documentation links and active command names were checked against the current repository.
- No runtime code or SQLite schema changed.

Rollback notes:
- Remove the new design document and its two documentation links. Runtime behavior and stored data are unchanged.

## 2026-07-15 - Make incident diagnosis Agent-led through context retrieval

Files changed:
- Query CLI, result shaping, handoff, usage sampling, and obsolete runtime-log modules.
- Query/Reflect/Maintain Skill protocols and incident/query documentation.
- Incident, query, evidence-boundary, design, and Agent benchmark tests.

What changed:
- Removed the public `evidence-context` and `analyze-runtime-log` commands and their Runtime handlers.
- Made `context` return `agent-query-handoff/v1` with historical references, learned log keywords/templates, current source anchors, raw bounded graph edges, and a one-candidate-per-query follow-up contract.
- Removed public evidence-chain, log-search-plan, and historical `likely_causes` output from normal query results.
- Deleted unused Runtime hypothesis, temporary-log analysis, reflection-template, and evidence-governance paths.
- Defined the incident workflow as user problem query, Agent-owned temporary-log analysis, multiple candidate causes, one follow-up query per cause, current-source inspection, and Agent-inferred call/causal chains.
- Kept repository design and impact analysis as separate read-only capabilities, and kept exactly four public Skills.

Why:
- Temporary user logs and causal diagnosis require the local Agent's reasoning and source-inspection loop. Runtime-generated chains and hypotheses duplicated that role, encouraged false certainty, and complicated the interface instead of improving project context retrieval.

Verification:
- Public CLI help no longer exposes `evidence-context` or `analyze-runtime-log`.
- All 341 tests passed, including focused query, incident, evidence-boundary, benchmark, semantic, and design coverage.
- Python compilation, diff check, exactly four public Skills, and the 500-line Python gate passed.

Rollback notes:
- Restore the removed parsers/handlers and temporary-log modules to recover the old Runtime-led flow. Stored SQLite data does not require migration; `query_handoff` is additive to normal `context` output.

## 2026-07-14 - Add user-facing design capability guide

Files changed:
- `docs/design-usage-guide.md`
- `README.md`

What changed:
- Added a Chinese end-to-end guide for natural-language use through the fixed Query Skill and direct CLI use for inspection or CI.
- Documented intent, contract, candidate Delta, optional project rules, Change Plan progress, compiler/test evidence, revision binding, final verification, and reviewed Outcome calibration.
- Added copy-ready ArkTS examples, result-state handling, Agent behavior boundaries, a minimal workflow, and common questions.

Why:
- The design control loop was implemented and internally documented, but users lacked one operational guide that explained how to invoke and interpret it without learning a fifth Skill.

Verification:
- Markdown links, command names, schema versions, and examples were checked against the current CLI and runtime protocol.
- `git diff --check` passed.

Rollback notes:
- Remove the guide and README link; runtime behavior and stored data are unchanged.

## 2026-07-14 - Harden repository-grounded design quality

Files changed:
- Design evaluation, Change Plan, progress, verification, calibration, storage, CLI, and tests.
- Optional `providers/arkts-arkanalyzer` package and exact capability cases.
- README, Agent, Query Skill reference, runtime, usage, Provider, design, and execution-plan documentation.

What changed:
- Replaced empty-sample perfect design metrics with `null` plus explicit metric coverage, calculated contract validity, added positive preference/verification cases, and enforced evaluation coverage readiness.
- Replaced fallback serial Change Plans with graph/coverage-derived dependencies so independent implementation steps remain parallel.
- Added optional `verification-run/v1` Git/source/report provenance, stale-evidence rejection, and `compiler-report/v1` ingestion.
- Required proposal-declared ArkTS/TypeScript entities before added files complete; partial files remain `in_progress` and expose bounded working-tree semantic evidence.
- Added a real optional ArkAnalyzer Scene/type Provider for exact definitions, calls, inheritance, interfaces, and ArkTS state ownership with explicit static fallback.
- Added compact design archetype/change-size/risk/API/graph calibration. Historical risk remains inactive before five matching reviewed outcomes and is only a final tie-break after current evidence.

Verification:
- All 333 tests passed when run in isolated module batches; focused design, progress, Provider, and quality-hardening suites also passed.
- Python compilation, JSON validation, Node syntax, CLI help, diff check, exactly four public Skills, and the 500-line Python gate passed.
- ArkAnalyzer external evaluation: 3/3 cases passed with relation recall 1.0, forbidden-edge rate 0.0, and resolution rate 1.0.
- On the 6,995-ArkTS-file sample: evaluation 560.98 ms, planning 446.55 ms, verification 546.25 ms, and progress 622.91 ms median. Calibration lookup measured 2.509 ms median and 3.449 ms p95.

Rollback notes:
- Unset `AGENT_MEMORY_SEMANTIC_PROVIDER_ARKTS` to return to static semantics. Removing provenance, semantic progress completion, calibration columns, and evaluation/DAG hardening does not require deleting source or raw logs; added outcome columns are compact and backward-compatible.

## 2026-07-14 - Add design implementation progress checkpoints

Files changed:
- Design progress runtime/CLI, shared changed-file resolver, tests, Query design reference, and design documentation.

What changed:
- Added read-only `design-progress` and ephemeral `design-progress/v1` reconstruction over the selected `change-plan/v1`.
- Classified steps as completed, ready, pending, or blocked from Git file/symbol Delta, passed test evidence, DAG dependencies, and design gates.
- Recognized proposal-declared untracked added files with project-root path constraints and explicit evidence gaps.
- Allowed bounded manual completion only for consumer-review and observability steps; implementation and test steps still require automatic evidence.
- Allowed an empty working tree only for progress reconstruction while preserving strict empty-change behavior for Impact and final verification.

Why:
- The prior workflow jumped from a static change plan directly to final verification and could not tell the Agent which implementation step was currently safe to execute.

Verification:
- Focused progress, design, repository, evolution, and impact suites: 35 tests passed.
- Final full suite: 324 tests passed in 263.530 seconds.
- On the 6,995-ArkTS-file OpenHarmony sample repository, five CLI progress reconstructions had 645.41 ms median latency; the cold maximum was 1.612 seconds.
- Compilation, CLI help, diff check, fixed four-Skill count, and 500-line Python gate passed.

Rollback notes:
- Removing `design-progress` restores the prior static-plan/final-verify flow. The optional resolver flag defaults to the previous strict behavior, and no database rollback is required.

## 2026-07-14 - Add pre-candidate design workbench

Files changed:
- Design preparation runtime/CLI, proposal revision gate, design tests, Query design reference, and design documentation.

What changed:
- Added read-only `design-prepare` and runtime-only `design-workbench/v1` before candidate authoring.
- Added a bounded repository anchor catalog, relation vocabulary, synthesis brief, authoring readiness gaps, and fitness-rule context.
- Added an unclaimed `design-delta/v2` template with empty modifications, coverage claims, and verification claims.
- Bound prepared candidates to `baseline_revision`; `design-check` and comparison now hard-fail stale prepared candidates while preserving unbound legacy candidates.

Why:
- The prior flow exposed synthesis evidence only after a proposal existed, forcing the Agent to design before receiving the complete repository and constraint brief.

Verification:
- Focused design, repository-model, evolution, and exact-provider suites: 37 tests passed.
- Final full suite: 322 tests passed in 269.719 seconds.
- On the 6,995-ArkTS-file OpenHarmony sample repository, five CLI workbench builds had 527.02 ms median latency; the cold maximum was 1.567 seconds.
- Compilation, diff check, fixed four-Skill count, and 500-line Python gate passed.

Rollback notes:
- Removing `design-prepare` restores the prior direct author/check flow. Existing proposals without `baseline_revision` remain valid, and no database rollback is required.

## 2026-07-14 - Automate design verification evidence

Files changed:
- Design verification, source Delta, semantic parser, CLI, tests, and design protocol documentation.

What changed:
- Added bounded Git hunk mapping to fresh ArkTS/TypeScript symbols with learned-span fallback.
- Added exported API additions/removals/signature changes and source relation Delta, kept separate from learned-graph alignment.
- Added repeatable JUnit XML, generic/pytest JSON, and Jest report ingestion without executing test commands.
- Added replan triggers for unplanned exported API changes and supported source-relation mismatches.
- Kept source, diff bodies, reports, and verification output out of persistent memory.

Why:
- Caller-supplied file, symbol, and test claims left the design control loop unable to verify implementation drift automatically.

Verification:
- Final full suite: 321 tests passed in 251.901 seconds; all 11 design-control-loop tests passed independently.
- Compilation, diff check, fixed four-Skill count, and 500-line Python gate passed.
- On the 6,995-ArkTS-file OpenHarmony sample repository, seven bounded source-evidence collections had 17.17 ms median and 31.37 ms maximum latency; the end-to-end fixture including repository and memory setup completed in 1.11 seconds.

Rollback notes:
- Existing explicit files, symbols, `test-evidence/v1`, and legacy executed-test inputs remain compatible. Removing automatic evidence leaves the prior verification path intact.

## 2026-07-14 - Add repository-grounded design control loop

Files changed:
- Design protocol, repository-model, evaluation, planning, verification, outcome, CLI, storage, and governance runtime modules.
- `tests/test_design_control_loop.py` and existing design-context coverage.
- Agent, runtime, usage, schema, Skill protocol, Query design reference, README, and execution-plan documentation.

What changed:
- Added a revision-bound `repository-model/v2` shared by design context, candidate checks, comparison, impact analysis, and verification.
- Separated goal-derived baseline anchors from explicit candidate/intent scope so a proposal cannot define its own evidence boundary.
- Added v2 intent, contract, Delta, and evaluation support with `claimed`, `supported`, and `verified` coverage states while preserving v1 inputs and outputs.
- Added deterministic evaluation dimensions, decision sensitivity/tradeoff points, and a bounded dependency-ordered `change-plan/v1`.
- Added symbol and structured-test verification, graph revision drift checks, and explicit compact `design-outcome/v1` calibration with 1,000-row retention.
- Kept proposals, source, diffs, test logs, generated reasoning, and architecture rules out of persistent storage.
- Removed repeated internal architecture payloads from public model/comparison output.

Why:
- The previous commands checked isolated proposal slices but did not share one repository baseline, prove coverage claims, plan dependent edits, or calibrate predicted design impact against reviewed outcomes.

Verification:
- Focused design, evidence, semantic, impact, migration, and governance suites pass.
- Final complete suite: 316 tests passed in 217.371 seconds.
- On the 312 MiB / 16,300-file archive: warm single-candidate check median 0.496 seconds; two-candidate comparison median 0.490 seconds with one reused baseline.
- Compact comparison output fell from 55,627 to 22,558 bytes after separating internal and public repository-model payloads.

Rollback notes:
- V1 design inputs remain compatible. Removing v2 orchestration leaves existing code facts and design checks usable. Dropping `design_outcomes` removes calibration only.

## 2026-07-14 - Add lazy governance lanes and graph-quality snapshots

Files changed:
- `tools/agent_memory_runtime/governance_lane_plan.py`
- `tools/agent_memory_runtime/governance_plan.py`
- `tools/agent_memory_runtime/governance_plan_actions.py`
- `tools/agent_memory_runtime/governance_action_budget.py`
- `tools/agent_memory_runtime/graph_quality.py`
- `tools/agent_memory_runtime/graph_quality_snapshot.py`
- `tools/agent_memory_runtime/code_wiki_edges.py`
- `tools/agent_memory_runtime/storage_schema.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory_runtime/governance_health.py`
- `tests/test_lazy_governance_snapshot.py`
- Runtime, schema, usage, Agent, Maintain Skill, and execution-plan documentation.

What changed:
- Added dependency-driven focused execution for 18 known governance lanes while preserving complete-plan and unknown-lane fallback behavior.
- Added `execution_scope` metadata so focused zero counts cannot be mistaken for full-archive health.
- Added transactional graph revision invalidation in SQLite and a revision-bound runtime graph-quality snapshot.
- Added `--verify-graph-quality` for explicit fresh graph audits without mutating memory or graph rows.
- Added Lane guards that prevent unrelated correction, query-miss, and refresh-drift loaders from running during focused plans.

Why:
- A selected Lane previously paid for every governance report, and graph quality repeatedly scanned the full graph even when no learned structure changed.

Verification:
- Public CLI coverage passes for all 18 known lanes, unknown-lane fallback, snapshot hit, graph invalidation, and forced verification.
- Full suite: 310 tests passed in 368.818 seconds.
- On the 312 MiB benchmark archive: warm full plan 0.86 seconds / 167 SQLite execute calls; `memory_tiers` focused 0.41 seconds / 33 calls; cached `graph_quality` focused 0.49 seconds / 39 calls.

Rollback notes:
- Remove the focused planner branch to restore output-only Lane filtering. Removing `graph_runtime_state` is unnecessary; deleting `runtime/graph_quality_snapshot.json` safely forces recomputation.

## 2026-07-14 - Remove redundant loop queries and repeated computation

Files changed:
- `tools/agent_memory_runtime/semantic_ecma.py`
- `tools/agent_memory_runtime/retrieval_feedback.py`
- `tools/agent_memory_runtime/experience_usage.py`
- `tools/agent_memory_runtime/query_collect.py`
- `tools/agent_memory_runtime/query_edges.py`
- `tools/agent_memory_runtime/governance_corrections.py`
- `tools/agent_memory_runtime/governance_review_data.py`
- `tools/agent_memory_runtime/governance_utils.py`
- `tools/agent_memory_runtime/governance_learn_actions.py`
- `tools/agent_memory_runtime/governance_plan.py`
- `tools/agent_memory_runtime/governance_plan_actions.py`
- `tools/agent_memory_runtime/graph_quality.py`
- `tools/agent_memory_runtime/storage_migrations.py`
- `tests/test_graph_query_performance.py`
- `docs/superpowers/plans/2026-07-14-loop-query-computation-optimization.md`

What changed:
- Precomputed per-file ArkTS fields, state names, imports, and container intervals instead of rescanning them for every callable.
- Batched retrieval feedback and usage reads across semantic/reflection types and derived feedback adjustments in one pass.
- Combined inbound/outbound edge retrieval per batch and added matching recent-feedback indexes.
- Bounded active reflection governance, precomputed conflict text/tokens, blocked disjoint conflict pairs with inverted indexes, and replaced duplicate-record Cartesian comparisons with overlap postings.
- Reused active reflections, skill pattern candidates, action counts, graph quality, query-miss search results, and graph aggregate counts.
- Replaced a three-table missing-business-semantics UNION with bounded per-table reads and an equivalent sorted merge.

Why:
- Profiling showed repeated file scans, repeated database connections, duplicate graph-quality builds, and quadratic governance comparisons that grow poorly as memory approaches 500,000 rows.

Verification:
- Final full suite: 306 tests passed in 349.807 seconds.
- Large 312 MiB corpus: warm search completed in 0.52 seconds.
- Profiled maintain-plan SQLite execute calls fell from 235 to 178.
- All Python files remain under 500 lines; compilation, four-Skill count, CLI help, and diff checks pass.

Rollback notes:
- Revert the parsing context, feedback batch helpers, edge query merge, governance blocking indexes, and graph snapshot reuse independently. The two added SQLite indexes are non-destructive and may remain.

## 2026-07-14 - Bound code graph and query performance at large scale

Files changed:
- `tools/agent_memory_runtime/storage_search_schema.py`
- `tools/agent_memory_runtime/storage_migrations.py`
- `tools/agent_memory_runtime/code_wiki_design_edges.py`
- `tools/agent_memory_runtime/code_wiki_edges.py`
- `tools/agent_memory_runtime/code_wiki_indexing.py`
- `tools/agent_memory_runtime/semantic_index.py`
- `tools/agent_memory_runtime/semantic_models.py`
- `tools/agent_memory_runtime/derived_rebuild.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory_runtime/runtime_entry.py`
- `tests/test_graph_query_performance.py`
- Runtime, schema, Agent, Maintain Skill, and execution-plan documentation.

What changed:
- Version-gated FTS and edge-metadata migrations so normal CLI startup no longer rebuilds FTS or rewrites every graph edge.
- Replaced global basename-based `tested_by` inference with code-only, explicit-test, module-local, ambiguity-safe matching.
- Added `maintain-rebuild-derived` to repair FTS or source-derived graph rows while preserving code business semantics and durable memory.
- Scoped partial graph symbol/log reads, bounded reverse-dependent lookup, batched code row and containment/log edge writes, and range-bounded edge metadata annotation.
- Batched semantic adapter files and relation persistence, and bounded gap diagnostics without dropping valid semantic batches.
- Added graph amplification and relation-dominance audits.

Why:
- Real OpenHarmony pressure testing exposed repeated full-index work, cross-module test-edge pollution, and project-size-dependent partial refresh costs above 500,000 graph rows.

Verification:
- `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest discover -s tests -p 'test_*.py'`: 298 tests passed in 192.128 seconds.
- Full Python compilation, `python3 tools/check_line_limits.py`, four-Skill count, CLI help, and `git diff --check`: passed.
- OpenHarmony full index: 16,300 files, 84,227 symbols, 18,240 logs, 202,298 edges in 132.50-137.74 seconds.
- OpenHarmony miss query: 0.66 seconds; hit query: 1.89 seconds; 33-line partial refresh: 1.99 seconds.
- Safe graph rebuild preserved business and durable-memory checks and completed semantic indexing without adapter errors.
- SQLite `VACUUM` reduced the repaired benchmark database from 752 MiB to 312-328 MiB.

Rollback notes:
- Revert the version gates, derived rebuild command, scoped/batched writers, and module-local test matcher together. Existing SQLite rows remain readable; no destructive schema rollback is required.

## 2026-07-13 - Enforce Python file line limit

Files changed:
- `tools/check_line_limits.py`
- `tools/agent_memory.py`
- `tools/agent_memory_runtime/*.py`
- `tests/test_agent_memory.py`
- `tests/agent_memory_test_base.py`
- `tests/test_agent_memory_part_*.py`
- `docs/superpowers/plans/2026-07-13-python-file-line-limit-remediation.md`
- `gitlog.md`

What changed:
- Added a repository-local Python line-limit checker for `install.py`, `tools/**/*.py`, and `tests/**/*.py`.
- Split large runtime modules into focused facades and helper modules across query, code wiki, governance, storage, vault, runtime logs, and CLI entry handling.
- Split the oversized runtime test suite into numbered part files with shared test helpers.
- Preserved the four user-facing skills and the stable `tools/agent_memory.py` CLI entry point.

Why:
- Keep every Python code file under 500 lines so future agent edits remain reviewable, locally bounded, and easier to evolve.

Verification:
- Command: `python3 tools/check_line_limits.py`
- Result: passes, all Python files are <= 500 lines.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py tests/*.py install.py`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest discover tests`
- Result: passes, 237 tests.

Rollback notes:
- Revert the facade/helper module splits and restore the previous monolithic files if compatibility requires a single-file layout; keep `tools/check_line_limits.py` only if the line-limit gate should remain.

## 2026-07-13 - Add semantic drift evidence to refresh conflicts

Files changed:
- `tools/agent_memory_runtime/semantic_refresh.py`
- `tools/agent_memory_runtime/code_wiki.py`
- `tests/test_refresh_scope.py`
- `docs/usage-guide.md`
- `docs/superpowers/plans/2026-07-12-six-strategic-iterations.md`
- `gitlog.md`

What changed:
- Added refresh-time structural semantic snapshots for changed files.
- `maintain-refresh-scope` semantic conflicts now include summary drift and log-template additions/removals in `incoming`.
- Extended refresh-scope tests to verify the durable conflict carries log drift evidence.

Why:
- A changed file with preserved business semantics should tell the Agent what changed, not merely that a review is required.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_refresh_scope`
- Result: passes.

Rollback notes:
- Remove `load_refresh_semantic_snapshot`, revert `record_refresh_semantic_conflicts` to generic text, and drop the drift-evidence assertions/docs if conflict text should remain minimal.

## 2026-07-13 - Add edge rebuild metrics for scope refresh

Files changed:
- `tools/agent_memory_runtime/graph_refresh_metrics.py`
- `tools/agent_memory_runtime/code_wiki.py`
- `tests/test_refresh_scope.py`
- `docs/usage-guide.md`
- `docs/superpowers/plans/2026-07-12-six-strategic-iterations.md`
- `gitlog.md`

What changed:
- Added scoped graph refresh metrics for file, symbol, log, and memory edge rebuilds.
- `parse_stats.edge_rebuild` now reports scoped files, before/after node counts, relation counts, deleted/inserted estimates, and edge delta.
- Extended refresh-scope tests to verify changed-only refresh reports only changed and added files in the edge rebuild scope.

Why:
- Incremental refresh needs explainable graph work before it can be judged against performance and large-scale governance budgets.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_refresh_scope`
- Result: passes.

Rollback notes:
- Remove `graph_refresh_metrics.py`, the thin `code_wiki.py` metric calls, and the edge metric assertions/docs if refresh output should stay minimal.

## 2026-07-13 - Preserve business semantics during changed refresh

Files changed:
- `tools/agent_memory_runtime/semantic_refresh.py`
- `tools/agent_memory_runtime/code_wiki.py`
- `tests/test_refresh_scope.py`
- `docs/usage-guide.md`
- `docs/superpowers/plans/2026-07-12-six-strategic-iterations.md`
- `gitlog.md`

What changed:
- Added refresh-time snapshots for exact-match file, symbol, and log business semantics.
- Restored preserved `business_summary` and `business_terms` after merge-mode structural refresh.
- Added `maintain-refresh-scope` semantic conflict rows for changed files that still carry an existing business summary.

Why:
- Incremental project refresh should not silently erase accumulated business semantics, but preserved semantics on changed source must remain reviewable.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_refresh_scope`
- Result: passes.

Rollback notes:
- Remove `semantic_refresh.py`, the thin `code_wiki.py` calls, and the refresh-scope test/docs if changed-file refresh should drop business semantics instead.

## 2026-07-13 - Add changed-only learned scope refresh

Files changed:
- `tools/agent_memory_runtime/code_wiki.py`
- `tools/agent_memory_runtime/cli.py`
- `tests/test_refresh_scope.py`
- `docs/usage-guide.md`
- `docs/superpowers/plans/2026-07-12-six-strategic-iterations.md`
- `gitlog.md`

What changed:
- Added `maintain-refresh-scope --changed-only`.
- Changed-only refresh compares the persisted learn-scope file snapshot with current source, re-indexes only added or changed files, and retires removed structural anchors.
- Refresh output now includes `changed_only` and `refreshed_files`.

Why:
- Frequently updated learned projects should refresh code/log graph anchors without broad re-learning or unnecessary unchanged-file parsing.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_refresh_scope tests.test_agent_memory.AgentMemoryRuntimeTests.test_maintain_refresh_scope_updates_structure_and_reports_drift tests.test_agent_memory.AgentMemoryRuntimeTests.test_maintain_health_reports_scope_health_counts`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory_runtime/code_wiki.py tools/agent_memory_runtime/cli.py tests/test_refresh_scope.py`
- Result: passes.

Rollback notes:
- Remove the `--changed-only` CLI flag, changed-only refresh branch, test, and docs if all refreshes should continue to replay full learned scopes.

## 2026-07-13 - Add quality gate history and recurring failure review

Files changed:
- `tools/agent_memory_runtime/quality_gate_eval.py`
- `tools/agent_memory_runtime/eval_case_drafts.py`
- `tools/agent_memory_runtime/governance.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory.py`
- `tests/test_quality_gate_eval.py`
- `tests/test_quality_gate_history.py`
- `tests/test_eval_case_drafts.py`
- `docs/usage-guide.md`
- `docs/superpowers/plans/2026-07-12-six-strategic-iterations.md`
- `gitlog.md`

What changed:
- Added `runtime/quality_gate_history.jsonl` as a bounded runtime-only history stream for `eval-quality` runs.
- Added `eval-quality --history` and `--history --gate <name>` to inspect recent quality trends and recurring failed gates.
- Added `review_recurring_quality_gate_failure` to `maintain-plan` so repeated failures become a prioritized governance action.
- Added `eval-draft-cases` to generate review-only retrieval, log-signal, and evidence-attribution draft cases from runtime signals.

Why:
- Query, evidence, graph, and log quality changes need trend visibility, not only the latest snapshot.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_gate_eval tests.test_quality_gate_history`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_eval_case_drafts tests.test_eval_case_seed`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory_runtime/quality_gate_eval.py tools/agent_memory_runtime/governance.py tools/agent_memory_runtime/cli.py tests/test_quality_gate_history.py`
- Result: passes.

Rollback notes:
- Remove quality history JSONL helpers, `--history` CLI arguments, recurring failure actions, draft case generation, tests, and docs if quality trends and draft cases should remain external to the runtime.

## 2026-07-12 - Add query anti-interference intent v2

Files changed:
- `tools/agent_memory_runtime/query.py`
- `tools/agent_memory_runtime/retrieval_eval.py`
- `tests/test_experience_query_quality.py`
- `tests/test_retrieval_eval.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/superpowers/plans/2026-07-12-six-strategic-iterations.md`
- `gitlog.md`

What changed:
- Added compatible `memory_intent_v2` routing for code location, code business semantics, runtime log diagnosis, semantic correction, memory maintenance, procedure reuse, and general context.
- Added per-intent main reflection budgets and exposed them through `retrieval_lanes.lane_budgets`.
- Strengthened broad procedure-experience penalties for code/source queries, business-semantics queries, semantic-correction queries, missing negative preconditions, and low-overlap non-procedure queries.
- Added source-case quality profiling and trust caps for weak historical or non-source-like `source_cases`.
- Extended retrieval eval support and tests with `expected_memory_intent_v2`, `max_reflection_count`, and `must_not_trust`.

Why:
- Experience records should help without pulling source-oriented or semantic-correction queries into broad historical procedure advice.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_experience_query_quality tests.test_retrieval_eval tests.test_agent_memory`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_memory_calibration tests.test_retrieval_eval tests.test_experience_query_quality`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory_runtime/query.py tools/agent_memory_runtime/retrieval_eval.py`
- Result: passes.

Rollback notes:
- Revert the v2 intent aliasing, lane budgets, retrieval eval field, and related tests/docs if downstream consumers require only the legacy coarse `memory_intent`.

## 2026-07-12 - Add automatic task trace reflection loop

Files changed:
- `tools/agent_memory_runtime/usage_samples.py`
- `tools/agent_memory_runtime/task_trace_governance.py`
- `tools/agent_memory_runtime/governance.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory.py`
- `tests/test_auto_reflection_summary.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-reflect/SKILL.md`
- `docs/superpowers/plans/2026-07-12-six-strategic-iterations.md`
- `gitlog.md`

What changed:
- Added `runtime/last_task_trace.json` as a bounded runtime projection from recent query, log, and governance usage.
- Added `reflect --from-last-task` and `reflect --json` so Agents can turn the latest trace into a normal reflection with less retyping.
- Added `maintain-plan` detection for unreflected task traces, with lifecycle fields that suppress the action after reflection closure.
- Added `auto_summary_quality`, `reflection_payload_placeholders`, and `review_low_evidence_auto_summary` so weak generated summaries are reviewed before becoming durable reflections.
- Documented the automatic task trace flow and marked Phase 1 minimal loop implemented in the strategic plan.

Why:
- The memory system needs lower-friction experience capture before strategy and skill evolution can reliably use accumulated experience.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_auto_reflection_summary`
- Result: passes.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory_runtime/usage_samples.py tools/agent_memory_runtime/task_trace_governance.py tools/agent_memory_runtime/governance.py tools/agent_memory_runtime/cli.py tools/agent_memory.py`
- Result: passes.

Rollback notes:
- Remove task trace generation, task trace governance, `--from-last-task`, JSON reflect output, tests, and docs if automatic reflection candidates become noisy.

## 2026-07-12 - Add six strategic iterations plan

Files changed:
- `docs/superpowers/plans/2026-07-12-six-strategic-iterations.md`
- `gitlog.md`

What changed:
- Added a staged execution plan for automatic recording, query anti-interference, strategy-to-skill candidates, incremental graph refresh, quality dashboarding, and large-scale governance.
- Each phase includes implementation slices, acceptance criteria, tests, risks, and cross-phase invariants.

Why:
- The next major work should stay ordered around feedback loops, correctness, measurable quality, and scale without adding user-facing skills.

Verification:
- Command: `wc -l docs/superpowers/plans/2026-07-12-six-strategic-iterations.md`
- Result: plan document exists and is bounded.
- Command: `git diff --check`
- Result: passes.

Rollback notes:
- Remove the plan document and this log entry if the roadmap is replaced by a different execution order.

## 2026-07-12 - Improve experience query and graph quality

Files changed:
- `docs/superpowers/plans/2026-07-12-experience-query-graph-quality.md`
- `tools/agent_memory_runtime/quality_scoring.py`
- `tools/agent_memory_runtime/memory_calibration.py`
- `tools/agent_memory_runtime/query.py`
- `tools/agent_memory_runtime/graph_quality.py`
- `tools/agent_memory_runtime/retrieval_eval.py`
- `tools/agent_memory_runtime/eval_case_seed.py`
- `tools/agent_memory_runtime/graph_signal_eval.py`
- `tools/agent_memory_runtime/experience_evidence_eval.py`
- `tools/agent_memory_runtime/quality_gate_eval.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory.py`
- `tests/test_memory_calibration.py`
- `tests/test_experience_query_quality.py`
- `tests/test_quality_performance_scoring.py`
- `tests/test_retrieval_eval.py`
- `tests/test_graph_signal_eval.py`
- `tests/test_experience_evidence_eval.py`
- `tests/test_quality_gate_eval.py`
- `docs/runtime.md`
- `skills/agent-memory-query/SKILL.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- Added a derived `experience_evidence_profile` for reflection evidence, applicability, counter-evidence, and verification status.
- Added query intent profile metadata plus intent alignment and interference penalties for reflection retrieval.
- Added `graph_signal_quality.coverage_scorecard` with business semantic coverage, log diagnostic coverage, anchor coverage, and combined coverage score.
- Extended retrieval eval cases with `expected_memory_intent`, `required_preferred_lanes`, and `max_blocked_memory_notes` so query interference behavior can be regression-tested.
- Added `eval-graph-signal` and the `graph_signal` aggregate quality gate for code/log graph coverage regression.
- Added `eval-experience-evidence` and the `experience_evidence` aggregate quality gate for reflection evidence-profile regression.
- Added `eval-quality --list-gates` to inspect registered gates without executing cases or mutating the latest quality snapshot.

Why:
- Experience, query, code graph, and log graph quality need explainable signals before adding heavier retrieval infrastructure.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_memory_calibration tests.test_experience_query_quality tests.test_quality_performance_scoring tests.test_retrieval_eval tests.test_eval_case_seed tests.test_graph_signal_eval tests.test_experience_evidence_eval tests.test_quality_gate_eval`
- Result: passes.

Rollback notes:
- Remove the derived profile, intent penalty fields, coverage scorecard, tests, and docs if the extra explanation payload becomes too noisy.

## 2026-07-12 - Add quality gate filter

Files changed:
- `docs/superpowers/plans/2026-07-12-quality-gate-filter.md`
- `tools/agent_memory_runtime/quality_gate_eval.py`
- `tools/agent_memory_runtime/cli.py`
- `tests/test_quality_gate_eval.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- Added repeatable `eval-quality --gate <name>` filtering.
- Aggregate summary now includes `selected_gate_names`.
- Delta comparisons filter previous failures to selected gates, avoiding false resolved-failure signals during partial runs.

Why:
- Agents and scripts often need to rerun one quality lane without running the full aggregate gate.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_gate_eval`
- Result: passes.

Rollback notes:
- Remove the CLI flag, gate filtering, test, and docs if aggregate-only evaluation is preferred.

## 2026-07-12 - Add quality gate delta summary

Files changed:
- `docs/superpowers/plans/2026-07-12-quality-gate-delta.md`
- `tools/agent_memory_runtime/quality_gate_eval.py`
- `tests/test_quality_gate_eval.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- `eval-quality` now compares the current run with the previous runtime snapshot.
- Added `quality_gate_delta` with previous/current gate status, status change, newly failed gates, resolved gates, and unchanged failed gates.

Why:
- Agents need to know whether a quality gate failure is new, still failing, or just resolved without keeping a long-term history table.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_gate_eval`
- Result: passes.

Rollback notes:
- Remove delta computation, tests, and docs if previous-run comparison becomes noisy.

## 2026-07-12 - Add quality gate governance action

Files changed:
- `docs/superpowers/plans/2026-07-12-quality-gate-governance-action.md`
- `tools/agent_memory_runtime/quality_gate_eval.py`
- `tools/agent_memory_runtime/governance.py`
- `tools/agent_memory_runtime/governance_action_budget.py`
- `tests/test_quality_gate_eval.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- Added `review_quality_gate_failure` actions from the latest failed quality gate snapshot.
- Added the `quality_gate` governance lane to action budgeting.
- `maintain-plan` now includes `last_quality_gate` and a quality gate failure review counter.

Why:
- A failed aggregate quality gate should enter the same review workflow as memory, graph, log, and runtime performance issues.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_gate_eval`
- Result: passes.

Rollback notes:
- Remove the action builder, maintain-plan integration, lane weights, tests, and docs if quality gate failures should remain health-only.

## 2026-07-12 - Expose latest quality gate health

Files changed:
- `docs/superpowers/plans/2026-07-12-quality-gate-snapshot.md`
- `tools/agent_memory_runtime/quality_gate_eval.py`
- `tools/agent_memory_runtime/governance.py`
- `tests/test_quality_gate_eval.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- `eval-quality` now writes `runtime/last_quality_gate.json`.
- `maintain-health --json` exposes a compact `last_quality_gate` snapshot.
- Failed latest quality gates add a targeted recommended action.

Why:
- Maintenance should see recent quality gate status without requiring SQLite writes or long-term memory records.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_gate_eval`
- Result: passes.

Rollback notes:
- Remove snapshot helpers, maintain-health field, recommendation, tests, and docs if runtime snapshots become noisy.

## 2026-07-12 - Add quality gate automation hints

Files changed:
- `docs/superpowers/plans/2026-07-12-quality-gate-automation.md`
- `tools/agent_memory_runtime/quality_gate_eval.py`
- `tools/agent_memory_runtime/cli.py`
- `tests/test_quality_gate_eval.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- Added per-gate `next_command_template` to `eval-quality` output.
- Added `passed_gate_names`, `failed_gate_names`, and `skipped_gate_names` to the aggregate summary.
- Added `eval-quality --fail-on-fail` for scripts that need exit code 1 after a failing JSON report.

Why:
- The aggregate quality gate should be easy to automate and easy to drill into when a specific gate fails.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_gate_eval`
- Result: passes.

Rollback notes:
- Remove the flag, summary name lists, command templates, tests, and docs if aggregate output becomes too verbose.

## 2026-07-12 - Add golden eval case seed pack

Files changed:
- `docs/superpowers/plans/2026-07-12-golden-case-seed-pack.md`
- `tools/agent_memory.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory_runtime/eval_case_seed.py`
- `tests/test_eval_case_seed.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- Added `eval-seed-cases --target docs/eval/examples --json`.
- The command writes editable golden eval examples for retrieval, calibration, governance, log-signal, and evidence-attribution gates.
- Existing files are skipped unless `--force` is provided.

Why:
- `eval-quality` is more useful when projects can bootstrap case files, but unedited examples should not live in the default active gate directory.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_eval_case_seed`
- Result: passes.

Rollback notes:
- Remove the seed command, template module, test, and docs if examples are better maintained only as static documentation.

## 2026-07-12 - Add quality gate orchestrator

Files changed:
- `docs/superpowers/plans/2026-07-12-quality-gate-orchestrator.md`
- `tools/agent_memory.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory_runtime/quality_gate_eval.py`
- `tests/test_quality_gate_eval.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- Added `eval-quality --cases-dir <dir> --json` as a unified read-only quality gate.
- The command discovers known golden case files, skips missing files by default, and aggregates pass/fail status across retrieval, calibration, governance, log-signal, and evidence-attribution gates.
- Added `--strict` for CI-like checks where an empty cases directory should fail.

Why:
- Existing eval commands were useful but scattered. A single orchestrator makes quality checks easier before changing retrieval, experience, governance, code graph, or log diagnosis behavior.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_gate_eval`
- Result: passes.

Rollback notes:
- Remove the `eval-quality` parser entry, `quality_gate_eval.py`, tests, and docs if the aggregate gate becomes noisy or redundant.

## 2026-07-12 - Add quality closed-loop signals

Files changed:
- `docs/superpowers/plans/2026-07-12-experience-query-graph-log-quality-closed-loop.md`
- `tools/agent_memory.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory_runtime/query.py`
- `tools/agent_memory_runtime/experience_usage.py`
- `tools/agent_memory_runtime/governance.py`
- `tools/agent_memory_runtime/governance_eval.py`
- `tools/agent_memory_runtime/code_wiki.py`
- `tools/agent_memory_runtime/graph_quality.py`
- `tools/agent_memory_runtime/log_signal_quality.py`
- `tests/test_quality_closed_loop.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `skills/agent-memory-query/SKILL.md`
- `skills/agent-memory-maintain/SKILL.md`

What changed:
- Added `query_audit` to `context` and `search` for compact retrieval explanations.
- Added experience usage effectiveness metrics and maintain-health records.
- Added read-only `eval-governance` golden action evaluation.
- Added ArkTS state symbol extraction plus `defines_state` graph edges.
- Added log `observability_gaps` and a maintain-plan `review_log_observability_gap` action.

Why:
- Retrieval, experience reuse, graph learning, and log diagnosis need inspectable quality loops before further scale-up.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_closed_loop`
- Result: passes.

Rollback notes:
- Remove the new eval command, query audit fields, effectiveness fields, graph/log additions, tests, and docs if the quality payloads become too noisy.

## 2026-07-12 - Add governance lane command templates

Files changed:
- `tools/agent_memory_runtime/governance_action_budget.py`
- `tests/test_governance_action_budget.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/superpowers/plans/2026-07-12-governance-lane-command-templates.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- Added `recommended_lanes[*].next_command_template`.
- The template points to a compact maintain-plan rerun focused on that lane.
- Documented that this is navigation metadata, not automatic execution.

Why:
- Lane recommendations are more useful when the Agent can jump directly into the focused lane view without manually reconstructing command flags.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_governance_action_budget`
- Result: passes.

Rollback notes:
- Remove lane command template output, tests, and docs if this makes compact output too verbose.

## 2026-07-12 - Add governance lane recommendations

Files changed:
- `tools/agent_memory_runtime/governance_action_budget.py`
- `tests/test_governance_action_budget.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/superpowers/plans/2026-07-12-governance-lane-recommendations.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- Added `recommended_lanes` to `action_budget`.
- Each lane recommendation includes action count, max priority, average priority, and a compact top action.
- Documented that lane recommendations help choose a governance path before loading full action details.

Why:
- Large maintain plans often need a lane-level choice before an action-level choice. Counts alone are not enough when one lane has fewer but higher-priority actions.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_governance_action_budget`
- Result: passes.

Rollback notes:
- Remove lane recommendation aggregation, tests, and docs if the extra metadata is noisy.

## 2026-07-12 - Add governance lane filter hints

Files changed:
- `tools/agent_memory_runtime/governance_action_budget.py`
- `tests/test_governance_action_budget.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/superpowers/plans/2026-07-12-governance-lane-filter-hints.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- Added `lane_filter_status` to `action_budget`.
- Added `available_lanes` to `action_budget`.
- Documented that unknown lanes should be corrected from available lane hints rather than treated as no maintenance work.

Why:
- A mistyped `--action-lane` should not silently look like an empty maintenance plan.
- Low-token compact workflows need enough guidance to recover from lane-selection mistakes.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_governance_action_budget`
- Result: passes.

Rollback notes:
- Remove lane hint fields, tests, and docs if the extra metadata is unnecessary.

## 2026-07-12 - Add governance action lane filter

Files changed:
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory_runtime/governance.py`
- `tools/agent_memory_runtime/governance_action_budget.py`
- `tests/test_governance_action_budget.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/superpowers/plans/2026-07-12-governance-action-lane-filter.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- Added `maintain-plan --action-lane <lane>`.
- Filtered only `action_budget.top_actions` by governance lane while preserving full action generation and lane counts.
- Added `selected_lane` and `candidate_actions` to the action budget.
- Kept next command templates lane-aware.

Why:
- Large archives are easier to maintain when an Agent can review one governance lane at a time without losing visibility into other lanes.
- This keeps the optimization output-only and avoids new queues, tables, or scoring changes.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_governance_action_budget`
- Result: passes.

Rollback notes:
- Remove the parser flag, lane filtering, budget fields, tests, and docs if lane filtering proves confusing.

## 2026-07-12 - Add governance budget navigation

Files changed:
- `tools/agent_memory_runtime/governance_action_budget.py`
- `tests/test_governance_action_budget.py`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/superpowers/plans/2026-07-12-governance-budget-navigation.md`
- `skills/agent-memory-maintain/SKILL.md`
- `gitlog.md`

What changed:
- Added stable `review_key` values to compact `action_budget.top_actions`.
- Added `source_hint` to compact top actions so low-token outputs still show where the action came from.
- Added `next_command_templates` to the action budget for compact reruns and full maintain-plan review.

Why:
- Compact action budgets should be navigable without forcing the Agent to infer how to continue from sparse action summaries.
- This keeps the large-archive flow token-light while preserving the confirmation-first maintenance model.

Verification:
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_governance_action_budget`
- Result: passes.

Rollback notes:
- Remove `review_key`, `source_hint`, `next_command_templates`, the navigation test, and docs if the extra metadata adds noise.

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
# 2026-07-13 - Add goal-oriented evidence coordination and change impact analysis

Files touched:

- `tools/agent_memory_runtime/evidence_models.py`
- `tools/agent_memory_runtime/goal_planner.py`
- `tools/agent_memory_runtime/evidence_collectors.py`
- `tools/agent_memory_runtime/evidence_fusion.py`
- `tools/agent_memory_runtime/evidence_context.py`
- `tools/agent_memory_runtime/impact_scope.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory_runtime/runtime_entry.py`
- `tests/test_evidence_fabric.py`
- `skills/agent-memory-query/SKILL.md`
- `skills/agent-memory-maintain/SKILL.md`
- `README.md`
- `agent.md`
- `docs/runtime.md`
- `docs/usage-guide.md`
- `docs/superpowers/plans/2026-07-13-goal-oriented-evidence-fabric.md`
- `gitlog.md`

What changed:

- Added deterministic goal planning and a unified evidence contract over semantic facts, reflections, episodes, code anchors, code logs, memory edges, and incident traces.
- Added bounded cross-source fusion with per-lane score normalization, authority/trust/graph/freshness factors, explicit penalties, evidence tiers, chains, gaps, and audit output.
- Added `evidence-context` for compact LLM-ready coordinated retrieval.
- Added `impact-scope` for Git diff, explicit file, and unified-diff input; it reports direct changed anchors, one-hop reverse dependents, outgoing dependencies, related memory, risk, coverage gaps, and verification targets.
- Reused runtime usage/performance samples, query misses, retrieval feedback, and task traces. No new durable result table or raw-log persistence was added.
- Kept the public surface at four skills and updated query/maintain guidance.

Why:

- Independent query, code graph, log graph, causal trace, and experience scores can conflict or amplify weak historical memory.
- Agents need one goal-aware evidence view where current change/code/log anchors remain primary and experience is corroborating advice.
- Change review needs a deterministic, bounded impact scope before an LLM chooses files, tests, or runtime signals to inspect.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_evidence_fabric`
- Result: 5 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_evidence_fabric tests.test_agent_memory_part_03 tests.test_incident_trace tests.test_retrieval_feedback tests.test_memory_calibration`
- Result: 31 tests pass.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest discover tests`
- Result: 242 tests pass in 154.981 seconds on the final implementation state.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py tests/*.py install.py`
- Result: passes.
- Command: `python3 tools/check_line_limits.py`
- Result: all Python files are at or below 500 lines.
- Command: `git diff --check`
- Result: passes.
- Command: `find skills -mindepth 1 -maxdepth 1 -type d | sort`
- Result: exactly the four public Agent Memory skills remain.

Rollback notes:

- Remove the two CLI commands and evidence coordination modules. Existing search, context, learning, incident trace, governance, and the four public skills remain independently usable.

## 2026-07-13 - Harden the goal-oriented evidence fabric

Files touched:

- `tools/agent_memory_runtime/evidence_*.py`
- `tools/agent_memory_runtime/goal_planner.py`
- `tools/agent_memory_runtime/impact_*.py`
- `tools/agent_memory_runtime/code_wiki_edges.py`
- `tools/agent_memory_runtime/runtime_log_*.py`
- `tools/agent_memory_runtime/otel_lite.py`
- `tools/agent_memory_runtime/storage_*.py`
- `tools/agent_memory_runtime/governance_*.py`
- `tests/test_evidence_fabric_hardening.py`
- `README.md`, `agent.md`, `docs/`, `references/schema.md`, and query/maintain skills

What changed:

- Added bounded local/global query decomposition, stable-id novelty stopping, source/location/pattern diversity, and lightweight global aggregates.
- Added current code-edge provenance, active-edge filtering, migration-safe defaults, and graph governance signals without retaining unbounded edge history.
- Added OTel-lite trace/span/event/result normalization for temporary logs and four causal evidence levels with explicit signals and counter-evidence.
- Added compact impact-test feedback and one-hop graph-aware test recommendations; raw diffs and test logs are not persisted.
- Added evidence-runtime and impact-feedback governance summaries while preserving SQLite, the single runtime entry point, and four public skills.

Why:

- Query, code graph, runtime logs, causal chains, and impact analysis need coordinated evidence controls so weak or repeated experience cannot redirect diagnosis.
- The runtime needs better recall and verification feedback without adding a vector store, graph database, daemon, raw-log archive, or unbounded database growth.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_evidence_fabric_hardening tests.test_evidence_fabric tests.test_incident_trace tests.test_otel_lite tests.test_log_signal_quality tests.test_graph_quality tests.test_memory_calibration tests.test_auto_reflection_summary`
- Result: 46 tests passed before the final graph-neighbor test was added; the hardening module then passed all 11 focused tests.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest discover tests`
- Result: 253 tests passed in 172.145 seconds on the final implementation state.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py tests/*.py install.py`
- Result: passed.
- Command: `python3 tools/check_line_limits.py`
- Result: all Python files are at or below 500 lines.
- Command: `find skills -mindepth 1 -maxdepth 1 -type d -print | sort`
- Result: exactly the four public Agent Memory skills remain.
- Command: `python3 tools/agent_memory.py --help`
- Result: `evidence-context`, `impact-scope`, and `impact-feedback` are available through the single runtime entry point.

Rollback notes:

- Remove adaptive query execution and impact feedback handlers/table, then fall back to the prior single-query Evidence Fabric. Existing memory and current graph data remain usable.

## 2026-07-14 - Add repository-grounded design reasoning

Files touched:

- `skills/agent-memory-query/SKILL.md`
- `skills/agent-memory-query/references/*.md`
- `tools/agent_memory_runtime/architecture_slice.py`
- `tools/agent_memory_runtime/code_wiki_design_edges.py`
- `tools/agent_memory_runtime/design_check.py`
- `tools/agent_memory_runtime/goal_planner.py`
- `tools/agent_memory_runtime/evidence_context.py`
- `tools/agent_memory_runtime/evidence_query_execution.py`
- `tools/agent_memory_runtime/code_wiki_edges.py`
- `tools/agent_memory_runtime/code_wiki_extractors.py`
- `tools/agent_memory_runtime/cli.py`
- `tools/agent_memory_runtime/runtime_entry.py`
- `tests/test_repository_design.py`
- `README.md`, `agent.md`, `docs/`, `references/`, and `gitlog.md`

What changed:

- Reduced the Query Skill from 206 lines to a thin progressive-disclosure router and moved intent-specific behavior into five one-level reference protocols.
- Added a current-code-first `design` goal. Code and active graph evidence have full source weight while historical reflection remains low-weight advisory context.
- Added bounded architecture slices with depth 2, 80-node, and 160-edge limits, including boundaries, state owners, extension points, consumers, tests, observability, provenance, and explicit gaps.
- Added conservative ArkTS design edges for component composition, service use, event dispatch/binding, Ability configuration, and naming-matched tests using the existing versioned `memory_edges` table.
- Added `design-check` for deterministic Delta Graph validation: shape/path checks, introduced cycles, multiple state owners, boundary reversals, UI/data bypasses, consumer review, test/observability gaps, and unknown anchors.
- Kept design generation in the Agent protocol. The runtime does not call an LLM or persist proposals, architecture slices, generated answers, or chain-of-thought.

Why:

- Code design should use general software-design reasoning grounded in current repository structure, not retrieve a past project pattern and apply it as the main answer.
- The Query Skill had become dense enough that diagnosis, impact, trust, evaluation, and future design rules would interfere and consume context together.

Verification:

- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_repository_design`
- Result: 7 design, protocol, ArkTS graph, architecture-slice, validation, and Delta Graph tests passed.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_repository_design tests.test_evidence_fabric_hardening tests.test_evidence_fabric tests.test_agent_memory_part_13 tests.test_agent_memory_part_14 tests.test_quality_closed_loop tests.test_graph_quality`
- Result: 51 focused tests passed before final compatibility and scope refinements; all affected cases are included in the final full suite.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest discover tests`
- Result: 260 tests passed in 199.864 seconds on the final implementation state.
- Command: `PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py tests/*.py install.py`
- Result: passed.
- Command: `python3 tools/check_line_limits.py`
- Result: all Python files are at or below 500 lines.
- Command: `find skills -mindepth 1 -maxdepth 1 -type d -print | sort`
- Result: exactly the four public Agent Memory skills remain.
- Command: `python3 tools/agent_memory.py design-check --help`
- Result: the new check is available through the single stable runtime entry point.
- Command: `git diff --check`
- Result: passed.

Rollback notes:

- Remove the design goal, architecture slice, ArkTS design-edge helper, and `design-check`; restore the previous Query Skill body. Existing memory, query, diagnosis, impact, and four public skills remain usable.

## 2026-07-14 - Complete long-term design reasoning evolution

Files added or extended:

- `tools/agent_memory_runtime/design_protocol.py`
- `tools/agent_memory_runtime/design_fitness.py`
- `tools/agent_memory_runtime/design_compare.py`
- `tools/agent_memory_runtime/design_verify.py`
- `tools/agent_memory_runtime/design_eval.py`
- `tools/agent_memory_runtime/design_evidence.py`
- `tools/agent_memory_runtime/cli_design.py`
- `docs/design-reasoning.md`
- `docs/eval/design-cases.json`
- `tests/test_design_evolution.py`
- Existing design graph, runtime entry, Query Skill reference, README, runtime, usage, schema, protocol, and plan documentation.

What changed:

- Added versioned `design-contract/v1`, `design-delta/v1`, `design-rules/v1`, and `design-evaluation/v1` protocols while retaining legacy proposal compatibility.
- Added deterministic project fitness rules for forbidden edges, required edges, and single ownership. Explicit project rules remain caller-owned and cannot be promoted from experience automatically.
- Added `design-compare` with shared architecture-slice reuse, hard-gate-first ranking, quality coverage, uncertainty, change-size dimensions, deterministic reasons, and tradeoffs.
- Added `design-verify` for planned/actual file drift, explicit executed tests, learned-graph alignment, proposal fitness rechecks, and replan triggers.
- Added ArkTS calls, state reads/writes, API exposure/consumption, callbacks, implements, and conservative overrides. Architecture edges now expose evidence class and extractor provenance; extractor version is `code-wiki:v4`.
- Added `eval-design` and nine deterministic ArkTS seed cases covering state, service boundaries, API compatibility, routes/config, async observability, migration, callbacks, tests, and logs.
- Preserved the four public Skills, stable runtime entry, SQLite schema, bounded graph traversal, read-only design artifacts, and 500-line Python limit.

Verification:

- `PYTHONPYCACHEPREFIX=/tmp/agent-memory-pyc python3 -m unittest tests.test_repository_design tests.test_design_evolution tests.test_evidence_fabric tests.test_evidence_fabric_hardening tests.test_agent_memory_part_13 tests.test_agent_memory_part_14 tests.test_quality_closed_loop tests.test_graph_quality`: 58 tests passed.
- `PYTHONPYCACHEPREFIX=/tmp/agent-memory-pyc python3 -m unittest discover tests`: 266 tests passed in 127.040 seconds.
- `PYTHONPYCACHEPREFIX=/tmp/agent-memory-pyc python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py tests/*.py install.py`: passed.
- `python3 tools/check_line_limits.py`: all Python files are at or below 500 lines.
- `python3 tools/agent_memory.py --help`: design check, compare, verify, and evaluation commands are available through the single runtime entry.
- Four-skill directory check, JSON validation, and `git diff --check`: passed.

Rollback notes:

- Remove compare, verify, evaluation, protocol, fitness, and evidence-class modules to return to the prior single-proposal design checker. No SQLite migration or stored-memory rollback is required.

## 2026-07-15 - Add language-neutral semantic indexing and Incident causal candidates

Files added or extended:

- `tools/agent_memory_runtime/semantic_models.py`
- `tools/agent_memory_runtime/semantic_adapters.py`
- `tools/agent_memory_runtime/semantic_ecma.py`
- `tools/agent_memory_runtime/semantic_index.py`
- `tools/agent_memory_runtime/incident_semantic_chain.py`
- Existing code learning, graph, impact, architecture, Incident, storage, documentation, and Skill protocol files.
- `tests/test_semantic_index.py`
- `docs/semantic-index.md`
- `docs/superpowers/plans/2026-07-15-semantic-index-code-graph-causal-chain.md`

What changed:

- Added validated, bounded `semantic-index/v1` batches and a language-neutral `LanguageAdapter` registry.
- Added ArkTS and TypeScript static adapters for definitions, calls, state flow, inheritance, callbacks, API boundaries, and await relationships.
- Enriched `code_symbols` with stable identity, qualified name, signature, source span, adapter provenance, source digest, and evidence class.
- Persisted resolved semantic relations as versioned SQLite `memory_edges`; stronger exact evidence blocks weaker duplicate writes.
- Expanded narrow relearning to capture and rebuild reverse dependents before symbol ids are replaced.
- Added fixed-size SQLite query chunks for semantic binding and reverse-dependent refresh scopes.
- Included symbol-level relationships in bounded architecture slices and change-impact analysis.
- Added compact Incident causal chains from observed log to enclosing symbol and semantic candidates. Causal role is kept separate from evidence precision, and raw log streams or chain-of-thought are not stored.
- Preserved the stable CLI, SQLite source of truth, four public Skills, FTS5 fast path, and file-level graph fallback.

Verification:

- `PYTHONPYCACHEPREFIX=/tmp/agent-memory-pyc python3 -m unittest discover -s tests -p 'test_*.py'`: 276 tests passed in 147.981 seconds.
- `PYTHONPYCACHEPREFIX=/tmp/agent-memory-pyc python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py tests/*.py install.py`: passed.
- `python3 tools/check_line_limits.py`: all Python files are at or below 500 lines.
- Four-Skill directory check: exactly four public Agent Memory skills remain.
- `python3 tools/agent_memory.py --help`: all functionality remains behind the single stable runtime entry.
- `git diff --check`: passed.

Rollback notes:

- Disable semantic adapter invocation and remove compact Incident `causal_chain` consumption. Existing file-level edges, code/log records, FTS5 queries, string candidate chains, design checks, impact analysis, and four Skills remain usable. Added nullable columns require no destructive rollback.

## 2026-07-15 - Add ArkTS exact semantic-provider infrastructure

Files added or extended:

- `tools/agent_memory_runtime/semantic_provider_protocol.py`
- `tools/agent_memory_runtime/semantic_provider_process.py`
- `tools/agent_memory_runtime/semantic_runtime.py`
- `tools/agent_memory_runtime/semantic_provider_metrics.py`
- `tools/agent_memory_runtime/semantic_eval.py`
- `tools/agent_memory_runtime/cli_semantic.py`
- Existing semantic indexing, Impact, Incident, governance, CLI, documentation, and Skill files.
- `tests/fixtures/exact_semantic_provider.py`
- `tests/test_semantic_provider.py`
- `tests/test_semantic_eval.py`
- `docs/eval/semantic-cases.json`
- `docs/semantic-provider.md`
- `docs/superpowers/plans/2026-07-15-arkts-exact-semantic-provider.md`

What changed:

- Added versioned `semantic-provider-request/v1` and `semantic-provider-result/v1` process contracts around the existing `semantic-index/v1` batch.
- Added explicit environment-only provider discovery, no-shell invocation, timeout, accepted-output limits, correlation, digest/path/identity validation, and classified failure handling.
- Added ArkTS `auto` selection: a valid configured provider emits exact evidence; absent or failed providers fall back to the built-in static adapter with visible parse feedback.
- Preserved exact-over-static duplicate authority and source-version edge lifecycle behavior.
- Ranked Impact and Incident semantic candidates by evidence precision before confidence while retaining `possible` causal roles for code-only paths.
- Added bounded runtime provider telemetry, `maintain-health` summary, and a read-only repeated-fallback Maintain action without adding SQLite growth.
- Added `eval-semantic` with temporary golden fixtures, expected/forbidden relation checks, resolution and growth metrics, and selected-vs-static disagreement reporting.
- Documented the production bridge contract. The checked-in executable is explicitly a protocol test double, not an es2panda implementation.

Verification:

- `PYTHONPYCACHEPREFIX=/tmp/agent-memory-pyc python3 -m unittest tests.test_semantic_provider tests.test_semantic_eval tests.test_semantic_index tests.test_evidence_fabric tests.test_evidence_fabric_hardening tests.test_incident_trace tests.test_graph_quality tests.test_quality_performance_scoring tests.test_agent_memory_part_13 tests.test_agent_memory_part_14`: 84 focused tests passed.
- `PYTHONPYCACHEPREFIX=/tmp/agent-memory-pyc python3 -m unittest discover -s tests -p 'test_*.py'`: 291 tests passed in 194.499 seconds, including exact cross-scope symbol-key binding.
- `python tools/agent_memory.py eval-semantic --project . --cases docs/eval/semantic-cases.json --mode static --json`: three cases passed; expected relation recall 1.0, forbidden-edge rate 0.0, and raw relation resolution rate 0.9524.
- Full Python compilation, JSON validation, line-limit check, four-Skill check, CLI help, and diff check passed.

Rollback notes:

- Unset `AGENT_MEMORY_SEMANTIC_PROVIDER_ARKTS` to return immediately to static-only learning. Removing provider selection, telemetry, evaluation, and exact-priority ordering requires no destructive SQLite rollback; existing exact edges remain ordinary versioned memory edges until the next focused refresh.

## 2026-07-14 - Document the local Agent incident diagnosis loop

Files added or extended:

- `docs/local-agent-incident-workflow.md`
- `docs/usage-guide.md`
- `README.md`

What changed:

- Documented how a local Agent uses Agent Memory as a diagnosis control layer instead of a one-shot query database.
- Added an end-to-end workflow for coordinated evidence, temporary runtime-log analysis, hypothesis falsification, source inspection, impact analysis, verification feedback, and bounded reflection.
- Defined evidence authority, causal-level handling, stopping conditions, temporary-log retention, correction-versus-procedure experience boundaries, and periodic governance.
- Preserved the single runtime entry point, SQLite source of truth, and four public Skills.

Verification:

- Checked all documented command options against the current CLI help.
- Documentation-only change; no runtime tests required.

Rollback notes:

- Remove the new guide and its README/usage-guide links. No runtime or stored-memory migration is involved.

## 2026-07-14 - Add the natural-language design assistant entry

Files added or extended:

- `tools/agent_memory_runtime/design_assist.py`
- `tools/agent_memory_runtime/design_guidance.py`
- Existing design preparation, CLI, runtime entry, four-Skill protocol, and design documentation files.
- `tests/test_design_assist.py`

What changed:

- Added read-only `design-assist` as a compact natural-language entry with `design-only`, `design-and-implement`, and `compare` modes.
- Reused the existing design evidence and candidate-independent workbench instead of creating a second design pipeline.
- Added deterministic design-force detection, structural recognition of existing patterns, conditional pattern candidates with preconditions and contraindications, principle checks, and required design decisions.
- Added the same `design-guidance/v1` payload to `design-prepare` for advanced flows.
- Kept pattern names advisory: unsupported candidates are marked `needs_evidence`, conflicting intent becomes `caution`, and small fixed changes may correctly return no pattern candidate.
- Preserved one runtime entry point, SQLite source of truth, no persisted workbench, and exactly four public Skills.

Verification:

- `PYTHONPYCACHEPREFIX=/tmp/agent-memory-pyc python3 -m unittest tests.test_design_assist`: 3 tests passed.
- `PYTHONPYCACHEPREFIX=/tmp/agent-memory-pyc python3 -m unittest discover -s tests -p 'test_*.py'`: 336 tests passed in 244.095 seconds.
- Full Python compilation, line-limit check, CLI help, exactly-four-Skill check, and `git diff --check`: passed.

Rollback notes:

- Remove `design-assist`, `design-guidance/v1`, their parser/handler registration, tests, and documentation references. Existing design preparation, checking, comparison, progress, verification, and outcomes remain compatible; no SQLite migration is involved.

## 2026-07-14 - Harden causal diagnosis with Span Graph Lite and hypothesis testing

Files added or extended:

- `tools/agent_memory_runtime/runtime_span_graph.py`
- `tools/agent_memory_runtime/diagnosis_hypotheses.py`
- Runtime log parsing, OTel-lite projection, incident trace storage/query, evidence fusion, governance health, and schema migration modules.
- Incident diagnosis Skill protocol, runtime/usage/schema documentation, and focused causal diagnosis tests.

What changed:

- Added parent-span and service resource identity extraction while preserving chronological runtime episode chains.
- Added bounded `runtime-span-graph/v1` nodes, parent edges, correlated temporal paths, quality gaps, and compact Incident Trace persistence without storing full raw logs.
- Added diagnosis hypothesis ledgers with supporting/counter evidence, missing evidence, and one discriminating next check; only the latest bounded ledger is kept as runtime state.
- Tightened causal levels: static adjacency remains association; supported requires connected mechanism plus explicit correlation and temporal order, or reviewed resolution; verified additionally requires intervention and before/after evidence.
- Added incident status fields for intervention and verification evidence plus governance summaries for causal quality and open/verified hypotheses.
- Kept span graph selection linear over the input and bounded ordering to 80 relevant events.

Verification:

- `PYTHONPYCACHEPREFIX=/tmp/agent-memory-pyc python3 -m unittest discover -s tests -p 'test_*.py'`: 343 tests passed in 282.226 seconds.
- A 100,000-event synthetic related-event selection retained 10 events and completed graph selection/build in 239.17 ms.
- Python compilation, CLI help, exactly-four-Skill check, diff check, and the 500-line Python limit passed.

Rollback notes:

- Remove Span Graph Lite and hypothesis ledger output, revert the stricter causal classifier, and leave the added nullable Incident Trace columns unused. No destructive SQLite rollback is required.

## 2026-07-15 - Document Agent CLI Query Skill workflows in Chinese

Files added or extended:

- `docs/agent-cli-query-skill-guide.zh-CN.md`
- `README.md`
- `README.zh-CN.md`
- `docs/usage-guide.md`
- `agent.md`

What changed:

- Added a detailed Chinese guide for invoking the fixed `agent-memory-query` Skill from a local Agent CLI.
- Documented intent routing, evidence authority, diagnosis prompts, temporary-log analysis, Span Graph Lite, Hypothesis Ledger iteration, causal levels, Incident closure, impact feedback, and stopping conditions.
- Documented the simple `design-assist` workflow and the substantial `design-prepare/check/compare/progress/verify` control loop without requiring users to author protocol JSON.
- Added reusable Agent instructions, ArkTS-oriented examples, output-reading order, token-saving guidance, common failure modes, and operational checklists.

Verification:

- Checked every documented command and option against current CLI help.
- Documentation links and Markdown whitespace passed `git diff --check`.

Rollback notes:

- Remove the Chinese guide and its four navigation links. No runtime or SQLite changes are involved.

## 2026-07-15 - Add self-collected Agent A/B benchmark loop

Files added or extended:

- `tools/agent_memory_runtime/agent_benchmark*.py`
- `tools/agent_memory_runtime/benchmark_history.py`
- `tools/agent_memory_runtime/benchmark_mutations.py`
- `tools/agent_memory_runtime/benchmark_workspace.py`
- `tools/agent_memory_runtime/benchmark_memory.py`
- CLI/runtime registration and governance health integration.
- `tests/test_agent_benchmark.py`
- `docs/agent-benchmark.md` and related runtime, usage, README, Agent, and Maintain Skill documentation.

What changed:

- Added review-only benchmark case harvesting from real Git history without exposing fix commits or commit messages to Agent runs.
- Added non-destructive ArkTS/TypeScript mutations for removed awaits, corrupt route targets, and corrupt resource keys with source-digest and exact-occurrence guards.
- Added an Agent-neutral JSON stdin/stdout Runner protocol for paired baseline and Query Skill executions.
- Materialized each case in a fresh frozen workspace and rebuilt isolated memory from that revision for the Memory variant, preventing current-HEAD memory leakage.
- Added deterministic scoring of the external Agent result: root-cause category, file recall/precision, forbidden direction, causal calibration, verification, query rounds, tokens, latency, and explicit context uplift.
- Rejected private reasoning fields, kept raw logs and reasoning out of persistence, and exposed only a compact latest benchmark summary through maintain health.

Verification:

- Focused 27-test benchmark, quality-gate, design-assist, and causal-diagnosis regression passed.
- `PYTHONPYCACHEPREFIX=/tmp/agent-memory-pyc python3 -m unittest discover -s tests -p 'test_*.py'`: 349 tests passed in 484.094 seconds.
- Git history harvesting scanned 100 commits and produced 10 bounded draft previews in about 5.6 seconds on this repository.
- Deterministic scoring processed 1,000 cases and 2,000 A/B observations in 23.48 ms.
- CLI help, exactly-four-Skill, Python compilation, diff, and 500-line checks passed.

Rollback notes:

- Remove the three benchmark commands, benchmark modules, tests, documentation, and governance summary. Runtime benchmark JSON files are disposable telemetry; no SQLite rollback is required.

## 2026-07-15 - Restore the Agent-led investigation boundary

Files added or extended:

- `tools/agent_memory_runtime/agent_context.py`
- Evidence context, temporary runtime-log analysis, Span Graph, Incident Trace, evidence governance, and benchmark modules.
- `skills/agent-memory-query/` diagnosis protocol.
- `docs/context-provider-boundary.md` and related runtime, usage, benchmark, README, and Chinese Agent CLI documentation.
- `tests/test_causal_diagnosis.py` and benchmark tests.

What changed:

- Removed Runtime-generated diagnosis hypothesis ledgers, candidate root causes, stop decisions, and intervention suggestions from query and log-analysis output.
- Added bounded `agent-investigation-context/v1` handoffs containing evidence references, observed relation references, investigation gaps, query terms, and an explicit `no_runtime_diagnosis` boundary.
- Upgraded Span Graph output to `runtime-span-graph/v2`; `relation_paths` now report only parent-span, runtime identity, and temporal observations. Historical `causal_paths` remain readable inside stored evidence.
- Kept code graph, code-log graph, Incident links, relation levels, and experience as inspectable context. The local Agent CLI now explicitly owns hypotheses, source inspection, root-cause reasoning, experiments, and verification.
- Reframed A/B scoring as external Agent outcome and context uplift. The Runtime prepares isolated context, while the external Runner remains the only component that diagnoses or designs.
- Replaced hypothesis governance with relation coverage and evidence-gap governance; raw user logs remain temporary and outside SQLite.
- Restricted runtime-log reflection templates to observed context. Experience type, reasoning, success/failure lessons, misleading terms, verification, repair actions, and correction claims now remain Agent-owned completion fields.

Verification:

- Focused evidence, runtime relation, and Agent benchmark regression: 29 tests passed in 17.825 seconds.
- Focused runtime reflection-boundary regression: 26 tests passed in 19.564 seconds.
- `PYTHONPYCACHEPREFIX=/tmp/agent-memory-pyc python3 -m unittest discover -s tests -p 'test_*.py' -q`: 349 tests passed in 249.389 seconds.
- Actual CLI contract checks confirmed `agent-investigation-context/v1`, `no_runtime_diagnosis=true`, `runtime-span-graph/v2`, relation-only paths, and empty Agent-owned reflection fields.
- Python compilation, line-limit, CLI help, exactly-four-Skill, and diff checks passed.

Rollback notes:

- Restore `diagnosis_hypotheses.py`, the v1 Span Graph field, and old output/docs if Runtime-generated diagnoses are intentionally reintroduced. No SQLite migration is involved; old runtime snapshots are disposable.

## 2026-07-15 - Add log-anchored candidate call paths to context

Files added or extended:

- `tools/agent_memory_runtime/path_*.py`, `context_facade.py`, and `context_composition.py`.
- `tools/agent_memory_runtime/command_handlers.py` and active-edge indexes.
- Query Skill incident guidance, runtime/usage/Chinese documentation, and the architecture design.
- `tests/test_log_anchored_paths.py` and `tests/test_path_search.py`.

What changed:

- Kept `context` as the only public query entry while adding injected log-anchor, graph-reader, entry-policy, search, and ranking abstractions behind a facade.
- Added strong code-log identity activation, ambiguous emitter preservation, bounded reverse breadth-first search, ArkTS lifecycle/event entry recognition, structural provenance scoring, entry diversity, and expected log anchors.
- Isolated lanes so experience and semantic corrections remain advisory and cannot create seeds, graph edges, or path scores.
- Kept temporary user logs outside Runtime and SQLite; the Agent CLI compares all candidate paths with real log order and current source before forming a causal conclusion.
- Added active-edge relation indexes and per-layer batched graph reads to bound work on large graphs.

Verification:

- Focused log-anchor integration and path-search unit tests: 10 tests passed.
- Exact two-entry reconstruction, expected logs, stale-edge exclusion, ordinary-query non-activation, depth/cycle bounds, batched frontier reads, and experience/correction isolation are covered.
- Existing context, evidence, benchmark, causal-boundary, graph-performance, and part-10 through part-14 regressions passed.
- A 500,000-edge in-memory SQLite probe used the relation-aware active-target index; table creation, population, indexing, analysis, and the bounded lookup completed in about 1.2 seconds total.
- `PYTHONPYCACHEPREFIX=/tmp/agent-memory-pyc python3 -m unittest discover -s tests -p 'test_*.py' -q`: 351 tests passed in 260.034 seconds.
- Python compilation, diff whitespace, exactly-four-Skill, and 500-line checks passed.

Rollback notes:

- Remove the context composition and path modules, restore the direct `limited_context` call, and remove the two relation-aware indexes. No candidate path records require migration because paths are never persisted.

## 2026-07-16 - Validate log paths on an external ArkTS project

Files extended:

- `tools/agent_memory_runtime/code_wiki_extractors.py` and `semantic_ecma.py`.
- `tools/agent_memory_runtime/path_ranking.py` and `agent_benchmark_eval.py`.
- Log-path, semantic-index, path-search, and Agent benchmark tests.

What changed:

- Bound ArkTS logs to `async`, `static async`, and other modified methods instead of their enclosing component or no symbol.
- Added semantic handling for static methods, default imports, and imported static calls/awaits.
- Deduplicated same-seed paths with identical node sequences, preferring more specific async/callback/event relations, and suppressed unknown-entry variants when the same seed has a recognized entry.
- Canonicalized bounded benchmark root-cause categories and treated verified causal evidence as satisfying a supported-evidence oracle.

External validation:

- Read-only mutation harvesting on `/Users/liuhui/Documents/code/browser` generated 14 deterministic cases: 5 removed-await, 1 route-target, and 8 resource-key cases; source files remained unchanged.
- Learning indexed 34 files, 146 symbols, 31 log statements, and 455 current graph edges after semantic fixes.
- Real code logs reconstructed `Index.aboutToAppear`, `PagesDialog.aboutToAppear -> awaits -> loadHistoryData`, and two `Index.aboutToAppear -> awaits -> RdbUtils` paths without missing emitters.
- A one-case isolated Codex A/B correctly found the route fault and expected file in both variants. Memory produced no accuracy uplift on this obvious source-local fault and added about 3,100 estimated tokens and 3.6 seconds, so this case should gate selective query routing rather than ranking calibration.
- Focused log-path, path-search, semantic-index, and benchmark regression: 31 tests passed.
- `PYTHONPYCACHEPREFIX=/tmp/agent-memory-pyc python3 -m unittest discover -s tests -p 'test_*.py' -q`: 356 tests passed in 250.067 seconds.
- Python compilation, diff whitespace, and 500-line checks passed.

Rollback notes:

- Restore the previous method/import regexes and ranking/evaluation rules. External workspaces and case packs were temporary and did not modify the ArkTS repository.

## 2026-07-16 - Add selective compact context retrieval

Files added or extended:

- `tools/agent_memory_runtime/context_compact.py`, CLI context registration, and command handling.
- Query Skill routing and code-understanding, incident, and evidence protocols.
- Runtime, usage, local-Agent, Chinese guide, README, boundary, and mission documentation.
- `tests/test_log_anchored_paths.py`.

What changed:

- Added the backward-compatible `context --compact` view without changing retrieval, ranking, SQLite state, or the default full context contract.
- Kept bounded log/code anchors, current-graph path candidates, relation hints, correction and semantic guards, advisory experience references, evidence gaps, expansion guidance, and the Agent/Runtime role boundary.
- Omitted full records, repeated search terms, retrieval explanations, trust-reason internals, query audit, static policies, and duplicate edge details from first-round Agent injection.
- Enforced an estimated 1,500-token compact budget through deterministic progressive reductions while preserving correction guards.
- Added Query Skill L0/L1/L2 routing: bounded current-source inspection for precise local faults, compact Memory for logs/cross-module/async/history or unresolved work, and full output only for focused audit expansion.

Verification:

- A real ArkTS log query against the learned `browser` project fell from about 14,487 estimated tokens to 1,315 while preserving `PagesDialog.aboutToAppear -> awaits -> loadHistoryData` and its log anchors, a 90.9% reduction.
- Compact contract, budget, correction preservation, default full-output compatibility, and selective Skill routing tests passed.
- Existing base runtime, part10-part14, design, quality-loop, and memory-calibration regressions passed.
- `PYTHONPYCACHEPREFIX=/tmp/agent-memory-pyc python3 -m unittest discover -s tests -p 'test_*.py' -q`: 359 tests passed in 1112.403 seconds. This unusually slow single run is recorded as validation, not a performance baseline.
- Python compilation, diff whitespace, Query Skill progressive-disclosure line limit, and 500-line checks passed.

Rollback notes:

- Remove `--compact`, the compact projection module, and the L0/L1/L2 Skill rules. No SQLite migration or stored compact records require cleanup.

## 2026-07-16 - Add the long-term data governance kernel

Files added or extended:

- Long-term governance architecture and execution plan under `docs/superpowers/`.
- Feedback policy, retrieval feedback, experience usage, storage migrations,
  candidate collection, and maintain governance projections.
- Runtime, schema, usage, Chinese README, and Maintain Skill documentation.
- Retrieval-feedback, experience-usage, calibration, and active-learning tests.

What changed:

- Kept the fixed four-Skill surface and reused the existing
  `retrieval-feedback` and `experience-usage` commands instead of adding a
  generic context-feedback interface.
- Added optional task/query correlation, deterministic event keys, verification,
  lifecycle closure, target validation, and in-place migrations.
- Delayed ranking effects until an observation is verified or repeated by two
  independent tasks; `used`, `ignored`, and `superseded` no longer act as direct
  relevance labels.
- Replaced global latest-event scans with candidate-directed batched SQL reads,
  grouped stable signals once, and excluded resolved or ignored feedback.
- Exposed stable versus pending observations and closure commands through
  existing maintain health and plan outputs.
- Recorded durable governance cases, selective mutation audit events, retention,
  and algorithm self-evolution as explicit future phases rather than premature
  schema expansion.

Verification:

- Focused feedback, calibration, usage, active-learning, and quality regression:
  23 tests passed.
- Fingerprint, retrieval-feedback, and usage regression: 31 tests passed.
- `PYTHONPYCACHEPREFIX=/tmp/agent-memory-pyc python3 -m unittest discover -s tests -p 'test_*.py' -q`:
  366 tests passed in 1467.990 seconds.
- A synthetic 500,000-row SQLite probe used the candidate composite index and
  returned 80 bounded rows. The full setup and query took about 1.16 seconds;
  this is an index-path probe, not a production performance baseline.
- Python compilation, CLI help, diff whitespace, exactly-four-Skill, and
  500-line checks passed.

Rollback notes:

- Restore the previous feedback and usage aggregation modules and remove the new
  observation columns/indexes from fresh-schema creation. Existing SQLite
  columns can remain unused because SQLite does not require destructive rollback.

## 2026-07-16 - Move code design reasoning back to the Agent

Files added or extended:

- Long-term Design Context Provider architecture and execution plan under
  `docs/superpowers/` with SEI, ISO, ADR, ArchUnit, SCIP, and AWS references.
- `design-context` facade, versioned design-knowledge catalog, CLI registration,
  and evidence metadata for design-scoped correction guardrails.
- Query Skill design protocol, runtime/schema/protocol references, English and
  Chinese usage guidance, and README summaries.
- Design-context contract, routing, authority, compactness, correction, and
  compatibility tests.

What changed:

- Made `design-context/v1` the normal design retrieval contract while keeping
  the fixed four-Skill surface and `tools/agent_memory.py` runtime entry.
- Added two-pass Agent-controlled retrieval: an orientation request followed by
  optional explicit concerns, source anchors, and task constraints.
- Separated versioned general design knowledge from project SQLite memory. Each
  principle, tactic, or pattern reference carries applicability, preconditions,
  contraindications, tradeoffs, questions, retrieval reasons, and provenance.
- Composed current repository views, source anchors, consumers, task constraints,
  scoped semantic corrections, historical memory, quality questions, freshness,
  and evidence gaps in an explicit authority order.
- Kept unverified semantic corrections as source-check guardrails instead of
  falsely marking them confirmed or allowing them to establish architecture.
- Guaranteed that the new facade emits no pattern recommendation, generated
  candidate, candidate ranking, selected design, Delta template, or change plan.
- Moved old design-assist/prepare/check/compare/progress commands to
  compatibility-only documentation; the Agent owns design synthesis, tradeoffs,
  selection, implementation planning, and verification reasoning.
- Added a compact graph and knowledge projection capped at 1,500 estimated
  tokens without dropping authority, applicability, tradeoff, or provenance
  boundaries.

Verification:

- Design-context, legacy compatibility, and repository-design regression:
  16 tests passed.
- Design, evidence-fabric, and experience-query integration regression:
  45 tests passed.
- `PYTHONPYCACHEPREFIX=/tmp/agent-memory-pyc python3 -m unittest discover -s tests -p 'test_*.py' -q`:
  372 tests passed in 260.265 seconds.
- Python compilation, JSON catalog validation, CLI help, diff whitespace,
  exactly-four-Skill, and 500-line source checks passed.

Rollback notes:

- Remove the `design-context` parser/handler and knowledge catalog, restore the
  prior Query Skill design reference, and remove the design-correction metadata
  projection. No SQLite migration or persisted context requires rollback.

Documentation follow-up:

- Rewrote `docs/design-usage-guide.md` as a complete Chinese guide for the
  Agent-owned Design Context workflow. It now covers user request structure,
  two-pass queries, field interpretation, authority, semantic-correction
  guardrails, Agent design synthesis, answer format, verification, legacy
  command boundaries, common errors, and a minimal checklist.
- Added the dedicated guide to the Chinese README and mission-document indexes.
- Synchronized the English and Chinese READMEs with the current system:
  ArkTS-first semantic indexing, SQLite/FTS5 retrieval, memory and experience
  fields, code/log graphs, Agent-owned diagnosis and design, Skill evolution,
  project refresh and retirement, governance, impact analysis, quality
  evaluation, privacy boundaries, and the fixed four-Skill interface.

## 2026-07-16 - Start a real ArkTS Agent benchmark pilot

Files added or extended:

- Gramony source-reviewed development cases and pilot guidance.
- History-case classification and benchmark category normalization.
- Agent benchmark regression coverage and benchmark documentation.

What changed:

- Harvested 28 draft candidates from the real Gramony Git history and manually
  reviewed their source diffs.
- Curated ten bounded diagnosis drafts covering profile loading, startup
  lifecycle, split navigation, breakpoints, duplicate login submissions,
  sticker persistence, avatar layout, ArkWeb local media, chat title fallback,
  and reply-preview layout.
- Kept every case at `draft` because source review is not runtime reproduction.
- Removed ambiguous `split` from design-task keywords so a split-view navigation
  fix remains a diagnosis case.
- Added media, UI layout, database, push, and lifecycle category aliases for
  deterministic benchmark scoring.
- Added a read-only, ephemeral Codex CLI Runner example with schema-constrained
  output and measured token/elapsed telemetry.
- Updated design benchmark memory access to use Agent-owned `design-context`
  instead of the compatibility-only `design-assist` command.

Verification:

- Curated pack schema validation passed with ten reviewed records.
- Agent benchmark and Codex Runner regression: 12 tests passed.
- Frozen revision materialization produced 73 `.ets` files without Git history.
- The first real Codex A/B pair completed. It invalidated the profile-loading
  oracle: both variants found `ProfilePage.ets`, while `Me.ets` and navigation
  state were plausibly causal and the historical fix was only a loading-state
  workaround. The case was rejected instead of tuning retrieval against a weak
  oracle.
- A second, clearer startup-lifecycle pair passed with equal outcome quality:
  both variants found `Index.ets` and the lifecycle cause. The Memory run
  reported one query round instead of four, 11,588 fewer tokens, and 14,631 ms
  lower Agent elapsed time. The exploratory result is recorded with explicit
  model/runtime limitations and is not treated as general uplift evidence.
- Focused benchmark, Codex Runner, and design-context regression: 18 tests
  passed.
- Full regression: 376 tests passed in 1610.481 seconds.
- JSON validation, Python compilation, diff whitespace, exactly-four-Skill,
  public fingerprint, frozen-revision materialization, and 500-line source
  checks passed.

Rollback notes:

- Remove the Gramony case pack and pilot document, then restore the prior
  history keywords and category aliases. No SQLite migration is involved.

## 2026-07-17 - Run and audit the Gramony v3 external A/B

What changed:

- Completed the approved three-case, three-trial Gramony A/B: 18 external
  Codex calls on the pinned source revision with `gpt-5.5`, low reasoning,
  read-only source, and isolated user context.
- Preserved the raw v3 response pack for deterministic offline rescoring and
  recorded aggregate, per-case, stability, and exploration-audit results.
- Fixed observation normalization so `expansion_trace` is authoritative for
  round counts and preserves repeated reason codes.
- Aligned the total source-file cap with three primary anchors plus two rounds
  of two new files, while retaining per-round and search limits.
- Clarified category precedence: media loading, decoding, playback, and local
  media-resource access remain `media` when the concrete defect is API misuse.

Result:

- Navigation remained stable at 3/3 Memory trials; login improved by 0.2 and
  all three Memory trials correctly selected `async` and the expected files.
- WebM regressed in two Memory trials from `media` to `api`, producing a
  -0.2667 case delta. One WebM trial exceeded the search budget, and one login
  trial inspected an untraced file.
- The batch remains `fail`: Memory outcome score 0.9111 versus Baseline 0.9333,
  despite perfect Memory expected-file recall and predicted-file precision.

Verification:

- Raw response pack and pilot-result JSON parse successfully.
- Agent benchmark, source exploration, and Codex Runner regression: 44 tests
  passed; the focused compact-context contract group also passed 34 tests.
- Full regression: 410 tests passed in 816.099 seconds.
- JSON parsing, checked-in response rescoring, four-Skill, 500-line Python, and
  diff-whitespace checks passed.
- The immutable external response pack was rescored after protocol correction;
  real category and exploration failures remain, so no promotion is claimed.

Rollback notes:

- Restore the prior protocol normalization, five-file cap, and Runner category
  text, then remove the v3 response artifact and result section. No SQLite
  migration or persisted project-memory change is involved.

## 2026-07-17 - Prepare auditable Gramony v4 controls

What changed:

- Upgraded the active exploration contract to `anchor_first_gap_driven_v4`.
- Rendered exact Memory search, file, round, and files-per-round limits directly
  into the external Agent prompt and required a pre-search budget check.
- Required every opened file in `investigated_files` and every expansion or
  non-anchor file in the trace round that first opened it.
- Added explicit category precedence so concurrency remains `async`, domain
  failures such as WebM loading remain `media`, and API misuse stays a mechanism
  detail unless the API contract is the primary domain.
- Added Codex JSONL command telemetry parsing for `rg`, `grep`, `find`, and `fd`.
  V4 Codex observations require Runner-derived search counts to pass the source
  exploration gate; historical and third-party data retain marked fallback.

Result:

- The approved v4 three-case, three-trial Gramony batch completed all 18
  external calls and passed every quality, stability, context, configuration,
  and source-exploration gate.
- Baseline and Memory both scored 1.0 for outcome, root-cause accuracy,
  expected-file recall, and predicted-file precision. Navigation, canonical
  login category, and WebM were stable in all three Memory trials.
- Every observation used Runner-derived source-search telemetry. Memory reduced
  measured searches from 2.8889 to 0.5556 and query rounds from 2.2222 to
  1.1111.
- Memory still used 21,187 more average model tokens, took 14,781 ms longer,
  and inspected 0.67 more files than its same-batch Baseline. The development
  gate passes, but cost reduction remains the next priority.

Verification:

- Runner, source-exploration, compact-context, and benchmark regression: 59
  tests passed.
- Full regression: 413 tests passed in 334.311 seconds.
- JSON parsing, historical response rescoring, four-Skill, 500-line Python, and
  diff-whitespace checks passed.
- The frozen v3 response pack remains immutable and failing; no Oracle,
  category, or missing trace entry is rewritten by v4.
- The raw v4 response pack parses and rescored offline with the same all-pass
  result; it remains a three-case development result, not a Holdout claim.

Rollback notes:

- Restore policy v3, remove the prompt budget/category additions and Codex
  telemetry helper, and restore model-reported search counts. No SQLite
  migration or project-memory data is involved.

## 2026-07-17 - Add Agent benchmark cost attribution

What changed:

- Added privacy-safe Codex JSONL aggregation for input, cached input, uncached
  input, output, and reasoning Token counts.
- Added command count, command-output bytes, source-read count,
  source-read-output bytes, and tool-error count without persisting command
  output, source bodies, or private reasoning.
- Kept `quality_gate` backward-compatible and added an independent
  `efficiency_gate`. `promotion_gate` now requires both quality and efficiency.
- Set initial efficiency limits to at most 10% Token overhead, at most 15%
  elapsed-time overhead, complete cost attribution, and non-regressing source
  searches.
- Added `--fail-on-efficiency-fail`, persisted compact efficiency results, and
  exposed them through `maintain-health.agent_benchmark` recommendations.

Result:

- The immutable v4 Gramony pack remains `quality_gate=pass` but now reports
  `efficiency_gate=fail` and `promotion_gate=fail`: Token overhead is 18.11%,
  elapsed overhead is 26.38%, source-search non-regression passes, and detailed
  attribution coverage is zero because the pack predates the new fields.
- A new external batch is required to attribute cost to model input/output,
  cache behavior, source reads, and tool-output volume.

Verification:

- Cost telemetry, Runner, protocol, CLI, governance, and benchmark regression:
  50 focused tests passed.
- Full regression: 416 tests passed in 330.423 seconds.
- Historical response rescoring, JSON parsing, four-Skill, 500-line Python, and
  diff-whitespace checks passed.

Rollback notes:

- Remove the cost fields, efficiency module and CI option, then restore the
  quality-only persisted summary. No SQLite migration or project-memory data
  is involved.

## 2026-07-17 - Run the Gramony cost-attribution A/B

What changed:

- Completed the authorized three-case, three-trial Gramony A/B with 18 external
  Codex calls under the frozen v4 policy.
- Preserved the complete aggregate response pack in
  `docs/eval/gramony-v4-cost-attribution-responses.json` and updated the pilot
  report and structured result ledger.
- Kept source bodies, command output, and private reasoning out of the stored
  artifact.

Result:

- All 18 observations reported complete model and command cost fields and used
  Runner telemetry for source-search count.
- Quality passed: Memory reached 1.0 outcome, root-cause accuracy, expected-file
  recall, and predicted-file precision across all cases and trials.
- Efficiency failed: cumulative Token overhead was 63.43% and elapsed overhead
  was 27.71%, while source-search non-regression passed.
- Attribution identified cached-input replay as the dominant increase:
  cached input rose 97.20%, but uncached input fell 7.03%, command output fell
  26.88%, and source-read count fell 12.16%.
- Navigation is the main hotspot. A Baseline WebM trial that opened no source is
  an outlier, but excluding its pair still leaves 52.00% input and 20.56%
  elapsed overhead.
- Memory reported 1.5555 non-zero command exits on average. Aggregate telemetry
  treats these as review signals because it cannot distinguish expected search
  misses from real failures without persisting command details.

Verification:

- The raw pack contains 18 observations, three trials per variant and case,
  complete cost attribution, and valid JSON.
- Offline rescoring reports `quality_gate=pass`, `efficiency_gate=fail`, and
  `promotion_gate=fail` without an LLM judge.
- The cost-attribution implementation already passed 50 focused tests and the
  full 416-test regression suite before this external batch.

Rollback notes:

- Remove the attribution response pack and its report entries. No runtime data,
  SQLite migration, benchmark Oracle, or frozen source revision is changed.

## 2026-07-17 - Add the v5 sufficient-evidence Agent protocol

What changed:

- Added `anchor_first_sufficient_evidence_v5` with a compact
  `TRIAGE -> GAP -> VERIFY -> STOP` source-inspection loop.
- Moved benchmark prompt composition behind
  `examples/codex_benchmark_prompt.py`, keeping the Runner focused on execution
  and normalization.
- Added one-read-per-file and 180-line read guidance while retaining the v4
  search, file, expansion, category, and direct-evidence limits.
- Preserved Runner-search telemetry enforcement for both historical v4 and new
  v5 observations.
- Separated expected `rg/grep` no-match exits from real tool errors and added
  source-read amplification metrics.

Result:

- The minimal Memory protocol is eight lines and 1,592 characters versus the
  previous 15 lines and 1,848 characters.
- Historical v4 cost-attribution responses still rescore to
  `quality_gate=pass`, `efficiency_gate=fail`, and `promotion_gate=fail` with
  unchanged metrics.
- V5 remains a local candidate. Its interaction-cost hypothesis requires a new
  repeated external A/B before promotion.

Verification:

- Runner prompt, telemetry, source-exploration, path-handoff, benchmark, and
  cost tests: 63 tests passed.
- Full regression: 417 tests passed in 449.012 seconds.
- Structured benchmark reports parse as JSON; no benchmark Oracle or frozen
  response artifact was modified.

Rollback notes:

- Restore policy v4 and inline prompt composition, then remove the read limits,
  search-miss field, and read-amplification metrics. No SQLite migration or
  project-memory data is involved.

## 2026-07-17 - Run the Gramony v5 external A/B

What changed:

- Completed the authorized three-case, three-trial v5 benchmark with 18
  external Codex calls against the same frozen Gramony revisions.
- Preserved the raw aggregate pack in
  `docs/eval/gramony-v5-sufficient-evidence-responses.json`.
- Recorded quality, efficiency, per-observation contract failures, v4 trend,
  and the next bounded protocol change.

Result:

- All Memory trials returned the expected root-cause category, causal level,
  and repair-owner files.
- Quality still failed because navigation Memory trial 2 used four searches and
  WebM Memory trial 1 used five against the limit of three.
- Efficiency narrowly failed: Token overhead was 10.59% against 10%, and elapsed
  overhead was 18.27% against 15%.
- Commands fell 15.29%, command output 59.22%, source reads 38.57%, and
  source-read output 43.00% against the same-batch Baseline.
- Compared directionally with v4 Memory, v5 reduced model tokens 13.21%,
  commands 16.28%, source reads 33.85%, and read output 54.03%.
- All observations reported the new search-miss field. It was zero, so the
  remaining non-zero exits were not expected `rg/grep` no-match results.

Verification:

- The response pack contains exactly 18 observations, with three trials for
  each case and variant and complete cost telemetry.
- Offline rescoring reproduces `quality_gate=fail`, `efficiency_gate=fail`, and
  `promotion_gate=fail` without an LLM judge.

Rollback notes:

- Remove the v5 response pack and report entries. No runtime data, SQLite
  migration, Oracle, or frozen source revision is changed.

## 2026-07-17 - Add the v6 ledgered-stop candidate

What changed:

- Added `anchor_first_ledgered_stop_v6`, retaining the v5 sufficient-evidence
  loop and restoring explicit pre-command search and read ledgers.
- Required compound/pipeline search occurrences to count separately, known
  anchors to be read directly, and each source path to be read at most once.
- Added a v6-only Codex exploration audit requiring complete cost telemetry and
  `source_read_count <= source_file_count`; historical v4/v5 scoring is not
  changed.
- Split non-zero command exits into search, source-read, and other command
  families without storing command text or output.

Result:

- The minimal v6 Memory protocol is eight lines and 1,750 characters, below the
  v4 protocol while restoring the ledger omitted by v5.
- V6 is locally verified and remains pending the same repeated Gramony external
  A/B. No gate threshold, Oracle, or retrieval ranking changed.

Verification:

- Prompt, telemetry, source-exploration, path-handoff, benchmark, and cost
  regression: 64 tests passed.
- Full regression: 418 tests passed in 503.485 seconds.
- Historical v4 and v5 response packs retain their previous gate outcomes and
  efficiency metrics under v6 code.

Rollback notes:

- Restore policy v5, remove the ledger line, v6 read audit, and family-specific
  error fields. No SQLite migration or project-memory data is involved.

## 2026-07-17 - Run the Gramony v6 external A/B

What changed:

- Completed the authorized three-case, three-trial v6 benchmark with 18
  external Codex calls against the frozen Gramony revisions.
- Preserved the raw aggregate pack in
  `docs/eval/gramony-v6-ledgered-stop-responses.json`.
- Recorded read-ledger, trace, zero-command telemetry, quality, efficiency, and
  command-family error findings.

Result:

- The search ledger worked: every Memory observation stayed within three
  searches and average searches fell to 0.8889.
- Quality failed on four repeated-read observations, one incomplete expansion
  trace, and one no-source login observation that scored 0.4.
- Efficiency failed: Token overhead was 24.64% and elapsed overhead was 20.32%.
- Commands, command output, source searches, source reads, and read output all
  improved against same-batch Baseline, but cached-input replay remained high.
- Compared directionally with v5 Memory, v6 reduced tokens 4.18%, commands
  19.45%, searches 63.64%, and reads 16.28%; elapsed time was flat.
- All Memory non-zero exits were classified as other-command failures. Search
  misses/errors and source-read errors were zero.

Verification:

- The response pack contains exactly 18 observations with consistent v6 Runner
  metadata and complete cost/error-family telemetry.
- Offline rescoring reproduces `quality_gate=fail`, `efficiency_gate=fail`, and
  `promotion_gate=fail` without an LLM judge.

Rollback notes:

- Remove the v6 response pack and report entries. No runtime data, SQLite
  migration, Oracle, or frozen source revision is changed.

## 2026-07-17 - Add the v7 search-ledger candidate

What changed:

- Kept the v6 hard search ledger and audited three-search limit under
  `anchor_first_search_ledger_v7`.
- Replaced the hard one-read-per-file quality rule with a bounded read plan:
  one 180-line window plus one additional window for a named evidence gap.
- Added source-read amplification to the efficiency gate with a 2.0 ceiling
  and Baseline non-regression check.
- Treat complete tool-less Codex turns as Runner-telemetry zero searches and
  expose Memory read amplification through benchmark governance health.

Result:

- Focused prompt, telemetry, exploration, path, cost, and governance
  regressions: 46 tests passed.
- Full regression: 422 tests passed in 453.621 seconds.
- Historical three-case rescoring preserves v4 quality-pass/efficiency-fail
  and v5/v6 quality-fail/efficiency-fail outcomes; the new read-amplification
  checks pass on all three immutable packs.
- V7 remains a local candidate pending the repeated 18-call Gramony A/B; no
  Oracle, quality threshold, retrieval ranking, or SQLite data changed.

Rollback notes:

- Restore the v6 policy and one-read quality audit, then remove the two read
  amplification efficiency checks. Historical response artifacts remain valid.

## 2026-07-18 - Run the Gramony v7 external A/B

What changed:

- Completed the three-case, three-trial v7 benchmark with 18 external Codex
  calls against the frozen Gramony revisions.
- Preserved the privacy-safe aggregate response pack in
  `docs/eval/gramony-v7-search-ledger-responses.json`.
- Recorded aggregate and per-case source-read amplification alongside quality,
  efficiency, trace, and error-family results.

Result:

- All Memory diagnosis and file metrics reached 1.0, and every search count
  came from Runner telemetry.
- Quality failed because all three Login trials incompletely accounted for
  expanded files; trial 2 also exceeded the per-round expansion-file budget.
- Efficiency failed with 16.41% Token and 23.10% elapsed overhead.
- Searches, reads, command output, read output, and aggregate read amplification
  improved against Baseline. WebM still had 2.8333 reads per file, hidden by
  the passing 1.4667 aggregate.
- V7 is not promotable. The next candidate needs deterministic expansion
  accounting and per-case efficiency checks before another external run.

Verification:

- The response pack contains exactly 18 observations with consistent v7
  Runner metadata and complete cost/search telemetry.
- Offline rescoring reproduces `quality_gate=fail`, `efficiency_gate=fail`, and
  `promotion_gate=fail` without an LLM judge.

Rollback notes:

- Remove the v7 response pack and result entries. No SQLite migration, Oracle,
  frozen source revision, or project-memory data changed.

## 2026-07-18 - Add the v8 deterministic-expansion candidate

What changed:

- Added `anchor_first_deterministic_expansion_v8`, retaining the v7 search
  ledger and bounded read plan.
- Runner now derives expansion-file count and minimum two-file rounds from
  investigated files and primary anchors; Agent trace files are representative.
- Added per-case Token, elapsed, search, and read-amplification efficiency
  checks alongside aggregate checks.
- Exposed failed efficiency-case count and IDs through benchmark governance.

Result:

- Focused Runner, protocol, path, cost, and governance regression: 73 tests
  passed.
- Full regression: 427 tests passed in 245.793 seconds.
- V4-v7 offline replay preserves their existing quality and promotion outcomes.
- New per-case checks surface the historical Login Token/time and WebM read
  hotspots that aggregate checks masked.
- V8 is locally implemented and remains pending the repeated 18-call Gramony
  A/B. No retrieval ranking, Oracle, SQLite schema, or memory data changed.

Rollback notes:

- Restore v7 policy, trace-completeness accounting, and aggregate-only
  efficiency checks. Historical response artifacts require no migration.

## 2026-07-18 - Improve core query context and test read windows

What changed:

- Added exact path-segment and long identifier identity signals, source-location
  preference, and file-diverse result bounding for code retrieval.
- Compact handoff now groups same-file symbols, carries source ranges and a
  merged 180-line `read_window`, and removes duplicate containment evidence.
- Updated the Codex benchmark protocol to treat source ranges as targets inside
  one file read instead of separate read requests.
- Preserved two privacy-safe development response packs for the Login/WebM
  core-context check and the targeted WebM read-window check.

Result:

- Frozen Login now returns Password, PhoneNumber, and VerifyCode with source
  ranges; frozen WebM ranks StickerInfo and MessageBubble first and includes
  both sticker-rendering function ranges.
- The first four-call A/B reduced Login reads from 9 to 3, searches from 3 to
  0, Token use by about 50%, and elapsed time by about 16%, with outcome 1.0.
- WebM outcome and file precision reached 1.0, but the read-window retest still
  made 6 reads across 2 files. Prompt-only guidance did not solve repeated
  source reads; a budgeted non-persistent source-excerpt stage remains next.
- Focused query/retrieval/benchmark regression passed 97 tests. Full regression
  after the read-window addition passed 428 tests in 244.680 seconds.

Rollback notes:

- Remove the identity scoring, diversity bound, compact source metadata, and
  read-window prompt. SQLite schema, frozen Oracle, and project memory data do
  not require migration.

## 2026-07-18 - Add budgeted non-persistent source excerpts

What changed:

- Added a language-neutral current-source excerpt provider for the first two
  compact primary anchors, bounded by ranges, lines, characters, and the
  existing 1,500-Token payload budget.
- Reject absolute, traversal, missing, and external-symlink source paths.
- Return excerpt bodies to the caller while persisting only source-range
  metadata in `runtime/last_context.json`.
- Updated Query Skill and Runner guidance so an Agent reuses current-worktree
  excerpts instead of rereading the same lines.

Result:

- Frozen WebM compact context is about 1,216 Tokens and contains the concrete
  `audio/webm` Base64 `loadData` call. Frozen Login remains below budget at
  about 1,244 Tokens while retaining all three Login files.
- Source-excerpt, path-boundary, compact-query, Runner-prompt, log-path, query,
  and retrieval focused regressions pass.
- Final full regression passes all 430 tests in 252.937 seconds; Query Skill
  remains within its 120-line progressive-disclosure limit at 118 lines.
- The external WebM A/B was rejected because it would disclose current source
  bodies to an external model. No external result was recorded or inferred.

Rollback notes:

- Remove `context_source_excerpt.py`, its compact-context attachment and
  persistence redaction calls, and the source-excerpt Agent guidance. No
  SQLite migration or stored-memory rewrite is required.

## 2026-07-18 - Redact source excerpts at the external Runner boundary

What changed:

- The bundled Codex benchmark Runner now removes source-excerpt bodies before
  constructing an external prompt while retaining inspectable line metadata.
- Prompt logic distinguishes actual current-worktree bodies from metadata-only
  anchors, so redacted runs still require direct source verification.
- Runner metadata reports `source_excerpt_delivery=external_metadata_only`.
- Added an end-to-end fake-Codex regression that fails if a unique source body
  reaches the external process stdin.

Result:

- External Codex benchmark runs can evaluate anchor and range retrieval without
  transmitting compact source bodies.
- No supported local model CLI was found, so full source-excerpt behavior was
  not assigned an invented Agent quality result. The generic Runner protocol
  remains available for a trusted local implementation.
- Historical v4, v7, and v8 response packs replay offline with their existing
  non-promotion outcomes; no observation was rewritten.
- Final full regression passes all 431 tests in 249.804 seconds. Source-privacy
  tests remain in a separate 81-line module and all Python files stay below
  the 500-line limit.

Rollback notes:

- Remove external-context redaction and its metadata field only if the external
  source-disclosure boundary is intentionally restored. Runtime query behavior
  and SQLite data require no migration.

## 2026-07-18 - Add a trusted local Ollama benchmark Runner

What changed:

- Added a loopback-only Ollama Benchmark Runner using native `/api/chat` tool
  calls and the shared Codex/Ollama structured response schema.
- Added bounded, read-only workspace `read_source` and literal `search_source`
  tools with path, symlink, file-size, output, search, file, line, and read limits.
- Kept full compact source excerpts inside the declared local process boundary
  while continuing to persist only aggregate telemetry and file paths.
- Added mock Ollama end-to-end, model/host boundary, source tool, and existing
  external Codex privacy regressions plus local usage documentation.

Result:

- The simulated local Agent performs a native tool call, receives current
  source, returns the benchmark schema, and reports Runner-derived tool and
  Ollama Token totals. The full regression passes all 436 tests in 246.564
  seconds; the final binary/path/tool-loop focused regression passes 24 tests.
- External Codex behavior remains metadata-only and its compatibility/privacy
  tests pass unchanged.
- Ollama `0.32.1` and four local model tags were installed for bounded probes;
  no model passed the single-case quality and efficiency smoke gate, so no
  three-case quality or promotion claim is made.
- A first real `qwen3:8b` tool probe on an Intel six-core/16-GB host timed out
  after five minutes at roughly 19 generated Tokens. The Runner now disables
  thinking and caps tool/final generation at 256/512 Tokens; a smaller-model
  smoke test is required before any Gramony quality claim.
- Real compatibility probes found that `qwen3:1.7b` can call tools but failed a
  Login A/B on planning quality, while `qwen3:4b` emitted reasoning text without
  a tool call. `llama3.2:3b` returned a native tool call in 12.3 seconds but
  encoded integer arguments as digit strings, so the tool facade now safely
  normalizes ASCII digit strings and continues to reject other invalid types.
- A real `llama3.2:3b` Login A/B also failed: Memory received two correct source
  excerpts but returned a placeholder category, while Baseline invented JS file
  names without reading source. This exposed and fixed a telemetry issue:
  `source_file_count` now derives only from Runner-observed reads and delivered
  excerpts, never model-claimed predicted or supporting files.
- Preserved both privacy-safe failed smoke packs for offline replay, stopped the
  18-call matrix, removed the unusable 8B/4B blobs, and retained only the 1.7B
  protocol fixture plus 3B smoke candidate locally.

Rollback notes:

- Remove the Ollama Runner, source tool module, tests, and documentation. The
  Runtime API, four Skills, SQLite schema, and stored memory require no change.

## 2026-07-18 - Add a model-free system context capability gate

What changed:

- Added `eval-context-capability` to rebuild frozen cases and score compact
  context supply before invoking an external Agent.
- Separated code-anchor, source-excerpt, log, experience, causal-context, and
  compactness profiles; capabilities without an explicit Oracle remain
  informational rather than passing implicitly.
- Persisted privacy-safe bounded results and exposed the latest summary through
  `maintain-health.context_capability`.
- Added selective promotion of one score-qualified exact log-emitter code
  identity while retaining ordinary weak-log suppression.

Result:

- The first Gramony run caught a real split-view retrieval loss that previous
  Agent outcome scoring had hidden: `ChatList.ets` existed in full log-emitter
  results but was removed from compact context.
- After the scoped fix, split-view navigation, duplicate login submission, and
  WebM access all pass. Code and primary-anchor recall are 1.0, source-excerpt
  recall is 0.8889, and average compact context is 1,215.3333 Tokens.
- The gate invokes no model and stores no source body. It authorizes a later
  Agent A/B but does not convert failed local-model smoke runs into a quality
  pass.
- Full regression passes all 443 tests in 252.332 seconds. All changed Python
  files remain below 500 lines and `git diff --check` is clean.

Rollback notes:

- Remove the context capability command, evaluator, governance summary, and
  exact log-emitter identity slot. Existing Agent A/B artifacts and SQLite data
  require no migration.

## 2026-07-18 - Add a six-case system capability suite

What changed:

- Added a reviewed minimal ArkTS fixture with two log, two experience, and two
  bounded causal-path cases plus explicit positive and negative Oracles.
- Added bounded reflection fixture injection through the existing public
  `reflect` command and expanded deterministic scoring for log emitters,
  main/guard experience lanes, path files, relations, and forbidden noise.
- Scoped compact anchors and candidate paths after explicit negative log
  clauses, preserved correction identity under budget trimming, and recognized
  English semantic questions before memory-maintenance terms.
- Kept trigger-relevant correction experience in the guard lane beside a
  procedure while leaving unrelated correction memories blocked.

Result:

- The first run failed 5 of 6 cases and exposed concrete context-supply defects;
  the final isolated run passes all 6 cases without changing the Oracles.
- Code-anchor and source-excerpt recall are 1.0. Log, experience, causal, source,
  code, and compactness profiles all pass at an average 1,002.5 Tokens.
- Persisted reports contain no Oracle, source body, temporary log, or Agent
  output. The evaluator invokes no model.
- Selection logic was split from compact rendering; all changed Python files
  remain below 500 lines. The full regression passes all 450 tests in 252.548
  seconds.

Rollback notes:

- Remove the six-case fixture, context setup adapter, expanded Oracle fields,
  and compact anchor selection module. No SQLite migration is required because
  fixtures use isolated temporary memory only.

## 2026-07-18 - Gate system capability across query variants

What changed:

- Added a bounded `query_variants` protocol that expands each selected scenario
  into isolated context queries while sharing one reviewed Oracle and fixture.
- Added per-scenario query robustness, variant pass rate, failed variant IDs,
  and `maintain-health.context_capability` stability fields.
- Expanded six ArkTS scenarios to original, English paraphrase, and Chinese or
  explicit-noise wording for 18 model-free system queries.
- Prioritized explicit business-semantics phrases over generic `refresh`
  maintenance terms and measured procedure correction applicability by trigger
  coverage instead of full-query length.

Result:

- The first robustness run passed 15/18 and isolated all failures to experience
  wording sensitivity; log and causal-path variants already passed 12/12.
- After the scoped fixes, all 6 scenarios and 18 variants pass. Query robustness,
  code, source, log, experience, causal context, and compactness all pass;
  average compact context is 998.6667 Tokens.
- Unrelated procedure correction guards remain blocked by existing regressions,
  and no Agent, Oracle, source body, or temporary log is persisted.
- The full regression passes all 452 tests in 249.351 seconds, and all Python
  files remain within the 500-line limit.

Rollback notes:

- Remove query variant expansion and robustness fields, then restore the six
  original task descriptions. No runtime database migration is required.

## 2026-07-18 - Add precision, source-span, abstention, and sealed holdout gates

What changed:

- Added query-focused current-source windows and persisted only bounded range
  metadata, never source bodies.
- Added hard Top-K, anchor-precision, source-span-recall, evidence-gap, and
  no-evidence abstention Oracles to the model-free capability evaluator.
- Expanded the synthetic suite to seven scenarios and 21 wording variants, and
  exposed MRR, source-span recall, and abstention status through governance.
- Sealed three previously unused Gramony history fixes as a separate holdout
  before their first system-capability run.

Result:

- The synthetic gate passes all 21/21 variants; abstention passes 3/3, expected
  anchor MRR is 1.0, and average compact context is 992.9524 Tokens.
- The three-case Gramony development validation passes Top-K, precision, and
  human source-span gates with source-span recall 1.0 and MRR 0.6667.
- The untouched Gramony holdout fails 0/3 on the strict combined gate. It still
  reaches 0.8333 file recall and MRR, but exposes ranking noise, source excerpts
  displaced by log evidence, and a missed cross-component reply preview. The
  holdout is retained as a failure baseline and is not used for tuning.
- Full regression passes all 458 tests in 249.507 seconds. JSON fixtures and
  whitespace checks pass, and every Python file remains below 500 lines.

Rollback notes:

- Remove the quality scorer, source-span metadata, negative fixture, and sealed
  holdout pack. No SQLite migration is required.

## 2026-07-18 - Generalize compact retrieval across lexical, graph, and source evidence

What changed:

- Added query-only CamelCase, underscore, and conservative English morphology
  expansion without changing the base tokenizer used by memory governance.
- Normalized symbol and log graph candidates to their containing files, added
  bounded named ArkTS navigation routes, and reranked at most one independently
  supported graph neighbor behind direct evidence.
- Added lightweight code-anchor diversity, weak-graph abstention, and explicit
  multi-target protection so related code can expand recall without displacing
  requested files or manufacturing evidence.
- Fairly divided the compact source-excerpt budget across the first three
  primary anchors, selected query-focused windows, and retained a bounded
  fallback path when a primary excerpt is unavailable.
- Expanded the synthetic capability suite with cross-component and log-dense
  cases, and expanded Gramony development validation with Sticker extension and
  new-chat-title cases. The sealed Gramony holdout was not rerun or used for
  tuning.
- Enforced the existing 1,500-Token budget on compact design context and kept
  the public related-edge result contract at ten entries while using broader
  candidates only inside graph reranking.

Result:

- The model-free synthetic gate passes 9/9 scenarios and 27/27 query variants.
  Code recall, primary recall, MRR, source-span recall, and query robustness are
  1.0; abstention passes 3/3; average compact context is 1,014.8519 Tokens.
- The five-case Gramony development gate passes 5/5 with code and primary recall
  1.0, MRR 0.7, source and source-span recall 1.0, and average compact context
  1,175.4 Tokens. Average preparation is 1,343.8 ms and query time is 408.4 ms.
- Focused retrieval, graph, source, and budget regressions pass. The final full
  regression passes all 470 tests in 251.300 seconds.
- Both evaluation JSON files parse successfully, whitespace checks pass, and
  every Python file remains at or below 500 lines.

Rollback notes:

- Remove query-only normalization, graph-neighbor promotion, named-route
  extraction, source-budget fairness, and the two added development scenarios.
  No SQLite schema or persisted project-memory migration is required.

## 2026-07-18 - Measure retrieval generalization on a second sealed Gramony set

What changed:

- Source-reviewed three previously unused Gramony fixes covering a chat-search
  layout overlap, cross-component sender-name propagation, and formatted-message
  persistence reload.
- Froze task wording, revisions, expected files, Top-K, precision thresholds,
  and source spans before execution in a new holdout pack. Its pre-run SHA-256 is
  `72e1588b9cb41850068e2e4d1831013e0dea600bfd9b7776160e41790c6766f1`.
- Preserved a compact first-run result artifact without source bodies, Oracle
  payloads, Agent output, or temporary logs. No retrieval implementation or
  holdout threshold was changed after observing the result.

Result:

- The first and only valid model-free run passes 1/3 cases. Anchor and primary
  recall are 0.7778, anchor precision is 0.3889, MRR is 1.0, and source-span
  recall is 0.6667 at an average 1,192.6667 Tokens.
- Formatted-entity persistence passes. Search-header layout reaches the correct
  file and source span but fails precision. Consecutive sender-name context
  misses the two upstream components that calculate and forward UI state.
- The result is retained as a failed generalization observation. Future work
  must develop backward component-property flow and precision on separate
  development cases, then validate against another unseen set.
- JSON, whitespace, and 19 focused capability tests pass. The final full
  regression passes all 470 tests in 250.551 seconds; the unrestricted rerun
  was required only for two fake Ollama tests that bind a loopback port.

Rollback notes:

- Remove the second holdout pack, its compact result, and the corresponding
  documentation. No Runtime code, SQLite schema, or project memory changed.

## 2026-07-18 - Add bounded ArkTS component-property navigation

What changed:

- Added a standalone ArkTS component-call parser that extracts only top-level
  object-argument names, ignores comments, and emits `passes_property` edges
  only when the target resolves to one unique learned component.
- Added a single recursive CTE that walks component composition/property edges
  backwards for at most two hops. Compact ranking can promote at most two
  source-locatable parents and records `graph_depth`; public edge output remains
  one hop and the Runtime does not infer data flow or causality.
- Allowed two strong component-flow neighbors in the compact diversity lane
  while retaining existing weak-graph abstention and explicit-target guards.
- Expanded ArkTS source-window behavior markers so component property bindings,
  `@Prop`, and conditional rendering outrank matching import lines.
- Added a generic Timeline page/row/bubble development fixture and three query
  variants without rerunning or modifying either sealed Gramony holdout.

Result:

- The focused component-flow gate passes 3/3 variants with anchor recall,
  precision, MRR, and source-span recall all at 1.0.
- The complete model-free development gate passes 10/10 scenarios and 30/30
  variants. Code recall, primary recall, MRR, source-span recall, and query
  robustness are 1.0; abstention passes 3/3; average compact context is 1,033.4
  Tokens, preparation is 676.0 ms, and query time is 282.6333 ms.
- The prior 9/27 development scenarios still pass unchanged. Neither sealed
  Gramony holdout was rerun or used as a tuning input.
- Focused graph, source-window, diversity, design-edge, and query-performance
  regressions pass. The final full regression passes all 471 tests in 252.793
  seconds, and every Python file remains at or below 500 lines.

Rollback notes:

- Remove `passes_property` extraction, component-lineage promotion, the Timeline
  fixture/scenario, and the added ArkTS source markers. Rebuild derived graph
  edges to remove the relation; no SQLite schema or durable memory migration is
  required.

## 2026-07-18 - Measure component-context generalization on a third sealed set

What changed:

- Source-reviewed and froze three previously unused Gramony UI fixes covering a
  chat-bottom safe area, a chat-list divider, and home-search spacing.
- Recorded the case pack SHA-256 as
  `c2fe3ca4d161ff1e70b8b2549758ee87d4096f2ed56e7bd131548e768482fb69`
  before execution and confirmed it remained unchanged afterwards.
- Preserved a compact first-run result without source bodies, raw logs, Agent
  output, or hidden Oracle payloads. Retrieval code and thresholds were not
  changed after observing the result.

Result:

- The first and only valid model-free run passes 0/3 cases. Anchor recall is
  0.5, precision is 0.2778, MRR is 0.6667, and source-span recall is 0.1667 at
  an average 1,101 Tokens.
- Home-search spacing recalls both expected files but misses precision and one
  source span. Chat-bottom context reaches the leaf component but not its page
  container. Chat-list divider misses the exact behavior owner.
- The failed holdout is retained as an immutable generalization observation.
  Future implementation work must use separate development cases and a new
  unseen set for validation.
- Both JSON artifacts parse, the sealed case hash is unchanged, whitespace
  checks pass, all 23 focused context-capability tests pass, and every Python
  file remains at or below 500 lines.

Rollback notes:

- Remove the third holdout pack, its compact result, and the corresponding
  documentation. No Runtime code, SQLite schema, or project memory changed.

## 2026-07-18 - Improve ArkTS behavior owners and component-lineage precision

What changed:

- Added two independent Commerce development scenarios for a three-component
  property chain and an exact ArkTS UI operation owner, each with three query
  variants. No sealed Gramony holdout was read, rerun, or modified for tuning.
- Added bounded, source-ordered ArkTS chained-operation names to file summaries
  and kept operation arguments and source bodies out of SQLite.
- Excluded known ArkUI Builder calls from function-symbol extraction while
  preserving project-defined uppercase methods.
- Conditioned component-lineage seeds on direct query support, focused compact
  candidates on coherent static branches, and stopped unrelated same-prefix
  candidates from backfilling a complete branch.
- Merged file-level behavior evidence with the best same-file source location,
  prioritized UI modifiers and component bindings in source windows, and kept
  a uniquely supported behavior owner isolated from unproven graph neighbors.
- Required short ASCII query terms to match token boundaries and allowed source
  locatability to boost only candidates with an existing textual match. This
  preserved no-evidence abstention after adding the Catalog fixture.

Result:

- Both new scenarios improve from 1/3 and 0/3 baselines to 3/3 variants.
- The complete model-free development gate passes 12/12 scenarios and 36/36
  variants. Code and primary recall, MRR, source-span recall, and query
  robustness are 1.0; abstention passes 3/3; average compact context is
  1,006.0278 Tokens, preparation is 677.2222 ms, and query time is 282.4722 ms.
- Forty focused tests pass. The final unrestricted regression passes all 476
  tests in 257.659 seconds; unrestricted execution is needed only for fake
  Ollama tests that bind a loopback port.
- JSON and whitespace checks pass, and every Python file remains at or below
  500 lines.

Rollback notes:

- Remove ArkTS operation summary extraction, candidate focusing, query-aware
  lineage seeding, structural source bonuses, and the two Commerce scenarios.
  Relearn affected ArkTS scopes to restore older generated summaries. No SQLite
  schema migration or durable memory rewrite is required.

## 2026-07-18 - Add sealed real-project validation and theory-grounded gates

What changed:

- Added canonical SHA-256 holdout sealing through the existing runtime facade.
  Sealing verifies source-reviewed cases, hidden Oracle fields, immutable
  revisions, fix commits, and declared files against the real Git diff. Pack
  loading rejects missing or modified required seals before evaluation.
- Added Context and Agent failure attribution for candidate generation,
  ranking, passage selection, graph structure, experience governance,
  abstention, compactness, Agent protocol, evaluation integrity, and Agent
  efficiency. Reports include method references, permitted repair layers,
  prohibited shortcuts, and the next validation boundary.
- Added ten sealed Jingmo cases, a separate three-case post-repair Jingmo pack,
  and two reserved unseen Gramony cases. The 15 source-reviewed sealed cases
  cover two real ArkTS repositories without changing the four-Skill surface.
- Added three independent Commerce development scenarios and bounded ArkTS
  member-operation indexing, explicit multi-type identity focusing,
  entity-role suppression, and query-focused file-anchor source windows.
  Candidate selection moved from the runtime facade into a dedicated module.
- Added cross-project Context history to `maintain-health`, grouped compactly
  by source project and clearly separating sealed from unsealed observations.
- Updated the system capability, Agent benchmark, runtime, and usage documents,
  and recorded an explicit release decision instead of claiming promotion.

Result:

- The development Context gate passes all 15 scenarios and 45 query variants.
  Anchor recall, primary recall, MRR, source-span recall, and wording stability
  are 1.0; average compact context is 956.4889 Tokens.
- The first sealed Jingmo observation passes 1/10. A new, non-overlapping
  post-repair pack passes 0/3 and remains immutable; its leading failure is
  ranking precision, followed by candidate generation and passage selection.
- The recorded Gramony Agent A/B has 18 complete observations across three
  cases and three paired trials. Result quality is stable, but Memory adds
  16.41% Token and 23.1% elapsed overhead and fails per-case efficiency checks.
  Quality, efficiency, and promotion gates therefore remain failed.
- Seal tampering, source audit, failure analysis, Context governance, ArkTS
  retrieval, and source-window focused tests pass. The unrestricted full suite
  passes all 491 tests in 292.902 seconds; loopback permission is required only
  by the fake Ollama HTTP server tests. JSON, compile, whitespace, and line-
  count audits pass, and every Python source/test file is at most 500 lines.

Rollback notes:

- Remove the seal/failure-analysis modules, new evaluation artifacts, cross-
  project governance summary, and query-selection refinements. No SQLite schema
  migration, fifth Skill, daemon, vector store, or durable user memory rewrite
  was introduced.

## 2026-07-18 - Add large-repository fielded retrieval and consume Gramony holdout

What changed:

- Extracted candidate generation from `query_collect.py` into a replaceable
  SQLite recall port with bounded broad, conjunctive, and per-concept FTS5
  lanes. Extra lanes activate only when broad recall is saturated.
- Added full-query recall and stage audits, query-focus coverage reranking, and
  evidence-backed symbol-range-first source passage selection. Compact context
  remains unchanged and under the existing Token budget.
- Added independent noisy retrieval fixtures that reproduce multi-owner recall,
  ranking interference, and whole-file passage drift without using holdout
  Oracles.
- Consumed the two sealed Gramony cases once and stored an immutable summary.
  Updated the release decision instead of retuning the consumed pack.

Result:

- Focused retrieval, graph, audit, and performance regressions pass 39 tests.
- The development Context gate remains 45/45 with anchor recall 1.0, MRR
  0.9722, source-span recall 1.0, average context 957.8 Tokens, and average
  query time 351.1111 ms.
- The sealed Gramony observation passes 0/2. Anchor recall and MRR are 0.75,
  precision is 0.25, source-span recall is 0.0, and average context is 1,287.5
  Tokens. Promotion remains denied; the pack is now immutable and unavailable
  for tuning.
- Full discovery ran 496 tests: 494 passed in the restricted sandbox, while two
  fake Ollama tests could not bind `127.0.0.1`; both loopback tests passed when
  rerun with local socket permission. JSON, compile, whitespace, and line-count
  checks pass across 263 Python files, with no file above 500 lines.

Rollback notes:

- Remove the candidate recall/ranking modules and query audit integration, then
  restore direct broad FTS recall and global source-window selection. No schema
  migration or durable user-memory rewrite is required. Evaluation observations
  must remain retained even if the implementation is rolled back.

## 2026-07-19 - Add coverage-first excerpts and consume Bookkeep holdout

What changed:

- Added independent regressions for late query-owner terms, dominant shared
  owners, executable ArkTS passage focus, and three-anchor excerpt coverage.
- Changed compact source budgeting so three primary anchors retain small source
  windows before one candidate consumes the available excerpt budget.
- Reviewed and sealed three real Bookkeep fixes from immutable Git history,
  including one noisy commit whose expected file remains symptom-scoped.
- Stored the one-time external result and updated the three-project release
  decision without changing the consumed pack or its thresholds.

Result:

- The 15-scenario/45-variant development Context gate passes 45/45 with anchor
  recall 1.0, MRR 0.9676, source-span recall 1.0, and average context 943.5111
  Tokens.
- The sealed Bookkeep observation passes 0/3. No code anchor is returned, so
  anchor recall, MRR, and source-span recall are 0.0; average context is 388
  Tokens. The root failure is candidate generation across abstract English
  symptoms, Chinese domain vocabulary, generic page names, and ArkTS syntax.
- Sealed inventory now contains 18 cases across Jingmo, Gramony, and Bookkeep.
  Promotion remains denied and all consumed holdouts remain immutable.
- Full discovery ran 500 tests: 498 passed in the restricted sandbox and the
  two fake Ollama loopback tests passed when rerun with local socket permission.
  JSON, compile, whitespace, and 500-line audits all pass.
- Post-run audit found that the sealed pack labels the source branch as
  `master`, while Bookkeep remote HEAD is `main`. Full audited revisions drove
  source preparation, so the observation is valid; the consumed pack remains
  unchanged and the discrepancy is recorded in its result summary.

Rollback notes:

- Revert the minimum excerpt allocation and its regression if compact source
  quality regresses. Retain all sealed packs and immutable observations even if
  retrieval code is rolled back; no schema migration is involved.

## 2026-07-19 - Add structural symptom recall and consume Home Assistant holdout

What changed:

- Added a language-neutral behavior concept module for abstract scrolling,
  reactive aggregate refresh, and visual overlap symptoms. The bounded
  `sqlite_fts5_fielded/v2` structural lane applies only to code-file summaries
  and exposes its term count in full query audit.
- Indexed ArkTS `forEach` behavior and added structural marker coverage to code
  focusing, suppressing stronger lexical noise when a candidate lacks the
  behavior requested by the symptom.
- Preserved two alternate causal paths under tight compact budgets by dropping
  one redundant non-emitter excerpt before collapsing path diversity. Code
  anchors and common emitter source evidence remain available.
- Added three independent development scenarios with nine wording variants.
  Reviewed, source-audited, and sealed four real Home Assistant fixes, executed
  the pack exactly once, and retained the failed observation unchanged.
- Updated runtime, usage, benchmark, capability, plan, and release-governance
  documentation. The public four-Skill surface and SQLite source of truth are
  unchanged.

Result:

- The development Context gate passes 54/54 variants across 18 scenarios with
  anchor recall 1.0, MRR 0.9741, source-span recall 1.0, average compact context
  893.5556 Tokens, and average query time 327.3704 ms.
- The sealed Home Assistant observation passes 0/4. The layout owner is found
  at rank one with the required source span but fails precision; lifecycle,
  callback-containment, and authoritative-refresh owners are not recalled.
  Aggregate anchor recall and MRR are 0.25. The pack is consumed and cannot be
  rerun for tuning.
- Sealed inventory now contains 22 cases across four real ArkTS projects.
  Promotion remains denied because real-project Context generalization and the
  recorded Agent efficiency gate do not both pass.
- Full discovery ran 505 tests: 503 passed in the restricted sandbox, while the
  two fake Ollama tests could not bind `127.0.0.1`; both passed with local
  loopback permission. JSON, compile, whitespace, and line-count audits pass,
  and every Python source/test file remains at most 500 lines.

Rollback notes:

- Remove the structural recall/focus modules and their independent development
  fixtures, restore the previous recall provider version, and remove the path
  diversity excerpt preference if regressions appear. Retain all sealed packs
  and immutable result summaries; no SQLite migration or durable memory rewrite
  was introduced.

## 2026-07-19 - Add mechanism-aware recall and consume Aigis holdout

What changed:

- Added a conservative ArkTS behavior-marker extractor for existing fallback,
  repository, callback, deserialization, action, lifecycle, state-write, and
  async mechanisms. Markers are persisted in file summaries and never infer a
  missing repair.
- Added language-neutral reusable-spacing, fallback-recovery,
  callback-containment, and post-action-refresh concepts. Structural focusing
  now keeps a bounded minimal cover of complementary marker evidence.
- Added exact high-entropy identifier abstention so generic topic overlap cannot
  substitute for an unknown identifier without direct or graph support.
- Changed `eval-context-capability` to run all scenarios by default, while an
  explicit limit remains available for a deliberately bounded selection.
- Added four independent development scenarios and twelve wording variants,
  then reviewed, sealed, and executed four real Aigis cases exactly once.
  Updated the five-project release decision without tuning the consumed pack.

Result:

- The development Context gate passes 66/66 variants across 22 scenarios with
  anchor and primary-anchor recall 1.0, MRR 0.9883, source-span recall 1.0,
  average compact context 854.0152 Tokens, and average query time 383.6212 ms.
- The sealed Aigis observation passes 1/4. Aggregate anchor recall is 0.75,
  precision 0.25, MRR 0.625, source-span recall 0.5, and average context
  1,194.25 Tokens. The pack is consumed and unavailable for tuning.
- Sealed inventory now contains 26 cases across five real ArkTS projects.
  Promotion remains denied because external Context generalization and the
  recorded Agent efficiency gate do not both pass.
- Full discovery ran 515 tests: 513 passed in the restricted sandbox; the two
  fake Ollama tests blocked only by loopback binding both passed with local
  socket permission. JSON, compile, whitespace, and line-count audits pass,
  with every Python source/test file at most 500 lines.

Rollback notes:

- Remove the mechanism extractor, concept mappings, minimal structural cover,
  and opaque-identifier guard together if recall regresses; restore the prior
  evaluation default only if callers explicitly require partial packs. Retain
  the sealed Aigis pack and immutable observation under any rollback. No SQLite
  migration or durable user-memory rewrite was introduced.

## 2026-07-19 - Add event and persistence recall and consume sixth holdout

What changed:

- Added conservative ArkTS markers for event-to-state handoff, validation
  early-stop ownership, explicit persistence writes, and paired counter/time
  commits. Added language-neutral query concepts for the same mechanisms.
- Kept directly supported structural owners eligible when they also carry graph
  provenance, without promoting generic graph neighbors as direct evidence.
- Added four independent development scenarios and twelve query variants for
  state handoff, validation, persistence, and combined-owner precision.
- Reviewed and sealed four real harmonyos-games fixes, executed the pack once,
  stored the immutable result, and updated the six-project release decision.

Result:

- The development Context gate passes 78/78 variants across 26 scenarios with
  anchor and primary-anchor recall 1.0, MRR 0.9928, source-span recall 1.0,
  average compact context 822.3077 Tokens, and average query time 320.6154 ms.
- The harmonyos-games observation passes 1/4. Aggregate anchor recall is 0.75,
  precision 0.375, MRR 0.75, source-span recall 0.75, and average context is
  1,112 Tokens. Two expected owners rank first but fail precision; one gesture
  state owner is not recalled.
- Sealed inventory now contains 30 cases across six real ArkTS projects.
  Promotion remains denied. The consumed pack cannot be rerun or used to tune
  ranking, query wording, thresholds, or Oracles.
- Full discovery ran 520 tests: 518 passed in the restricted sandbox, and the
  two fake Ollama tests blocked only by loopback binding both passed with local
  socket permission. All eval JSON, compile, whitespace, and 500-line audits
  pass.

Rollback notes:

- Remove the four new mechanism markers, query concepts, selection adjustment,
  and independent fixtures together if regressions appear. Retain every sealed
  pack and immutable observation. No SQLite migration or durable memory rewrite
  was introduced.

## 2026-07-19 - Add gesture precision and consume JustPDF holdout

What changed:

- Added conservative ArkTS markers for gesture callbacks and indexed collection
  writes, and recognized `restore` as an existing lifecycle operation.
- Added language-neutral concepts for gesture-state symptoms, adjacent
  collection mutation, and lifecycle-persistence ownership without changing
  global ranking thresholds.
- Added three independent development scenarios and nine wording variants with
  explicit partial-owner noise and method-level source-span Oracles.
- Reviewed four single-owner fixes across JustPDF history, source-audited and
  sealed the pack, executed it once, and stored the immutable result.

Result:

- The development Context gate passes 87/87 variants across 29 scenarios with
  anchor and primary-anchor recall 1.0, MRR 0.9936, source-span recall 1.0,
  average compact context 801.7011 Tokens, and average query time 312.931 ms.
- The JustPDF observation passes 1/4. Aggregate anchor recall is 0.75,
  precision 0.3125, MRR 0.625, source-span recall 0.25, and average context is
  1,150.5 Tokens. One async owner is absent; two recalled owners miss their
  audited method windows, and touch arbitration retains excess neighbors.
- Sealed inventory now contains 34 cases across seven real ArkTS projects.
  Promotion remains denied and the consumed pack cannot be rerun or tuned.
- Full discovery ran 525 tests: 523 passed in the restricted sandbox, and the
  two fake Ollama tests blocked only by loopback binding both passed with local
  socket permission. All eval JSON, compile, whitespace, and 500-line audits
  pass.

Rollback notes:

- Remove the gesture/collection markers, lifecycle restore term, query concepts,
  independent fixtures, and their tests together if regressions appear. Retain
  every sealed pack and immutable observation. No SQLite migration or durable
  memory rewrite was introduced.

## 2026-07-19 - Add async method focus and consume FinVideo holdout

What changed:

- Added language-neutral query concepts for asynchronous state ordering and
  touch-state arbitration while reusing conservative, source-checkable ArkTS
  behavior markers.
- Made English concept triggers word-aware, preventing substrings such as
  `interaction` from activating the unrelated `action` mechanism.
- Preferred complete multi-mechanism owners over generic operation-name
  matches, while retaining explicit file and symbol identity precedence.
- Added language-adapter-backed callable ranges for source excerpt selection,
  preserved mechanism-complete methods before lexical fallback, and reduced
  repeated source reads to one scan per file.
- Added two independent development scenarios and six wording variants, then
  reviewed and sealed four FinVideo fixes, executed that pack exactly once,
  and stored its immutable observation.

Result:

- The development Context gate passes 93/93 variants across 31 scenarios with
  anchor and primary-anchor recall 1.0, MRR 0.994, source-span recall 1.0,
  average compact context 789.9462 Tokens, and average query time 435.5699 ms.
- The FinVideo observation passes 0/4. Aggregate anchor recall is 0.75,
  precision 0.3958, MRR 0.75, source-span recall 0.25, and average context is
  948.5 Tokens. Nested ArkUI callbacks and Builder ranges remain weak,
  conditional folder loading misses its owner, and two cases retain excess
  neighbors.
- Sealed inventory now contains 38 cases across eight real ArkTS projects.
  Promotion remains denied and the consumed pack cannot be rerun or tuned.
- Full discovery ran 529 tests: 527 passed in the restricted sandbox, and the
  two fake Ollama tests blocked only by loopback binding passed with local
  socket permission. All 44 eval JSON files, compile, whitespace, and 500-line
  audits pass; the largest Python source/test file is 496 lines.

Rollback notes:

- Remove the async/touch concepts, word-aware trigger matching, combination
  precedence, callable-range focus, independent fixtures, and their tests
  together if regressions appear. Retain every sealed pack and immutable
  observation. No SQLite migration or durable memory rewrite was introduced.

## 2026-07-19 - Add ArkTS DSL focus and consume Wechat holdout

What changed:

- Added conservative ArkTS markers for indexed touch access, conditional data
  sources, lifecycle callback cleanup, horizontal and vertical layout axes, and
  async request ordering guards.
- Added a language-adapter source range layer that combines ECMA callables with
  nested chained ArkUI arrow callbacks, allowing callback and Builder windows
  to compete independently.
- Added bounded component identifier terms and raw-query-only explicit path
  protection. Semantic expansions, negative references, and behavior-only
  queries cannot pin unrelated paths.
- Added four independent development scenarios and twelve wording variants,
  then reviewed and sealed four Wechat_HarmonyOS fixes, executed the pack
  exactly once, and stored its immutable observation.

Result:

- The development Context gate passes 105/105 variants across 35 scenarios
  with anchor and primary-anchor recall 1.0, MRR 0.9896, source-span recall
  1.0, average compact context 764.5714 Tokens, and average query time 520 ms.
- The Wechat observation passes 1/4. Aggregate anchor recall is 0.75,
  precision 0.25, MRR 0.5833, source-span recall 0.25, and average context is
  1,138.5 Tokens. Reusable toolbar recall, audio lifecycle passage precision,
  and keyboard/back event ownership remain external generalization gaps.
- Sealed inventory now contains 42 cases across nine real ArkTS projects.
  Promotion remains denied and the consumed pack cannot be rerun or tuned.
- Focused ArkTS retrieval and source-range regression passes 78/78 tests. Full
  discovery ran 542 tests: 540 passed in the restricted sandbox, and the two
  fake Ollama tests blocked only by loopback binding passed with local socket
  permission. All 46 eval JSON files, compile, whitespace, seal consistency,
  and 500-line audits pass; the largest Python source/test file is 496 lines.

Rollback notes:

- Remove the new marker concepts, ArkTS range adapter, component terms,
  explicit-path safeguards, independent fixtures, and their tests together if
  regressions appear. Retain every sealed pack and immutable observation. No
  SQLite migration or durable memory rewrite was introduced.

## 2026-07-19 - Add role/boundary recall and consume Siyuan holdout

What changed:

- Added conservative ArkTS markers and language-neutral query concepts for
  reusable Toolbar roles, media resource acquire/release ownership, and
  keyboard/back event boundaries. Business ActionBar components remain
  excluded from the reusable Toolbar role.
- Kept a bounded structural FTS lane available when broad recall saturates and
  removed expansion-only tails under two strong identity paths, while
  preserving component-flow lineage.
- Added three independent development scenarios and nine wording variants for
  toolbar ownership, resource shutdown, and key-event precision.
- Reviewed four single-owner Siyuan Harmony fixes, source-audited and sealed
  the pack, executed it exactly once, and stored the immutable result.

Result:

- The development Context gate passes 114/114 variants across 38 scenarios
  with anchor and primary-anchor recall 1.0, MRR 0.9905, source-span recall
  1.0, average compact context 746.8684 Tokens, and average query time
  556.5351 ms.
- The Siyuan observation passes 0/4. Aggregate anchor recall is 0.75,
  precision 0.2708, MRR 0.4583, source-span recall 0.0, and average context is
  1,074.25 Tokens. Archive I/O ownership is absent; three other owners are
  noisy or late, and all four audited method windows are missed.
- Sealed inventory now contains 46 cases across ten real ArkTS projects.
  Promotion remains denied and the consumed pack cannot be rerun or tuned.
- Focused mechanism, recall, precision, and source-focus regression passes
  43/43 tests. Full discovery ran 551 tests: 549 passed in the restricted
  sandbox, and the two fake Ollama tests blocked only by loopback binding both
  passed with local socket permission. All 48 eval JSON files, compile,
  whitespace, seal consistency, and 500-line audits pass; the largest Python
  source/test file is 496 lines.

Rollback notes:

- Remove the new role/boundary markers, query concepts, structural-lane
  scheduling, identity-tail focus, independent fixtures, and their tests
  together if regressions appear. Retain every sealed pack and immutable
  observation. No SQLite migration or durable memory rewrite was introduced.

## 2026-07-19 - Add I/O/conversion recall and consume Termony holdout

What changed:

- Added conservative ArkTS behavior markers and language-neutral concepts for
  archive asset I/O, collection aggregation, keyboard/focus state, and native
  color conversion.
- Merged query-supported callable ranges ahead of stored source ranges so a
  matching implementation method remains visible without discarding existing
  graph evidence.
- Tightened reusable-spacing expansion to explicit margin and padding terms
  after an independent collection fixture exposed a generic shared-owner false
  positive.
- Added four independent development scenarios and twelve wording variants,
  then reviewed and sealed four Termony fixes, executed that pack exactly once,
  and stored its immutable observation.

Result:

- The development Context gate passes 126/126 variants across 42 scenarios
  with anchor and primary-anchor recall 1.0, oracle precision 0.9309, MRR
  0.9915, source-span recall 1.0, average compact context 726.373 Tokens, and
  average query time 994.9683 ms.
- The Termony observation passes 1/4. Aggregate anchor recall, primary recall,
  precision, and MRR are 0.5; source-span recall is 0.25 and average context is
  721.25 Tokens. Clipboard extraction and sequential permission owners are not
  recalled, empty-result scrolling recalls the owner but misses its method
  window, and touch-coordinate conversion passes completely.
- Sealed inventory now contains 50 cases across eleven real ArkTS projects.
  Promotion remains denied and the consumed pack cannot be rerun or tuned.
- Focused marker, recall, precision, source-focus, and diversity regression
  passes 75/75 tests. Full discovery ran 563 tests: 561 passed in the restricted
  sandbox, and the two fake Ollama tests blocked only by loopback binding passed
  in the focused 3/3 local-socket suite. All 50 eval JSON files, compile,
  whitespace, seal consistency, and 500-line audits pass; the largest Python
  source/test file is 496 lines.

Rollback notes:

- Remove this stage's behavior markers, concepts, callable-range merge,
  independent fixtures, and their tests together if regressions appear. Retain
  every sealed pack and immutable observation. No SQLite migration or durable
  memory rewrite was introduced.

## 2026-07-19 - Add behavior-owner recall and consume ClearChat holdout

What changed:

- Added conservative ArkTS markers and language-neutral query concepts for
  clipboard content reads, permission request/result guards, process-output
  read loops, and runtime-capability probes.
- Removed explicit negative clauses before behavior expansion, suppressed
  generic identity-only log emitters for structural queries without active
  path reconstruction, and preserved exact log and path-led retrieval.
- Fixed ArkTS callback range detection so a later arrow expression cannot be
  attached to an already closed call.
- Added four independent development scenarios and twelve wording variants,
  then reviewed and sealed four ClearChat fixes, executed that pack exactly
  once, and stored its immutable observation.

Result:

- The development Context gate passes 138/138 variants across 46 scenarios
  with anchor and primary-anchor recall 1.0, oracle precision 0.9412, MRR
  0.9922, source-span recall 1.0, average compact context 714.0 Tokens, and
  average query time 1,195.2826 ms.
- The ClearChat observation passes 0/4. Aggregate anchor and primary recall are
  0.5, precision is 0.1875, MRR is 0.375, source-span recall is 0.25, and
  average context is 1,225.25 Tokens. Cache ownership passes recall and span
  gates but broad neighbors reduce precision; streaming persistence windows,
  initialization timeout ownership, and WebView security ownership remain
  external generalization gaps.
- Sealed inventory now contains 54 cases across twelve real ArkTS projects.
  Promotion remains denied and the consumed pack cannot be rerun or tuned.
- Focused marker, recall, precision, source-focus, diversity, UI-context, and
  source-excerpt regression passes 96/96 tests. Full discovery ran 571 tests:
  569 passed in the restricted sandbox, and the two fake Ollama tests blocked
  only by loopback binding passed in the focused 3/3 local-socket suite. All 52
  eval JSON files, compile, whitespace, seal consistency, and 500-line audits
  pass; the largest Python source/test file is 497 lines.

Rollback notes:

- Remove this stage's behavior markers, concepts, structural log suppression,
  callback-range fix, independent fixtures, and their tests together if
  regressions appear. Retain every sealed pack and immutable observation. No
  SQLite migration or durable memory rewrite was introduced.

## 2026-07-19 - Add async/security owners and consume ccplayer holdout

What changed:

- Added conservative ArkTS markers and language-neutral query concepts for
  serialized persistence, timeout cancellation, WebView access and URL-scheme
  policy, and bounded-cache eviction.
- Required UI context for ambiguous visual-cover terms so data overwrites do
  not activate overlay retrieval.
- Added four independent development scenarios and twelve wording variants,
  then reviewed and sealed four ccplayer fixes, executed that pack exactly
  once, and stored its immutable observation.

Result:

- The development Context gate passes 150/150 variants across 50 scenarios
  with anchor and primary-anchor recall 1.0, oracle precision 0.945, MRR
  0.9929, source-span recall 1.0, average compact context 711.4133 Tokens,
  average memory preparation time 3,654.1933 ms, and average query time
  1,466.8867 ms.
- The ccplayer observation passes 1/4. Aggregate anchor recall is 0.5, primary
  recall is 0.25, precision and MRR are 0.3125, source-span recall is 0.125,
  and average context is 1,136.5 Tokens. Surface callback ordering passes;
  idempotent release ownership, source-reset lifecycle state, and prepared
  command eligibility remain external generalization gaps.
- Sealed inventory now contains 58 cases across thirteen real ArkTS projects
  and fourteen immutable packs. Promotion remains denied and the consumed
  pack cannot be rerun or tuned.
- Focused marker, recall, precision, source-focus, diversity, UI-context, and
  source-excerpt regression passes 105/105 tests. Full discovery ran 580
  tests: 577 passed in the restricted sandbox; the fingerprint-policy failure
  was fixed and verified by a focused 10/10 run, while the two fake Ollama
  tests blocked only by loopback binding passed in the focused 3/3
  local-socket suite. All 54 eval JSON files, compile, whitespace, seal
  consistency, and 500-line audits pass; the largest Python source/test file
  is 497 lines.

Rollback notes:

- Remove this stage's behavior markers, concepts, visual-cover
  disambiguation, independent fixtures, and their tests together if
  regressions appear. Retain every sealed pack and immutable observation. No
  SQLite migration or durable memory rewrite was introduced.

## 2026-07-20 - Add freshness-first incremental code index generations

What changed:

- Bound learned code files, symbols, and log statements to SHA-256 source
  digests and atomic index generations, with per-project active index state.
- Made refresh replacement and removed-file retirement one SQLite transaction;
  changed-only refresh advances the generation without rebuilding unchanged
  files or overwriting governed business semantics and experience.
- Added candidate-bounded freshness validation to code/log recall, graph
  expansion, and independently reconstructed paths. Changed or deleted source
  anchors are blocked, while digestless legacy rows remain explicitly
  `unverified` until refreshed.
- Exposed detailed `source_freshness` in full Context, a status-driven compact
  projection in compact Context, and digest coverage plus generation health in
  `maintain-health`.
- Documented the four-phase long-term design using content-addressed Git
  objects, Skyframe invalidation, Tree-sitter incremental parsing, SCIP source
  ranges, and SQLite snapshot isolation as foundations.

Result:

- Freshness, external-source, generation, deletion, changed-only refresh,
  legacy compatibility, path-only validation, and health coverage pass 8/8.
- Query/Context regression passes 52/52 and log-anchored path regression
  passes 12/12; the earlier broad focused suite passed 93/93.
- The development Context capability gate passes 150/150 variants across 50
  scenarios with anchor and primary recall 1.0, oracle precision 0.945, MRR
  0.9929, and source-span recall 1.0. A later 15-query compact sample also
  passes within the 1,500-token budget; its timing was excluded because the
  host was under abnormal load.
- Full discovery ran 587 tests: 585 passed in the restricted sandbox, and the
  two loopback-bind failures passed in the focused 3/3 local-socket suite.
  Compile, all 54 eval JSON files, whitespace, and 500-line audits pass; the
  largest Python source file is 499 lines.

Rollback notes:

- Remove `code_index_state`, the three derived-row digest/generation columns,
  freshness filters, and Context projections together. Existing nullable
  columns preserve legacy archive readability; no experience, semantic fact,
  reflection, or episode lifecycle was changed. Phases 2-4 remain future work.

## 2026-07-20 - Add Scope-first Git incremental refresh

What changed:

- Added a provider-neutral `ScopeChangeProvider` contract with `git/v1` and
  `snapshot/v1` implementations. Git compares each persisted learn Scope's
  baseline directly with the current worktree and never uses repository-wide
  changes as the business boundary.
- Persisted per-Scope baseline revision, last checked revision, provider, and
  refresh state. Multiple intermediate commits collapse into one net change;
  SHA-256 snapshots remain authoritative for actual add/change/remove drift.
- Applied exact learned files to entry Scopes, subtrees to path Scopes, and the
  repository root only to explicit project Scopes. Entry changes recompute the
  bounded import closure; external source roots inside a larger Git repository
  keep source-relative paths.
- Included untracked files inside the Scope and retained digest checks for
  previously learned ignored files. Missing baselines, non-Git roots, oversized
  entry pathspecs, and Git failures fall back to a Scope-local snapshot scan.
- Added a 200-relevant-file incremental budget. Overflow performs no index
  writes and does not advance the baseline; `maintain-health` exposes the state,
  and an explicit full refresh by Scope id restores `current`.
- Reused one full Scope scan for both snapshot and write selection, avoiding a
  duplicate directory traversal introduced during the first implementation.

Result:

- Seven Git Scope cases pass: unrelated-team noise isolation, multi-commit
  coalescing, outside-only checkpoint advancement, legacy fallback, entry
  closure replacement, nested external source roots, ignored-file digest
  fallback, and overflow recovery are covered across the suite.
- The final freshness/refresh focus passes 17/17 and the broader learning,
  governance, and migration focus passes 51/51.
- Full discovery ran 595 tests: 593 passed in the restricted sandbox, and the
  two loopback-bind failures passed in the focused 3/3 local-socket suite.
  Compile, all 54 eval JSON files, whitespace, and 500-line audits pass.

Rollback notes:

- Remove the Scope checkpoint columns, `scope_changes.py`, changed-only Provider
  integration, overflow health state, and related tests together. Existing
  `file_snapshot` remains sufficient for the prior full Scope fallback, and no
  semantic facts, experiences, reflections, or episodes are rewritten.

## 2026-07-20 - Observe learned Scope boundary dependencies

What changed:

- Added `scope_boundary_dependencies` for resolved in-project imports outside a
  learned Scope. The registry retains consumer/dependency identity, content
  digest, extractor-level symbol-surface digest, status, and audit timestamps
  without learning or indexing the dependency file.
- Extended Scope change providers to classify normal and boundary candidates
  separately. Git unions exact registered dependency paths into change
  discovery, while refresh writes remain limited to learned Scope files.
- Reported bounded `boundary_changes` with affected consumers, missing state,
  content drift, and structural-surface drift. Function-body edits retain the
  same surface digest; symbol shape changes do not.
- Added `boundary_drift` to relevant Context freshness and governance health.
  The warning preserves fresh learned anchors, does not infer impact or expand
  retrieval, and clears only after a reviewed full refresh accepts the current
  boundary baseline.
- Documented the boundary protocol, schema, Agent reasoning boundary, user
  workflow, and remaining compiler-exact/reverse-dependent follow-up work.

Result:

- Boundary behavior and structural digest tests pass 2/2. The combined refresh,
  provider, freshness, query, migration, and governance focus passes 53/53;
  log-anchored path regression passes 12/12.
- Full discovery ran 597 tests: 595 passed in the restricted sandbox, and the
  only two loopback-bind errors passed in the focused 3/3 local-socket suite.
- Compile, whitespace, and the 500-line gate pass. New runtime modules are 196,
  264, and 438 lines; the largest existing Python source remains within the
  enforced limit.

Rollback notes:

- Remove `scope_boundary_dependencies`, `scope_boundaries.py`, boundary
  candidate classification, `boundary_drift` projections, and their tests
  together. This returns changed-only maintenance to strict learned-Scope
  observation; no learned code row or governed memory record requires data
  conversion.

## 2026-07-20 - Establish a million-entity query baseline

What changed:

- Added isolated `eval-scale` profiles for 100,000/300,000 and
  1,000,000/3,000,000 searchable-entity/active-edge combinations. The runner
  uses the production SQLite schema, FTS5 triggers, WAL, candidate recall, and
  graph indexes without writing synthetic rows to project memory.
- Added warm p95 gates for candidate hit/miss, generic method-term abstention,
  exact log FTS, qualified and file-local method lookup, and active incoming and
  outgoing graph edges. Query-plan gates require accepted composite indexes.
- Added a direct `(project_id, qualified_name)` symbol index after the initial
  query-plan audit exposed the previous file-prefixed index limitation.
- Persisted bounded CamelCase identifier components in symbol summaries so
  business terms reach methods through FTS5. Generic method/class/function/
  symbol-only queries now abstain, and code-table `%LIKE%` compatibility
  fallback is skipped above a 50,000-row high watermark.
- Added the release workflow, scale model, SLOs, isolation contract, and actual
  before/after measurements to architecture and usage documentation.

Result:

- The first million run failed: candidate hit 12,089 ms, miss 10,952 ms, and
  saturated method FTS 11,317 ms p95, while exact indexed lookups stayed below
  0.04 ms. This isolated the failure to lexical fallback and high-frequency FTS.
- The repaired million run passes with exactly 1,000,000 searchable entities,
  3,000,000 active edges, and a 2,008.3 MiB temporary database. Candidate hit is
  72.095 ms p95, miss 24.571 ms, generic abstention 0.093 ms, exact log FTS
  0.265 ms, and indexed symbol/graph lookups at or below 0.024 ms.
- The optimized 100,000/300,000 profile also passes: candidate hit is 10.459 ms
  p95 and miss 17.621 ms. Scale and focused query/learning/Context regression
  pass, including the log-anchored path suite.
- Full discovery ran 602 tests: 600 passed in the restricted sandbox, and the
  only two loopback-bind errors passed in the focused 3/3 local-socket suite.
  Compile, whitespace, 54 eval JSON files, and the 500-line gate pass.

Rollback notes:

- Remove `eval-scale`, `scale_benchmark.py`, the direct qualified-name index,
  identifier-term suffixes, and scale-bounded fallback together. Reverting the
  fallback alone restores multi-second full scans at method-level scale; retain
  the before/after report when evaluating an alternative tokenizer.

## 2026-07-20 - Gate Git incremental maintenance at million scale

What changed:

- Extended both `eval-scale` profiles with four production-path maintenance
  workloads: no change, committed Scope-external noise, one changed 20-method
  file, and one changed 500-method file. Every sample uses a real temporary Git
  repository, persisted Scope checkpoint, `git/v1`, FTS triggers, graph rebuild,
  semantic indexing, and atomic generation activation.
- Added bounded phase timings to code-index writes so extraction, Scope load,
  invalidation, insertion, graph rebuild, summarization, and commit costs can be
  separated without a benchmark-only refresh implementation.
- Replaced scoped graph rebuild's all-project file scan with a bounded candidate
  loader. It combines scoped files, referenced-symbol owners, exact imports and
  routes, module markers, and test basename candidates retrieved through the
  existing `code_file_fts` path index. Full graph repair remains all-file.
- Added a regression proving partial relearn restores same-module `tested_by`
  relations while excluding a same-name production file outside that module.

Result:

- Initial million baseline failed: the 20-method refresh was 4,428.580 ms p95,
  including 4,071.153 ms in graph rebuild. Profiling traced the fixed cost to
  repeated Python path parsing while pairing tests across all 50,000 files.
- Final million run passes all gates with 1,000,000 searchable entities,
  3,000,000 active edges, and a 2,113.0 MiB database. No-change is 90.221 ms,
  Scope-external is 89.841 ms, 20 methods is 452.654 ms, and 500 methods is
  1,685.729 ms p95. The 20-method graph phase is 87.627 ms.
- Query performance remains stable: candidate hit is 72.075 ms p95, miss is
  29.478 ms, exact log FTS is 0.174 ms, and indexed symbol/graph lookups are at
  or below 0.025 ms.
- Full discovery ran 603 tests: 601 passed in the restricted sandbox, and the
  only two loopback-bind errors passed in the focused 3/3 local-socket suite.
  Compile, whitespace, 54 eval JSON files, and the 500-line gate pass.

Rollback notes:

- Remove `scale_maintenance.py`, maintenance aggregation from `eval-scale`, and
  `code_wiki_edge_candidates.py` together. Restoring the previous scoped graph
  path preserves behavior but reintroduces project-size-linear test pairing and
  fails the million-scale 20-method SLO.

## 2026-07-20 - Generalize method-owner context without ranking interference

What changed:

- Added bounded source-derived `method_evidence` for semantic `function` and
  `method` entities. Extraction loads each source file once, stays inside the
  callable span, and retains at most 36 normalized member/call terms from at
  most 240 lines.
- Added a separate sparse `code_method_fts` table and versioned FTS migration.
  Empty class, field, and symbol evidence does not create an FTS row. Search
  rebuilds and SQLite triggers preserve the derived-index contract.
- Added a low-priority method recall lane with at most 24 candidates, two-term
  direct evidence qualification, and lane-conditioned scoring. Method body
  vocabulary cannot raise an ordinary symbol candidate's score.
- Added explicit result-exclusion query decomposition. `do not return` and
  `不要返回` clauses no longer drive candidate recall, scoring, graph expansion,
  or behavior expansion; useful compound domain stems remain while generic
  entity-role terms are removed.
- Added independent method-owner and query-language regressions, updated user
  and runtime documentation, and recorded the full architecture and rollback
  boundary in the staged implementation plan.

Result:

- The first broad-summary implementation regressed the context gate to 148/150.
  The isolated lane removed that interference. A frozen pre-change replay also
  exposed an existing 149/150 must-not precision defect; query decomposition
  repaired it without a case-specific rule.
- The final development context gate passes all 150 variants across 50 ArkTS
  scenarios. Average compact query latency is 441.1 ms including isolated case
  setup and freshness checks.
- CI scale passes at 100,000 searchable entities and 300,000 edges: candidate
  hit is 10.1 ms p95, 20-method refresh is 201.9 ms, and 500-method refresh is
  554.6 ms.
- Million scale passes at exactly 1,000,000 searchable entities and 3,000,000
  edges with a 2.064 GiB database. Candidate hit is 69.4 ms p95, 20-method
  refresh is 419.9 ms, and 500-method refresh is 1,681.3 ms. Database size stays
  below the prior 2.113 GiB baseline.
- Full discovery ran 610 tests: 608 passed in the restricted sandbox, and the
  only two loopback-bind errors passed in the focused 3/3 local-socket suite.
  Compile with a temporary bytecode cache, 54 eval JSON files, whitespace, and
  the 500-line gate pass.

Rollback notes:

- Remove `method_evidence`, `code_method_fts`, semantic body extraction, and the
  method recall lane together. Keep explicit result-exclusion decomposition as
  an independent fix for the reproduced pre-existing precision defect.

## 2026-07-20 - Harden method focus and run fourteenth-project observation

What changed:

- Added four independent ArkTS development scenarios for idempotent release,
  source-replacement state, prepared command eligibility, and implementation
  ownership over examples, each with three query variants.
- Restricted method evidence recall to bounded raw query terms and promoted
  method focus only under strong multi-term direct evidence without a competing
  exact, flow, multi-concept, or structural owner.
- Added explicit sample/example/demo result-role exclusion before final code
  selection and preserved ordinary role retrieval.
- Reviewed four real Wake-HarmonyOS fixes at immutable pre-fix revisions,
  verified every changed file, and sealed the pack with digest
  `0ca1a2810280a686a77587c8e98c884c373ffbf6c4e85e17aa9aa08a43612873`.

Result:

- The expanded development Context gate passes 162/162 variants across 54
  scenarios with 719.6111 average context Tokens and 441.5247 ms average query
  time including isolated setup and freshness checks.
- The new sealed project was executed exactly once and passed 1/4. Cross-page
  import completion and return ownership passed; command-owner precision,
  visual-state passage focus, and cross-layer error-contract recall remain the
  independent repair targets.
- Agent A/B was not run because the Context gate failed. The sealed inventory
  is now 14 projects and 62 cases; promotion remains denied.
- CI scale passes at 100,000 searchable entities and 300,000 edges. Candidate
  hit is 10.405 ms p95, the 20-method refresh is 204.952 ms, and the 500-method
  refresh is 564.104 ms.
- Full discovery ran 619 tests: 617 passed in the restricted sandbox, and the
  two loopback-bind errors passed in the focused 3/3 local-socket suite. Compile,
  56 eval JSON files, whitespace, and the 500-line gate pass.

Rollback notes:

- Revert method focus competition and explicit example-role filtering together
  with their independent fixtures if they introduce regressions. Never modify
  or rerun the consumed Wake-HarmonyOS pack; validate future repairs only with
  project-neutral development cases and a new sealed project.

## 2026-07-20 - Generalize contract ownership and run fifteenth-project observation

What changed:

- Added three independent ArkTS scenarios and nine query variants for UI command
  binding, comparison-target disclosure state, and cross-layer error return and
  presentation contracts.
- Added bounded executable-syntax markers for object callback bindings,
  chevron rotation/toggle state, caught-error return boundaries, and UI failure
  presentation boundaries.
- Split comparison clauses and explicit result exclusions from positive
  retrieval evidence while preserving `instead of` as faulty-behavior context.
- Separated direct path identity from semantic graph-path expansion. Added a
  tightly bounded lowerCamelCase method identity fallback without lowering the
  existing three-term method-focus threshold.
- Added focused query-language, marker, path-identity, method-focus, and recall
  regressions. All Python production and test files remain at or below 500
  lines.

Result:

- The development Context gate passes 171/171 variants across 57 scenarios.
  Anchor recall is 1.0, Oracle precision is 0.9604, MRR is 0.9938, source-span
  recall is 1.0, average compact context is 720.2281 Tokens, and average query
  time is 454.8889 ms.
- CI scale passes at 100,000 searchable entities and 300,000 edges. Candidate
  hit is 11.346 ms p95 and the 500-method refresh is 562.315 ms p95.
- Full discovery ran 633 tests: 630 passed, one new-file fingerprint failure
  was fixed and its focused policy/marker suite passed 5/5, and the two
  loopback-bind errors passed in the focused 3/3 authorized local-socket suite.
  Compile, 58 eval JSON files, whitespace, and the 500-line gate pass.
- Four real RayTV fixes were reviewed at immutable pre-fix revisions and sealed
  with digest
  `589240f57caefbf641a803e859a51635dd4dd0080f854bd412aa055c0d198a3f`.
  The pack was executed exactly once and passed 0/4. All expected files were
  recalled, but generated preview sources, alternate Python implementations,
  same-domain neighbors, and missed large-file passages kept the Context gate
  red. Agent A/B was not run.
- The sealed inventory is now 15 projects and 66 cases; promotion remains
  denied.

Rollback notes:

- Revert the three contract marker families, clause decomposition, and bounded
  focus changes with their development fixtures if an independent regression
  appears. Never modify or rerun the consumed RayTV pack.

## 2026-07-20 - Filter generated sources and tighten implementation context

What changed:

- Added a bounded source-path policy for generated preview/cache directories
  and an extensible explicit-language suffix registry.
- Applied generated-source filtering during learning and as a query-time
  fallback policy for archives created before the learning filter.
- Added guarded asynchronous action evidence so complete branch/state/async UI
  owners outrank same-domain thin service and repository methods.
- Added `omit/omitting` result-exclusion parsing and four independent ArkTS
  scenarios for canonical sources, language choice, owner precision, and a
  method window near the end of a 500-line file.

Result:

- The development Context gate passes 183/183 variants across 61 scenarios.
  Anchor recall and source-span recall are 1.0, Oracle precision is 0.9478, MRR
  is 0.9943, average compact context is 722.2951 Tokens, and average query time
  is 472.3005 ms.
- Full discovery ran 642 tests: 639 passed in the restricted sandbox, the
  fixture fingerprint failure was fixed and its focused 8-test suite passed,
  and both loopback-bind tests passed outside the sandbox.
- CI scale passes with 100,000 searchable entities and 300,000 edges. Candidate
  hit is 10.02 ms p95 and 500-method incremental refresh is 578.846 ms p95.
- Compile with a temporary bytecode cache, whitespace, JSON parsing, and the
  500-line Python gate pass. The large ArkTS fixture is exactly 500 lines.
- RayTV was not rerun. The sealed inventory remains 15 projects and 66 cases;
  promotion remains denied pending a new independent sealed observation.

## 2026-07-20 - Run sixteenth-project FlameChase observation

What changed:

- Reviewed three source-provable fixes from the previously unseen MPL-2.0
  FlameChase ArkTS project at their complete pre-fix revisions.
- Added and sealed diagnosis cases for custom-dialog close ownership, award
  preference-key restoration, and platform gating of a dark-mode control.
- Recorded the immutable Context observation without modifying retrieval logic
  or running Agent A/B.

Result:

- The sealed digest is
  `51784c6b80b0b0baf68e85136cec638f4351a0ea8f8325319165b9007dbe965c`.
  The pack was executed exactly once and passed 0/3.
- Aggregate anchor recall is 0.6667, Oracle precision is 0.25, MRR is 0.3333,
  source-span recall is 0.3333, average compact context is 1,109.3333 Tokens,
  and average query time is 641.6667 ms.
- Dialog close ownership was absent from candidates. Award restoration found
  the lifecycle owner but missed its audited passage and retained the display
  page. Platform gating found the expected page and exact passage but retained
  three unrelated neighbors.
- The sealed inventory is now 16 projects and 69 cases. Promotion remains
  denied, and the FlameChase pack must not be rerun or used for tuning.

## 2026-07-20 - Repair indirect owner and contract-focused context

What changed:

- Added three independent ArkTS scenarios for indirect dialog caller ownership,
  persistence-key restoration, and platform-sensitive UI controls. Their first
  baseline passed 2/9 variants.
- Added project-neutral structural markers for UI callback bindings,
  persistence reads, and platform-sensitive UI ownership.
- Added an explicit-intent, one-hop reverse caller lookup bounded to indirect
  roles and two callback-owning callers. Default graph depth is unchanged.
- Focused complete persistence/platform contract owners before generic method
  evidence, with regression tests for marker extraction and caller selection.
- Updated the release record and capability documentation without changing or
  rerunning any consumed sealed pack.

Result:

- The new scenarios pass 9/9 and seven related regression scenarios pass 21/21.
- The complete development Context gate passes 192/192 variants across 64
  scenarios. Anchor recall and source-span recall are 1.0, Oracle precision is
  0.9504, MRR is 0.9945, and average compact context is 721.5365 Tokens.
- Full discovery ran 646 tests. The restricted sandbox had only two expected
  loopback-bind permission errors; the complete loopback module passed 3/3
  outside the sandbox.
- CI scale passes with 100,000 searchable entities, 80,000 symbols, and 300,000
  graph edges. Candidate hit/miss p95 is 10.632/19.334 ms, single-file refresh
  p95 is 223.003 ms, and 500-method refresh p95 is 621.899 ms.
- Compile, whitespace, JSON, and the Python 500-line gate pass. Promotion stays
  denied until a new independently reviewed sealed project validates the repair.

## 2026-07-20 - Run seventeenth-project LinysBrowser observation

What changed:

- Selected the previously unseen MIT-licensed LinysBrowser_NEXT ArkTS browser
  and reviewed its complete Git history.
- Added three source-reviewed cases for location permission dialog cancellation,
  non-2-in-1 bottom avoid layout, and oversized saved WebState restoration.
- Verified all before/after revisions and changed files, then sealed the pack
  with digest
  `7b337f701b4545df9abec518af691936dee2264510cc799e6342791b41826ea3`.
- Executed the sealed Context gate exactly once and persisted the full result.

Result:

- The external Context gate passes 0/3. Aggregate anchor recall is 0.3333,
  primary recall is 0, Oracle precision is 0.0833, MRR is 0.0833, and source
  excerpt/span recall is 0.
- The location dialog owner is recalled only at rank 4 behind generic dialog
  infrastructure. The platform layout owner and saved-state restore owner are
  absent from candidate generation.
- Average compact context is 1,134 Tokens, average memory preparation is
  6,232 ms, and average query time is 1,000 ms.
- Agent A/B was not run. The sealed inventory is now 17 projects and 72 cases;
  promotion remains denied and this pack must not be rerun or used for tuning.

## 2026-07-20 - Add multi-stage retrieval rank fusion boundary

What changed:

- Documented the long-term multi-stage retrieval architecture from query intent
  through bounded retrievers, rank fusion, owner reranking, hierarchical source
  selection, and compact context budgeting.
- Added a storage-neutral `RankFusionPort` and deterministic weighted Reciprocal
  Rank Fusion over existing SQLite FTS5 candidate channels.
- Preserved channel-local BM25 semantics and the downstream owner reranker;
  full query audit now explains each candidate's fusion provenance.
- Added project-neutral fusion, compatibility, and query-audit tests without
  changing the four Skills, public `context` command, SQLite source of truth, or
  compact output budget.

Result:

- Focused retrieval tests pass 19/19; all query tests pass 62/62 and all context
  tests pass 39/39.
- The development Context gate remains 192/192 variants across 64 scenarios,
  with 1.0 anchor recall, 0.9945 MRR, 1.0 source-span recall, and 721.5365
  average compact Tokens.
- CI scale passes at 100,000 entities, 80,000 symbols, and 300,000 edges;
  candidate hit/miss p95 is 10.226/17.61 ms and 500-method refresh p95 is
  592.658 ms.
- Full discovery ran 650 tests. Only the two expected loopback-bind tests fail
  in the restricted sandbox, and their complete module passes 3/3 where binding
  is allowed. Compile and the Python 500-line gate pass.
- No consumed sealed pack was rerun or changed. Promotion remains denied;
  Phase 2 will add fielded passage retrieval and independent Recall@20 metrics.

## 2026-07-20 - Add shadow fielded passage retrieval

What changed:

- Added rebuildable source-derived file, symbol, and callable passages with
  separate identity, semantic, method-body, and string-key fields.
- Added six weighted SQLite FTS5 field channels behind nested RRF and exposed
  their provenance only in full-query development audit.
- Added candidate file Recall@20 to deterministic capability evaluation without
  a second Context construction or extra compact Agent output.
- Kept the Phase 1 candidate path in production after direct fielded serving
  exposed five owner-reranker regressions on the development suite.

Result:

- The complete development Context gate passes 192/192 variants across 64
  scenarios. Anchor recall is 1.0, Oracle precision 0.9504, MRR 0.9945,
  source-span recall 1.0, and average compact context 721.5365 Tokens.
- Shadow fielded candidate file Recall@20 is 0.8925, so the new retriever is not
  promoted until recall and downstream reranking are calibrated together.
- CI scale passes at 100,000 entities, 80,000 symbols, and 300,000 edges;
  candidate hit/miss p95 is 30.514/55.063 ms and 500-method refresh p95 is
  2,127.179 ms.
- Full discovery ran 656 tests. Only two expected restricted-sandbox loopback
  tests failed, and their module passed 3/3 with loopback access. Python source
  and tests remain within 500 lines.
- No consumed sealed pack was rerun or changed. Promotion remains denied; Phase
  3 owns semantic-adapter recall improvements before any serving switch.

## 2026-07-21 - Add language-neutral semantic mechanism evidence

What changed:

- Extended the existing semantic IR with optional bounded mechanism records for
  operations, guards, resource bounds, callbacks, platform predicates, and
  persistence reads/writes.
- Upgraded the built-in ArkTS and TypeScript static adapters to `1.1` without
  changing the external `semantic-index/v1` compatibility boundary.
- Persisted bounded mechanism metadata on symbols and added an independently
  weighted `semantic_mechanism_fts` passage lane under `fts-v4`.
- Added a rebuild migration for the derived passage schema and project-neutral
  IR, extraction, persistence, retrieval, and migration tests.

Result:

- The complete development Context gate passes 192/192 variants across 64
  scenarios. Anchor recall is 1.0, Oracle precision 0.9504, MRR 0.9945,
  source-span recall 1.0, and average compact context 721.5365 Tokens.
- Shadow candidate file Recall@20 improves from 0.8925 to 0.8980. The fielded
  candidate set remains non-serving because this is below promotion quality.
- CI scale passes at 100,000 entities, 80,000 symbols, and 300,000 edges;
  candidate hit/miss p95 is 10.956/20.271 ms and 500-method refresh p95 is
  812.501 ms.
- Query tests pass 62/62, Context tests 40/40, and focused semantic/passage tests
  33/33. Full discovery ran 660 tests; only two restricted-sandbox loopback
  errors remained, and that module passed 3/3 with loopback access.
- Compile, JSON, whitespace, and Python 500-line gates pass.
- No consumed sealed pack was rerun or changed. Promotion remains denied; Phase
  4 owns hierarchical localization and owner-reranker calibration.
