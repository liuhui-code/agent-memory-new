---
name: agent-memory-maintain
description: Use when the user asks to initialize, check health, update, repair, refresh, or sync the Agent Memory system or Obsidian vault.
---

# Agent Memory Maintain

Use this skill for memory system health and maintenance.

Memory data is stored in the current workspace `.agent-memory/` by default, next to `skills/` and `tools/`, not in the learned external source directory. Use `--memory-home <path>` when the user configured a custom location; otherwise the runtime uses `AGENT_MEMORY_HOME` or `./.agent-memory`.

## Initialize Or Repair

```bash
python tools/agent_memory.py init --project .
python tools/agent_memory.py doctor --project .
```

## Health Check

```bash
python tools/agent_memory.py doctor --project .
python tools/agent_memory.py maintain-health --project . --json
```

## Refresh Learned Scopes

When the project source has changed and the learned code wiki may be stale:

```bash
python tools/agent_memory.py maintain-refresh-scope --project . --json
```

To refresh one previously learned scope only:

```bash
python tools/agent_memory.py maintain-refresh-scope --project . --scope-id 3 --json
```

Use this before broad `learn-path --replace` or `wiki-index` resets. It replays previously learned scopes from SQLite, refreshes current file/symbol/log/edge structure, retires removed-file structure, and returns `semantic_review_targets` so we can decide whether a focused `learn-business` pass is needed next.
After refresh, run `maintain-plan --json` if you want the drift to be translated into review actions such as `review_semantic_drift`, `mark_experience_stale_if_anchor_removed`, or `review_skill_pattern_staleness`.

## Review Queue

When the user asks to review, clean, govern, merge, or check memory quality:

```bash
python tools/agent_memory.py maintain-review --project . --json
python tools/agent_memory.py reflect-review --project . --json
python tools/agent_memory.py miss-list --project . --status open --json
python tools/agent_memory.py maintain-plan --project . --json
```

Use `maintain-plan` to propose grouped actions before changing records.

## Guided Review Workflow

When the user asks to clean, organize, review, or govern memory:

1. Run `doctor`.
2. Run `maintain-health --json`.
3. Run `maintain-plan --json`.
4. Present grouped actions to the user by risk and type, including open query misses.
5. Wait for confirmation before executing `maintain-status`, `maintain-merge`, or `maintain-promote`.
6. After confirmed changes, run `vault-export`.
7. Treat the vault as a bounded human-readable mirror on large archives. If a generated page says it is truncated, continue full inspection through runtime JSON or direct SQLite-backed commands rather than assuming the vault contains every row.

If an action has `command: null`, draft the needed replacement fact or lesson first, then ask for confirmation.

When `maintain-plan` returns `promote_experience_candidate`, review the reflection as reusable experience. Check `candidate_fields`, `verification_method`, `source_cases`, and `skill_candidate`; do not promote it automatically.
If the action also includes compressed trace-case fields such as `query_rounds`, `useful_followup_focus`, `useful_followup_terms`, `misleading_followup_terms`, `inspection_targets`, or `final_verification_path`, review them as evidence about how the Agent actually converged.
When `maintain-plan` returns `review_skill_pattern_candidate`, treat it as a multi-case aggregation hint, not a ready-made skill. Review `supporting_reflection_ids`, `common_followup_focus`, `common_query_terms`, `supporting_cases`, and `verification_methods` before drafting any skill candidate.
If `draft_path` and `draft_markdown` are present, use them as the proposed review artifact for `docs/skill-candidates/`. Review and edit the draft first; do not treat it as an approved skill.
If `common_steps`, `common_stop_conditions`, `expected_outputs`, or `failure_modes` are present, treat them as the first pass at turning repeated experience into executable skill structure.
If `draft_status`, `package_status`, or `promotion_stage` are present, use them as the current repo-state signal instead of inferring state from file paths alone.
If `draft_review_status`, `package_review_status`, or `review_guidance` are present, use them to decide whether the next step is writing a draft, reviewing a draft, or reviewing a candidate package before any manual promotion.
If `promotion_readiness`, `quality_score`, or `quality_reasons` are present, use them as the runtime's current evidence-strength signal for whether the pattern is only interesting, worth review, or close to manual promotion.
If `helped_reuse_count`, `partial_reuse_count`, `misleading_reuse_count`, `anchor_health`, or `missing_anchor_paths` are present, use them to judge whether the pattern is still grounded in current code or is drifting away from its original anchors.
These are reviewer aids, not permission to skip manual promotion checks.
After `vault-export`, the same grouped pattern appears in `Governance/Skill Pattern Candidates.md` for human review.
That vault page now also mirrors reviewer metadata and the non-overwrite policy for reviewed artifacts, so Obsidian review sees the same guardrails as runtime JSON.
When `maintain-plan` returns `review_incident_strategy_candidate`, treat it as a runtime-incident diagnosis policy candidate rather than a formal skill. Review `goal_symptoms`, `common_log_events`, `recommended_steps`, `verification_paths`, `misleading_signals`, and `log_design_feedback` before drafting it.
After `vault-export`, the same grouped incident strategy appears in `Governance/Incident Strategy Candidates.md`.

When `maintain-plan` returns `review_recurring_incident_fingerprint`, keep it lightweight. Review `goal_area`, `common_log_events`, `dominant_failure_signals`, and `misleading_signals` first, then decide whether the repeated signature is worth drafting into `docs/incident-fingerprints/`. This is for preserving repeated incident shape, not for building a full runtime history store.

When `maintain-plan` returns `review_log_design_gap`, keep the follow-up narrow. Use `goal_area`, `high_value_log_anchor_targets`, and `suggested_log_kinds` to patch one or two high-value logs in the affected code path. Prefer start markers, decision checkpoints, or request/session correlation fields over broad logging expansion.
When `governance_summary` or `learn_governance_summary` is present, choose the smallest governance lane that removes the current bottleneck. Prefer `learn_semantic_repair` before `skill_evolution` whenever drift or correction is concentrated in a few files.
When the grouped runtime-incident strategy is ready to be drafted into the repo, use:

```bash
python tools/agent_memory.py maintain-incident-strategy-draft \
  --project . \
  --strategy-name "<strategy-name>" \
  --json
```

This writes only `docs/incident-strategies/<strategy-name>.md`. It does not create or promote a formal skill.
When the pattern is ready to be written into the repo as a draft document, use:

```bash
python tools/agent_memory.py maintain-skill-draft \
  --project . \
  --pattern-name "<pattern-name>" \
  --json
```

This writes only `docs/skill-candidates/<pattern-name>.md`. It still does not create or update a real skill under `skills/`.
The generated draft includes YAML frontmatter with review metadata such as `artifact_type`, `promotion_status`, `supporting_reflection_ids`, and `common_followup_focus`.
Keep `review_status`, `reviewer`, and `review_notes` in that frontmatter/body pair up to date during human review instead of inventing an external checklist.
If a draft already carries human review metadata, rerunning `maintain-skill-draft` should preserve it. Read `write_action` and `warning` before assuming the runtime rewrote the file.

To write every currently clustered draft in one pass, use:

```bash
python tools/agent_memory.py maintain-skill-draft \
  --project . \
  --pattern-name all \
  --json
```

When a reviewed draft should move into a candidate skill package, use:

```bash
python tools/agent_memory.py maintain-skill-package \
  --project . \
  --pattern-name "<pattern-name>" \
  --json
```

This writes only `skills/_candidates/<pattern-name>/SKILL.md`. It still does not create or update a formal skill under `skills/<name>/`.
It also writes `skills/_candidates/<pattern-name>/PROMOTION.md` as the manual promotion checklist for the final human step.
The candidate package includes YAML frontmatter with `promotion_status: candidate` and `source_draft` so reviewers can trace where it came from.
Keep the same `review_status`, `reviewer`, and `review_notes` fields when the draft is promoted into `_candidates/`.
If a candidate package already carries human review metadata, rerunning `maintain-skill-package` should preserve it. Read `write_action` and `warning` before assuming the runtime rewrote the file.
Formal promotion into `skills/<name>/` remains manual for now. Follow `docs/skill-promotion-rules.md` before treating a candidate package as a real skill.
For a read-only final gate, use:

```bash
python tools/agent_memory.py maintain-skill-promotion-status \
  --project . \
  --pattern-name "<pattern-name>" \
  --json
```

Use its `promotion_blockers` output before attempting any manual copy into `skills/<name>/`.
When `experience_type` is present on a reflection action, keep the governance path aligned:

- `procedure_experience` -> future skill candidate review path
- `correction_experience` -> learn or semantic repair review path

For `review_correction_experience`, prefer the structured repair bundle over ad hoc rewriting:

- `correction_targets`
- `learning_rule_draft`
- `learn_business_payload_template`
- `workflow_steps`

Use these to patch the affected business semantics through `learn-business` at the narrowest possible scope.

When `maintain-plan` returns `review_query_miss`, inspect `suggested_fixes`:

```text
learn_missing_scope
add_business_terms
rewrite_reflection
ignore_noise
```

Choose the smallest fix. A miss caused by missing code context should trigger `agent-memory-learn`; a miss caused by weak business meaning should trigger `learn-business`; a miss caused by absent experience should trigger `agent-memory-reflect`; irrelevant misses can be marked ignored.
When `suggested_query_terms` is present, use those terms first for the next recursive `search` or `context` call. They combine the miss wording with the current code-memory hint anchors.
When `followup_focus` is present, treat it as the intended query-repair scene, such as `route`, `resource`, `log`, or `config`.
When `query_workflow_steps` is present, follow them before broadening the learning scope.

When `maintain-plan` returns `semantic_gap_targets`, treat them as the next enrichment queue. Feed those file, symbol, or log anchors back into `agent-memory-learn` and `learn-business` instead of re-learning broad directories.

When `maintain-plan` returns `learn_business_payload_template`, edit that template in place and send it to:

```bash
python tools/agent_memory.py learn-business --project . --payload "<json>" --json
```

Prefer filling the template over inventing a new payload shape. It keeps file, symbol, and log anchors aligned with the existing code wiki rows.
If the template includes `hint_terms` and `hint_context`, use them as the default retrieval anchors for the next `business_terms` and `business_summary` draft.

When `workflow_steps` is present, follow it in order. Treat it as the default local Agent CLI procedure for targeted semantic enrichment.

When `maintain-plan` returns `review_semantic_conflict`, do not replace stored summaries immediately. These conflicts are now durable SQLite governance records and also appear in the vault review pages. Read current source, decide which summary is grounded in the code, then prepare a reviewed replacement in a later governed step.
When `apply_command_template` is present on a conflict action, use it only after that review is complete.

List or close semantic conflicts with:

```bash
python tools/agent_memory.py list --project . --type semantic-conflict --json
python tools/agent_memory.py conflict-status --project . --id "<id>" --status resolved --resolution "<why>"
python tools/agent_memory.py conflict-apply --project . --id "<id>" --resolution "<why incoming summary is correct>" --decision-note "<evidence>" --replacement-source "<source anchor>"
```

Use `conflict-apply` only after checking current source and deciding the incoming summary is the right replacement. It applies the stored incoming summary to the target file, symbol, or log and marks the conflict `applied`. The runtime now requires the target to resolve to exactly one stored row; ambiguous symbol or log targets are rejected for manual cleanup first.

## Governance Actions

Mark a record stale, archived, rejected, merged, or active:

```bash
python tools/agent_memory.py maintain-status \
  --project . \
  --type semantic \
  --id "<id>" \
  --status stale \
  --reason "<why>"
```

Merge duplicate semantic facts:

```bash
python tools/agent_memory.py maintain-merge \
  --project . \
  --type semantic \
  --ids "3,8" \
  --fact "<consolidated fact>" \
  --json
```

Promote an episode into a durable semantic fact:

```bash
python tools/agent_memory.py maintain-promote \
  --project . \
  --episode-id "<id>" \
  --fact "<durable fact>" \
  --json
```

Promote a high-quality reflection into a durable semantic fact:

```bash
python tools/agent_memory.py maintain-promote \
  --project . \
  --reflection-id "<id>" \
  --fact "<durable fact>" \
  --json
```

Mark a query miss reviewed, resolved, or ignored:

```bash
python tools/agent_memory.py miss-status \
  --project . \
  --id "<id>" \
  --status resolved \
  --resolution "<what fixed the miss>"
```

Open misses are merged by normalized query text. Use `miss_count` and `last_seen_at` to prioritize recurring retrieval gaps before one-off misses.

## Refresh Indexes

```bash
python tools/agent_memory.py wiki-index --project .
```

Refreshing the wiki also refreshes extracted code log statements and the generated file/function/log edges.

## Sync Obsidian Mirror

```bash
python tools/agent_memory.py vault-export --project .
python tools/agent_memory.py vault-index --project .
```

Rules:

- SQLite is the source of truth.
- Obsidian is a generated review mirror.
- Do not modify shell profiles.
- Report failed `doctor` checks exactly.
- `agent-memory-query` should stay fast; run heavier governance through this maintain skill.
- Do not auto-delete memory. Prefer stale, merge, archive, or reject status changes.
- `maintain-plan` is read-only. It proposes actions; it does not mutate memory.
- Merge only when the replacement fact is more precise than all source facts.
- Promote only durable lessons, not task logs.
- Treat `rewrite_reflection` and `mark_stale` actions from `maintain-plan` as confirmation-required reflection quality actions.
- Treat `promote_experience_candidate` as a review signal, not an automatic promotion.
- Treat `review_query_miss` actions as low-risk signals that may require learning a missing path, adding business terms, rewriting a reflection, or ignoring noise.
- Treat `add_business_terms` actions as targeted enrichment work; prefer patching the listed semantic gaps over re-indexing large code scopes.
- Vault export includes generated code log statement, memory edge, query miss, semantic conflict, reflection quality, and experience candidate pages for review.
