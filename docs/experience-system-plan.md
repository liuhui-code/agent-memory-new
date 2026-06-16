# Experience System Plan

## Goal

Build an experience layer above Agent Memory without breaking the four-skill interface.

The system keeps this boundary:

```text
Memory Layer
  facts / episodes / code wiki / logs / business semantics / edges

Reflection Layer
  task review / reasoning summary / worked paths / failed paths / assumptions

Experience Layer
  verified abstract rule / preconditions / transfer rule / verification method / reusable skill pattern
```

Memory is compressed fact. Experience is a higher abstraction produced from facts, context, hidden assumptions, failed paths, and reasoning.
Business semantic patches are a separate experience subtype: they correct or enrich the code wiki's business meaning for a concrete file, symbol, log statement, or edge. They are not task procedures.

## Design Principles

- Keep SQLite as the source of truth.
- Keep Obsidian as a generated review mirror.
- Keep the user-facing interface to four skills: learn, query, maintain, reflect.
- Do not add vector databases, graph databases, daemons, or a fifth skill.
- Do not treat a raw reflection as accepted experience.
- Require experience candidates to state when they apply, when they do not apply, how to verify them, and which cases support them.
- Let the Agent do recursive reasoning through repeated query calls; keep runtime graph traversal bounded.

## Target Lifecycle

```text
episode / code / log / business memory
  -> structured reflection
  -> experience candidate
  -> reuse feedback
  -> accepted experience
  -> skill_candidate
```

Accepted experience and generated skill candidates are later-stage goals. Phase one only makes experience candidates explicit and queryable.

## Phase One: Experience Candidate Loop

Phase one strengthens the existing reflection layer. It does not add an `experiences` table.

The Agent writes richer structured reflections with these experience-candidate fields:

```text
hidden_assumptions
negative_preconditions
verification_method
reuse_feedback
source_cases
skill_candidate
```

Required meaning:

- `hidden_assumptions`: assumptions that made the lesson valid or risky.
- `negative_preconditions`: cases where the lesson should not be applied.
- `verification_method`: concrete source, log, test, or reproduction check before trusting the lesson.
- `reuse_feedback`: whether the rule is only a candidate, helped, partial, misleading, or unused.
- `source_cases`: episode, reflection, file, log, route, or command evidence supporting the candidate.
- `skill_candidate`: optional process template name when the candidate looks reusable.

`experience_type` now separates three lanes:

- `procedure_experience`: a reusable task or diagnosis workflow that may later cluster into a skill candidate.
- `correction_experience`: a guardrail that prevents repeated wrong assumptions or misleading retrieval directions.
- `semantic_patch_experience`: a business-semantic patch tied to `anchor_type`, `anchor_key`, `semantic_field`, and `proposed_value`.

`semantic_patch_experience` is applied through learn/maintain governance, not as a normal how-to memory. Query may show it as `semantic_patch_notes` when the current problem touches the same code anchor or business meaning.

The first phase updates:

- `reflections` schema through migration columns.
- `agent-memory-reflect` skill payload instructions.
- `agent-memory-query` skill result-use order.
- reflection quality review signals.
- `maintain-plan` actions for complete experience candidates and query miss repair choices.
- docs and tests proving the protocol stays visible.

## Query Use Order

Query should use memory as an investigation map:

```text
memory_intent and retrieval_lanes
  -> procedure experiences when the intent can reuse a workflow
  -> correction guards when the task needs warning or diagnosis
  -> semantic facts
  -> code wiki and business semantics
  -> semantic_patch_notes for anchored business meaning repair
  -> code log matches
  -> bounded memory_edges
  -> episodes
```

The Agent must verify experience candidates against current source, logs, tests, and code wiki evidence before using them as conclusions.
Correction experiences should normally act as warnings. Semantic patches should normally improve or repair anchored code business semantics instead of becoming the main answer.

## Maintain Direction

Maintain should eventually group reflection and miss signals into these actions:

```text
rewrite_reflection
add_business_terms
review_query_miss
promote_experience_candidate
review_semantic_patch
review_retrieval_interference
review_experience_conflict
mark_stale
merge_duplicate_fact
```

For phase one:

- `promote_experience_candidate` means a structured reflection is ready for human or Agent review as reusable experience. It does not create a new experience table row.
- `review_semantic_patch` means a structured reflection proposes a code-business semantic correction. Apply it through focused `learn-business` only after checking the anchor against current source.
- `review_retrieval_interference` means a reflection has misleading reuse or over-retrieval risk and needs lower confidence, a tighter trigger, or stale marking.
- `review_experience_conflict` means a newer experience changes guidance for the same trigger/scope or proposes a different semantic patch for the same anchor. Review which record should stay active before query relies on both.
- `review_query_miss` includes `suggested_fixes`: `learn_missing_scope`, `add_business_terms`, `rewrite_reflection`, and `ignore_noise`.
- Reflection reuse writes `reflection_reuse_events` with `helped`, `partial`, `misleading`, or `unused` outcomes.
- Runtime quality review still asks the Agent and user to decide before mutation.

## Later Direction

After phase one is stable:

1. Consider an `experiences` table only after reflection candidates have proven useful.
2. Generate `skill_candidate` drafts from repeatedly successful accepted experience.

## Success Criteria

- Agents can write experience-candidate structure after diagnosis, design, execution, or workflow attempts.
- Query can find candidates by problem, assumptions, verification method, source cases, and skill candidate name.
- Reflection review flags candidates missing hidden assumptions, negative preconditions, verification method, or reuse feedback.
- Vault export writes `Governance/Experience Candidates.md` for human review.
- Vault export writes `Governance/Reflection Reuse.md` for reuse feedback review.
- Users still interact through four skills.
