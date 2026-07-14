# Agent Memory Runtime Specification

Version: 0.1
Status: Draft
Audience:
- Codex
- AI coding agents
- agent-memory runtime
- maintainers

Goal:
Define the execution protocol for:
- initialization
- querying
- updating
- reflection
- LLM interaction
- memory lifecycle

This document defines operational behavior, not implementation details.

---

# 1. System Overview

The system consists of four layers:

```text
LLM / Codex
    ↓
Skill / Protocol Layer
    ↓
tools/agent_memory.py
    ↓
Workspace memory home
    ↓
Per-project SQLite + Obsidian Vault Mirror
```

The first MVP keeps the runtime intentionally small:

- SQLite is the source of truth.
- Obsidian Markdown is a generated mirror.
- Skills call `tools/agent_memory.py`.
- Query commands support `--json`.
- Keyword search ships before vector search.
- Governance commands keep memory clean without slowing normal query flow.
- `--project` selects the memory archive and query context. Learning commands can use `--source` to read code from an external source tree into that archive. `--memory-home`, `AGENT_MEMORY_HOME`, or the current workspace `./.agent-memory` selects where memory data is stored.

See `docs/mvp-implementation-plan.md` for the full implementation plan.

---

# 2. Query Fast Path

`context`, `search`, `wiki-search`, `evidence-context`, and `impact-scope` are read-oriented commands.

They may:

- filter inactive, stale, merged, archived, or rejected memories;
- return confidence, status, source, scope, evidence, and warnings;
- update lightweight usage fields such as `use_count` and `last_used_at`.
- record a query miss when no result set has matches.
- return learned code log statements and lightweight edges between files, symbols, and log statements.
- return compact one-hop `evidence_chains` derived from allowed edge matches.
- return a bounded `log_search_plan` that turns user problem language into log-oriented anchors, logger hints, and candidate log events.
- return a compact `query_audit` that explains result counts and why top records matched, reranked, passed gates, or were penalized.
- return `memory_intent_v2` alongside the compatible `memory_intent`, plus `retrieval_lanes.lane_budgets`, so Agents can see whether the query is code-location, business-semantics, runtime-log diagnosis, procedure reuse, semantic correction, maintenance, or general context.
- bound result sets before JSON output so large archives do not return unbounded payloads.

They must not:

- merge records;
- promote episodes;
- run expensive duplicate scans;
- export the vault.
- recursively traverse the memory graph.
- return arbitrary relation types from `memory_edges`.

Network limits for the query fast path:

```text
max_depth = 1
edge_limit = 10
evidence_chain_limit = 3
allowed_relations = contains, emits_log
```

The runtime returns these limits in `network_limits` so skill callers know the context is intentionally bounded. Recursive reasoning belongs in the LLM skill layer: inspect the returned context, sharpen the query, and call `context` again.

`search` is also bounded. It returns `result_limits` in the JSON payload so callers can see the current cap for each result set.
`context` and `search` also return `query_audit`. This is an LLM-facing debug trail, not a ranking input. Use it to spot broad matches, stale or low-trust experience, feedback penalties, and missing query anchors before changing stored memory.

`evidence-context` adds a bounded coordination pass over the existing result lanes. A deterministic goal planner chooses lane weights for design, diagnosis, change impact, code understanding, experience reuse, or governance. Candidates are normalized per source, then reranked by relevance, goal fit, authority, trust, graph support, completeness, freshness, and explicit penalties. This prevents a high raw score from one lane, especially a weak historical experience, from dominating direct code/log evidence only because scoring scales differ.

The planner also selects `query_scope: local|global`, emits at most three deterministic `subqueries`, and reports each round in `retrieval_metadata.query_execution`. It stops on sufficient cross-lane coverage, zero new evidence, low novelty, or the hard round limit. Final selection caps repeated sources, locations, and title patterns. Global mode adds only bounded SQL aggregates for code languages, active graph relations, incident scenes/statuses, and experience types; it does not traverse or summarize the entire database with an LLM.

The `design` goal is local by default and weights current code plus active graph edges above historical memory. It attaches `architecture_slice`, which expands from retrieved code files through indexed active edges with hard limits of depth 2, 80 nodes, and 160 edges. The slice exposes entry points, typed nodes/edges, inferred layers, state owners, extension points, consumers, tests, observability anchors, provenance, truncation, and coverage gaps. It is a current-code view, not a complete call graph.

`design-check --proposal <file>` accepts a bounded, versioned Delta Graph. Optional `--contract` and `--rules` inputs add measurable quality scenarios and explicit fitness rules. `design-compare` evaluates two to eight candidates against one reused architecture slice and applies hard gates before coverage, uncertainty, and change cost. `design-verify` compares the selected proposal with actual Git/files, tests, and the refreshed learned graph. `eval-design` runs deterministic JSON case packs. These commands do not call an LLM or persist proposals and diffs. See `docs/design-reasoning.md`.

Evidence chains expose `causal_evidence.level`: `association`, `supported`, `verified`, or `rejected`. Shared text or one anchor remains association. Structural edges or runtime correlation can support a chain. Resolution/verification evidence can verify it. Stale, ignored, misleading, or superseded evidence rejects it. `signals` and `counter_evidence` explain the classification.

`impact-scope` accepts `--base`, repeated `--files`, or `--diff-file`. It resolves changed paths without shell execution, finds exact learned anchors, and traverses only indexed one-hop `memory_edges`. It returns reverse dependents, outgoing dependencies, a bounded risk score, evidence tiers, coverage gaps, and a focused verification checklist. It writes only `runtime/last_impact_scope.json`; it does not persist source diffs.

`memory_edges` carry `source_revision`, `extractor_version`, `valid_from`, `valid_to`, `evidence_kind`, and `last_verified_at`. Query and impact traversal use only edges whose `valid_to` is null. `graph_quality.edge_governance` reports legacy, missing-revision, and unverified edge counts.

ArkTS learning also emits conservative design relations when they are directly inspectable: `renders_component`, `uses_service`, `dispatches_event`, `handles_event`, `configured_by`, and `tested_by`. Existing `defines_state`, `imports`, `routes_to`, `uses_resource`, `contains`, and `emits_log` relations remain available. Ambiguous symbol targets are skipped instead of producing speculative edges.

`impact-feedback` stores a compact change fingerprint, changed paths, recommended/executed/failed/flaky tests, missed targets, outcome, and note. `impact-scope` combines bounded static test-name/semantic matches with up to 200 recent feedback rows. Historical failures raise a recommendation; flaky outcomes add a warning and penalty. No diff body or test log is persisted.

Both commands reuse the existing usage sample, performance sample, query-miss, retrieval-feedback, and maintenance paths. They do not add a second source of truth or persist full historical result sets. The latest coordinated query is mirrored in `runtime/last_evidence_context.json`.

For temporary runtime logs, the runtime also exposes a bounded analysis command:

```bash
python tools/agent_memory.py analyze-runtime-log --project . --query "<query>" --log-file /path/to/runtime.log --json
```

This command does not ingest raw logs into SQLite. It:

- reuses the current query fast path to build a `log_search_plan`
- normalizes raw log lines into lightweight events
- extracts lightweight runtime fields such as `event_name`, `trace_id`, `span_id`, `trace_flags`, `error_code`, `route`, `request_id`, `session_id`, `result`, `module`, `ability`, and `request_path` when they are present
- scores those events against code-log anchors and query hints
- returns bounded evidence slices, `session_candidates`, and a `runtime_episode_candidate`
- returns `log_signal_summary` and `low_signal_events` so Agents can see whether the temporary runtime evidence has enough timestamp, process, logger, stage, reason, correlation, and route/resource fields for diagnosis
- attaches a bounded `otel_lite` projection to matched runtime events so Agents can read stable severity, logger, event, request, session, error, reason, route, and resource fields before falling back to raw excerpts
- includes a lightweight `candidate_chain` and `chain_confidence` inside the runtime episode so downstream reflection can preserve the rough failure sequence
- returns `log_improvement_suggestions` when the current evidence suggests a few missing high-value branch, start, or correlation logs
- prepares a `reflect_payload_template` so the diagnosis can be compressed directly into a structured reflection or experience candidate, including correction-oriented fields such as `old_hypothesis`, bounded `evidence`, `misleading_followup_terms`, and a concrete `repair_action`

The raw log file stays outside SQLite. The runtime only writes the last structured analysis snapshot to `runtime/last_runtime_log_analysis.json`.
The `otel_lite` projection is an output adapter, not a new dependency or durable raw-log store. It uses familiar OpenTelemetry-style field names where useful while keeping the MVP local and lightweight.
It also keeps a runtime-only rolling summary in `runtime/last_usage_sample.json`. This usage sample is not a new database table. It stores bounded facts such as:

- which commands were used
- how many query rounds happened
- latest followup focus
- suggested terms
- dominant runtime signals
- candidate chain
- governance lanes touched by `maintain-plan`

`reflect` now auto-merges that runtime usage sample when structured fields are missing from the provided payload. Explicit payload fields still win. The sample is then closed after the reflection is written so the next unrelated task starts from a fresh usage sample.

The same bounded usage sample also writes `runtime/last_task_trace.json`. This is a runtime-only projection that gathers recent queries, command sequence, context anchors, runtime-log signals, governance lanes, candidate evidence, a `reflection_payload_template`, and an `auto_summary_quality` profile. Use:

```bash
python tools/agent_memory.py reflect --project . --from-last-task --task "<task>" --lesson "<lesson>" --json
```

`--from-last-task` starts from the trace template, then lets explicit payload or command arguments override it. It does not create a fifth skill, does not persist raw logs, and still writes through the normal `reflect` path. If `maintain-plan` returns `review_low_evidence_auto_summary`, inspect `auto_summary_quality` and `reflection_payload_placeholders` before reflecting; placeholder text is review guidance, not durable memory content.

# 3. Governance Path

Governance belongs to `agent-memory-maintain` and these runtime commands:

```bash
python tools/agent_memory.py maintain-health --project . --json
python tools/agent_memory.py maintain-review --project . --json
python tools/agent_memory.py maintain-plan --project . --json
python tools/agent_memory.py maintain-refresh-scope --project . --json
python tools/agent_memory.py maintain-rebuild-derived --project . --target graph --json
python tools/agent_memory.py miss-list --project . --status open --json
python tools/agent_memory.py miss-status --project . --id 1 --status resolved --resolution "..."
python tools/agent_memory.py maintain-status --project . --type semantic --id 1 --status stale --reason "..."
python tools/agent_memory.py maintain-merge --project . --type semantic --ids 1,2 --fact "..." --json
python tools/agent_memory.py maintain-promote --project . --episode-id 1 --fact "..." --json
python tools/agent_memory.py maintain-promote --project . --reflection-id 1 --fact "..." --json
python tools/agent_memory.py maintain-skill-draft --project . --pattern-name "arkts-route-blank-screen-diagnosis" --json
python tools/agent_memory.py maintain-incident-strategy-draft --project . --strategy-name "log-auth-session-profile-blank-diagnosis" --json
python tools/agent_memory.py maintain-incident-fingerprint-draft --project . --fingerprint-name "incident-auth-session-profile-blank-load-profile-failed-session-invalid-401" --json
python tools/agent_memory.py maintain-skill-package --project . --pattern-name "arkts-route-blank-screen-diagnosis" --json
python tools/agent_memory.py maintain-skill-promotion-status --project . --pattern-name "arkts-route-blank-screen-diagnosis" --json
```

Governance actions should preserve history. Prefer status transitions over destructive deletion.

`maintain-refresh-scope` is the low-risk codebase drift path for projects that keep changing. It replays previously learned `wiki-index`, `learn-path`, and `learn-entry` scopes from the persisted `learn_scopes` manifest table, refreshes structural code-wiki rows, retires removed-file structure, and returns semantic drift targets without blindly overwriting business semantics or experiences.

`maintain-rebuild-derived` repairs generated indexes without replacing learned code rows. Use `--target search` to rebuild FTS5 content, `--target graph` to rebuild source-derived code/log edges, or `--target all` for both. Graph repair preserves business summaries, business terms, semantic facts, reflections, and episodes, and returns before/after relation counts, edge amplification, relation dominance, semantic adapter results, and preservation checks. Pass the original `--source` when an archive learned an external source tree. This command is safer than `wiki-index --replace` when only derived data is damaged.

FTS tables and edge-metadata migrations are version-gated. Normal commands rely on SQLite triggers for incremental FTS maintenance and do not rebuild or rewrite the complete index at startup. A version change performs one migration pass; explicit search repair remains available through `maintain-rebuild-derived`.

`maintain-plan` is read-only. It converts review signals into confirmable action candidates for the skill layer. It must not mutate SQLite.

`maintain-plan --json` also returns an explainable quality scoring layer:

- `quality_summary`: total scored records, low-quality count, high-value count, and average quality score.
- `low_quality_records`: bounded records whose `quality_score` is below the review threshold.
- `high_value_records`: bounded records with enough evidence, freshness, and reuse signal to keep active or review for promotion.

The score is deterministic. It combines retrieval relevance, evidence strength, freshness, conflict safety, reuse success, and governance completeness. It is an advisory governance signal, not an automatic promotion or deletion decision.

Quality scores now feed two read-only governance actions:

- `review_low_quality_memory`: emitted when a semantic fact, reflection, or incident trace falls below the quality threshold. Suggested follow-ups include source verification, confidence lowering, stale marking, duplicate merge review, or tighter trigger conditions.
- `review_high_value_experience`: emitted when a reflection/experience has enough evidence, freshness, and reuse signal to deserve prioritized review. Procedure experiences route toward skill-evolution review; correction and semantic-patch experiences route toward learn-semantic-repair review.

Both actions require confirmation. They are review priorities, not automatic mutations.

Reflection quality also includes an optional evidence-chain score when `source_cases` contains incident trace anchors such as `incident_trace:7`. `maintain-plan` resolves those anchors to `incident_traces` and `incident_trace_links`, then returns:

- `evidence_chain_score`
- `evidence_chain_reasons`
- `evidence_chain_trace_ids`
- `evidence_chain_anchor_count`
- `evidence_chain_summary`

If an otherwise high-value reflection lacks a grounded chain, `maintain-plan` may emit `review_weak_evidence_chain`. This action is a prompt to link a source case, verify against an incident trace, or add code/log anchors. It does not mean the experience is wrong.

`maintain-health --json` also returns `graph_quality` for the learned code/log graph. It reports code files, symbols, log statements, memory edges, orphan symbols/logs, stale edges, low-confidence edges, and symbol/log anchor coverage. The runtime binds this expensive aggregate to SQLite `graph_runtime_state.graph_revision` and caches the payload in `runtime/graph_quality_snapshot.json`. Output includes `graph_revision`, `quality_revision`, and `snapshot_status` (`hit`, `recomputed`, or `verified`). Learning increments the revision transactionally; `--verify-graph-quality` forces a fresh calculation without changing graph or memory rows. `maintain-plan --json` may emit `review_graph_quality` when graph health is `watch` or `poor`.

`maintain-health --json` also returns `graph_signal_quality`. This layer scores whether graph anchors are useful for retrieval and diagnosis, not only whether edges exist. It reports weak anchors, missing business semantics, missing log signal fields, concrete `top_repair_targets`, and a compact `coverage_scorecard`. The scorecard separates business semantic coverage, log diagnostic coverage, and symbol/log anchor coverage so an Agent can decide whether to enrich code meaning, improve log fields, or refresh graph edges. `maintain-plan --json` may emit `review_graph_signal_quality` when repair targets are available. Suggested repairs should stay narrow: enrich business terms, add request/session correlation, or add route/resource/reason/result fields to the specific log or symbol target.
`maintain-plan --json` may also emit `review_log_observability_gap` in the `log_diagnosis` lane when learned log statements are missing diagnosis fields. This action is derived from existing graph signal quality and does not persist raw runtime logs.

`maintain-health --json` and `maintain-plan --json` also return `active_learning_queue`. This queue is computed on demand from existing signals: open query misses, graph-signal repair targets, experience usage outcomes, and low-quality memory records. It ranks what to improve next but does not mutate memory. `maintain-plan` may emit `review_active_learning_queue` actions that point back to the concrete underlying target.

`maintain-health --json` and `maintain-plan --json` also return `memory_tiers`. This is a read-only hot/warm/cold/archive-candidate view across semantic facts, reflections, and episodes. It uses bounded recent scans, status, usage count, last-used time, confidence, and quality score to show which records are actively useful, merely retained, low-confidence and unused, or already stale/archived candidates. `maintain-plan` may emit `review_memory_tier` actions for cold and archive-candidate records; these actions are review prompts only and do not change retrieval behavior by themselves.

`maintain-plan --json` also returns `action_budget`. It annotates proposed actions with `priority_score` and `priority_reasons`, then exposes a bounded `top_actions` list plus counts by lane and risk. With no `--action-lane`, the complete plan remains compatible and `execution_scope.mode` is `full`. A known `--action-lane <lane>` now runs only that lane's declared loader groups, returns only that lane's actions, and reports `execution_scope.mode = focused`, `computed_groups`, and `full_archive_summary = false`. Unknown lane names preserve the previous full-computation fallback so `available_lanes` can still correct a typo. Focused zero counts are lane-local and must not be interpreted as full-archive health.

Use `maintain-plan --compact --json` when token budget matters. Compact mode preserves `execution_scope`, summaries, `action_budget`, compact top actions, and `health_overview`. Without a Lane it only reduces output size; with a known Lane it also reduces SQLite reads and computation through dependency-driven execution.

`context` and `search` also attach quality hints to semantic and reflection matches. Reflection matches use `quality_score` inside the existing memory-lane gate to produce `rerank_score`; this lets verified, evidence-backed experience outrank broad or misleading experience after the intent gate has already decided the record belongs in the main lane. The rerank is deliberately soft: it does not make stale, blocked, correction-only, or semantic-patch-only records bypass their lane rules.

When a retrieved semantic fact or reflection was actually useful, ignored, misleading, or superseded during a task, record that outcome:

```bash
python tools/agent_memory.py experience-usage \
  --project . \
  --query "<task query>" \
  --type reflection \
  --id 12 \
  --outcome misleading \
  --note "why this record hurt or helped" \
  --json
```

`experience-usage` stores bounded outcome events in SQLite. Future similar queries receive `usage_feedback_bonus`, `usage_feedback_penalty`, `usage_feedback_reasons`, and `usage_feedback_ids` on matching semantic or reflection rows. This is separate from `retrieval-feedback`: retrieval feedback says whether a returned record was relevant to a query; experience usage says what happened after the Agent tried to use it. `maintain-health` summarizes helpful, misleading, total, success, failure, success-rate, misleading-rate, and effectiveness-band fields, and `maintain-plan` may emit `review_experience_usage` for misleading or superseded records.

Code log matches include `log_signal_score`, `log_signal_band`, `present_signals`, `missing_signals`, and `suggested_log_fields`. These fields estimate whether a learned log statement is diagnostic enough to anchor future runtime-log analysis. They are derived at query time from existing code-log metadata and message templates; they do not mutate learned code records.

Reflection matches also include `experience_maturity`, `experience_maturity_score`, `maturity_reasons`, and `counter_evidence`. Maturity levels are derived at query time: `raw_observation`, `structured_candidate`, `verified_case`, `reused_pattern`, `skill_candidate`, or `deprecated_pattern`. Trust calibration consumes these fields, but they remain advisory and do not mutate stored reflections.

`maintain-plan --json` may emit `review_immature_experience`, `review_missing_counter_evidence`, or `review_maturity_regression`. These actions ask reviewers to add trigger/repair structure, record negative preconditions or does-not-apply cases, or rewrite/deprecate experiences whose maturity regressed after misleading feedback. They do not update reflections automatically.

`context` and `search` also return `memory_use_policy` and per-record calibration fields. `trust_level` labels a returned row as `source_truth`, `verified_experience`, `usable_hint`, `weak_hint`, `possibly_stale`, or `conflict_warning`. `trust_reasons` and `retrieval_explanation` explain the score using existing evidence: match reasons, gate reasons, quality, feedback penalty, status, confidence, source cases, verification method, experience maturity, and counter-evidence. Reflection rows also include `experience_evidence_profile`, a compact claim/evidence/applicability/counter-evidence/verification summary derived from existing fields. Calibration is answer-time guidance only; it does not change stored memory.

Reflection and correction-guard rows may also include `query_risk_flags`, `trust_cap`, `trust_cap_reasons`, `intent_alignment`, `interference_penalty`, and `interference_reasons`. These fields explain why an otherwise high-scoring experience was bounded or should be used only as cautionary context. Hard risks such as stale status, deprecated maturity, and misleading outcomes cap trust even when confidence or quality is high. Softer risks such as missing counter-evidence on a verified procedure keep a risk flag; positive calibration feedback can raise trust, but the Agent still must verify where the procedure does not apply before treating it as a rule. For current-code queries, broad procedure memories are penalized so source-like code/wiki/log anchors remain primary.

`reflect --payload` keeps reusable procedure experience and correction experience separate. `procedure_experience` requires a repair action, verification method, and a trigger anchor such as `trigger_condition`, `useful_followup_focus`, `source_cases`, or `context_used`. `correction_experience` requires `trigger_condition`, `repair_action`, and a misleading signal such as `anti_pattern`, `misleading_followup_terms`, or `what_failed`. A correction experience cannot set `skill_candidate`; single-case semantic or business corrections route to guardrail and semantic-repair governance, not direct skill evolution.

All available golden evaluations can be checked with one local quality gate:

```bash
python tools/agent_memory.py eval-quality --project . --cases-dir docs/eval --json
```

`eval-quality` looks for known golden case files in the cases directory, skips missing files by default, and returns one combined `quality_gate`. Use `--gate log_signal` to run only a selected gate, and repeat `--gate` for a small subset. Use `--strict` for CI-like checks where an empty cases directory should fail. Use `--fail-on-fail` when scripts should receive exit code 1 after a failing JSON report. When the combined gate fails, inspect each failed gate's `next_command_template` and rerun that specific eval for full case detail.
Use `eval-quality --list-gates --json` to inspect registered gate names, case files, and rerun commands without executing cases or writing the latest quality gate snapshot.
Each run also writes `runtime/last_quality_gate.json`. The output includes `quality_gate_delta`, a previous-run comparison with `newly_failed_gates`, `resolved_failed_gates`, and `status_change`. `maintain-health --json` exposes a compact `last_quality_gate` view from that file and recommends review when the latest gate failed. `maintain-plan --json` may emit `review_quality_gate_failure` in the `quality_gate` lane so the failure enters normal action budgeting. Treat the snapshot as disposable runtime telemetry, not durable memory.

To bootstrap editable examples without activating them as the default gate, run:

```bash
python tools/agent_memory.py eval-seed-cases --project . --target docs/eval/examples --json
```

The seed command writes example JSON files and a README under `docs/eval/examples` by default. Edit anchors to match the current project's memory before copying files into `docs/eval` or before running `eval-quality --cases-dir docs/eval/examples`.

Retrieval changes can be checked with a local golden-query eval:

```bash
python tools/agent_memory.py eval-retrieval --project . --cases docs/eval/golden-retrieval.json --json
```

The cases file is JSON, not durable memory. Each case has a `query`, optional `name`, `expected` match specs, `must_not_include` match specs, optional `expected_top` specs, optional `noise` specs, optional `expected_memory_intent`, optional `expected_memory_intent_v2`, optional `required_preferred_lanes`, optional `max_blocked_memory_notes`, optional `max_reflection_count`, and optional `must_not_trust` specs. The command runs the same `context` path that Agents consume and reports expected hit rate, blocked-bad rate, exact anchor rank, expected-top hit rate, experience noise rate, intent match rate, required lane match rate, blocked budget rate, reflection count rate, trust-block rate, missed anchors, and unexpected bad matches. It is intended for regression testing query quality before changing ranking, scoring, learn semantics, code graph, or log graph behavior.

Trust calibration can be checked with:

```bash
python tools/agent_memory.py eval-calibration --project . --cases docs/eval/golden-calibration.json --json
```

Calibration cases use `expected_trust` specs for rows that should have a target `trust_level` or minimum `trust_score`, and `must_not_trust` specs for rows that must not be treated as strong evidence. The command reports expected trust rate, blocked-overtrust rate, missed expected trust, and unexpected trusted matches.

Experience evidence quality can be checked with:

```bash
python tools/agent_memory.py eval-experience-evidence --project . --cases docs/eval/golden-experience-evidence.json --json
```

Experience evidence cases are temporary evaluation fixtures. Each case can match an active reflection by id or text, then check `min_profile_score`, `expected_verification_status`, and `required_true` fields such as `has_evidence`, `has_applicability`, or `has_counter_evidence`. The command evaluates the derived `experience_evidence_profile` directly from stored reflections, so it catches weak experience records independently of query ranking.

Governance action behavior can be checked with:

```bash
python tools/agent_memory.py eval-governance --project . --cases docs/eval/golden-governance.json --json
```

Governance cases are read-only fixtures. Each case can define `expected_actions` and `must_not_actions` using action fields such as `action`, `governance_lane`, `type`, or `id`. The command reports expected-action hit rate and blocked-bad-action rate so archive, active-learning, and review-lane changes do not silently alter maintenance behavior.

Log signal quality can be checked with:

```bash
python tools/agent_memory.py eval-log-signal --project . --cases docs/eval/golden-log-signal.json --json
```

Log signal cases are temporary evaluation fixtures. Each case contains `logs`, optional `min_good_rate`, and optional `max_low_signal_rate`. The command normalizes each line, scores diagnostic fields, and reports `log_signal_good_rate` plus `low_signal_event_rate`. It does not store raw logs in SQLite.

Code/log graph signal quality can be checked with:

```bash
python tools/agent_memory.py eval-graph-signal --project . --cases docs/eval/golden-graph-signal.json --json
```

Graph signal cases are temporary evaluation fixtures. Each case can set `min_coverage_score`, `allowed_coverage_statuses`, `max_repair_targets`, and `required_repair_targets`. The command reads the current `graph_signal_quality.coverage_scorecard` and `top_repair_targets`, then reports whether business semantic coverage, log diagnostic coverage, anchor coverage, and expected repair targets still match the golden expectations.

Answer grounding can be checked with:

```bash
python tools/agent_memory.py eval-evidence-attribution --project . --cases docs/eval/golden-evidence-attribution.json --json
```

Evidence attribution cases are temporary evaluation fixtures. Each case contains a query, answer claims, and grounding thresholds. The command runs the normal `context` path, compares each claim with returned semantic facts, reflections, code wiki records, code logs, edges, and incident traces, then reports grounded, weak, and unsupported claims. Use this after changing query, graph, log, or reflection quality logic to catch answers that sound plausible but are not supported by retrieved context.

When a retrieved semantic fact or reflection is weakly related, stale, too broad, wrong-domain, or misleading for a specific query, record targeted negative feedback:

```bash
python tools/agent_memory.py retrieval-feedback \
  --project . \
  --query "ArkTS route blank screen" \
  --type reflection \
  --id 2 \
  --reason weak_related \
  --json
```

Open feedback applies a bounded query-similarity penalty to matching future `context` and `search` results. Results include `feedback_penalty`, `feedback_reasons`, and `feedback_ids` when a penalty applies. `maintain-plan` may emit `review_retrieval_feedback`; this prompts review, confidence tightening, stale marking, or supersession, but does not mutate memory automatically.

The same command can record calibration feedback with `useful`, `verified_useful`, `undertrusted`, or `overtrusted`. Query results then expose `calibration_feedback_bonus`, `calibration_feedback_penalty`, `calibration_feedback_reasons`, and `calibration_feedback_ids`; the answer-time trust score consumes those fields. `maintain-plan` may emit `review_overtrusted_memory` or `review_undertrusted_memory` so humans can decide whether to tighten triggers, lower confidence, add evidence, or leave the feedback as a one-off observation.

`maintain-health --json` includes `runtime_performance`, a summary built from bounded samples in `runtime/performance_samples.jsonl`. Samples track operation name, elapsed milliseconds, result counts, token estimate, database size, status, and a performance score. This is runtime telemetry for local maintenance only; it is not a durable memory record and should be treated as disposable.

`maintain-plan --json` also includes `runtime_performance` and may emit `review_runtime_performance_budget` when an operation breaches local latency targets, token budget, non-ok status, or a poor/watch performance band. This action is a maintenance prompt to tighten limits, review noisy memory, refresh stale context, or split expensive maintenance work. It does not automatically delete telemetry or mutate memory.

Query miss commands manage feedback from failed retrievals. A miss is recorded only when `context`, `search`, or `wiki-search` has zero matches. Repeated open misses with the same source and normalized query are merged into one row with `miss_count` and `last_seen_at`, so maintenance can focus on recurring retrieval gaps instead of duplicate rows.

Query commands expand common natural-language problem descriptions into technical search terms before scoring rows. The expansion is deterministic and local. It helps symptom queries such as `页面跳转后白屏`, `图片资源显示不出来`, or `加载用户资料失败日志` match learned ArkTS route, resource, config, and log records without adding a vector database.

When `maintain-plan` returns `review_query_miss`, it now also returns:

- `suggested_query_terms`
- `followup_focus`
- `query_command_template`
- `query_workflow_steps`

These fields let the skill layer recurse back into `search` or `context` with stronger route, resource, log, file, and symbol anchors before widening the learning scope.

When repeated runtime-log-backed `procedure_experience` reflections describe the same diagnosis flow, `maintain-plan` may also emit `review_incident_strategy_candidate`. This is the Goal-Oriented Incident Diagnosis strategy-library path. It groups:

- `goal_symptoms`
- `common_log_events`
- `recommended_steps`
- `verification_paths`
- `misleading_signals`
- `log_design_feedback`

and exposes a read-only `write_command_template` for drafting the grouped strategy into `docs/incident-strategies/`.

When repeated runtime-log-backed reflections share the same narrow failure signature, `maintain-plan` may also emit `review_recurring_incident_fingerprint`. This is the lightweight recurring-incident path. It groups:

- `goal_symptoms`
- `common_log_events`
- `dominant_failure_signals`
- `misleading_signals`

and exposes a read-only `write_command_template` for drafting the grouped fingerprint into `docs/incident-fingerprints/`.

`maintain-plan` now also returns:

- `governance_summary`
- `learn_governance_summary`

`governance_summary` groups pending work by governance lane, including `learn_semantic_repair`, `skill_evolution`, `log_diagnosis`, and `incident_recurrence`.
`learn_governance_summary` keeps learn-side follow-up focused with:

- `correction_repairs`
- `semantic_drift_reviews`
- `top_affected_paths`

# 3.5 Structured Reflection Path

`agent-memory-reflect` should let the local Agent CLI organize a completed attempt before writing memory. For diagnosis, design, execution, and workflow attempts, prefer:

```bash
python tools/agent_memory.py reflect --project . --payload "<json>"
python tools/agent_memory.py reflect --project . --payload-file "<review.json>"
```

The payload stores the Agent-authored task review in `reflections`:

```json
{
  "experience_type": "procedure_experience",
  "task_type": "diagnosis",
  "outcome": "success",
  "problem": "Profile page opens blank after navigation.",
  "task": "diagnose profile blank page",
  "summary": "Queried memory and found a route path mismatch.",
  "reasoning_summary": "The useful clue was the route edge plus router.pushUrl log.",
  "context_used": ["query: profile blank page route", "file: pages/Home.ets", "log: router.pushUrl failed"],
  "what_worked": ["Search by business page name", "Check route edges"],
  "what_failed": ["Searching only generic blank-screen terms"],
  "hidden_assumptions": ["The blank screen happened after route navigation."],
  "negative_preconditions": ["Do not apply when no navigation occurred."],
  "query_rounds": 3,
  "trajectory_summary": "The first query was broad, the second locked onto route edges, and the third inspection confirmed the target page mismatch.",
  "useful_followup_focus": "route",
  "useful_followup_terms": ["profile", "router.pushUrl", "pages/ProfileDetail"],
  "misleading_followup_terms": ["blank screen"],
  "inspection_targets": ["pages/Home.ets", "pages/ProfileDetail.ets", "router.pushUrl failed"],
  "final_verification_path": "Reproduce navigation -> inspect route registration -> confirm router target mismatch.",
  "related_cases": ["case_profile_route_001"],
  "verification_method": "Confirm route registration, inspect router logs, and reproduce navigation.",
  "reuse_feedback": "experience candidate until reused",
  "source_cases": ["episode:12", "reflection:7", "file: pages/Home.ets"],
  "skill_candidate": "arkts-route-blank-screen-diagnosis",
  "lesson": "ArkTS blank-screen diagnosis should combine business page names with route terms.",
  "future_rule": "When a HarmonyOS page opens blank after navigation, query business page terms plus route/router terms first.",
  "trigger_condition": "Page opens blank after route navigation",
  "repair_action": "Query memory with business page name, route terms, and related log template"
}
```

`experience_type` is optional but now supported in the protocol layer:

- `procedure_experience`: reusable diagnosis, query, repair, or change-design workflow
- `correction_experience`: correction of learned business semantics or memory understanding
- `semantic_patch_experience`: anchored code business-semantic correction or enrichment

This classification does not add a fifth skill. It only helps `maintain-plan` route experience candidates toward future skill-candidate review or toward learn/semantic-repair governance.

For code business-semantic repair, `reflect` writes the correction candidate into `reflections`, not directly into `code_files`, `code_symbols`, or `code_log_statements`. Use `semantic_patch_experience` with:

- `anchor_type`
- `anchor_key`
- `semantic_field`
- `existing_value`
- `proposed_value`
- `patch_reason`

Then run `maintain-plan --json`, review `review_semantic_patch`, and apply the returned `learn_business_payload_template` through `learn-business` when current source confirms the patch.

`maintain-plan` may also return `review_experience_conflict` when newer reflections disagree with older active guidance. This currently covers:

- `procedure_experience` or `correction_experience` records with the same trigger/scope but materially different `repair_action` or `future_rule`
- `semantic_patch_experience` records that target the same `anchor_key` + `semantic_field` with different `proposed_value`

This is review-only governance output. Use it to decide whether the older record should be marked stale, whether trigger boundaries need tightening, or whether the losing semantic patch should be marked superseded.

When `maintain-plan` returns `review_correction_experience`, it now carries a learn-governance repair bundle instead of only a type label:

- `correction_targets`
- `learning_rule_draft`
- `learn_business_payload_template`
- `workflow_steps`
- `command_template`

Use this bundle to repair the affected file, symbol, or log business semantics in place through `learn-business`, rather than widening the learning scope.

These fields participate in `search` and `context`, so later issue-location or design skills can retrieve successful and failed attempts by problem description, business term, file, log, or prior query.

The compressed trace-case fields are intentionally short and structured:

- `query_rounds`
- `trajectory_summary`
- `useful_followup_focus`
- `useful_followup_terms`
- `misleading_followup_terms`
- `inspection_targets`
- `final_verification_path`
- `related_cases`

They are not a raw transcript. They exist so later `maintain-plan` runs can cluster reusable procedure paths and can separate noisy anchors from effective ones while keeping the user-facing interface at four skills.

When at least two complete `procedure_experience` reflections point to the same `skill_candidate`, `maintain-plan` may also emit a `review_skill_pattern_candidate` action. This is still read-only governance output. It groups supporting reflection ids, shared follow-up focus, common query terms, supporting cases, and verification methods so a later reviewer can decide whether the repeated pattern is stable enough to draft as a skill candidate.

The same action now also carries:

- `draft_path`: suggested review document path such as `docs/skill-candidates/<pattern>.md`
- `draft_markdown`: a first-pass Markdown draft built from the clustered cases
- `common_stop_conditions`: clustered verification end states or stopping conditions
- `common_steps`: first-pass execution steps inferred from repeated followup focus, anchors, and verification paths
- `expected_outputs`: what a future skill should reliably hand back
- `failure_modes`: recurring weak patterns, noisy anchors, or anti-patterns

This does not write to the repo automatically. It gives the local Agent CLI or a human reviewer a stable draft artifact to inspect before creating any real skill.
The grouped candidate now also carries stage metadata:

- `draft_status`: `not_written` or `written`
- `draft_review_status`
- `package_path`
- `package_status`: `not_written` or `written`
- `package_review_status`
- `promotion_stage`: `clustered`, `draft`, or `candidate_package`
- `review_guidance`
- `promotion_readiness`
- `quality_score`
- `quality_reasons`
- `helped_reuse_count`
- `partial_reuse_count`
- `misleading_reuse_count`
- `anchor_health`
- `missing_anchor_paths`

These quality signals are advisory. They do not promote a skill automatically. They help distinguish:

- repeated but still weak patterns
- patterns worth human review
- patterns that are strong enough to consider manual promotion

`vault-export` now mirrors these grouped candidates into `Governance/Skill Pattern Candidates.md`, including the proposed draft path, review statuses, reviewer metadata, preservation policy, anchor health, and a Markdown preview. The vault remains a generated review mirror; it does not approve or install the skill.

Runtime-log-backed incident strategies are mirrored separately in `Governance/Incident Strategy Candidates.md`. They are intended as reusable diagnosis policies that can later inform skill evolution, but they start as reviewable strategy drafts rather than formal skills.

When repeated runtime-log-backed diagnosis reflections expose the same logging weakness, `maintain-plan` may also emit `review_log_design_gap`. This is a lightweight log-governance action, not a new storage subsystem. It groups:

- `goal_area`
- `goal_symptoms`
- `high_value_log_anchor_targets`
- `suggested_log_kinds`
- `log_design_feedback`

Use it to guide a few high-value start, branch, or correlation logs in the source code without broadening memory scope or persisting more runtime history.

For large archives, `vault-export` now defaults to bounded human-readable summaries for aggregate pages such as `Semantic Facts/project-facts.md`, `Codebase Wiki/files.md`, `symbols.md`, `log-statements.md`, and `memory-edges.md`, and only exports the most recent bounded set of per-record episode/reflection files. Generated pages include a truncation notice when the vault mirror is showing only a subset. SQLite remains the full machine-readable source of truth.

# 3.6 Refresh And Retirement Path

Structural learning commands now persist a refreshable learn manifest in `learn_scopes`:

- `wiki-index`
- `learn-path`
- `learn-entry`

Each manifest stores the learned scope type, source root, target path or entry, depth, mode, and a file snapshot hash map. This lets `maintain` refresh previously learned scopes after the project evolves.

Refresh command:

```bash
python tools/agent_memory.py maintain-refresh-scope --project . --json
python tools/agent_memory.py maintain-refresh-scope --project . --scope-id 3 --json
```

Refresh output is intentionally low-risk:

- `added_files`
- `changed_files`
- `removed_files`
- `parse_stats`
- `semantic_review_targets`

Current MVP behavior:

- current files in the scope are re-indexed
- removed files in the scope have their structural `code_files`, `code_symbols`, `code_log_statements`, and derived edges retired from the code wiki
- business semantics, reflections, and experiences are not silently deleted

Use `semantic_review_targets` to decide whether the next step is:

- focused `learn-business`
- correction-experience repair
- later stale review for experiences anchored to removed code

`maintain-plan` now consumes recent refresh drift as well. When a refreshed scope changed, it may emit:

- `review_semantic_drift`
- `mark_experience_stale_if_anchor_removed`
- `review_skill_pattern_staleness`

The first action keeps business semantics aligned with changed code. The second is advisory and confirmation-gated: it marks reflections whose anchors point at removed files as candidates for stale review rather than silently deleting them.

When a reviewer is ready to materialize the draft into the repo, use:

```bash
python tools/agent_memory.py maintain-skill-draft \
  --project . \
  --pattern-name "<pattern-name>" \
  --json
```

This writes the current `draft_markdown` into `docs/skill-candidates/<pattern-name>.md`. It still does not touch the formal `skills/` directory.
The written draft now starts with stable YAML frontmatter such as `artifact_type`, `promotion_status`, `supporting_reflection_ids`, `common_followup_focus`, and `supporting_cases` so later review and promotion tooling can read it without reparsing the body text.
It also reserves human review metadata in place: `review_status`, `reviewer`, and `review_notes`.
If an existing draft already carries human review metadata such as a non-empty reviewer, non-empty review notes, or a `review_status` other than `pending_review`, the runtime preserves that artifact and returns `write_action: preserved_existing_reviewed_artifact` plus a warning instead of overwriting it.

To materialize every current skill-pattern draft in one pass, use:

```bash
python tools/agent_memory.py maintain-skill-draft \
  --project . \
  --pattern-name all \
  --json
```

When a reviewed draft should become a candidate skill package, use:

```bash
python tools/agent_memory.py maintain-skill-package \
  --project . \
  --pattern-name "<pattern-name>" \
  --json
```

This writes:

```text
skills/_candidates/<pattern-name>/SKILL.md
```

and also writes:

```text
skills/_candidates/<pattern-name>/PROMOTION.md
```

It still does not create or update a formal skill under `skills/<name>/`.
The candidate package also carries YAML frontmatter with `promotion_status: candidate` and `source_draft`, so the review chain from draft -> candidate package stays auditable inside the repo.
The same review metadata fields stay with the package so a reviewer can record status and notes without inventing a second format.
If an existing candidate package already carries human review metadata, the runtime preserves it and returns the same non-overwrite warning instead of silently replacing the reviewed artifact.
The generated `PROMOTION.md` is the manual execution template for the final human promotion step into `skills/<name>/SKILL.md`.
For a read-only promotion gate check, use:

```bash
python tools/agent_memory.py maintain-skill-promotion-status \
  --project . \
  --pattern-name "<pattern-name>" \
  --json
```

This does not promote the skill. It reports `promotion_blockers`, `ready_for_manual_promotion`, reviewer metadata, checklist status, anchor freshness, and the eventual formal target path.

The extra experience-candidate fields do not create accepted experience by themselves.
Future Agents must verify them against current source, logs, tests, and code wiki
evidence before using them as conclusions.

# 4. Code Learning Path

`learn-entry`, `learn-path`, and `wiki-index` update the codebase wiki.

`learn-business` writes Agent-authored business semantics into the existing code wiki tables:

```bash
python tools/agent_memory.py learn-business --project . --payload "<json>" --json
```

The payload contains files, symbols, and logs with `business_summary` and `business_terms`. Use it after the Agent has read the target source and organized the code's real business meaning. It does not create a separate business table; it enriches `code_files`, `code_symbols`, and `code_log_statements`.

`learn-business` uses object-level merge semantics by default. It updates only the addressed file, symbol, and log rows; merges `business_terms`; preserves existing non-empty `business_summary` values; and reports `semantic_conflicts` instead of silently overwriting conflicting summaries.

`learn-business --json` also returns semantic quality feedback for the submitted scope:

```text
semantic_stats
semantic_gaps
semantic_followup
```

`semantic_stats` reports coverage counts for file, symbol, and log business meaning. `semantic_gaps` lists the specific files, symbols, or logs that still lack `business_summary` or `business_terms`.
When gaps remain, `semantic_followup` returns:

- `command_template`
- `workflow_steps`
- `recommended_next_action`
- `truncated`
- `returned_counts`
- `remaining_counts`
- `followup_payload_template`

The follow-up template is priority-ordered and batch-limited so the Agent can enrich the highest-value files, symbols, and logs first without rebuilding anchors.
Each follow-up file, symbol, and log item also includes `hint_terms` and `hint_context`. These are deterministic retrieval anchors derived from code names, summaries, routes, resources, logger families, and message templates. Agents should reuse them when drafting second-pass business semantics.

Recent `semantic_conflicts` are stored durably in SQLite and also flow into `maintain-plan` as `review_semantic_conflict` actions for later governance.

Conflict review can be managed with:

```bash
python tools/agent_memory.py list --project . --type semantic-conflict --json
python tools/agent_memory.py conflict-status --project . --id 1 --status resolved --resolution "confirmed existing summary against current source"
python tools/agent_memory.py conflict-apply --project . --id 1 --resolution "confirmed incoming summary against current source" --decision-note "current file responsibility changed" --replacement-source "source:pages/ProfileDetail.ets"
```

`conflict-apply` is the governed replacement path. It applies the stored incoming `business_summary` to the target file, symbol, or log row and closes the conflict with status `applied`. It also enforces exact single-row target matching; ambiguous symbol or log targets are rejected instead of applying a broad update.
`maintain-plan` now includes `apply_command_template` on `review_semantic_conflict` actions so an Agent can carry the approved replacement step directly after review.

They also extract code log statements and rebuild deterministic code-wiki edges:

```text
code_file --contains--> code_symbol
code_file --contains--> code_log_statement
code_symbol --emits_log--> code_log_statement
code_file --defines_state--> code_symbol
```

This supports memory-aware diagnosis without adding a separate user-facing skill. An Agent can query an observed log or console message, receive `code_log_matches`, inspect `edge_matches`, then recursively query again with the related file/function names.
For ArkTS files, learning also extracts component state symbols such as `@State`, `@Prop`, `@Link`, and `@Provide` as `state` code symbols. The `defines_state` edge makes local UI state visible to route, resource, and log-oriented diagnosis without adding a separate graph database.

`tested_by` is intentionally conservative. Only code files with explicit test directory segments or test/spec filename conventions are candidates. Production and test files must share the nearest package/module root, configuration files never participate, and ambiguous production matches are skipped. This prevents repeated filenames in monorepos from creating cross-module test edges.

Learning commands return parse feedback. `learn-entry --json` and `learn-path --json` include `parse_stats`:

```text
files_indexed
languages
symbols_total
symbols_by_type
code_logs_total
code_logs_by_level
semantic_index
memory_edges_total
```

Agents should use these counts to detect narrow or failed learning scopes before relying on the codebase wiki.
When the learned files still lack business semantics, `learn-entry --json` and `learn-path --json` also include `semantic_followup` with a second-pass `learn-business` template scoped to the files just indexed.

# 4.5 ArkTS Incident Trace Path

Use `incident-trace` when the user provides a symptom and temporary runtime log evidence:

```bash
python tools/agent_memory.py incident-trace --project . --symptom "页面跳转后白屏" --log-text "router.pushUrl failed for ProfileDetail" --json
python tools/agent_memory.py incident-trace --project . --symptom "页面跳转后白屏" --log-file /tmp/runtime.log --json
```

The command stores only compact trace fields. It does not persist the full raw log stream. When a matched code log has a semantic enclosing symbol, `causal_chain` adds bounded symbol-level candidates with independent `observed`, `supports`, `possible`, or `inferred` roles. Static reachability is never reported as observed runtime causality. Query commands may return `incident_trace_matches`, and `maintain-plan` may return `promote_incident_trace_to_reflection` or `review_log_anchor_gap`.

# 4.6 Semantic Index

ArkTS and TypeScript learning automatically emits validated `semantic-index/v1` batches. The runtime enriches `code_symbols` with stable key, qualified name, signature, span, adapter, source digest, and evidence class, then persists resolved semantic relations as versioned `memory_edges`. Partial learning also refreshes existing reverse dependents so replacing a target symbol does not silently lose incoming calls.

Built-in adapters are lightweight static analyzers and therefore emit `static`, never `exact`. Future compiler, language-server, or SCIP providers must use the same `LanguageAdapter` boundary. Full details and limits are in `docs/semantic-index.md`.

An external provider is enabled only through `AGENT_MEMORY_SEMANTIC_PROVIDER_<LANGUAGE>`, currently most relevant as `AGENT_MEMORY_SEMANTIC_PROVIDER_ARKTS`. It receives `semantic-provider-request/v1` on stdin and must return a correlated `semantic-provider-result/v1` containing an exact batch. The runtime invokes one executable without a shell, enforces timeout/output acceptance limits, validates digests and paths, and falls back to static analysis during normal learning. `maintain-health` exposes `semantic_provider`; repeated fallback produces a read-only `review_semantic_provider_failures` action in `maintain-plan`.

Use `eval-semantic --cases docs/eval/semantic-cases.json --mode static|auto|external --json` for a temporary, non-persistent quality comparison. See `docs/semantic-provider.md` for the full protocol.

# 5. Reflection Quality Path

Reflection quality belongs to `agent-memory-reflect` and is reviewed through:

```bash
python tools/agent_memory.py reflect-review --project . --json
```

`reflect-review` is read-only. It reports missing trigger conditions, missing repair actions, missing hidden assumptions, missing negative preconditions, missing verification methods, missing reuse feedback, vague rules, unused reflections, and misleading outcomes.

For runtime-log-backed reflections, `reflect-review` also includes `runtime_feedback_summary`:

- `effective_signals`
- `misleading_signals`
- `verification_checkpoints`

Use that summary to decide whether a diagnosis was compressed into reusable runtime evidence or still needs rewriting before promotion.

# 6. Search Batching

`search --json` supports batched aggregated retrieval:

```bash
python tools/agent_memory.py search --project . --query "<query>" --per-type-limit 10 --aggregate-limit 8 --cursor 0 --json
```

The response includes:

- `truncated`
- `next_cursor`
- `total_candidates_by_type`
- `returned_counts_by_type`
- `per_type_limit`
- `aggregate_limit`
- `suggested_followup_terms`
- `followup_focus`

Use `next_cursor` only when the current batch does not provide enough evidence. Query remains bounded by design.
`suggested_followup_terms` are scene-aware. The runtime biases them toward exact route, resource, log, or config anchors based on the current problem wording and strongest matches before falling back to broader file-path or summary-derived terms.
