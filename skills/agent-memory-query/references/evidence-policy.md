# Evidence Policy

Use this protocol when historical memory, semantic corrections, conflicts, or trust calibration materially affect the answer.

## Commands

```bash
python tools/agent_memory.py context --project . --query "<query>" --json
python tools/agent_memory.py search --project . --query "<query>" --json
```

`search` is paged and bounded. Follow `next_cursor` only when the current batch cannot answer the question.

## Retrieval Lanes

Read these fields before using reflections:

- `memory_intent` and `retrieval_lanes`: why each memory lane was or was not eligible.
- `memory_use_policy`: answer-time policy for historical records.
- `correction_guards`: warnings that prevent repeated errors but do not steer the main task.
- `semantic_patch_notes`: anchored repairs to code/business meaning.
- `blocked_memory_notes`: records excluded because intent or trigger did not match.
- `conflict_notes`: unresolved semantic conflicts.

## Trust

Use `experience_maturity`, `trust_level`, `trust_score`, `trust_cap`, `query_risk_flags`, `counter_evidence`, and `retrieval_explanation` together.

- `source_truth`: current inspectable source evidence.
- `verified_experience`: reusable but still advisory.
- `usable_hint`: a lead that needs current-source confirmation.
- `weak_hint`: use only to choose the next inspection.
- `possibly_stale` or `conflict_warning`: caution or counter-evidence.

`correction_experience` guards against a known mistake. `semantic_patch_experience` repairs anchored business semantics. Neither is a general procedure. A high score cannot change that lane role.

## Feedback

If retrieval trust was wrong, record bounded calibration feedback:

```bash
python tools/agent_memory.py retrieval-feedback --project . --query "<query>" --type reflection --id <id> --reason overtrusted --json
```

If a memory was actually used, helpful, ignored, misleading, or superseded, record task-outcome feedback with `experience-usage`. Do not delete a record merely because it was wrong for one query.

## Evaluation

Use existing project golden cases when changing retrieval behavior:

```bash
python tools/agent_memory.py eval-retrieval --project . --cases <cases.json> --json
python tools/agent_memory.py eval-calibration --project . --cases <cases.json> --json
python tools/agent_memory.py eval-evidence-attribution --project . --cases <cases.json> --json
```

Treat failures as regression evidence, not permission to rewrite memory automatically.
