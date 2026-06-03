# Guided Memory Review Workflow

This workflow turns raw memory governance signals into an Agent-readable cleanup plan.

The user should be able to ask:

```text
检查并整理记忆系统。
```

The Agent should run:

```bash
python tools/agent_memory.py doctor --project .
python tools/agent_memory.py maintain-health --project . --json
python tools/agent_memory.py maintain-plan --project . --json
```

## Runtime Boundary

`maintain-plan` is read-only. It proposes actions but does not mutate SQLite.

The Agent must ask for confirmation before running:

```bash
python tools/agent_memory.py maintain-status ...
python tools/agent_memory.py maintain-merge ...
python tools/agent_memory.py maintain-promote ...
```

## Action Types

- `archive`: stale memory can be moved out of the active path.
- `review`: duplicate candidates need human or Agent judgment before merge.
- `verify`: low-confidence memory needs evidence.
- `promote_or_mark_reviewed`: reflection may become a durable fact or be marked reviewed.
- `promote_experience_candidate`: structured reflection has enough assumptions, boundaries, verification, and source cases to review as reusable experience.
- `review_skill_pattern_candidate`: repeated procedure experiences point to the same reusable pattern and should be reviewed as a possible skill draft.
- `promote_or_archive`: episode may become a durable fact or be archived.
- `review_query_miss`: a previous query returned no memory or wiki results.
- `rewrite_reflection`: reflection lacks enough trigger/action structure.
- `mark_stale`: reflection has been misleading and should leave the active path.

## Confirmation Rule

The Agent should group actions by risk:

```text
Low risk:
  archive stale records

Medium risk:
  review duplicates
  verify low-confidence records
  promote reflections or episodes
  promote experience candidates

Low-friction feedback:
  review query misses
```

Actions with `command: null` need the Agent to draft the replacement fact, durable lesson, or verification step first.

For `review_query_miss`, inspect `suggested_fixes`:

```text
learn_missing_scope: learn an entry file or directory that probably contains the missing context.
add_business_terms: enrich learned code files, symbols, or logs with business meaning.
rewrite_reflection: add a missing experience candidate or improve a weak one.
ignore_noise: mark a one-off or irrelevant miss ignored.
```

If `maintain-plan` also returns `semantic_gap_targets`, use them as a concrete enrichment queue. Prefer filling the listed file, symbol, and log business meaning with `learn-business` before refreshing larger scopes.

If `maintain-plan` returns `learn_business_payload_template`, use that JSON as the starting point for the next `learn-business` write. Fill only the missing summaries and terms, then write it back without broadening the learning scope.

If `workflow_steps` is present on the action, use it as the execution checklist for the Agent:

```text
read current source
fill missing business meaning in template
write with learn-business
re-run query or maintain-plan
```

If `maintain-plan` returns `review_semantic_conflict`, treat it as a review-only action. The existing summary stayed in storage; the incoming summary was captured for comparison and persisted in SQLite governance state. Resolve it against current source before any future replacement step.

After review, close the record explicitly:

```bash
python tools/agent_memory.py conflict-status --project . --id "<id>" --status resolved --resolution "<decision>"
```

If the incoming summary is the correct replacement, apply it through the governed path instead:

```bash
python tools/agent_memory.py conflict-apply --project . --id "<id>" --resolution "<decision>"
```

If the command rejects the target as ambiguous, fix the duplicated symbol/log identity first. Do not widen the update.
Prefer adding `--decision-note` and `--replacement-source` so the reason for replacement stays attached to the conflict record.

If `maintain-plan` returns `review_skill_pattern_candidate`, use the grouped evidence before drafting any skill:

- supporting reflection ids
- common follow-up focus
- common query terms
- supporting cases
- verification methods

When present, `draft_path` and `draft_markdown` are the proposed Markdown artifact for `docs/skill-candidates/`. Review and revise that draft before creating or updating anything under `skills/`.

After `vault-export`, the same grouped draft also appears in:

```text
Governance/Skill Pattern Candidates.md
```

Use that page for human review. The vault mirror is still generated output, not the source of truth.

When the grouped draft is ready to become a repo artifact, write it explicitly:

```bash
python tools/agent_memory.py maintain-skill-draft \
  --project . \
  --pattern-name "<pattern-name>" \
  --json
```

This is still a review-stage artifact under `docs/skill-candidates/`, not a formal installed skill.

If `maintain-plan` returns `review_incident_strategy_candidate`, use the grouped runtime-incident evidence before drafting any diagnosis strategy:

- goal symptoms
- common log events
- recommended steps
- verification paths
- misleading signals
- log design feedback

After `vault-export`, the same grouped draft also appears in:

```text
Governance/Incident Strategy Candidates.md
```

When the grouped incident strategy is ready to become a repo artifact, write it explicitly:

```bash
python tools/agent_memory.py maintain-incident-strategy-draft \
  --project . \
  --strategy-name "<strategy-name>" \
  --json
```

This is still a review-stage artifact under `docs/incident-strategies/`, not a formal installed skill.

To export every current grouped draft after a review session, use:

```bash
python tools/agent_memory.py maintain-skill-draft \
  --project . \
  --pattern-name all \
  --json
```

When one reviewed draft should be staged as a candidate skill package, use:

```bash
python tools/agent_memory.py maintain-skill-package \
  --project . \
  --pattern-name "<pattern-name>" \
  --json
```

This writes only `skills/_candidates/<pattern-name>/SKILL.md`. Promotion into a real skill remains a separate human-reviewed step.

See also:

```text
docs/skill-promotion-rules.md
```

That document defines the boundary between:

- `docs/skill-candidates/`
- `skills/_candidates/`
- `skills/`

## Example Agent Response

```text
Memory review found:
- 2 stale records that can be archived.
- 1 duplicate candidate that needs a merged fact.
- 3 unreviewed episodes that may contain durable knowledge.
- 1 experience candidate ready for review.
- 2 query misses with suggested fixes.

I can archive the stale records now. For the duplicate and episode promotions, I will draft the replacement facts first and wait for confirmation.
```

After confirmed changes, run:

```bash
python tools/agent_memory.py vault-export --project .
```

If a query miss is handled, mark it:

```bash
python tools/agent_memory.py miss-status --project . --id 7 --status resolved --resolution "learned relevant directory"
```

Obsidian remains a generated review mirror. SQLite remains the source of truth.
