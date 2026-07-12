---
name: agent-memory-query
description: Use when the user asks to query, search, recall, inspect, or retrieve previous memory, project facts, reflections, task history, or codebase wiki context.
---

# Agent Memory Query

Retrieve memory context before substantial work or when the user asks what the system knows.

This skill intentionally stays small. Complex recursive workflows should use the templates in:

- `docs/templates/diagnosis-memory-query-template.md`
- `docs/templates/change-design-memory-query-template.md`

## Context Query

```bash
python tools/agent_memory.py context --project . --query "<query>" --json
```

Use for:

```text
查一下之前有没有相关经验。
What does memory know about this module?
Before editing, retrieve relevant context.
```

The runtime expands common symptom words into technical search terms. For HarmonyOS/ArkTS projects, natural-language queries such as `页面跳转后白屏`, `图片资源显示不出来`, or `加载用户资料失败日志` can match route, resource, config, and log records indexed from learned source.

## Raw Search

```bash
python tools/agent_memory.py search --project . --query "<query>" --json
python tools/agent_memory.py search --project . --query "<query>" --per-type-limit 10 --aggregate-limit 8 --cursor 0 --json
```

`search` is batched and bounded. It returns ranked subsets plus:

- `truncated`
- `next_cursor`
- `total_candidates_by_type`
- `returned_counts_by_type`
- `per_type_limit`
- `aggregate_limit`

Use `next_cursor` for another pass when the first batch is insufficient. Do not ask for unbounded output.

## Wiki Search

```bash
python tools/agent_memory.py wiki-search --project . --query "<query>" --json
```

When the query is an observed error, print, or console message, inspect `code_log_matches` and `edge_matches` from `context` or `search`. `wiki-search` may return matching log statements with `kind: "log_statement"`.

Code and log matches include `search_terms` and `match_reasons`. Use `match_reasons` to explain why a record was retrieved, and use high-signal `search_terms` as anchors for a sharper follow-up query.
Code log matches may include `log_signal_score`, `log_signal_band`, `missing_signals`, and `suggested_log_fields`. Prefer high-signal logs as diagnosis anchors. Treat low-signal logs as evidence gaps, not as source truth.
`context` and `search` also include `query_audit`. Use it when retrieval looks noisy or surprising. It explains result counts, top-match reasons, rerank score, quality score, trust level, feedback penalty, gate reasons, and retrieval explanation. Do not quote it to the user unless they ask how retrieval behaved.
`context` and `search` also return `suggested_followup_terms`. Use those first when forming the next recursive query; they are prioritized by the current retrieval scene:

- route/navigation problems bias toward route targets and router anchors
- resource/display problems bias toward resource keys and `$r(...)` anchors
- log/error problems bias toward log templates and logger families
- config/permission problems bias toward permissions, dependencies, abilities, and config files

Only fall back to broader file or summary terms after those anchors.
The runtime also returns `followup_focus` when it can classify the current scene. Treat it as the default branch selector for recursive query logic.
When the issue likely needs runtime log evidence, also read `log_search_plan`. It converts the current problem into bounded log-analysis hints:

- `candidate_log_events`
- `search_terms`
- `logger_hints`
- `function_hints`
- `file_hints`
- `recommended_order`

If the user provides a temporary raw log file, use the same skill to call:

```bash
python tools/agent_memory.py analyze-runtime-log --project . --query "<query>" --log-file "<path>" --json
```

Treat the returned `slices`, `session_candidates`, and `runtime_episode_candidate` as diagnosis evidence. If the log evidence is good enough to keep, start from `reflect_payload_template` rather than rewriting a reflection payload from scratch. Do not treat the raw log file itself as long-term memory.
Also inspect `log_signal_summary` and `low_signal_events`. Poor signal events are useful clues only after current source/log inspection; use their `suggested_log_fields` and `observability_gaps` as narrow follow-up engineering guidance.
When matched events include `otel_lite`, prefer those stable fields for the LLM-facing summary: severity, logger, event name, request id, session id, error code, reason, route, and resource. Use raw excerpts only when the structured fields are insufficient.
When present, use `runtime_episode_candidate.candidate_chain` as the compact incident narrative and `chain_confidence` as a lightweight confidence hint rather than inferring a full causal graph yourself.
If `log_improvement_suggestions` is present, treat it as follow-up engineering guidance for adding a few high-value start, branch, or correlation logs. Keep those suggestions narrow and tied to the matched code-log anchors.

`context` also includes `network_limits` and may include compact `evidence_chains`. Treat these chains as one-hop explanations, not complete graph paths.

`context` and `search` also include memory firewall metadata:

- `memory_intent`: the runtime's current query intent, such as `procedure_reuse`, `correction_guard`, `semantic_lookup`, `incident_diagnosis`, `code_current`, or `general_context`
- `retrieval_lanes`: counts and policy for main reflections, correction guards, semantic patches, and blocked memories
- `memory_brief`: compact counts for what entered or was blocked from context
- `correction_guards`: warning-only experiences that should prevent repeated mistakes but should not become the main task direction by default
- `semantic_patch_notes`: anchored business-semantic corrections for code files, symbols, logs, or edges
- `blocked_memory_notes`: records kept out of the main context because their type or trigger did not match the query intent
- `conflict_notes`: matching unresolved semantic conflicts

Read these fields before relying on `reflections`. A recent reflection with weak intent match should not steer the task.

`context` and `search` also include `memory_use_policy`, and calibrated result rows may include:

- `experience_maturity`: `raw_observation`, `structured_candidate`, `verified_case`, `reused_pattern`, `skill_candidate`, or `deprecated_pattern`
- `counter_evidence`: whether the experience records negative preconditions or cases where it does not apply
- `trust_level`: `source_truth`, `verified_experience`, `usable_hint`, `weak_hint`, `possibly_stale`, or `conflict_warning`
- `trust_score`: bounded 0-1 advisory confidence
- `trust_reasons`: compact reasons behind the trust level
- `query_risk_flags`: caution flags such as `missing_counter_evidence`, `misleading_experience`, `deprecated_experience`, or `semantic_correction_guidance`
- `trust_cap`: the maximum trust score applied because of hard or soft risk signals
- `trust_cap_reasons`: why the cap or risk flag was applied
- `retrieval_explanation`: match, gate, quality, feedback, status, and confidence details

Use `experience_maturity` before applying a reflection as a reusable rule. Treat `raw_observation` as a weak hint, `verified_case` as a case-backed procedure, `reused_pattern` as stronger reusable guidance, `skill_candidate` as promotion material, and `deprecated_pattern` as warning or counter-evidence.
Use `trust_level` before injecting memory into an answer. Treat `source_truth` as inspectable code/log/wiki evidence, `verified_experience` as a reusable but still advisory procedure, `usable_hint` as a lead, `weak_hint` as a next-inspection hint only, and `possibly_stale` or `conflict_warning` as cautionary context.
Use `query_risk_flags` before following a high-scoring experience. `missing_counter_evidence` means the procedure still lacks clear boundaries; `misleading_experience` and `deprecated_experience` should be used as warnings, not instructions; `semantic_correction_guidance` should repair the interpretation of code/business meaning rather than steer the whole task as a procedure.
If a memory result's trust label was wrong for the actual task outcome, record calibration feedback with `retrieval-feedback`: use `verified_useful` or `useful` when a low/medium-trust result proved valuable, `undertrusted` when the runtime should trust it more next time, and `overtrusted` when a strong-looking result misled the task. This adjusts future answer-time trust for similar queries without rewriting the memory record.
If a returned semantic fact or reflection was actually used, helpful, ignored, misleading, or superseded during the task, record the outcome with `experience-usage`. This is stronger task-outcome feedback than relevance-only retrieval feedback, and future similar queries will expose `usage_feedback_bonus`, `usage_feedback_penalty`, and `usage_feedback_reasons` on matching rows.

If `context`, `search`, or `wiki-search` returns no results, the runtime records a query miss automatically. Do not add manual keywords just to improve retrieval; let maintain review real misses later.

## Use Order

Use returned data in this order:

```text
memory_intent and retrieval_lanes
  -> memory_use_policy and per-record trust_level
  -> reusable procedure experiences when the intent matches
  -> correction_guards as warnings
  -> semantic facts
  -> code wiki and business semantics
  -> semantic_patch_notes for anchored business meaning repair
  -> code log matches
  -> incident_trace_matches for prior compact ArkTS diagnosis traces
  -> bounded memory_edges and evidence_chains
  -> episodes
```

Treat experience candidates as decision frames, not proof. Check their
`hidden_assumptions`, `negative_preconditions`, `verification_method`,
`reuse_feedback`, `source_cases`, and optional `skill_candidate`; verify them against current source, logs, tests, and code wiki evidence before using them as conclusions.

Rules:

- Retrieved memory is advisory.
- Current source files are more authoritative than stored memory.
- Use `confidence`, `status`, `source`, `scope`, `evidence`, and `warning` fields when deciding what to inject.
- Avoid injecting stale or low-confidence memories as facts.
- Prefer reflections that include a clear trigger condition and repair action.
- Prefer experience candidates that also include hidden assumptions, negative preconditions, verification method, reuse feedback, and source cases.
- Treat `correction_experience` as guardrail context unless the user is explicitly asking about a mistake, conflict, failure, or misleading prior memory.
- Treat `semantic_patch_experience` as a code-business semantic repair note. Use it to inspect or update the anchored code wiki record, not as a general procedure.
- Do not let recency override `memory_intent`, `status`, `confidence`, or `blocked_memory_notes`.
- Treat reflections missing scope or actionability as weak hints, not strong rules.
- Keep injected context concise.
- Do not run merge, promotion, duplicate detection, or vault export from this skill.
- Do not manually maintain keyword lists for retrieval. Query misses are the feedback signal.
- Start with the user's natural-language problem. If results are weak, issue a sharper follow-up using matched file paths, symbols, routes, resources, log templates, or edge evidence.
- Prefer this order for the next recursive query:
  1. `suggested_followup_terms`
  2. top-hit `search_terms`
  3. exact file/symbol/log anchors from the current result
- When `search` is truncated, summarize the current batch first, then issue the next `search` call with `--cursor <next_cursor>` only if evidence is still incomplete.
- For bug diagnosis, use the diagnosis template to query memory recursively as the problem frame changes.
- For design/change planning, use the change design template to query memory recursively as the proposed plan changes.
- If a log statement matches, use related edges to refine the next query with the file path, function name, and message template.
- If `incident_trace_matches` appears, treat it as prior diagnosis evidence. Verify its linked code/log anchors against current source before following the suspected chain.
- If maintain output has marked a record low quality, stale, misleading, or conflicting, do not use recency alone to inject it into the main answer. Prefer high-quality, current, evidence-backed records when available.
- When query/context returns `quality_score` or `rerank_score`, use it only after checking the lane. A high-quality correction guard is still a guardrail, not the main task procedure, unless the query intent is about a correction, conflict, or failure.
- When evaluating retrieval changes, use `python tools/agent_memory.py eval-retrieval --project . --cases <golden-cases.json> --json` if a golden case file exists. Treat failures as regression evidence to inspect, not as automatic permission to rewrite memory.
- When evaluating trust calibration changes, use `python tools/agent_memory.py eval-calibration --project . --cases <golden-calibration.json> --json` if a calibration case file exists. Treat failures as evidence to inspect the trust model, feedback records, or case expectations.
- When evaluating whether answer claims are grounded in retrieved context, use `python tools/agent_memory.py eval-evidence-attribution --project . --cases <golden-evidence-attribution.json> --json` if a case file exists. Treat unsupported claims as a signal to improve context, answer framing, or evidence anchors.
- If a returned semantic fact or reflection is clearly weak-related, too broad, stale, wrong-domain, or misleading for the current query, record targeted feedback with `retrieval-feedback` instead of deleting it. This lets future similar queries down-rank the record while preserving it for other contexts.
- Do not ask the runtime for unbounded graph traversal. Recursive investigation should happen by issuing a sharper follow-up query.
