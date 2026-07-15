# Repository-Grounded Code Design Protocol

Use this protocol for feature design, refactoring, interface changes, state flow, service boundaries, or module decomposition. Base the design on current repository facts and general software-design reasoning, not on learned project patterns.

## Workflow

1. Start with `design-assist` for a natural-language design request. Read current structure, forces, recognized patterns, pattern candidates, principle checks, and required decisions.
2. Clarify only unresolved business tradeoffs, exclusions, hard constraints, and measurable acceptance criteria. Do not ask the user to author runtime JSON.
3. Express scope, exclusions, acceptance criteria, constraints, and open questions as `design-intent/v1` internally for substantial work.
4. Use `design-prepare` only when the full revision-bound workbench is needed; resolve blocking authoring gaps before proposing a candidate.
5. Reconstruct topology, ownership, behavior, data, failure, runtime, and change views from the candidate-independent baseline.
6. Identify stable boundaries and the smallest credible extension points.
7. Generate the smallest viable candidate first; add alternatives only for a material structural or behavioral tradeoff.
8. Express each serious candidate as `design-delta/v2`, binding scenario claims to Delta, repository, and verification references.
9. Run `design-check`; when alternatives exist, run `design-compare` and preserve its decision, sensitivities, tradeoffs, and selected plan.
10. Implement dependency-ready `change_plan.steps`; independent steps may proceed together. Treat `in_progress` added files as incomplete until the expected semantic declaration exists.
11. Run `design-verify` against the implementation base and existing machine-readable test/compiler reports. Bind high-trust reports with `verification-run/v1`; stale bound evidence cannot verify an obligation. Record only the compact reviewed outcome.

```bash
python tools/agent_memory.py design-assist --project . --query "<design goal>" --mode design-only --json
python tools/agent_memory.py design-prepare --project . --intent "<intent.json>" --contract "<contract.json>" --json
python tools/agent_memory.py design-check --project . --intent "<intent.json>" --proposal "<proposal.json>" --contract "<contract.json>" --json
python tools/agent_memory.py design-compare --project . --intent "<intent.json>" --proposal "<a.json>" --proposal "<b.json>" --contract "<contract.json>" --json
python tools/agent_memory.py design-progress --project . --proposal "<selected.json>" --base HEAD --test-report "<junit-or-json-report>" --verification-run "<verification-run.json>" --json
python tools/agent_memory.py design-verify --project . --proposal "<selected.json>" --base HEAD~1 --test-report "<junit-or-json-report>" --verification-run "<verification-run.json>" --json
python tools/agent_memory.py design-outcome --project . --verification "<verification.json>" --outcome success --json
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
- Treat `existing_patterns` as structurally observed signals, `pattern_candidates` as conditional tactics, and `needs_evidence` or `caution` as unresolved applicability. Never apply a pattern from its name alone.

## Delta Graph

The proposal describes intended structural change, not source code or chain-of-thought:

```json
{
  "schema_version": "design-delta/v2",
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
  "coverage_evidence": [],
  "verification": {"tests": ["profile cache tests"], "observability": ["cache result signal"]}
}
```

## Output

Return current architecture facts, constraints, candidate approaches, rejected alternatives, proposed Delta Graph summary, check findings, affected areas, assumptions, risks, and verification plan. Do not present a generic pattern name as the design rationale.
