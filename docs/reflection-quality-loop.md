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

## System Meta-Reflection Research And Proposal

The [system meta-reflection research and plan](system-meta-reflection-research-and-plan.zh-CN.md)
reviews Reflexion, Self-Refine, ACE, GEPA, MemRL, model judging, code self-improvement
and production evaluation practices. It proposes a task-end review led by the user's
existing Agent model and a complete system-change workflow covering rules, Query, Learn,
Reflect, evaluators and data structures. A candidate should identify the failing layer
or new requirement and lead to a version-bound rule diff, patch or migration plan,
appropriate checks, application and rollback records. The
[v1 design specification](system-meta-reflection-design.zh-CN.md) fixes trigger, budget,
report/proposal and state semantics. Initial client workflows are written in the Reflect
and Maintain Skills' portable references. The [governance registry contract](system-meta-reflection-runtime.zh-CN.md)
describes new explicit review-save, inspection and limited state-audit commands in the
existing SQLite archive. The [explicit check workflow](system-meta-reflection-checks.zh-CN.md)
also records observed process exits and declared-file bindings without advancing proposals.
The related controlled synthetic regressions have passed. Explicit
[acceptance/application/recovery entries](system-meta-reflection-lifecycle.zh-CN.md) now
cover the bounded lifecycle; no background task hook was added. A saved review or zero exit alone is not
a completed system improvement.

[Task-end decisions and explicit slots](system-meta-reflection-triggers.zh-CN.md) are
also written: the four Skills hand off only real closed tasks with concrete signals,
and `reflect-system-trigger --claim` can reserve one slot before generation. Repeated
automatic claims skip; explicit manual revisions retain the same thread. A slot is
neither authenticated task identity nor evidence that a model ran. Host invocation and
concurrency in other real hosts remain unvalidated; a controlled Codex task-end handoff
and synthetic slot concurrency have passed.
No query response wrapper or background hook was added.

The [isolated candidate path](system-meta-reflection-candidates.zh-CN.md) is also written:
a real Git baseline plus bound patch becomes a separate test subject, with v2 check
plans observing that subject's tracked Git state and changed bytes. This source and its
synthetic regressions have passed; candidate readiness does not establish functional or
release readiness, complete command-source use, or an applied product change.

System reviews must distinguish task outcomes, observed tool/source checks, model opinions
and causal benefit claims. They belong outside ordinary project-memory retrieval. The
existing reflection types and scope field do not provide that isolation automatically.
The optional governance tables are created only on an explicit `reflect-system` save;
ordinary retrieval does not read them. Do not submit system fields as a new `reflect --payload` type.

Existing retrieval and experience feedback can influence ranking after their stability
rules are met. A model review must not automatically become `verified`, `verified_useful`
or `confirmed` feedback. The future review workflow must retain the current query contract,
account for its additional cost and keep unavailable evidence explicit. Compatibility
preserves the public contract while permitting declared, evaluated algorithm changes
in new versions. Structural proposals also need old/new data compatibility, migration,
derived-index rebuilding and separate code/data recovery plans. The 17 mechanism scenarios
and nine trigger scenarios remain `not_run` under the user's request to skip verification.
