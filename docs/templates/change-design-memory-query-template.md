# Repository-Grounded Change Design Template

This compatibility template now points to the installed Query Skill's focused design protocol:

```text
skills/agent-memory-query/references/code-design.md
```

The design workflow is grounded in current code and typed graph relationships. Historical memory supplies warnings or business-semantic corrections only.

## Workflow

```text
Clarify goal and constraints
  -> retrieve design evidence
  -> inspect bounded architecture slice
  -> reconstruct current responsibilities and dependency direction
  -> generate candidate delta graphs
  -> run deterministic design checks
  -> compare tradeoffs
  -> recommend the smallest verifiable design
```

## Retrieve Current Architecture

```bash
python tools/agent_memory.py design-assist \
  --project . \
  --mode design-only \
  --query "<design goal and current anchor>" \
  --json
```

Read current code evidence before `architecture_slice`. Treat missing anchors or edges as coverage gaps. Do not infer an absent dependency from an incomplete learned scope.

## Check A Candidate

Express the intended structural change as nodes and typed edges, not as source code or hidden reasoning:

```json
{
  "goal": "",
  "anchors": [],
  "add_nodes": [],
  "modify_nodes": [],
  "add_edges": [],
  "remove_edges": [],
  "assumptions": [],
  "invariants": []
}
```

```bash
python tools/agent_memory.py design-check --project . --proposal proposal.json --json
```

Revise blocked candidates. Explain warnings that remain acceptable. A generic pattern name is not a sufficient design rationale.

## Output

- Goal, exclusions, and acceptance criteria
- Current architecture facts and evidence gaps
- Constraints and invariants
- Candidate designs and real tradeoffs
- Recommended Delta Graph
- Deterministic check findings
- Affected areas and verification plan

Do not persist the proposal as experience merely because it was generated. Reflect only after implementation and verification reveal a durable lesson.
