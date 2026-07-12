# Agent Memory Usage Guide

This project is designed for skill-first usage.

The user should not need to remember low-level commands during normal work. The intended flow is:

```text
User says what they want in natural language
  -> LLM chooses one of four Agent Memory skills
  -> Skill calls tools/agent_memory.py
  -> Runtime reads or writes SQLite
  -> Obsidian vault is exported for human review
```

The CLI remains the stable backend API and a debugging escape hatch.

## The Four Skills

| Skill | User intent | Main runtime commands |
|---|---|---|
| `agent-memory-learn` | Learn code from an entry file, directory, or whole project | `learn-entry`, `learn-path`, `wiki-index` |
| `agent-memory-query` | Search or retrieve memory context | `context`, `search`, `wiki-search` |
| `agent-memory-maintain` | Initialize, health-check, refresh, or sync | `init`, `doctor`, `wiki-index`, `vault-export` |
| `agent-memory-reflect` | Save lessons, facts, and task reflections | `reflect`, `update`, `vault-export` |

## 1. Install Into A Project

Run this once from the project root:

```bash
python install.py --project . --local-skills
```

This creates:

```text
.agent-memory/
  config.json
  projects/<project_id>/
    memory.db
    runtime/
    vault/
.agent-skills/
tools/agent_memory.py
```

The project directory is the code source. Memory data is stored in the current workspace `.agent-memory/` directory by default, next to `skills/` and `tools/`. Override it with `--memory-home <path>` or `AGENT_MEMORY_HOME=<path>`.

Verify:

```bash
python tools/agent_memory.py doctor --project .
```

## 2. Learn Part Of A Project

Prefer asking the Agent in natural language:

```text
Learn the code around tools/agent_memory.py.
```

Expected skill path:

```text
agent-memory-learn
  -> python tools/agent_memory.py learn-entry --project . --entry tools/agent_memory.py --depth 2 --json
```

If the source code lives outside the current memory archive directory, keep `--project .` for the archive/query context and add `--source` for the external source root:

```bash
python tools/agent_memory.py learn-entry --project . --source /path/to/app --entry entry/src/main/ets/pages/Index.ets --depth 2 --json
```

The runtime will:

```text
Read the entry file
  -> extract imports relative to the source root
  -> follow related files up to depth
  -> merge that file set into the current project archive's codebase wiki
  -> extract code log statements and rebuild file/function/log edges
  -> return parse_stats with file, symbol, log, language, and edge counts
  -> save an episode describing what was learned
```

`learn-entry --json` returns parse feedback:

```json
{
  "parse_stats": {
    "files_indexed": 1,
    "languages": { "ArkTS": 1 },
    "symbols_total": 4,
    "symbols_by_type": { "component": 1, "route": 1, "resource": 1 },
    "code_logs_total": 1,
    "code_logs_by_level": { "error": 1 },
    "memory_edges_total": 6
  }
}
```

Use `--replace` only when you want this learned scope to replace the current codebase wiki:

```bash
python tools/agent_memory.py learn-entry --project . --entry tools/agent_memory.py --depth 2 --replace --json
```

For a directory:

```text
Learn the skills directory.
```

Expected skill path:

```text
agent-memory-learn
  -> python tools/agent_memory.py learn-path --project . --path skills --json
```

External directory example:

```bash
python tools/agent_memory.py learn-path --project . --source /path/to/app --path entry/src/main/ets --json
```

Partial learning is incremental by default. A second `learn-path` call adds or refreshes that directory without removing previously learned files. Use `--replace` only for an explicit reset:

```bash
python tools/agent_memory.py learn-path --project . --path skills --replace --json
```

Each `wiki-index`, `learn-path`, and `learn-entry` run now also records a persistent learn-scope manifest in SQLite. That gives `agent-memory-maintain` a stable way to refresh those exact learned scopes later when the project changes, without asking the user to restate every path or entry file.

Learning also stores code log statements such as `print(...)`, `logger.error(...)`, `console.warn(...)`, and ArkTS `hilog.info(...)`. These are connected to learned files and nearest detected functions through `memory_edges`.

For HarmonyOS projects, learning also indexes `.json5` config files, ArkTS router targets, and `$r(...)` resource references as code wiki symbols. `learn-entry` can follow ArkTS router targets such as `router.pushUrl({ url: 'pages/Detail' })` to the related `.ets` page.

`learn-entry --json` and `learn-path --json` can also return `semantic_followup` immediately after structural indexing. Use it to start the next `learn-business` pass on the exact files just learned, rather than waiting for a later maintenance review.

For higher-quality business recall, the Agent should read the target files first, organize file/method/field/log business meaning, then write it with `learn-business`:

```bash
python tools/agent_memory.py learn-business --project . --payload "<json>" --json
```

This stores `business_summary` and `business_terms` directly on existing code file, symbol, and log records. Business terms should name real business objects such as profile, avatar, order status, device binding, user id, route names, resource keys, and log meanings.

`learn-business` is merge-oriented by default:

- it updates only the file, symbol, and log rows named in the payload
- it merges new `business_terms` into existing terms
- it keeps existing non-empty `business_summary` values unless the new value is identical
- if a new non-empty summary disagrees with an existing non-empty summary, the runtime returns `semantic_conflicts` instead of overwriting it

`learn-business --json` also returns semantic coverage feedback for the submitted scope:

```json
{
  "semantic_stats": {
    "files_total": 2,
    "files_with_business_summary": 1,
    "files_with_business_terms": 1,
    "symbols_total": 2,
    "symbols_with_business_summary": 1,
    "symbols_with_business_terms": 1,
    "logs_total": 2,
    "logs_with_business_summary": 1,
    "logs_with_business_terms": 1
  },
  "semantic_gaps": {
    "files_missing_business_summary": ["pages/Empty.ets"],
    "symbols_missing_business_terms": ["pages/ProfileDetail.ets::profileCache"],
    "logs_missing_business_summary": ["pages/ProfileDetail.ets::load profile start"]
  }
}
```

Use `semantic_stats` to judge whether the learned scope has enough business meaning for query. Use `semantic_gaps` to decide what the Agent should read and enrich next.

When gaps remain, `semantic_followup` provides a ready-made second-pass template:

```json
{
  "semantic_followup": {
    "command_template": "python tools/agent_memory.py learn-business --project . --payload '<json>' --json",
    "recommended_next_action": "run_learn_business_now",
    "truncated": false,
    "workflow_steps": [
      "Read the listed files, symbols, and logs in current source.",
      "Fill missing business_summary and business_terms in followup_payload_template.",
      "Write the completed payload with learn-business.",
      "Re-run learn-business, query, or maintain-plan to confirm the semantic gap is reduced."
    ],
    "followup_payload_template": {
      "files": [
        {
          "file_path": "pages/ProfileDetail.ets",
          "business_summary": "",
          "business_terms": [],
          "symbols": [{"symbol": "profileCache", "business_summary": "", "business_terms": []}],
          "logs": [{"message_template": "load profile start", "business_summary": "", "business_terms": []}]
        }
      ]
    }
  }
}
```

Use `priority_score` and `priority_reasons` on returned files to decide what to enrich first. If `truncated` is `true`, finish the visible batch, then rerun the learn or maintain flow to fetch the next semantic batch.
Use `hint_terms` as the initial candidate vocabulary for `business_terms`, and read `hint_context` before writing the new `business_summary`. This keeps later natural-language query terms aligned with real file, symbol, resource, route, and log anchors.

For the whole project:

```text
Refresh the whole codebase wiki.
```

Expected skill path:

```text
agent-memory-learn
  -> python tools/agent_memory.py wiki-index --project .
```

## 3. Query Memory

Ask:

```text
Before editing, check whether we have relevant memory for this task.
```

Expected skill path:

```text
agent-memory-query
  -> python tools/agent_memory.py context --project . --query "<task>" --json
```

When broader retrieval is needed, use batched search:

```bash
python tools/agent_memory.py search --project . --query "<task>" --per-type-limit 10 --aggregate-limit 8 --cursor 0 --json
```

If `search` returns `truncated: true`, continue only with `next_cursor` when the current evidence is still incomplete.
Use `suggested_followup_terms` from `context` or `search` as the first candidate set for the next recursive query. Add specific `search_terms` or exact anchors only after that.
If `followup_focus` is present, use it to decide whether the next recursive step should bias route, resource, log, or config anchors.
Use `log_search_plan` when the user reports a symptom that likely needs runtime log evidence. It turns the natural-language problem into:

- candidate code-log events
- high-signal search terms
- logger/tag hints
- file/function hints
- a recommended log inspection order

If `maintain-plan` returns `review_query_miss`, prefer its `suggested_query_terms` over inventing a fresh keyword set. Those terms combine the original miss wording with current code-memory hint anchors.
If `maintain-plan` returns `review_correction_experience`, use its `correction_targets`, `learning_rule_draft`, and `learn_business_payload_template` to repair the affected business semantics in place. Keep the repair scoped to the named file, symbol, or log records instead of broadening the learn scope first.

If a query returns no semantic facts, reflections, episodes, or wiki matches, the runtime records a query miss automatically. The user does not need to maintain keywords.

The runtime also performs lightweight query expansion before matching. It maps common symptom words to technical terms, especially for HarmonyOS/ArkTS work. For example:

```text
页面跳转后白屏 -> route, router, pushUrl, page, pages
图片资源显示不出来 -> resource, media, image, app.media, $r
加载用户资料失败日志 -> load, profile, failed, log, hilog, error
```

This is deterministic keyword expansion, not a vector database. If the first result is broad, the Agent should query again with matched anchors such as file paths, route names, resources, log templates, or function names.

Code and log matches include `search_terms` and `match_reasons`. `search_terms` expose the generated anchors used for retrieval. `match_reasons` explain whether a row matched by exact file path, exact symbol, log text, expanded query terms, or broader summary text.

Code log matches may also include `log_signal_score`, `log_signal_band`, `missing_signals`, and `suggested_log_fields`. Prefer stronger-signal logs as anchors for recursive diagnosis. Treat low-signal logs as evidence gaps, not as source truth.

When diagnosing an error message or observed output, query the message text directly. `context` may return `code_log_matches` and `edge_matches` that point to the likely file and function.

If the user also provides a temporary runtime log file, keep that raw file out of long-term memory and analyze it as bounded evidence:

```bash
python tools/agent_memory.py analyze-runtime-log \
  --project . \
  --query "个人资料页空白，怀疑登录态异常" \
  --log-file ./profile-runtime.log \
  --json
```

This command reuses current code/log memory, normalizes raw lines into lightweight events, and returns only a few scored slices plus:

- `session_candidates`
- `runtime_episode_candidate`
- `log_improvement_suggestions`
- `reflect_payload_template`

Use `runtime_episode_candidate.candidate_chain` and `chain_confidence` when you need a compact explanation of how the incident unfolded.
Use `log_improvement_suggestions` when the current logs were just barely enough; they point at a few high-value start, branch, or correlation logs worth adding to the source code later.
Use `log_signal_summary` and `low_signal_events` to judge whether matched runtime evidence has enough fields for diagnosis. A poor signal event may still match the query, but it lacks fields such as `request_id`, `session_id`, `route`, `resource`, `reason`, `error_code`, or `result`; use `suggested_log_fields` as narrow logging-improvement guidance.
When matched events include `otel_lite`, prefer those structured fields for the LLM-facing summary: severity, logger, event name, request id, session id, error code, reason, route, and resource. Use raw excerpts only when the structured fields are insufficient.
Use `reflect_payload_template` as the starting point when you want to turn temporary runtime-log evidence into a structured reflection or experience candidate. It is designed for diagnosis sessions, not for long-term raw-log archival. The template now also carries bounded `evidence`, `misleading_followup_terms`, and a concrete `repair_action`. When the query is correcting an earlier diagnosis, the template may already switch to `correction_experience` and include `old_hypothesis`.
The runtime also keeps a rolling `runtime/last_usage_sample.json` during `context`, `search`, `analyze-runtime-log`, and `maintain-plan`. This is a bounded runtime-side summary, not a new long-term database row. A later `reflect` call can reuse it automatically to fill missing fields such as `task_type`, `problem`, `query_rounds`, `useful_followup_focus`, `useful_followup_terms`, `misleading_followup_terms`, `inspection_targets`, `evidence`, and `repair_action`.
The runtime also keeps bounded performance samples in `runtime/performance_samples.jsonl`. `maintain-health --json` and `maintain-plan --json` summarize those samples as `runtime_performance` so Agents can see whether `maintain-plan`, `context`, or other operations are becoming slow, token-heavy, or storage-heavy. Do not treat this JSONL file as project knowledge; it is local operational telemetry. If `review_runtime_performance_budget` appears, prefer tightening query limits, reviewing noisy memory records, refreshing stale context, or splitting expensive maintenance work before adding heavier indexing.

`maintain-plan --json` may include `quality_summary`, `low_quality_records`, and `high_value_records`. Use these as review hints:

- low-quality records should be verified, tightened, marked stale, or merged;
- high-value records are better candidates for reuse, promotion review, or future skill-pattern clustering;
- a high score does not override current source code, current user instructions, or explicit conflict signals.
Query outputs may also include `quality_score`, `quality_band`, `quality_reasons`, and `rerank_score` on semantic and reflection matches. Prefer higher-quality matches when several records point in the same direction, but still obey `memory_intent`, `correction_guards`, `semantic_patch_notes`, `blocked_memory_notes`, and current source code.
Reflection rows may include `experience_maturity`, `experience_maturity_score`, `maturity_reasons`, and `counter_evidence`. Treat `raw_observation` as a hint only, prefer `verified_case` and `reused_pattern` when evidence agrees, and treat `deprecated_pattern` as warning or counter-evidence. If a high-value procedure lacks counter-evidence, verify where it does not apply before using it as a rule.
Query outputs also include `memory_use_policy`, and rows may include `trust_level`, `trust_score`, `trust_reasons`, `retrieval_explanation`, `query_risk_flags`, `trust_cap`, and `trust_cap_reasons`. Use `source_truth` and `verified_experience` before ordinary hints. Treat `weak_hint` as a lead for the next inspection, not a conclusion. Treat `possibly_stale` and `conflict_warning` as caution signals even when the record matched the query.

Read `query_risk_flags` before using a reflection as task direction. `misleading_experience`, `deprecated_experience`, and `inactive_or_stale_experience` are hard warnings. `missing_counter_evidence` means the procedure may be useful but still lacks negative applicability boundaries; verify current source, logs, and tests before using it as a rule. `semantic_correction_guidance` means the row should repair or constrain interpretation, not become a generic procedure.

When recording experience, keep procedure and correction records distinct. Use `procedure_experience` for reusable diagnosis or repair workflows, and include trigger, repair, verification, and negative preconditions. Use `correction_experience` for wrong business/code semantics or misleading prior memory, and include the old misleading pattern plus the corrected action. Do not attach `skill_candidate` to correction experience; it should be reviewed as semantic repair or guardrail evidence instead.
`maintain-plan --json` may turn those scores into confirmable actions:

- `review_low_quality_memory`: inspect the record, then choose a narrow fix such as source verification, trigger tightening, confidence lowering, stale marking, or merge review.
- `review_high_value_experience`: prioritize the experience for reuse, skill-pattern review, semantic-repair review, or promotion review. Do not promote it automatically.
- `review_missing_counter_evidence`: add negative preconditions, does-not-apply cases, or counter examples before treating the experience as a rule.
- `review_immature_experience` and `review_maturity_regression`: add missing structure or deprecate/rewrite experience that became misleading.

When reflections cite incident traces in `source_cases`, for example `incident_trace:7`, `maintain-plan` can also report evidence-chain fields. Prefer experiences with strong evidence chains when several records are otherwise similar. If `review_weak_evidence_chain` appears, keep the experience usable but verify whether it should be linked to an incident trace, code log, symbol, or file anchor.

`maintain-health --json` reports `graph_quality`. If it shows orphan code logs, orphan symbols, stale edges, or poor anchor coverage, prefer a focused `learn-entry` or `learn-path` refresh around the affected source scope before broad re-learning. `review_graph_quality` in `maintain-plan` is a review prompt, not an automatic graph repair.

`maintain-health --json` also reports `graph_signal_quality`. Structural graph health tells you whether anchors and edges exist; signal quality tells you whether those anchors carry enough business/log meaning to help the next Agent. Use `top_repair_targets` as a focused queue for `learn-business` enrichment or source logging improvements.

`maintain-health --json` and `maintain-plan --json` also report `active_learning_queue`. Use it as the first triage view when many governance signals exist. It ranks open query misses, weak graph/log anchors, misleading or helpful experience usage, and low-quality memories into a single bounded queue. The queue is read-only; follow the underlying action type before changing memory.

Before changing retrieval ranking, quality scoring, learn-business semantics, code graph extraction, or log graph extraction, run a golden-query evaluation if a case file exists:

```bash
python tools/agent_memory.py eval-retrieval --project . --cases docs/eval/golden-retrieval.json --json
```

The eval command reads JSON cases and uses the normal `context` path. `expected` entries define anchors that should appear; `must_not_include` entries define records that should stay out of the named result lane. Use `expected_top` when an exact code/log/experience anchor must be first in its result lane. Use `noise` to measure high-trust distracting experience that still leaks into results. A failing case is a regression signal for review, not an automatic memory mutation.

Before changing trust calibration, feedback handling, or answer-time memory policy, run calibration evaluation if a case file exists:

```bash
python tools/agent_memory.py eval-calibration --project . --cases docs/eval/golden-calibration.json --json
```

`expected_trust` entries define records that should carry a target trust level or minimum trust score. `must_not_trust` entries define records that must not be treated as strong evidence. A failure means inspect the calibration model, feedback records, or case expectations before changing stored memory.

Before changing log parsing, log signal scoring, or runtime-log diagnosis output, run log signal evaluation if a case file exists:

```bash
python tools/agent_memory.py eval-log-signal --project . --cases docs/eval/golden-log-signal.json --json
```

Each case contains short temporary `logs` plus optional `min_good_rate` and `max_low_signal_rate`. The command reports `log_signal_good_rate` and `low_signal_event_rate`; it does not persist the raw log lines.

Before changing answer composition, evidence ranking, code graph, log graph, or experience quality behavior, run evidence attribution evaluation if a case file exists:

```bash
python tools/agent_memory.py eval-evidence-attribution --project . --cases docs/eval/golden-evidence-attribution.json --json
```

Each case contains a query and answer claims. The command uses the normal `context` path and reports grounded, weak, and unsupported claims. Treat unsupported claims as a signal to improve retrieval anchors, log/code semantics, or answer framing.

When a result is clearly distracting for a specific query, record retrieval feedback instead of deleting the memory:

```bash
python tools/agent_memory.py retrieval-feedback \
  --project . \
  --query "<query>" \
  --type reflection \
  --id 12 \
  --reason weak_related \
  --json
```

Valid retrieval reasons are `weak_related`, `stale`, `wrong_domain`, `too_broad`, and `misleading`. Calibration reasons are `useful`, `verified_useful`, `undertrusted`, and `overtrusted`. Future similar queries apply bounded penalties or bonuses to that record and expose `feedback_penalty` plus `calibration_feedback_*` fields. `maintain-plan` surfaces `review_retrieval_feedback`, `review_overtrusted_memory`, or `review_undertrusted_memory` so the record can later be tightened, lowered in confidence, strengthened with evidence, marked stale, merged, or left alone if the feedback is not reproducible.

After the Agent actually uses a returned semantic fact or reflection, record the task outcome when it is clearly helpful, ignored, misleading, or superseded:

```bash
python tools/agent_memory.py experience-usage \
  --project . \
  --query "<query that retrieved the memory>" \
  --type reflection \
  --id 12 \
  --outcome helpful \
  --note "<short outcome note>" \
  --json
```

This is the lightweight closed loop for experience quality. Future similar queries expose `usage_feedback_bonus`, `usage_feedback_penalty`, and `usage_feedback_reasons`, so useful experience can rise slightly and misleading experience can stop steering the main task.

After repeated runtime-log-backed diagnosis, `maintain-plan --json` may also return:

- `review_incident_strategy_candidate`
- `review_recurring_incident_fingerprint`
- `review_log_design_gap`

Use the incident-strategy path when the diagnosis flow itself is becoming reusable. Use the recurring-fingerprint path when you mainly need a compact summary of repeated signals without storing more runtime history. Use the log-design-gap path when the evidence shows a narrow logging weakness worth fixing in source.

Ask:

```text
Search the codebase wiki for memory runtime commands.
```

Expected skill path:

```text
agent-memory-query
  -> python tools/agent_memory.py wiki-search --project . --query "memory runtime commands" --json
```

`wiki-search` also returns matching code log statements with `kind: "log_statement"`.

For workflows that need repeated query refinement, use the integration templates:

```text
Bug diagnosis:
  docs/templates/diagnosis-memory-query-template.md

Design or modification planning:
  docs/templates/change-design-memory-query-template.md

Recommended local Agent CLI loop:

```text
learn-entry / learn-path
  -> inspect parse_stats
  -> if semantic_followup.recommended_next_action == run_learn_business_now:
       fill followup_payload_template
       run learn-business
  -> run context
  -> if evidence is broad or truncated:
       run search with per-type and aggregate limits
       continue with --cursor <next_cursor> only when needed
  -> if maintain-plan returns review_query_miss:
       retry search with suggested_query_terms before broadening learn scope
  -> if maintain-plan returns semantic_gap_targets or review_semantic_conflict:
       enrich or review before broad re-indexing
```

To review durable semantic conflicts directly:

```bash
python tools/agent_memory.py list --project . --type semantic-conflict --json
python tools/agent_memory.py conflict-status --project . --id "<id>" --status resolved --resolution "<decision>"
python tools/agent_memory.py conflict-apply --project . --id "<id>" --resolution "<decision>" --decision-note "<evidence>" --replacement-source "<source anchor>"
```

`conflict-apply` is exact-match only. If the target would affect multiple stored symbols or logs, the runtime stops and asks for manual cleanup first.
If `maintain-plan` returns `apply_command_template` for a conflict, use that exact command after reviewing current source and confirming the incoming summary is correct.
When `maintain-plan` returns `learn_business_payload_template` with `hint_terms` and `hint_context`, reuse those anchors directly instead of inventing new terminology for the enrichment pass.

General memory-aware answering with logs:
  docs/templates/memory-query-answer-skill-template.md
```

These templates are meant to be copied into other skills. They keep `agent-memory-query` simple while allowing recursive memory-aware reasoning.

## 4. Maintain Memory System

Ask:

```text
Initialize memory for this project.
```

Expected skill path:

```text
agent-memory-maintain
  -> python tools/agent_memory.py init --project .
  -> python tools/agent_memory.py doctor --project .
```

Ask:

```text
Check memory system health.
```

Expected skill path:

```text
agent-memory-maintain
  -> python tools/agent_memory.py doctor --project .
  -> python tools/agent_memory.py maintain-health --project . --json
```

Ask:

```text
检查记忆系统健康状况，并整理需要 review 的记忆。
```

Expected skill path:

```text
agent-memory-maintain
  -> python tools/agent_memory.py maintain-health --project . --json
  -> python tools/agent_memory.py maintain-plan --project . --json
```

The Agent should group the proposed actions by risk and ask for confirmation before mutating memory. Query miss actions are low-risk signals that suggest the Agent may need to learn a path, add a durable fact, or ignore the miss. It may then execute confirmed actions:

```bash
python tools/agent_memory.py maintain-status --project . --type semantic --id 12 --status stale --reason "source changed"
python tools/agent_memory.py maintain-merge --project . --type semantic --ids 3,8 --fact "..."
python tools/agent_memory.py maintain-promote --project . --episode-id 9 --fact "..."
python tools/agent_memory.py miss-status --project . --id 7 --status resolved --resolution "learned relevant directory"
```

Ask:

```text
Refresh what we already learned from the project, and retire stale structural code memory.
```

Expected skill path:

```text
agent-memory-maintain
  -> python tools/agent_memory.py maintain-refresh-scope --project . --json
```

Optional narrow refresh:

```bash
python tools/agent_memory.py maintain-refresh-scope --project . --scope-id 3 --json
```

This is the low-risk update path for changing codebases:

- replay previously learned scopes from `learn_scopes`
- refresh current file, symbol, log, and edge structure
- retire structural rows for files removed from that learned scope
- return `semantic_review_targets` for added, changed, or removed files whose business meaning may now need review

Use it before broad `--replace` re-learning when the project has evolved but you want to preserve accumulated business semantics and experience review history.

After a refresh, `maintain-plan` may return:

- `review_semantic_drift`
- `mark_experience_stale_if_anchor_removed`
- `review_skill_pattern_staleness`

Use the first to drive focused `learn-business` repair. Use the second to review older reflections or experience candidates that still point at files removed from the refreshed scope.

`maintain-plan` is read-only. Actions with `command: null` need the Agent to draft a replacement fact or durable lesson before execution.

Ask:

```text
Sync memory to Obsidian.
```

Expected skill path:

```text
agent-memory-maintain
  -> python tools/agent_memory.py vault-export --project .
```

## 5. Reflect And Remember

Ask:

```text
Reflect on this task and save the lesson.
```

Expected skill path:

```text
agent-memory-reflect
  -> python tools/agent_memory.py reflect ...
  -> python tools/agent_memory.py vault-export --project .
```

Prefer structured reflection fields when possible:

```bash
python tools/agent_memory.py reflect \
  --project . \
  --payload '{
    "experience_type": "procedure_experience",
    "task_type": "diagnosis",
    "outcome": "success",
    "problem": "Profile page opens blank after navigation.",
    "task": "diagnose profile blank page",
    "summary": "Queried memory, inspected route registration, and found a route path mismatch.",
    "reasoning_summary": "The useful clue was the route edge plus router.pushUrl log.",
    "context_used": ["query: profile blank page route", "file: pages/Home.ets", "log: router.pushUrl failed"],
    "what_worked": ["Search by business page name", "Check route edges"],
    "what_failed": ["Searching only generic blank-screen terms"],
    "query_rounds": 3,
    "trajectory_summary": "The first query was broad, the second locked onto route edges, and the third inspection confirmed the target page mismatch.",
    "useful_followup_focus": "route",
    "useful_followup_terms": ["profile", "router.pushUrl", "pages/ProfileDetail"],
    "misleading_followup_terms": ["blank screen"],
    "inspection_targets": ["pages/Home.ets", "pages/ProfileDetail.ets", "router.pushUrl failed"],
    "final_verification_path": "Reproduce navigation -> inspect route registration -> confirm router target mismatch.",
    "related_cases": ["case_profile_route_001"],
    "lesson": "ArkTS blank-screen diagnosis should combine business page names with route terms.",
    "future_rule": "When a HarmonyOS page opens blank after navigation, query business page terms plus route/router terms first.",
    "trigger_condition": "Page opens blank after route navigation",
    "repair_action": "Query memory with business page name, route terms, and related log template"
  }'
```

Use `experience_type` only to classify the reflection:

- `procedure_experience` for reusable diagnosis/query/repair/change-design workflows
- `correction_experience` for semantic correction and learn-governance feedback

This does not change the user-facing interface. The user still works through the same four skills.

When the Agent has enough context, also record the compressed trace-case fields instead of a long transcript:

- `query_rounds`
- `trajectory_summary`
- `useful_followup_focus`
- `useful_followup_terms`
- `misleading_followup_terms`
- `inspection_targets`
- `final_verification_path`
- `related_cases`

These help later experience review and future skill-pattern extraction without adding a fifth skill.

Use the argument form for short manual notes:

```bash
python tools/agent_memory.py reflect \
  --project . \
  --task "<task>" \
  --summary "<what happened>" \
  --mistake "<what went wrong or empty>" \
  --lesson "<durable lesson>" \
  --future-rule "<rule for next time>" \
  --scope "<where this applies>" \
  --evidence "<file, command, or episode>" \
  --trigger-condition "<when to remember this>" \
  --anti-pattern "<mistake pattern to avoid>" \
  --repair-action "<concrete next action>" \
  --applies-to "<valid scope>" \
  --does-not-apply-to "<invalid scope>" \
  --confidence 0.8
```

When a task used older reflections, record whether they helped:

```bash
python tools/agent_memory.py reflect \
  --project . \
  --task "<task>" \
  --lesson "<new lesson>" \
  --used-reflection-ids "3,8" \
  --reflection-outcome helped
```

Valid reuse outcomes are:

```text
helped
partial
misleading
unused
```

The runtime updates the older reflection's aggregate reuse fields and writes
auditable `reflection_reuse_events` rows. Vault export mirrors the history in
`Governance/Reflection Reuse.md`.

When repeated `procedure_experience` reflections cluster into the same `skill_candidate`,
`maintain-plan --json` can return `review_skill_pattern_candidate`. After review, write
the current draft into the repo with:

```bash
python tools/agent_memory.py maintain-skill-draft \
  --project . \
  --pattern-name "arkts-route-blank-screen-diagnosis" \
  --json
```

This writes:

```text
docs/skill-candidates/arkts-route-blank-screen-diagnosis.md
```

The generated draft starts with YAML frontmatter so later review or promotion tooling can read:

- `artifact_type: skill_candidate_draft`
- `promotion_status: draft`
- `review_status`
- `reviewer`
- `review_notes`
- `supporting_reflection_ids`
- `common_followup_focus`
- `supporting_cases`

The file is still a draft artifact. It does not create a formal skill under `skills/`.

When repeated runtime-log-backed diagnosis reflections describe the same incident workflow,
`maintain-plan --json` can also return `review_incident_strategy_candidate`. After review, write
the grouped diagnosis policy into the repo with:

```bash
python tools/agent_memory.py maintain-incident-strategy-draft \
  --project . \
  --strategy-name "log-auth-session-profile-blank-diagnosis" \
  --json
```

This writes:

```text
docs/incident-strategies/log-auth-session-profile-blank-diagnosis.md
```

These drafts are for reusable incident-diagnosis strategies:

- goal symptoms
- common log events
- recommended steps
- verification paths
- misleading signals
- log design feedback

Treat them as the bridge between repeated runtime incidents and later skill evolution, not as formal installed skills.

To write every currently clustered draft candidate in one pass:

```bash
python tools/agent_memory.py maintain-skill-draft \
  --project . \
  --pattern-name all \
  --json
```

When a reviewed draft should become a candidate skill package:

```bash
python tools/agent_memory.py maintain-skill-package \
  --project . \
  --pattern-name "arkts-route-blank-screen-diagnosis" \
  --json
```

This writes:

```text
skills/_candidates/arkts-route-blank-screen-diagnosis/SKILL.md
skills/_candidates/arkts-route-blank-screen-diagnosis/PROMOTION.md
```

The candidate package also includes YAML frontmatter such as:

- `artifact_type: skill_candidate_package`
- `promotion_status: candidate`
- `review_status`
- `reviewer`
- `review_notes`
- `source_draft`

`maintain-plan` and the vault review page also expose the stage directly:

- `promotion_stage: clustered`
- `promotion_stage: draft`
- `promotion_stage: candidate_package`

When the draft or candidate package already exists, runtime outputs also surface:

- `draft_review_status`
- `package_review_status`
- `review_guidance`
- `promotion_readiness`
- `quality_score`
- `quality_reasons`

Treat these as confidence signals for reviewers, not as automatic promotion switches.

If a draft or candidate package already has human review metadata such as a real reviewer or a non-`pending_review` status, rerunning the write command preserves that artifact and returns a warning instead of overwriting the review work.
The vault `Governance/Skill Pattern Candidates.md` page mirrors the same stage, reviewer, and preservation-policy information so human review in Obsidian sees the same boundary conditions as the runtime JSON.
The vault `Governance/Incident Strategy Candidates.md` page mirrors grouped runtime-log-backed diagnosis strategies so reviewers can inspect recurring incident patterns without reopening raw logs.

`maintain-plan --json` may also return `review_log_design_gap` when repeated runtime-log-backed diagnosis reflections point to the same missing log design signals. Treat it as a narrow code-quality review action:

- inspect `goal_area` and `goal_symptoms`
- use `high_value_log_anchor_targets` as the first patch targets
- use `suggested_log_kinds` to decide whether the code needs a start marker, decision checkpoint, or request/session correlation field
- keep the patch small and tied to the matched code-log anchors

It is still a candidate package, not a formal installed skill.
Promotion into `skills/<name>/` remains manual. Use `docs/skill-promotion-rules.md` as the review checklist before treating any candidate package as a real skill.
The generated `PROMOTION.md` next to the candidate package is the concrete manual execution template for that final step.

Review reflection quality:

```bash
python tools/agent_memory.py reflect-review --project . --json
```

Ask:

```text
Remember that this project treats SQLite as the source of truth.
```

Expected skill path:

```text
agent-memory-reflect
  -> python tools/agent_memory.py update --project . --type semantic --fact "..." --source user --confidence 1.0
```

## 6. Manual CLI Fallback

When debugging or scripting, call the runtime directly:

```bash
python tools/agent_memory.py learn-entry --project . --entry tools/agent_memory.py --depth 2 --json
python tools/agent_memory.py learn-entry --project . --source /path/to/app --entry entry/src/main/ets/pages/Index.ets --depth 2 --json
python tools/agent_memory.py learn-path --project . --path skills
python tools/agent_memory.py learn-path --project . --source /path/to/app --path entry/src/main/ets
python tools/agent_memory.py learn-path --project . --path skills --replace
python tools/agent_memory.py context --project . --query "..." --json
python tools/agent_memory.py update --project . --type semantic --fact "..." --source user --confidence 1.0
python tools/agent_memory.py reflect --project . --task "..." --lesson "..."
python tools/agent_memory.py reflect-review --project . --json
python tools/agent_memory.py maintain-health --project . --json
python tools/agent_memory.py maintain-review --project . --json
python tools/agent_memory.py maintain-plan --project . --json
python tools/agent_memory.py maintain-skill-draft --project . --pattern-name "..." --json
python tools/agent_memory.py maintain-skill-draft --project . --pattern-name all --json
python tools/agent_memory.py maintain-incident-strategy-draft --project . --strategy-name "..." --json
python tools/agent_memory.py maintain-skill-package --project . --pattern-name "..." --json
python tools/agent_memory.py maintain-skill-promotion-status --project . --pattern-name "..." --json
python tools/agent_memory.py miss-list --project . --status open --json
python tools/agent_memory.py miss-status --project . --id 1 --status ignored --resolution "not useful"
python tools/agent_memory.py vault-export --project .
```

When the memory archive grows large, `vault-export` keeps the Obsidian mirror review-friendly by truncating large aggregate pages and exporting only a bounded recent set of per-record episode/reflection notes. The generated Markdown will say when it is truncated; use the runtime and SQLite data as the complete source of truth.

## 7. Obsidian Review

Export the vault:

```bash
python tools/agent_memory.py vault-export --project .
```

Open this directory in Obsidian:

```text
.agent-memory/projects/<project_id>/vault/
```

Obsidian is a read-only review mirror in the MVP. Edit memory through skills or CLI commands, then export again.

## 8. Design Rule

When adding new features, preserve this direction:

```text
Natural language request first
One of four skills chooses action
Runtime command performs deterministic work
SQLite remains source of truth
Obsidian remains review mirror
```

## 9. Governance Performance Rule

Keep regular retrieval fast:

```text
agent-memory-query consumes governance metadata.
agent-memory-reflect writes local lessons and lightweight metadata.
agent-memory-maintain performs heavier review, merge, stale, promote, and export work.
```

Do not run duplicate detection, promotion, or vault dashboard generation on every query.

## 10. ArkTS Incident Trace

When the user provides a symptom plus temporary runtime logs, store only a compact trace:

```bash
python tools/agent_memory.py incident-trace \
  --project . \
  --symptom "页面跳转后白屏" \
  --log-text "router.pushUrl failed for ProfileDetail" \
  --json
```

`incident-trace` records the ArkTS scene, short log excerpt, dominant events, matched code log anchors, and candidate chain. It does not store the full raw log stream. Later `context` or `search` calls may return `incident_trace_matches`; maintain can review resolved traces and suggest a reflection payload with `source_cases: ["incident_trace:<id>"]`.
