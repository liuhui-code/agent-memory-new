# Goal-Oriented Evidence Fabric Implementation Plan

**Goal:** Coordinate memory retrieval, code graph, log graph, and incident causal evidence so an Agent receives one ranked, explainable context for diagnosis and change-impact work.

**Constraints:** Keep the four public skills, `tools/agent_memory.py` as the only runtime entry point, SQLite as source of truth, bounded graph traversal, no vector or graph database, and every Python file at or below 500 lines.

## Architecture

```text
User goal / changed files
  -> Goal Planner
  -> Existing FTS5 + code graph + log graph + incident trace collectors
  -> Unified EvidenceItem records
  -> Goal-aware fusion and bounded reranking
  -> Evidence chains, gaps, and next actions
  -> Runtime audit summary + existing governance feedback
```

The coordination layer does not replace existing ranking or storage. It normalizes the best candidates from each existing subsystem and applies a second, bounded cross-domain ranking pass. Historical experience stays advisory and cannot outrank direct current-code anchors only because it is recent or lexically similar.

## Industry Alignment

- Change Impact Analysis: start from an explicit change set, follow bounded dependency relationships, and turn likely impact into verification scope.
- Requirements Traceability: retain explainable links from a goal or symptom to code, logs, incidents, and validation actions.
- OpenTelemetry signal/context patterns: prefer stable event, logger, correlation, error, route, and resource fields over raw log prose when available.
- Retrieval-Augmented Generation: retrieve from specialized stores, normalize incompatible scores, rerank against the current goal, and expose grounding evidence to the LLM.

These are implemented with the project's existing SQLite, FTS5, and lightweight edges. No external graph, vector, telemetry, or orchestration service is introduced.

## Unified Contract

Each returned evidence item contains:

- stable `evidence_id` derived from source type and row id
- `source` and `kind`
- compact `title`, `summary`, and current-source `location`
- original retrieval score plus normalized relevance, trust, freshness, graph, and goal-fit components
- penalties for stale, misleading, conflicting, weak, or unsupported evidence
- final score, reasons, warnings, and linked anchors

The output also contains:

- a deterministic goal plan and selected retrieval lanes
- top evidence grouped into direct, supporting, and advisory tiers
- bounded evidence chains and explicit evidence gaps
- recommended inspections or verification actions
- an audit summary with candidate counts and score factors

## Phase 1: Goal Planning and Evidence Normalization

- [x] Add deterministic goal classification for diagnosis, change impact, code understanding, experience reuse, and governance.
- [x] Map goals to retrieval lanes and per-source weights.
- [x] Normalize existing semantic, reflection, episode, code, log, edge, and incident-trace results.
- [x] Preserve existing calibration warnings and retrieval explanations.

Acceptance:

- The same query always produces the same plan.
- Every item has a source, stable id, score components, reasons, and authority tier.
- Current code and direct log anchors have higher authority than historical experience.

## Phase 2: Evidence Fusion and Explainable Chains

- [x] Normalize scores within each source lane so raw scoring scales cannot dominate other lanes.
- [x] Apply goal-fit, trust, graph proximity, freshness, and evidence-completeness bonuses.
- [x] Apply stale, misleading, conflict, unsupported, and weak-evidence penalties.
- [x] Build bounded chains from direct anchors through existing memory edges and incident-trace links.
- [x] Report missing code, log, incident, or experience evidence as gaps rather than fabricating a chain.

Acceptance:

- A recently stored weak experience cannot displace a direct source/log match.
- Every top result exposes the factors that produced its final score.
- Chain depth and output size are bounded.

## Phase 3: Evidence Context Command

- [x] Add `evidence-context --query ... --json` to the existing runtime CLI.
- [x] Reuse current query usage and performance sampling.
- [x] Write only the latest compact runtime artifact to `runtime/last_evidence_context.json`.
- [x] Keep raw user logs out of persistent memory.

Acceptance:

- The command returns a compact, LLM-ready context.
- Empty lanes produce actionable evidence gaps.
- Existing `search` and `context` behavior remains compatible.

## Phase 4: Change Impact Command

- [x] Add `impact-scope` with `--base`, `--files`, and `--diff-file` inputs.
- [x] Resolve Git changed files without shell execution and validate paths inside the project.
- [x] Find exact learned file anchors, contained symbols/logs, and bounded incoming/outgoing graph edges.
- [x] Query related incidents and experience using changed-path and business-semantic terms.
- [x] Score direct, likely, and advisory impact tiers and produce a verification checklist.

Acceptance:

- Exact changed files are always direct impact.
- Reverse import/router dependents are reported as likely impact.
- Experience and incidents remain advisory evidence.
- Unlearned changed files are reported as coverage gaps.

## Phase 5: Governance Integration

- [x] Add compact coordination signals to the existing task trace through query usage recording.
- [x] Reuse query misses and retrieval feedback instead of adding duplicate feedback tables.
- [x] Update query and maintain skill guidance without adding a public skill.
- [x] Document operational usage and authority rules.

Acceptance:

- `maintain-plan` can continue using existing misses, feedback, graph quality, and task traces.
- The public skill count remains four.
- No full result payload or temporary raw log is appended to SQLite.

## Phase 6: Verification

- [x] Add focused unit and CLI integration tests.
- [x] Run new tests and affected query/graph/incident tests.
- [x] Run the full test suite.
- [x] Run compile, line-limit, and diff checks.
- [x] Update `gitlog.md` with implementation and verification evidence.

## Performance Boundaries

- FTS5 candidate pools remain capped by existing limits.
- Fusion processes only bounded retrieved candidates.
- Impact graph traversal is one hop and queries indexed source/target columns.
- CLI result limits are explicit and capped.
- Only the latest context artifact is written to runtime storage.
- No raw diagnostic log persistence is introduced.

## Rollback

Remove the two CLI handlers and the evidence coordination modules. Existing `search`, `context`, code learning, incident trace, governance, schema, and four public skills remain independently usable.
