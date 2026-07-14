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
- `code_files`: lightweight file-level wiki index.
- `code_symbols`: lightweight symbol-level wiki index.
- `code_log_statements`: log, print, and console statements extracted from learned source files.
- `memory_edges`: lightweight relation edges between learned files, symbols, and log statements.
- `impact_feedback`: compact change/test outcome summaries used to improve later test recommendations.
- `learn_scopes`: persistent manifests for previously learned entry, path, or whole-project scopes.
- `query_misses`: failed retrieval attempts that may need later learning or reflection.
- `semantic_conflicts`: durable review records for conflicting business summaries.

`code_files`, `code_symbols`, and `code_log_statements` also store Agent-authored business semantics:

- `business_summary`: concise business meaning of the file, method, field, route, resource, or log.
- `business_terms`: JSON array of searchable business terms grounded in code names, fields, routes, resources, logs, or UI wording.

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
- `last_refresh_summary`: JSON summary of added, changed, removed, and semantic drift targets.
- `last_refreshed_at`: last successful scope refresh timestamp.

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
- `code_file --uses_service--> code_symbol`
- `code_file --dispatches_event/handles_event--> code_symbol`
- `code_file --configured_by--> code_file`
- `code_file --tested_by--> code_file`

The ArkTS edges connect learned pages/components to imported project files, router target pages, `$r(...)` resources, state, component composition, services, events, Ability configuration, and naming-matched tests. Ambiguous symbol targets are skipped. These edges are intentionally lightweight and are not a complete call graph.

`code_symbols` also carries nullable `semantic-index/v1` metadata: `symbol_key`, `qualified_name`, `signature`, `start_line`, `end_line`, `semantic_adapter`, `source_digest`, and `evidence_class`. ArkTS and TypeScript adapters may persist symbol-level `calls`, `reads_state`, `writes_state`, `implements`, `extends`, `overrides`, `registers_callback`, `exposes_api`, `consumes_api`, and `awaits` edges. The built-in adapters emit static evidence; exact compiler-derived evidence is reserved for future adapters.

Query commands do not recursively traverse `memory_edges`. The fast path only returns allowed one-hop relations, currently `contains`, `emits_log`, `imports`, `routes_to`, and `uses_resource`, with hard output limits. Heavier network health checks belong to maintain commands.

Each edge also carries governance metadata:

- `source_revision`: Git revision when available, otherwise `unversioned`
- `extractor_version`: producer version such as `code-wiki:v4`
- `valid_from` / `valid_to`: query eligibility interval
- `evidence_kind`: static import, route, resource, state, containment, or code-observability evidence
- `last_verified_at`: last focused learn/rebuild verification time

Normal query and impact traversal require `valid_to IS NULL`. Legacy rows are backfilled with `extractor_version: legacy`, `evidence_kind: legacy`, and timestamps derived from `created_at`.

Repository-grounded design uses runtime-only `architecture_slice` and Delta Graph JSON. Neither generated architecture slices nor design proposals are stored as SQLite records.

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

## Runtime-Only Design Schemas

Repository design reasoning does not add SQLite tables. It uses caller-owned JSON:

- `design-contract/v1`: goal, hard constraints, and measurable quality scenarios.
- `design-delta/v1`: candidate nodes/edges, assumptions, invariants, coverage, tests, and observability.
- `design-rules/v1`: explicit `forbid_edge`, `require_edge`, and `single_owner` rules.
- `design-evaluation/v1`: errors, warnings, quality coverage, architecture summary, and audit.
- `design-comparison/v1`: hard-gated candidate dimensions, recommendation, and tradeoffs.
- `design-verification/v1`: planned/actual file drift, graph alignment, tests, and replan triggers.

These artifacts are ephemeral. SQLite remains the source of truth only for current learned code/log/edge facts and governed memory.
