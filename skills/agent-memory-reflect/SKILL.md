---
name: agent-memory-reflect
description: Use after completing, failing, debugging, or changing a local agent task to save reflections, lessons, durable facts, and reusable project knowledge.
---

# Agent Memory Reflect

Use this skill to write durable lessons after work.

The local Agent CLI must lead the reflection. After one successful or failed diagnosis,
design, execution, or workflow attempt, first organize the task into structured data.
Then call the runtime to store it.

A reflection is an experience candidate, not accepted experience. The Agent must capture
the assumptions, invalid cases, verification method, source cases, and reuse feedback
needed for future Agents to decide whether the lesson should transfer.

When the task included multiple query rounds or inspection pivots, also capture the
compressed trace-case fields instead of a long transcript:

- `query_rounds`
- `trajectory_summary`
- `useful_followup_focus`
- `useful_followup_terms`
- `misleading_followup_terms`
- `inspection_targets`
- `final_verification_path`
- `related_cases`

When the reflection clearly belongs to a future governance path, include `experience_type`:

- `procedure_experience`: reusable diagnosis, query, repair, or change-design workflow
- `correction_experience`: guardrail for a wrong assumption, misleading memory, or failed retrieval direction
- `semantic_patch_experience`: anchored correction or enrichment of code business semantics

When recording `procedure_experience`, include `trigger_condition`, `repair_action`, and `verification_method`. This keeps reusable workflows from becoming broad advice.

When recording `correction_experience`, include enough evidence for later guardrail governance:

- affected file, symbol, or log anchors in `source_cases` or `inspection_targets`
- the misleading old understanding in `what_failed` or `misleading_followup_terms`
- the corrected understanding in `lesson`, `future_rule`, and `repair_action`
- `negative_preconditions`, so query can avoid applying the correction to similar-but-wrong cases
- if the input came from temporary runtime-log analysis, carry over `runtime_episode_candidate` evidence through `context_used`, `trajectory_summary`, `final_verification_path`, and `old_hypothesis` when present
- keep bounded runtime evidence in the reflection instead of raw logs: prefer `evidence`, `misleading_followup_terms`, and `repair_action` from `reflect_payload_template`

Do not set `skill_candidate` on `correction_experience`. A correction may later improve a skill or code semantic record, but a single correction should first become guardrail or semantic-repair evidence. Only `procedure_experience` should carry a `skill_candidate`, and only when the workflow has verification and reuse support.

When recording `semantic_patch_experience`, bind it to a concrete code-memory anchor:

- `anchor_type`: `code_file`, `code_symbol`, `code_log_statement`, or `memory_edge`
- `anchor_key`: file path, `file::symbol`, or `file::log template`
- `semantic_field`: `business_summary`, `business_terms`, `business_event`, `trigger_stage`, `symptom_terms`, `likely_causes`, `process_hint`, or `neighbor_terms`
- `existing_value`, `proposed_value`, and `patch_reason`

Semantic patches are not normal task procedures. They should be reviewed through `agent-memory-maintain` and applied through focused `learn-business` when current source supports the patch.

For runtime-log-backed diagnosis, also keep the feedback loop explicit:

- preserve the strongest runtime signals in `useful_followup_terms`
- preserve misleading or disproven directions in `misleading_followup_terms`
- preserve the closing verification path in `final_verification_path`
- if `analyze-runtime-log` returned `otel_lite`, use those structured severity/logger/event/request/session/error fields in `evidence` or `context_used` instead of copying large raw log excerpts

That lets `reflect-review`, `maintain-plan`, recurring incident fingerprints, and incident strategy candidates reuse the same bounded runtime evidence without storing raw logs.

When recent work already ran `context`, `search`, `analyze-runtime-log`, or `maintain-plan`, the runtime keeps a bounded `runtime/last_usage_sample.json` and `runtime/last_task_trace.json`. You can lean on those files instead of retyping everything. A minimal reflection payload can still inherit missing structured fields such as:

- `task_type`
- `problem`
- `query_rounds`
- `useful_followup_focus`
- `useful_followup_terms`
- `misleading_followup_terms`
- `inspection_targets`
- `trajectory_summary`
- `evidence`
- `repair_action`

Use `--from-last-task` when the latest trace is the right starting point:

```bash
python tools/agent_memory.py reflect --project . --from-last-task --task "<task>" --lesson "<lesson>" --json
```

Explicit payload values still win. The usage sample and task trace are runtime-side helpers and are closed after the reflection is written.

If `maintain-plan` reports `review_low_evidence_auto_summary`, inspect the trace's `auto_summary_quality` and fill the missing fields before writing. Treat `reflection_payload_placeholders` as prompts only; do not copy TODO placeholder text into durable memory. At minimum, add a real `verification_method`, concrete `repair_action`, and either `negative_preconditions` or `does_not_apply_to` for reusable procedure experience.

This does not add a fifth skill. It only helps `maintain-plan` route the reflection toward future skill-candidate review or toward learn/semantic-repair governance.

If the task used an existing semantic fact or reflection, record the usage outcome after reflection when the result clearly helped or misled the task:

```bash
python tools/agent_memory.py experience-usage --project . --query "<query>" --type reflection --id "<id>" --outcome helpful --json
```

Use `helpful` for records that materially improved the task, `ignored` for records that were retrieved but not useful, `misleading` for records that pulled the Agent toward a wrong path, and `superseded` when a newer or current-source-backed record replaced the old guidance.

## Save Agent-Structured Reflection

Prefer this JSON payload form when the Agent has enough context:

```bash
python tools/agent_memory.py reflect \
  --project . \
  --payload '{
    "task_type": "diagnosis",
    "outcome": "success",
    "problem": "Profile page opens blank after navigation.",
    "task": "diagnose profile blank page",
    "summary": "Queried memory, inspected route registration, and found a route path mismatch.",
    "reasoning_summary": "The useful clue was the route edge plus the router.pushUrl log.",
    "context_used": [
      "query: profile blank page route",
      "file: entry/src/main/ets/pages/Home.ets",
      "log: router.pushUrl failed",
      "reflection:#3"
    ],
    "what_worked": [
      "Search by business page name before scanning all pages.",
      "Check route edges before editing UI state."
    ],
    "what_failed": [
      "Searching only generic blank-screen terms was too broad."
    ],
    "hidden_assumptions": [
      "The page blanked after route navigation, not during static rendering.",
      "The destination page was expected to be registered."
    ],
    "negative_preconditions": [
      "Do not apply when no route navigation occurred.",
      "Do not apply to pure layout visibility bugs."
    ],
    "query_rounds": 3,
    "trajectory_summary": "The first query was broad, the second locked onto route edges, and the third inspection confirmed the target page mismatch.",
    "useful_followup_focus": "route",
    "useful_followup_terms": [
      "profile",
      "router.pushUrl",
      "pages/ProfileDetail"
    ],
    "misleading_followup_terms": [
      "blank screen"
    ],
    "inspection_targets": [
      "entry/src/main/ets/pages/Home.ets",
      "entry/src/main/ets/pages/ProfileDetail.ets",
      "log: router.pushUrl failed"
    ],
    "final_verification_path": "Reproduce navigation -> inspect route registration -> confirm router target mismatch.",
    "related_cases": [
      "case_profile_route_001"
    ],
    "verification_method": "Confirm route registration, inspect router logs, and reproduce navigation.",
    "reuse_feedback": "experience candidate until reused on another route issue",
    "source_cases": [
      "episode:profile-route-mismatch",
      "reflection:#3",
      "file: entry/src/main/ets/pages/Home.ets",
      "log: router.pushUrl failed"
    ],
    "skill_candidate": "arkts-route-blank-screen-diagnosis",
    "mistake": "The first query omitted the business page name.",
    "lesson": "ArkTS blank-screen diagnosis should combine the business page name with route terms.",
    "future_rule": "When a HarmonyOS page opens blank after navigation, query business page terms plus route/router terms first.",
    "scope": "HarmonyOS ArkTS route diagnosis",
    "evidence": "entry/src/main/ets/pages/Home.ets router.pushUrl",
    "trigger_condition": "Page opens blank after route navigation",
    "anti_pattern": "Only search generic symptom terms",
    "repair_action": "Query memory with business page name, route terms, and related log template",
    "applies_to": "ArkTS routing and page navigation failures",
    "does_not_apply_to": "Pure layout rendering bugs without navigation",
    "confidence": 0.9
  }'
```

For large payloads, write JSON to a temporary file and call:

```bash
python tools/agent_memory.py reflect --project . --payload-file "<review.json>"
```

When the work mainly corrected code business semantics, prefer a focused `semantic_patch_experience`:

```bash
python tools/agent_memory.py reflect \
  --project . \
  --payload '{
    "experience_type": "semantic_patch_experience",
    "task_type": "workflow",
    "outcome": "success",
    "task": "correct profile load semantics",
    "summary": "Corrected the learned business meaning for loadProfile.",
    "lesson": "loadProfile should include session validation in its business meaning.",
    "anchor_type": "code_symbol",
    "anchor_key": "pages/Profile.ets::loadProfile",
    "semantic_field": "business_summary",
    "existing_value": "loads profile page UI",
    "proposed_value": "loads profile data and validates session state before rendering",
    "patch_reason": "Caller flow and runtime logs show session validation happens before render.",
    "verification_method": "Inspect caller, related log statement, and session handling code.",
    "trigger_condition": "Learned business meaning conflicts with current source.",
    "repair_action": "Apply the semantic patch through learn-business after source review.",
    "evidence": "pages/Profile.ets loadProfile + session invalid log",
    "confidence": 0.88,
    "applies_to_current_code": true
  }'
```

After writing this reflection:

1. Run `python tools/agent_memory.py maintain-plan --project . --json`
2. Review the `review_semantic_patch` action
3. Apply the returned `learn_business_payload_template` through `learn-business` if current source supports the patch

`reflect` does not overwrite `code_files`, `code_symbols`, or `code_log_statements` by itself. It stores the semantic correction candidate first, then maintain and learn governance decide whether to apply it.

Valid `task_type` values:

- `diagnosis`
- `design`
- `execution`
- `workflow`

Valid `outcome` values:

- `success`
- `failure`
- `partial`

## Save Reflection

The argument form remains available for short reflections:

```bash
python tools/agent_memory.py reflect \
  --project . \
  --task "<task>" \
  --summary "<what happened>" \
  --mistake "<mistake or empty>" \
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

When this task reused earlier reflections, record the feedback:

```bash
python tools/agent_memory.py reflect \
  --project . \
  --task "<task>" \
  --lesson "<new lesson>" \
  --used-reflection-ids "3,8" \
  --reflection-outcome helped
```

Valid `--reflection-outcome` values:

- `helped`
- `partial`
- `misleading`
- `unused`

This writes an auditable reuse event for each used reflection and updates the
older reflection's aggregate reuse fields. Use `misleading` when the earlier
reflection made the current task worse; maintain can later mark it stale.

## Review Reflection Quality

```bash
python tools/agent_memory.py reflect-review --project . --json
```

## Remember Explicit User Fact

When the user says "remember this" or gives a stable preference:

```bash
python tools/agent_memory.py update \
  --project . \
  --type semantic \
  --fact "<fact>" \
  --source user \
  --confidence 1.0
```

## Sync Review Mirror

```bash
python tools/agent_memory.py vault-export --project .
```

Rules:

- Store durable lessons, not transcripts.
- Let the Agent summarize its own reasoning, evidence, failed attempts, and useful context before writing.
- Prefer `--payload` or `--payload-file` after a real task because structured fields improve future query recall.
- Treat every structured reflection as an experience candidate until it has reuse feedback and verification evidence.
- Include `hidden_assumptions` so future Agents can see why the conclusion might fail.
- Include `negative_preconditions` so similar-looking but different problems do not inherit the wrong rule.
- Include `verification_method` so future Agents know how to check the candidate against current source, logs, tests, or code wiki evidence.
- Include `source_cases` with episode ids, reflection ids, files, logs, routes, resources, or commands that support the candidate.
- When a diagnosis came from an ArkTS incident trace, include `incident_trace:<id>` in `source_cases`.
- Include `reuse_feedback` when a previous reflection or candidate helped, partly helped, misled, or was unused.
- Include `skill_candidate` when the reflection looks like a reusable process template, but do not generate a new skill automatically.
- Do not store secrets, credentials, or private tokens.
- Use semantic facts for explicit user instructions.
- Use reflections for task outcomes, mistakes, and future rules.
- Use `task_type=diagnosis` for issue-location work, `design` for plan creation, `execution` for implementation/verification, and `workflow` for process lessons.
- Use `outcome=failure` when the attempt did not solve the problem; failed attempts are useful if the next action is concrete.
- Include `scope` and `evidence` when the lesson only applies to part of a project.
- When a lesson came from diagnosing a log message, include the related file, function, or log message template in `evidence`.
- Prefer actionable reflections with `trigger-condition`, `anti-pattern`, `repair-action`, `applies-to`, and `does-not-apply-to`.
- Avoid vague lessons like "be careful"; write the condition and next action.
- If a reflection reveals an old memory is wrong, ask `agent-memory-maintain` to mark it stale or merge it.
