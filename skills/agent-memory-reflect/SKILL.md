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

When the reflection clearly belongs to one of these two future paths, include `experience_type`:

- `procedure_experience`: reusable diagnosis, query, repair, or change-design workflow
- `correction_experience`: correction of learned business semantics or memory understanding

When recording `correction_experience`, include enough evidence for later learn governance:

- affected file, symbol, or log anchors in `source_cases` or `inspection_targets`
- the misleading old understanding in `what_failed` or `misleading_followup_terms`
- the corrected understanding in `lesson`, `future_rule`, and `repair_action`
- if the input came from temporary runtime-log analysis, carry over `runtime_episode_candidate` evidence through `context_used`, `trajectory_summary`, `final_verification_path`, and `old_hypothesis` when present
- keep bounded runtime evidence in the reflection instead of raw logs: prefer `evidence`, `misleading_followup_terms`, and `repair_action` from `reflect_payload_template`

For runtime-log-backed diagnosis, also keep the feedback loop explicit:

- preserve the strongest runtime signals in `useful_followup_terms`
- preserve misleading or disproven directions in `misleading_followup_terms`
- preserve the closing verification path in `final_verification_path`

That lets `reflect-review`, `maintain-plan`, recurring incident fingerprints, and incident strategy candidates reuse the same bounded runtime evidence without storing raw logs.

This does not add a fifth skill. It only helps `maintain-plan` route the reflection toward future skill-candidate review or toward learn/semantic-repair governance.

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
