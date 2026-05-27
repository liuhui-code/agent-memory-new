# Reflection Quality Loop

The reflection loop keeps lessons actionable instead of accumulating vague task summaries.

## Write Actionable Reflections

Prefer:

```text
trigger_condition: when this lesson should be recalled
anti_pattern: what mistake pattern to avoid
repair_action: the concrete next step
applies_to: where the lesson applies
does_not_apply_to: where it should not be used
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

Record reuse feedback:

```bash
python tools/agent_memory.py reflect \
  --project . \
  --task "<task>" \
  --lesson "<new lesson>" \
  --used-reflection-ids "3,8" \
  --reflection-outcome helped
```

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
- `future_rule_too_generic`
- `lesson_too_generic`
- `never_applied`
- `misleading_outcome`

`maintain-plan` includes reflection quality actions:

- `rewrite_reflection`
- `mark_stale`

`never_applied` by itself is an observation signal, not a rewrite requirement.

These actions require confirmation. The runtime proposes; the Agent and user decide.
