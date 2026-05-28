---
name: agent-memory-reflect
description: Use after completing, failing, debugging, or changing a local agent task to save reflections, lessons, durable facts, and reusable project knowledge.
---

# Agent Memory Reflect

Use this skill to write durable lessons after work.

The local Agent CLI must lead the reflection. After one successful or failed diagnosis,
design, execution, or workflow attempt, first organize the task into structured data.
Then call the runtime to store it.

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
