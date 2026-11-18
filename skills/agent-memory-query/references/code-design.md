# Agent-Owned Code Design Protocol

Use this protocol for feature design, refactoring, interface changes, state flow,
service boundaries, or module decomposition. Agent Memory supplies bounded
context. The Agent owns all design reasoning and decisions.

## Workflow

Use this workflow for a material design choice. Follow the parent Skill's
selective routing first: a direct local edit does not require entering the
full design workflow. An explicit request to query Memory still requires it.

1. Frame the decision using the intake below. Reuse the user's request and
   applicable project documents; do not ask the user to author Runtime JSON.
2. Run an orientation query:

```bash
python3 tools/agent_memory.py design-context --project . --query "<design goal>" --compact --json
```

3. Inspect `current_repository.source_anchors` in current source. Treat graph
   relations as navigation evidence and missing edges as uncertainty.
4. Review task constraints, semantic corrections, and memory evidence in
   authority order. Historical experience cannot establish current architecture.
   When `project_context.normative_context` is returned, inspect the source document,
   approval reference, scope and supersession claims. Use an applicable approved
   specification to describe expected behavior, and current source to describe actual
   behavior. Drafts and stale references do not become hard constraints.
5. Use quality questions and knowledge entries to decide which concerns and
   principles actually apply. A returned pattern reference is not a recommendation.
6. When context is broad, query again with Agent-confirmed concerns and anchors:

```bash
python3 tools/agent_memory.py design-context --project . \
  --query "<same design goal>" \
  --concern modifiability --concern compatibility \
  --anchor "src/Feature.ets" \
  --constraint "<hard task constraint>" \
  --compact --json
```

7. Reconstruct current responsibilities, state ownership, behavior, data,
   failure paths, consumers, and change pressure from source and context.
8. Use the reference and review guidance below to author the smallest complete
   design. Add alternatives only for a material quality or structural tradeoff.
9. Explain applicable principles, rejected alternatives, assumptions, risks,
   and verification. Never cite a pattern name as the sole rationale. Use the
   decision template only when the choice deserves a durable record.
10. Use current tests, compiler output, source inspection, and optional factual
    validators to verify claims. A clean bounded check does not prove quality.

## Frame The Decision

Scale the work to the request. A local edit with an obvious implementation does
not need an architecture document, a reference search, or several candidates.
Keep the parent Skill's selective-retrieval rules and explicit Memory requests.
For an actual design decision, prefill a short brief:

| Input | Establish before committing to a design |
|---|---|
| Outcome | Who needs a different behavior; what observation would show success? |
| Hard constraints | Which APIs, data, lifecycle guarantees, and applicable contracts must hold? |
| Non-goals | Which tempting adjacent changes are outside this task? |
| Quality priorities | Which qualities compete here; what concrete scenario makes each important? |
| Change pressure | Which credible next change should stay local; which future needs are speculation? |
| Unknowns | What missing fact could change the selected mechanism or scope? |

Label statements as user requirements, reviewed project contracts, observed
facts, assumptions, or unknowns. An approved contract states intended behavior;
source states actual behavior. A discrepancy is a question to resolve, not
permission to silently replace either. Do not invent latency targets or load.
Ask only questions whose answers materially affect the decision. Continue
independent inspection; keep unresolved assumptions visible in the proposal.

## Select References, Not Answers

Read [design-reference-guide.md](design-reference-guide.md) when selecting a
design method, reference case, or pattern. Use only the relevant entry; do not
load a whole catalog for every task. Read
[design-examples.md](design-examples.md) when a worked example would resolve
uncertainty about scope, historical transfer, or unnecessary abstraction.

Identify the problem features first: the volatile decision, responsibility or
state owner, lifetime, consistency requirement, failure boundary, and credible
change. Search project decisions and experience using the existing context
commands. Generic external guidance remains advisory and can be read directly.
Do not infer that Memory adds value merely because it returned a reference.

For a reference that influences the decision, explain:

- the matching problem features and current evidence;
- required preconditions that are confirmed, unknown, or contradicted;
- what can transfer and what must not transfer;
- the cost or counterexample that would make the reference a poor fit.

Unknown prerequisites are not satisfied prerequisites. A lexical match is not
architectural fitness. No suitable reference, retaining the current structure,
or using a direct implementation are all valid outcomes.

## Review Material Alternatives

Include the current design as a baseline when meaningful. Compare distinct
mechanisms under the same requirements, rather than cosmetic variants or a
mandatory candidate count. Review the consequences, not a summed taste score:

| Lens | Decision-changing question |
|---|---|
| Boundary | Which changing decision is hidden; can consumers avoid knowing it? |
| Ownership | Who mutates state, validates identity, and ends the lifetime? |
| Completeness | What happens on failure, stale input, partial completion, and recovery? |
| Complexity | Is complexity removed or moved to callers, wiring, and special cases? |
| Evolution | For one credible future change, what changes and what stays stable? |
| Reversal | What would invalidate this choice; how can it be changed safely? |

Honor hard constraints first, then the task's quality priorities and total
maintenance cost. Principles can conflict: fewer layers may leak implementation
details; more abstraction may increase caller burden. One implementation can
still need a boundary for ownership, trust, or testing. Smallest complete does
not mean fewest lines. Follow stricter project-specific change policies.

For a durable choice, adapt
[design-decision-template.md](design-decision-template.md). Do not require this
format for a short answer. State whether each validation is planned, observed,
failed, or unknown; source checks do not establish long-term maintainability.

## Record Conditional Feedback

After an actual design attempt, use the existing `agent-memory-reflect` Skill
when a reusable lesson is worth saving. Keep the decision document in Git and
save a concise lesson with source/version references, conditions, alternatives
rejected, observed results, and a revisit condition. A design-only outcome can
be complete while its implementation and long-term benefits remain unverified.
Do not turn a hypothetical result into `what_worked` or a verified procedure.
Track helpful, ignored, misleading, or superseded reuse through the existing
experience feedback path. One successful check does not authorize a new global
rule, automatic Skill update, or a system meta-review.

## Context Interpretation

- `authority_order`: precedence when evidence conflicts.
- `current_repository`: graph snapshot, source anchors, boundaries, state
  owners, consumers, tests, and observability anchors.
- `project_context`: explicit constraints, scoped semantic corrections, and
  historical memory warnings, plus separately labeled normative-document candidates
  when a matching ADR or Feature Spec was learned. Their declared approval requires
  Agent review; the Runtime does not certify a decision or specification.
- `quality_context`: lexical routing hints and scenario questions. The Agent
  confirms or rejects each concern.
- `design_knowledge`: general principles, tactics, and patterns with
  applicability, preconditions, contraindications, tradeoffs, questions, and
  provenance.
- `evidence_gaps`: facts to inspect or mark as assumptions.
- `expansion_hints`: inputs for the next focused query.

## Hard Boundary

The Runtime must not recommend a pattern, generate candidates, rank
alternatives, select a design, or create an implementation plan. The Agent must
not reinterpret retrieval relevance as architectural fitness.

The older `design-assist`, `design-prepare`, `design-check`, `design-compare`,
and `design-progress` commands are compatibility-only. Do not use their
Runtime-generated guidance, ranking, or change plan in the normal design flow.
`design-verify` may be used only for objective source, API, graph, compiler, and
test evidence after Agent-owned design and implementation.

## Output

Return current structure facts, design goals and constraints, quality scenarios,
the Agent's selected design, material alternatives, principle-based reasoning,
affected areas, assumptions, risks, and a verification plan. Cite current files,
symbols, graph references, project constraints, and knowledge sources used.
