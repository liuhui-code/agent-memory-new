# Lazy Governance and Graph Quality Snapshot Plan

**Goal:** Make focused maintenance proportional to the selected governance lane and avoid repeated full graph-quality scans when the derived graph has not changed.

## Compatibility Boundaries

- `maintain-plan` without `--action-lane` keeps the complete output and behavior.
- Unknown lane names retain the existing full-computation/no-match behavior so existing automation receives lane hints.
- Known lanes execute only their declared dependencies and return `execution_scope.mode = focused`.
- SQLite remains the source of truth; graph quality is a revision-bound derived snapshot, not durable project knowledge.
- `tools/agent_memory.py` remains the only runtime entry point and the four user-facing Skills remain unchanged.

## Phase 1: Graph Revision State

- [x] Add `graph_runtime_state` keyed by project id with graph revision and timestamp.
- [x] Increment graph revision in the central code-memory edge rebuild transaction.
- [x] Keep snapshot invalidation transactional with graph writes.
- [x] Initialize old databases lazily at revision zero without rebuilding the graph.

## Phase 2: Revision-Bound Quality Snapshot

- [x] Split graph-quality computation from snapshot orchestration.
- [x] Return a cached payload when the runtime snapshot revision matches SQLite.
- [x] Recompute and persist a disposable runtime snapshot when absent or stale.
- [x] Add `--verify-graph-quality` to `maintain-health` and `maintain-plan` to force recomputation.
- [x] Expose `graph_revision`, `quality_revision`, and `snapshot_status` in graph-quality output.

## Phase 3: Lane Dependency Registry

- [x] Define the supported governance lanes and their loader groups in one module.
- [x] Provide explicit empty context defaults for focused action construction.
- [x] Compute only the selected lane's review, graph, quality, usage, trace, feedback, or semantic dependencies.
- [x] Precompute log-design candidates instead of querying from inside action rendering.

Lane groups:

| Lane | Required groups |
| --- | --- |
| `graph_quality` | graph snapshot, graph signal, semantic-provider health |
| `log_diagnosis` | graph signal, query misses, log-design candidates, semantic gap hints |
| `memory_tiers` | memory tier summary |
| `memory_quality` | quality rows/report, evidence chains, retrieval feedback |
| `active_learning` | graph signal, quality report, experience usage |
| `skill_evolution` | review rows, skill patterns, incident strategies, high-value quality rows |
| `learn_semantic_repair` | review rows, semantic conflicts/drift/gaps, correction templates, quality rows |
| `memory_hygiene` | review rows and reflection quality |
| `experience_conflict` / `retrieval_interference` | bounded active reflections |
| Other explicit lanes | their single bounded loader group |

## Phase 4: Focused Plan Output

- [x] Build actions only for the requested known lane.
- [x] Filter mixed quality/review actions to the requested lane before priority scoring.
- [x] Return computed-group metadata so zero values are not mistaken for full-archive health.
- [x] Preserve action-budget navigation and compact output.
- [x] Keep the existing full planner as the fallback path.

## Phase 5: Verification

- [x] Add public CLI tests for snapshot hit, invalidation, and forced verification.
- [x] Add public CLI tests proving all 18 focused lanes return only their Lane and report focused execution.
- [x] Profile SQLite statement counts for full and focused plans on the same archive.
- [x] Run focused tests and the complete suite; compilation and repository gates are recorded below.
- [x] Benchmark full and focused plans on the 312 MiB corpus.

## Results

- Final suite: 310 tests passed in 368.818 seconds.
- Warm full plan: 0.86 seconds and 167 SQLite execute calls.
- Focused `memory_tiers`: 0.41 seconds and 33 execute calls.
- Cached focused `graph_quality`: 0.49 seconds and 39 execute calls.
- The lightweight focused Lane reduced SQL calls by about 80% relative to the warm full plan.
- Graph quality returns `recomputed` on first/stale access, `hit` on a matching revision, and `verified` after explicit force verification.
