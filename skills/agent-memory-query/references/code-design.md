# Repository-Grounded Code Design Protocol

Use this protocol for feature design, refactoring, interface changes, state flow, service boundaries, or module decomposition. Base the design on current repository facts and general software-design reasoning, not on learned project patterns.

## Workflow

1. Clarify the goal, exclusions, hard constraints, and measurable acceptance criteria.
2. Run design evidence retrieval and inspect `architecture_slice`.
3. Reconstruct current responsibilities, dependency direction, state ownership, public consumers, tests, and observability.
4. Identify stable boundaries and the smallest credible extension points.
5. Generate two or three materially different candidate designs only when a real tradeoff exists.
6. Express each serious candidate as a Delta Graph.
7. Express hard constraints and measurable quality attributes as `design-contract/v1` when the choice is non-trivial.
8. Run `design-check`; when alternatives exist, run `design-compare` and preserve explicit tradeoffs.
9. Recommend the smallest viable design, then run `design-verify` after implementation and focused tests.

```bash
python tools/agent_memory.py evidence-context --project . --goal design --query "<design goal>" --json
python tools/agent_memory.py design-check --project . --proposal "<proposal.json>" --json
python tools/agent_memory.py design-compare --project . --proposal "<a.json>" --proposal "<b.json>" --contract "<contract.json>" --json
python tools/agent_memory.py design-verify --project . --proposal "<selected.json>" --base HEAD~1 --executed-tests "<test command>" --json
```

## Design Rules

- Reuse an existing responsibility boundary before adding an abstraction.
- Add an abstraction only for a demonstrated variation, coupling, ownership, or testability problem.
- Keep state ownership explicit and singular unless synchronization is part of the design.
- Preserve dependency direction; do not move business logic into UI, routing, logging, or configuration layers.
- Check every known consumer before changing a public interface.
- Give each new branch a test or inspectable verification path.
- Add observability only at high-value start, decision, failure, or result points.
- Mark anything not supported by current source or graph as an assumption.
- Treat missing graph coverage as uncertainty, not permission.
- Historical experience may warn about constraints but cannot establish the current architecture or select a design by itself.

## Delta Graph

The proposal describes intended structural change, not source code or chain-of-thought:

```json
{
  "schema_version": "design-delta/v1",
  "id": "profile-cache",
  "contract_id": "profile-cache-contract",
  "goal": "Add profile cache",
  "anchors": ["file:src/ProfileService.ets"],
  "add_nodes": [{"id": "new:ProfileCache", "kind": "service", "file_path": "src/ProfileCache.ets"}],
  "modify_nodes": ["file:src/ProfileService.ets"],
  "add_edges": [{"source": "file:src/ProfileService.ets", "relation": "uses_service", "target": "new:ProfileCache"}],
  "remove_edges": [],
  "assumptions": [],
  "invariants": ["ProfilePage does not own persistence"],
  "constraint_coverage": [],
  "quality_coverage": [],
  "verification": {"tests": ["profile cache tests"], "observability": ["cache result signal"]}
}
```

## Output

Return current architecture facts, constraints, candidate approaches, rejected alternatives, proposed Delta Graph summary, check findings, affected areas, assumptions, risks, and verification plan. Do not present a generic pattern name as the design rationale.
