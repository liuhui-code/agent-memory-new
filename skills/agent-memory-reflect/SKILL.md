---
name: agent-memory-reflect
description: Use after completing, failing, debugging, or changing a local agent task to store lessons, mistakes, future rules, and reusable project knowledge.
---

# Agent Memory Reflect

Write a task reflection.

Run:

```bash
python tools/agent_memory.py reflect \
  --project . \
  --task "<task>" \
  --summary "<what happened>" \
  --mistake "<mistake or empty>" \
  --lesson "<durable lesson>" \
  --future-rule "<rule for next time>"
```

Then sync the Obsidian mirror:

```bash
python tools/agent_memory.py vault-export --project .
```

Rules:

- Reflection should capture durable lessons, not a transcript.
- Be specific about mistakes and future rules.
- Do not invent lessons if the task did not produce one.
- Keep secrets out of reflections.
