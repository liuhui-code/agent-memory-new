# Reflection Quality Loop

The reflection loop keeps lessons actionable instead of accumulating vague task summaries.

## Write Actionable Reflections

Reflections are experience candidates. They become useful only when a future Agent can
understand why the lesson might apply, why it might not apply, and how to verify it.

Prefer:

```text
trigger_condition: when this lesson should be recalled
anti_pattern: what mistake pattern to avoid
repair_action: the concrete next step
applies_to: where the lesson applies
does_not_apply_to: where it should not be used
hidden_assumptions: assumptions that made the lesson valid or risky
negative_preconditions: similar cases where the lesson should not transfer
verification_method: source, log, test, or reproduction check before reuse
reuse_feedback: candidate/helped/partial/misleading/unused signal
source_cases: episodes, reflections, files, logs, routes, resources, or commands behind the lesson
skill_candidate: optional reusable process template name
```

Avoid:

```text
lesson: be careful
future_rule: do better next time
```

## Runtime Commands

Save a structured reflection:

```bash
python tools/agent_memory.py reflect \
  --project . \
  --task "<task>" \
  --lesson "<durable lesson>" \
  --future-rule "<next rule>" \
  --trigger-condition "<when to remember>" \
  --anti-pattern "<mistake pattern>" \
  --repair-action "<concrete action>" \
  --applies-to "<valid scope>" \
  --does-not-apply-to "<invalid scope>"
```

For full experience-candidate capture, prefer `--payload` or `--payload-file` with:

```json
{
  "hidden_assumptions": ["The route push completed before the blank screen."],
  "negative_preconditions": ["Do not apply when no navigation occurred."],
  "verification_method": "Confirm route registration, inspect logs, and reproduce navigation.",
  "reuse_feedback": "experience candidate until reused",
  "source_cases": ["episode:12", "reflection:7", "file: pages/Home.ets"],
  "skill_candidate": "arkts-route-blank-screen-diagnosis"
}
```

Record reuse feedback:

```bash
python tools/agent_memory.py reflect \
  --project . \
  --task "<task>" \
  --lesson "<new lesson>" \
  --used-reflection-ids "3,8" \
  --reflection-outcome helped
```

Use one of these outcomes:

```text
helped
partial
misleading
unused
```

Each feedback write creates `reflection_reuse_events` rows and updates the
older reflection's `applied_count`, `last_applied_at`, and `last_outcome`.

Review reflection quality:

```bash
python tools/agent_memory.py reflect-review --project . --json
```

Promote a durable reflection:

```bash
python tools/agent_memory.py maintain-promote \
  --project . \
  --reflection-id 12 \
  --fact "<durable fact>" \
  --json
```

## Quality Checks

`reflect-review` reports:

- `missing_scope`
- `missing_evidence`
- `missing_future_rule`
- `missing_trigger_condition`
- `missing_repair_action`
- `missing_hidden_assumptions`
- `missing_negative_preconditions`
- `missing_verification_method`
- `missing_reuse_feedback`
- `future_rule_too_generic`
- `lesson_too_generic`
- `never_applied`
- `misleading_outcome`

`maintain-plan` includes reflection quality actions:

- `rewrite_reflection`
- `mark_stale`

`never_applied` by itself is an observation signal, not a rewrite requirement.

These actions require confirmation. The runtime proposes; the Agent and user decide.
