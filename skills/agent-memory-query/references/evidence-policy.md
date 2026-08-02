# Evidence Policy

Use this protocol when historical memory, semantic corrections, conflicts, or trust calibration materially affect the answer.

## Commands

```bash
python3 tools/agent_memory.py context --project . --query "<query>" --compact --json
python3 tools/agent_memory.py search --project . --query "<query>" --json
```

`search` is paged and bounded. Follow `next_cursor` only when the current batch cannot answer the question.
Remove `--compact` when the task specifically requires complete trust reasons, ranking audit, or full conflict records.

## Typed Intent

When the evidence lane is known, declare it instead of relying on lexical inference:

```bash
python3 tools/agent_memory.py context --project . --query "<goal plus source terms>" --intent procedure_reuse --compact --json
```

Allowed values are `code_location`, `code_business_semantics`,
`runtime_log_diagnosis`, `procedure_reuse`, `semantic_correction`,
`memory_maintenance`, and `general_context`. Use a typed intent when domain words such
as `refresh`, `file`, or `maintenance` could describe either the business operation or
the requested evidence lane. Omit it only when the purpose is unclear, and audit
`memory_intent_source` for `explicit` versus `inferred` selection.

Typed intent controls lanes, not candidate translation. When user and source languages
differ, include a few Agent-extracted identifiers, source terms, or exact log phrases in
the same query. Do not maintain a static synonym list.

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
python3 tools/agent_memory.py retrieval-feedback --project . --query "<query>" --type reflection --id <id> --reason overtrusted --json
```

If a memory was actually used, helpful, ignored, misleading, or superseded, record task-outcome feedback with `experience-usage`. Do not delete a record merely because it was wrong for one query.

## Evaluation

Use existing project golden cases when changing retrieval behavior:

```bash
python3 tools/agent_memory.py eval-retrieval --project . --cases <cases.json> --json
python3 tools/agent_memory.py eval-calibration --project . --cases <cases.json> --json
python3 tools/agent_memory.py eval-evidence-attribution --project . --cases <cases.json> --json
```

Treat failures as regression evidence, not permission to rewrite memory automatically.
