# Agent Memory SQLite Schema

SQLite is the source of truth for the MVP. Obsidian files are generated mirrors.

Storage lives in a memory home, defaulting to the current workspace `./.agent-memory`. Each `--project` archive gets an isolated store at `projects/<project_id>/`. `--memory-home` or `AGENT_MEMORY_HOME` can override the default.

## Project Identity

`project_id` is `sha256(abs_project_path)[:16]`, where the path is the archive/query context passed as `--project`, not necessarily the source tree being learned.

## Tables

- `projects`: one row per project path.
- `episodes`: task history and outcome summaries.
- `semantic_facts`: durable facts, preferences, and project knowledge.
- `reflections`: lessons, mistakes, and future rules.
- `code_files`: lightweight file-level wiki index. ArkTS summaries may include at most 12 source-ordered chained operation names for lexical behavior lookup; operation arguments and source bodies are not stored.
- `code_symbols`: lightweight symbol-level wiki index.
- `code_log_statements`: log, print, and console statements extracted from learned source files.
- `memory_edges`: lightweight relation edges between learned files, symbols, and log statements.
- `graph_runtime_state`: graph revision used to invalidate runtime graph-quality snapshots.
- `impact_feedback`: compact change/test outcome summaries used to improve later test recommendations.
- `design_outcomes`: bounded compact design-verification metrics used only for calibration.
- `learn_scopes`: persistent manifests for previously learned entry, path, or whole-project scopes.
- `query_misses`: failed retrieval attempts that may need later learning or reflection.
- `retrieval_feedback`: query-scoped relevance and trust observations for semantic facts and reflections.
- `experience_usage_events`: actual task-use observations for semantic facts and reflections.
- `semantic_conflicts`: durable review records for conflicting business summaries.
- `runtime_schema_versions`: component migration versions for FTS and derived edge metadata.

`code_files`, `code_symbols`, and `code_log_statements` also store Agent-authored business semantics:

- `business_summary`: concise business meaning of the file, method, field, route, resource, or log.
- `business_terms`: JSON array of searchable business terms grounded in code names, fields, routes, resources, logs, or UI wording.

FTS5 tables are generated search indexes maintained incrementally by SQLite triggers. Their schema version is stored in `runtime_schema_versions`; they are rebuilt only on first creation, version migration, or explicit `maintain-rebuild-derived --target search`. They are not a second source of truth.

`memory_edges` are generated from current code rows and source files. `maintain-rebuild-derived --target graph` may replace these derived rows while preserving code business fields and durable memory tables. Its graph audit reports relation counts, edges per node, and dominant-relation share so accidental edge amplification can be detected before the graph is trusted.

## Governance Fields

Phase 2 adds memory governance metadata while keeping SQLite as the source of truth:

- `status`: `active`, `stale`, `merged`, `archived`, or `rejected`.
- `scope`: where a fact or reflection applies.
- `evidence`: source file, episode, user instruction, or command output behind the memory.
- `last_used_at` and `use_count`: lightweight usage signals updated by context queries.
- `reviewed_at`: when a memory was checked or consolidated.
- `merged_into_id`: replacement memory after consolidation.
- `stale_reason`: why a memory should no longer be trusted directly.

`episodes` also track `importance`, usage counts, and derived fact/reflection ids.

`reflections` also track reflection quality and reuse:

- `task_type`: `diagnosis`, `design`, `execution`, or `workflow`.
- `outcome`: `success`, `failure`, or `partial`.
- `problem`: the user-facing problem or goal being reflected on.
- `reasoning_summary`: compact explanation of how the Agent reached the conclusion.
- `context_used`: JSON list of queries, files, logs, edges, or prior memories used.
- `what_worked`: JSON list of useful actions.
- `what_failed`: JSON list of failed or weak actions.
- `hidden_assumptions`: JSON list of assumptions that made the lesson valid or risky.
- `negative_preconditions`: JSON list of similar cases where the lesson should not transfer.
- `query_rounds`: how many query or inspection rounds the Agent needed before converging.
- `trajectory_summary`: compressed summary of the successful and failed path through the task.
- `useful_followup_focus`: the dominant recursive query scene, such as `route`, `resource`, `log`, or `config`.
- `useful_followup_terms`: JSON list of the follow-up anchors that actually helped.
- `misleading_followup_terms`: JSON list of weak or noisy anchors that wasted a round.
- `inspection_targets`: JSON list of the files, logs, routes, resources, or symbols inspected on the way to the result.
- `final_verification_path`: the final reproduction, source, log, or test path that confirmed the conclusion.
- `related_cases`: JSON list of neighboring trace cases that should be reviewed together later.
- `verification_method`: concrete source, log, test, or reproduction check before reuse.
- `reuse_feedback`: whether the candidate helped, partly helped, misled, was unused, or is still only a candidate.
- `source_cases`: JSON list of episodes, reflections, files, logs, routes, resources, or commands behind the lesson.
- `skill_candidate`: optional reusable process template name.
- `experience_type`: optional reflection classification:
  - `procedure_experience`
  - `correction_experience`
  - `semantic_patch_experience`
- `trigger_condition`: when the Agent should remember the reflection.
- `anti_pattern`: the mistake or weak pattern to avoid.
- `repair_action`: the concrete next action.
- `applies_to` and `does_not_apply_to`: applicability boundaries.
- `anchor_type` and `anchor_key`: concrete code anchor for `semantic_patch_experience`; `anchor_type` is `code_file`, `code_symbol`, `code_log_statement`, or `memory_edge`.
- `semantic_field`: the code-business semantic field being patched, such as `business_summary`, `business_terms`, `business_event`, `trigger_stage`, `symptom_terms`, `likely_causes`, `process_hint`, or `neighbor_terms`.
- `existing_value`, `proposed_value`, and `patch_reason`: review data for a business semantic correction.
- `applies_to_current_code`, `superseded_by`, and `misleading_score`: lifecycle and interference signals used by query and maintain.
- `last_applied_at`, `applied_count`, and `last_outcome`: reuse feedback from later tasks.

`reflection_reuse_events` keeps the auditable reuse history behind those aggregate fields:

- `reused_reflection_id`: older reflection that was used.
- `applying_reflection_id`: new reflection that recorded the reuse feedback.
- `outcome`: `helped`, `partial`, `misleading`, or `unused`.
- `task`: task name from the applying reflection.
- `created_at`: when feedback was recorded.

`retrieval_feedback` and `experience_usage_events` are observations, not direct
truth updates. Both may carry `task_id`, `query_id`, `event_key`, and `verified`.
`event_key` provides task-level idempotency. Retrieval feedback also carries a
`status` lifecycle (`open`, `confirmed`, `resolved`, or `ignored`) and an optional
`resolution`. A signal affects query ranking only when it is verified or repeats
across at least two independent tasks. `used`, `ignored`, and `superseded` usage
outcomes remain governance evidence and never directly change ranking.

Query-time feedback reads are candidate-directed: after FTS recall identifies
semantic/reflection IDs, one bounded SQL query loads observations for only those
IDs. The Runtime does not use a global latest-event tail, so an older relevant
signal is not hidden by unrelated recent events.

`query_misses` track retrieval feedback:

- `query`: the user or Agent query that produced no results.
- `normalized_query`: lowercased whitespace-normalized query used to merge repeated open misses.
- `source`: `context`, `search`, or `wiki-search`.
- `result_counts`: JSON counts for each result set at miss time.
- `miss_count`: how many times the same open miss has been observed.
- `last_seen_at`: most recent repeated miss timestamp.
- `status`: `open`, `reviewed`, `resolved`, or `ignored`.
- `resolution`: how the miss was handled.

`semantic_conflicts` track durable business-summary review work:

- `target`: file, symbol, or log anchor such as `pages/ProfileDetail.ets::profileCache`.
- `entity_type`: `code_file`, `code_symbol`, or `code_log_statement`.
- `field`: currently `business_summary`.
- `existing` and `incoming`: the conflicting summaries.
- `source_command`: usually `learn-business`.
- `observed_at`: when the conflict was recorded.
- `status`: `open`, `reviewed`, `resolved`, `ignored`, or `applied`.
- `resolution`: short closure result.
- `decision_note`: reviewer rationale grounded in current source.
- `replacement_source`: source anchor behind the decision.
- `reviewed_at`: closure timestamp.

`learn_scopes` track refreshable learn manifests:

- `scope_key`: stable identity for a learned entry, path, or project scope.
- `scope_type`: `project`, `path`, or `entry`.
- `source_root`: source tree used when the scope was learned.
- `target_path`: directory or file subtree for `path` or `project` scopes.
- `entry_path`: entry file for `entry` scopes.
- `depth`: import-follow depth for entry learning.
- `mode`: `merge` or `replace`.
- `file_snapshot`: JSON map of `file_path -> content_hash` from the last refresh.
- `file_count`: number of indexed files in that snapshot.
- `status`: currently `active`.
- `baseline_revision`: Git commit used by the next Scope-filtered net comparison.
- `last_checked_revision`: Git HEAD observed by the latest refresh attempt.
- `change_provider`: latest provider, such as `git/v1`, `snapshot/v1`, or `full-scan/v1`.
- `refresh_state`: `current`, `overflow`, or `boundary_drift`; overflow retains
  the prior baseline, while boundary drift marks an observed external change.
- `last_refresh_summary`: JSON summary of added, changed, removed, and semantic drift targets.
- `last_refreshed_at`: last successful scope refresh timestamp.

`code_index_state` stores the active source-derived index generation per project:

- `generation`: monotonically increasing generation activated by a successful scoped index transaction.
- `source_revision`: Git revision when available, otherwise `unversioned`.
- `extractor_version`: source-derived row producer version.
- `status`: currently `active` after transaction commit.
- `indexed_file_count` and `retired_file_count`: scope-level write summary.
- `updated_at`: activation timestamp.

`code_files`, `code_symbols`, and `code_log_statements` carry nullable `source_digest` and `index_generation`. New rows use the SHA-256 digest of the indexed file and the generation active for that write. Nullable fields preserve old archives; query reports those legacy rows as `unverified` until a focused scope refresh stamps them.

`scope_boundary_dependencies` records resolved project imports that are outside
one learned Scope without promoting those files into learned code data:

- `scope_id`, `consumer_path`, and `dependency_path`: the owning Scope and the
  directed import boundary.
- `dependency_kind`: currently `import`.
- `source_digest`: last observed SHA-256 content digest.
- `surface_digest`: extractor-level digest of sorted symbol shapes; this is not
  a compiler-exact exported API or ABI signature.
- `status`: `active` or `missing`.
- `last_observed_at`, `created_at`, and `updated_at`: audit timestamps.

The unique key is project, Scope, consumer, dependency, and dependency kind.
The table is maintenance evidence: query surfaces Scope-level boundary drift,
but no boundary row automatically expands retrieval or durable learned scope.

## Code Log Statement Network

`learn-entry`, `learn-path`, and `wiki-index` extract code log statements as part of the existing codebase wiki workflow. This does not add a fifth user-facing skill.

`code_log_statements` stores:

- `file_path` and `line`: where the statement appears.
- `function`: nearest detected function or class-like symbol.
- `level`: `print`, `debug`, `info`, `warning`, `error`, `exception`, or similar.
- `logger`: logger family such as `print`, `logging`, `logger`, `console`, `hilog`, `debugPrint`, or `NSLog`.
- `message_template`: first string literal or compact argument text.
- `raw_statement`: the original single-line statement.
- `business_event`: optional normalized event name such as `profile_load_failed`.
- `trigger_stage`: optional stage hint such as `profile_page_about_to_appear`.
- `symptom_terms`: user-facing symptom vocabulary linked to the log.
- `likely_causes`: likely root-cause hints linked to the log.
- `process_hint`: common process or ability hint associated with the log.
- `neighbor_terms`: nearby start/retry/fallback log phrases that usually appear around the same flow.

`memory_edges` currently stores deterministic code-wiki edges:

- `code_file --contains--> code_symbol`
- `code_file --contains--> code_log_statement`
- `code_symbol --emits_log--> code_log_statement`
- `code_file --imports--> code_file`
- `code_file --routes_to--> code_file`
- `code_file --uses_resource--> code_symbol`
- `code_file --defines_state--> code_symbol`
- `code_file --renders_component--> code_symbol`
- `code_file --passes_property--> code_symbol`
- `code_file --uses_service--> code_symbol`
- `code_file --dispatches_event/handles_event--> code_symbol`
- `code_file --configured_by--> code_file`
- `code_file --tested_by--> code_file`

The ArkTS edges connect learned pages/components to imported project files, router target pages, `$r(...)` resources, state, component composition, named component-property bindings, services, events, Ability configuration, and naming-matched tests. Property evidence records only top-level argument names, not values or source bodies. Ambiguous symbol targets are skipped. These edges are intentionally lightweight and are not a complete call graph or data-flow graph.

Known ArkUI Builder calls are excluded from function-symbol extraction without suppressing project-defined uppercase methods. Chained operation names in `code_files.summary` are retrieval metadata only and do not create nodes or relations.

`code_symbols` also carries nullable `semantic-index/v1` metadata: `symbol_key`, `qualified_name`, `signature`, `start_line`, `end_line`, `semantic_adapter`, and `evidence_class`. ArkTS and TypeScript adapters may persist symbol-level `calls`, `reads_state`, `writes_state`, `implements`, `extends`, `overrides`, `registers_callback`, `exposes_api`, `consumes_api`, and `awaits` edges. The built-in adapters emit static evidence; exact compiler-derived evidence is reserved for future adapters.

External provider run metrics are not SQLite memory records. Configured-provider attempts are mirrored to bounded `runtime/semantic_provider_runs.jsonl` operational telemetry with at most 200 compact rows. Raw ASTs, provider stdout, source content, and compiler diagnostics are not persisted.

Public query edge output remains one hop and returns only allowed relations with hard output limits. Compact code-anchor ranking may separately walk `renders_component` and `passes_property` backwards for at most two hops and promote at most two source-locatable parents. This bounded navigation does not create a causal path or expose recursive graph output. Heavier network health checks belong to maintain commands.

Each edge also carries governance metadata:

- `source_revision`: Git revision when available, otherwise `unversioned`
- `extractor_version`: producer version such as `code-wiki:v4`
- `valid_from` / `valid_to`: query eligibility interval
- `evidence_kind`: static import, route, resource, state, containment, or code-observability evidence
- `last_verified_at`: last focused learn/rebuild verification time

Normal query and impact traversal require `valid_to IS NULL`. Legacy rows are backfilled with `extractor_version: legacy`, `evidence_kind: legacy`, and timestamps derived from `created_at`.

`graph_runtime_state` stores only `project_id`, a monotonically increasing `graph_revision`, and `updated_at`. The central graph rebuild increments this row in the same SQLite transaction as edge changes. Graph-quality payloads are disposable operational cache files under `runtime/graph_quality_snapshot.json`; they are accepted only when their project id and graph revision match SQLite. Maintenance reads therefore do not mutate SQLite, and deleting the runtime snapshot only causes a safe recomputation.

Agent-owned design uses runtime-only `design-context/v1` and `repository-model/v2`. User requirements, generated context, architecture slices, Agent proposals, and reasoning are not stored as SQLite records.

`impact_feedback` stores JSON arrays for changed files and recommended/executed/failed/flaky tests plus missed targets, outcome, note, change fingerprint, and timestamp. It never stores source diffs or test output.

`incident_traces` store compact ArkTS incident summaries produced from a symptom plus bounded runtime log text:

- `trace_key`: stable dedupe key from symptom, scene, dominant log event, and top code anchor.
- `status`: `open`, `diagnosed`, `resolved`, `stale`, or `ignored`.
- `symptom`: user-facing issue description.
- `arkts_scene`: `route`, `resource`, `network`, `permission`, `ability`, `state`, or `unknown`.
- `entry_log_text`: short bounded log excerpt, never the full raw log stream.
- `dominant_log_events`: JSON list of compact log events.
- `suspected_chain`: JSON list of candidate diagnosis chain steps.
- `causal_chain`: compact JSON chains whose steps separate causal role from evidence precision.
- `span_graph`: bounded JSON span nodes, parent edges, chronological causal paths, quality, and gaps; never the full raw log.
- `intervention`: the single reviewed change or experiment applied to test the diagnosis.
- `verification_evidence`: repeatable before/after metric, test, or observation used to verify the intervention.
- `resolution`: reviewed fix or closure summary.

`incident_trace_links` connect a trace to code memory anchors such as `code_log_statement`, `code_file`, `code_symbol`, or `memory_edge`. Relations include `matched_log`, `semantic_candidate`, `followup_target`, `suspected_cause`, and later reviewed variants.

## Staleness

`semantic_facts` and `reflections` include `is_stale` for backwards compatibility. New governance commands also set `status = 'stale'`. Stale records are excluded from `context` by default.

## Confidence

`semantic_facts.confidence` and `reflections.confidence` are 0.0 to 1.0 scores. User-provided facts should usually be 1.0.

## Lifecycle

```text
active -> stale -> archived
active -> merged -> replacement active memory
active -> rejected
episode/reflection -> promoted semantic fact
```

Query commands consume governance metadata. Maintain commands create, review, merge, stale, archive, reject, or promote memory records.

## Scoring And Runtime Performance

Quality scores are computed at runtime from existing rows. They are not a separate source-of-truth table. `maintain-plan --json` may include:

- `quality_summary`
- `low_quality_records`
- `high_value_records`

Each scored item includes `quality_score`, `quality_band`, `score_parts`, `reasons`, and `recommended_action`. The score is advisory and explainable; maintain commands still require confirmation before mutating memory.

Runtime performance samples are stored as bounded JSONL in:

```text
<project-memory-dir>/runtime/performance_samples.jsonl
```

These samples are operational telemetry, not memory. `maintain-health --json` summarizes them as `runtime_performance` with operation sample counts, p50/p95 elapsed time, average performance score, and latest status.

## Design Control Schemas

The normal design query returns disposable JSON:

- `design-context/v1`: authority-ordered task constraints, current repository facts, semantic corrections, historical warnings, quality questions, versioned design-knowledge references, evidence gaps, provenance, and Agent-directed expansion hints. It contains no recommendation, candidate selection, design score, or change plan.

Legacy compatibility design commands may also use caller-owned or disposable JSON:

- `design-intent/v1`: goal, scope, exclusions, acceptance criteria, constraints, and questions.
- `repository-snapshot/v2`: graph revision, freshness, counts, truncation, and gaps.
- `repository-model/v2`: bounded topology, ownership, behavior, data, failure, runtime, and change views.
- `design-workbench/v1`: revision-bound pre-candidate repository model, synthesis brief, anchor catalog, authoring gaps, rules, and unclaimed Delta template.
- `design-contract/v1`: goal, hard constraints, and measurable quality scenarios.
- `design-contract/v2`: v1 plus intent linkage and evidence requirements.
- `design-delta/v1`: candidate nodes/edges, assumptions, invariants, coverage, tests, and observability.
- `design-delta/v2`: v1 plus evidence references for claimed coverage and optional preparation `baseline_revision` binding.
- `design-rules/v1`: explicit `forbid_edge`, `require_edge`, and `single_owner` rules.
- `design-evaluation/v1`: errors, warnings, quality coverage, architecture summary, and audit.
- `design-evaluation/v2`: revision-bound model, coverage states, dimensions, synthesis brief, and change plan.
- `design-comparison/v1`: hard-gated candidate dimensions, recommendation, and tradeoffs.
- `design-decision/v1`: selected/rejected candidates, reasons, and tradeoffs.
- `change-plan/v1`: bounded dependency-ordered edits and verification obligations.
- `design-progress/v1`: ephemeral implementation step states, next-ready actions, blockers, Git/source Delta, test evidence, and evidence gaps.
- `design-verification/v1`: planned/actual file drift, graph alignment, tests, and replan triggers.
- `design-verification/v2`: v1 plus symbol drift, structured tests, scenario verification, and revisions.
- `test-evidence/v1`: command, status, exit code, compact summary, and verified obligations.
- `test-report/v1`: generic machine-readable test report accepted alongside JUnit XML, pytest-json-report, and Jest JSON.
- `design-source-delta/v1`: runtime-only Git-bound changed symbols, exported API signature changes, source relation Delta, digests, provenance, and evidence gaps; source and diff bodies are excluded.
- `design-outcome/v1`: compact persisted calibration result.

All design-context and legacy design artifacts except `design-outcome/v1` are ephemeral. Workbenches, candidate templates, and progress checkpoints are caller-owned or disposable and never enter SQLite. `design_outcomes` stores only candidate/contract ids, baseline/current graph revisions, status/outcome, four bounded metrics, failed-test count, replan count, and timestamp. It never stores requirements, context packs, proposals, progress, source, diffs, test logs, or reasoning; retention is capped at 1,000 rows per project. SQLite remains authoritative for current learned repository facts and compact governed outcomes.
