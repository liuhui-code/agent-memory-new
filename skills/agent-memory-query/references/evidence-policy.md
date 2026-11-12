# Evidence Policy

Use this shared policy when weighing evidence or reviewing normative context, and as the primary protocol when historical memory, semantic corrections, conflicts, or trust calibration materially affect the answer.

## Authority

Use evidence in this order:

```text
explicit user constraints
  -> current source and current configuration
  -> active typed graph edges and current code logs
  -> observed runtime/incident evidence
  -> anchored semantic corrections
  -> verified experience
  -> advisory experience and episodes
```

Current source can invalidate memory. Recency cannot override intent, status, confidence, counter-evidence, or a current code anchor. An absent graph edge is an evidence gap, not proof that no dependency exists.

## Normative Context

Inspect omission counts when this lane is present. `examined_document_count` covers
bounded candidates, while `candidate_limit_exceeded` marks additional unexamined
matches. `omitted_document_count` and `omitted_evidence_gap_count` accumulate known
omissions across selection, compact projection and budget reduction. Do not treat
those counts as total matching-document coverage. `truncated` also covers partial
body text; read the original for a complete contract. Full gap provenance and cached
record IDs distinguish documents from different source roots.

For stable product behavior or architecture decisions, inspect
`query_handoff.normative_context` in `context`, or
`project_context.normative_context` in `design-context`. Use the existing task route;
do not query every ADR and specification for an unrelated local task.

- Read the document's source root, path, digest, declared status, scope, approval
  reference, replacement references, freshness and `allowed_use`.
- `source.digest` identifies indexed raw bytes; `source.observed_digest` identifies
  this query's bounded read, or is null when unavailable. Compare the two without
  treating an observation as refreshed metadata or authenticated approval. The
  recorded revision belongs to learning time; Git state and bytes are separate
  observations rather than an atomic repository snapshot.
- Scope belongs to `scope_basis: document_source_root`. `source.matches_query_project`
  compares roots only. Confirm external-tree applicability against the current task,
  including global scopes marked `source_root_requires_agent_confirmation`.
- `expected_contract_candidate` means the metadata and current source permit review;
  it is not independently verified approval. Read the original Git document and its
  approval evidence before treating it as an applicable project constraint.
- Keep drafts as hypotheses and superseded/withdrawn/rejected documents as historical
  references. Resolve duplicate IDs and replacement claims before applying either.
- `replacement_lookup` describes bounded cached metadata in the same source root;
  `not_indexed`, `ambiguous` and `unique` refer only to that cache. Read both original
  documents for approval, scope and reciprocal claims. Target-source and approval flags
  remain false in this lookup; a linked record is not an inspected source or an approved
  replacement merely because it appears. Metadata gaps do not adjudicate invalidity.
- Changed, missing, untracked or modified documents require source/approval review.
  A fresh digest or a Git commit alone never proves approval.
- When `truncated` is true or an omission count is greater than zero, expand the same
  focused query without `--compact`, or read the cited source. An excerpt is not the
  full contract; candidate overflow also leaves matches unexamined.
- Report expected behavior and observed implementation separately when they disagree.
  The Agent owns diagnosis and design; Runtime does not choose which side is correct.

If a relevant document has not been learned, read it directly or use the existing Learn
Skill on that explicit scope. Keep the current task intent temporary; do not synthesize
an approved Feature Spec from the user's prompt or current implementation.

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
