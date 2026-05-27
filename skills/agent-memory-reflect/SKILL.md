---
name: agent-memory-reflect
description: Use after completing, failing, debugging, or changing a local agent task to save reflections, lessons, durable facts, and reusable project knowledge.
---

# Agent Memory Reflect

Use this skill to write durable lessons after work.

## Save Reflection

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
- Do not store secrets, credentials, or private tokens.
- Use semantic facts for explicit user instructions.
- Use reflections for task outcomes, mistakes, and future rules.
- Include `scope` and `evidence` when the lesson only applies to part of a project.
- Prefer actionable reflections with `trigger-condition`, `anti-pattern`, `repair-action`, `applies-to`, and `does-not-apply-to`.
- Avoid vague lessons like "be careful"; write the condition and next action.
- If a reflection reveals an old memory is wrong, ask `agent-memory-maintain` to mark it stale or merge it.
