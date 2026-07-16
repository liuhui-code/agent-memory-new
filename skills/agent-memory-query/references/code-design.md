# Agent-Owned Code Design Protocol

Use this protocol for feature design, refactoring, interface changes, state flow,
service boundaries, or module decomposition. Agent Memory supplies bounded
context. The Agent owns all design reasoning and decisions.

## Workflow

1. Read the user's goal, explicit constraints, exclusions, and acceptance
   criteria. Do not ask the user to author Runtime JSON.
2. Run an orientation query:

```bash
python tools/agent_memory.py design-context --project . --query "<design goal>" --compact --json
```

3. Inspect `current_repository.source_anchors` in current source. Treat graph
   relations as navigation evidence and missing edges as uncertainty.
4. Review task constraints, semantic corrections, and memory evidence in
   authority order. Historical experience cannot establish current architecture.
5. Use quality questions and knowledge entries to decide which concerns and
   principles actually apply. A returned pattern reference is not a recommendation.
6. When context is broad, query again with Agent-confirmed concerns and anchors:

```bash
python tools/agent_memory.py design-context --project . \
  --query "<same design goal>" \
  --concern modifiability --concern compatibility \
  --anchor "src/Feature.ets" \
  --constraint "<hard task constraint>" \
  --compact --json
```

7. Reconstruct current responsibilities, state ownership, behavior, data,
   failure paths, consumers, and change pressure from source and context.
8. Author the smallest viable design. Add alternatives only for a material
   quality-attribute or structural tradeoff.
9. Explain applicable principles, rejected alternatives, assumptions, risks,
   and verification. Never cite a pattern name as the sole rationale.
10. Use current tests, compiler output, source inspection, and optional factual
    validators to verify claims. A clean bounded check does not prove quality.

## Context Interpretation

- `authority_order`: precedence when evidence conflicts.
- `current_repository`: graph snapshot, source anchors, boundaries, state
  owners, consumers, tests, and observability anchors.
- `project_context`: explicit constraints, scoped semantic corrections, and
  historical memory warnings.
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
