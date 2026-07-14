# Repository-Grounded Design Reasoning Plan

**Goal:** Add code-design reasoning grounded in current repository structure without growing the public skill set, turning historical design experience into the primary decision source, or moving LLM reasoning into the deterministic runtime.

**Architecture:** `agent-memory-query` becomes a thin progressive-disclosure router. A design request loads one focused protocol. The runtime returns current-source evidence, a bounded architecture slice, and deterministic checks over a proposed delta graph. The Agent remains responsible for generating and comparing design alternatives.

**Boundaries:** Keep four public skills, `tools/agent_memory.py` as the only runtime entry point, SQLite as source of truth, and every Python file at or below 500 lines. Do not add a design-memory table, vector store, graph database, daemon, full call graph, fifth skill, or runtime LLM dependency.

## Phase 1: Query Skill Progressive Disclosure

- [x] Reduce `skills/agent-memory-query/SKILL.md` to intent routing, command selection, evidence authority, and output requirements.
- [x] Move detailed code understanding, incident diagnosis, change impact, evidence policy, and design reasoning into one-level `references/` files.
- [x] Ensure a task loads one primary protocol and the shared evidence policy only when required.
- [x] Retire the memory-first change-design template in favor of the repository-grounded design protocol.

Acceptance:

- Main Query Skill is no more than 120 lines.
- All referenced files exist one level below `SKILL.md`.
- Existing query, diagnosis, impact, feedback, and evaluation guidance remains reachable.
- The formal user-facing skill count remains four.

## Phase 2: Design Goal

- [x] Add deterministic design-intent terms and an explicit `design` goal.
- [x] Weight current code and active graph edges above semantic memory and strongly cap historical experience influence.
- [x] Add design-specific retrieval facets and evidence requirements.
- [x] Expose `--goal design` through `evidence-context`.

Acceptance:

- Natural-language design requests select `design` unless a different goal is explicit.
- Design retrieval remains local by default and bounded to three rounds.
- Current code and graph evidence outrank advisory experience.

## Phase 3: ArkTS Design Graph and Architecture Slice

- [x] Extract ArkTS state ownership, component composition, event dispatch/handling, service construction/use, and test-target relationships where statically inspectable.
- [x] Store new relationships in existing versioned `memory_edges` rows with provenance.
- [x] Build an architecture slice from selected current-code anchors and active edges.
- [x] Return bounded nodes, typed edges, boundaries, state owners, extension points, consumers, tests, observability anchors, and evidence gaps.
- [x] Attach the slice only for the design goal.

Acceptance:

- Slice size is capped at 80 nodes and 160 edges.
- Traversal depth is capped at two and uses indexed active-edge lookups.
- Missing graph coverage is explicit; it is never interpreted as low risk.
- No complete call graph or new durable graph store is introduced.

## Phase 4: Delta Graph Design Check

- [x] Define a small JSON proposal contract for added/modified nodes, added/removed edges, assumptions, and invariants.
- [x] Add `design-check --proposal <file> --json` through the stable runtime entry point.
- [x] Validate proposal paths and relation shape without executing code or calling an LLM.
- [x] Check cycles, multiple state owners, reverse boundary dependencies, bypassed service boundaries, uncovered public consumers, missing tests, missing observability, and unknown anchors.
- [x] Separate errors, warnings, evidence, and unverifiable assumptions.

Acceptance:

- Invalid proposal shape exits clearly.
- Checks are deterministic and bounded.
- A clean proposal and a known-risk proposal produce distinguishable results.
- The proposal body is not persisted to SQLite.

## Phase 5: Evaluation and Documentation

- [x] Add focused tests for skill routing, design goal selection, ArkTS design edges, architecture slicing, proposal validation, and design checks.
- [x] Add representative ArkTS cases for state ownership, service boundaries, route/config impact, tests, and logs.
- [x] Update README, runtime, usage, and schema/protocol documentation.
- [x] Record the completed work in `gitlog.md`.

## Phase 6: Verification

- [x] Run focused query, graph, ArkTS, impact, and design tests.
- [x] Run the complete test suite.
- [x] Run Python compilation, line-limit, diff, CLI help, skill-reference, and four-skill checks.

## Performance Guardrails

- Design queries use existing FTS5 retrieval before graph expansion.
- Architecture expansion is local, depth <= 2, nodes <= 80, edges <= 160.
- Delta checks operate on bounded proposal plus bounded current graph.
- No design proposal, generated answer, raw log, or chain-of-thought is persisted.
- Historical reflections remain advisory and cannot establish current architecture facts.

## Rollback

Remove the `design` goal, architecture-slice attachment, and `design-check` command, then restore the prior Query Skill body. Existing memory, code wiki, graph, diagnosis, impact analysis, and four public skills remain usable.
