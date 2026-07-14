# Loop, Query, and Computation Optimization Plan

**Goal:** Remove repeated database reads and file-wide computations from hot loops without changing retrieval, semantic, or governance behavior.

## Constraints

- Keep SQLite as the source of truth and `tools/agent_memory.py` as the runtime entry point.
- Preserve current command payloads and ranking semantics.
- Keep every code file at or below 500 lines.
- Prefer bounded batch reads and per-file indexes over caches with lifecycle state.

## Phase 1: Semantic parsing context - Complete

- Add a per-file immutable parsing context containing fields by owner, state entities by owner, and imported paths.
- Build field/state/import indexes once after entities and imports are known.
- Replace the top-level function container membership scan with an ordered interval cursor.
- Add regression tests proving fields are scanned once per container, regardless of method count, and semantic relations remain unchanged.

## Phase 2: Query feedback batching - Complete

- Read semantic and reflection retrieval feedback in one bounded SQL query.
- Derive relevance penalties and calibration adjustments in one pass over those rows.
- Read semantic and reflection usage events in one bounded SQL query and partition results by record type.
- Keep single-type public helpers as compatibility wrappers.
- Add tests for output equivalence and bounded query counts.

## Phase 3: Edge lookup batching - Complete

- Merge outbound and inbound edge reads for each target type and ID batch into one indexed query.
- Preserve confidence ordering, deduplication, relation allowlisting, and global edge limits.
- Add a query-count regression test.

## Phase 4: Governance reuse - Complete

- Load active reflections once and reuse them for interference and conflict detection.
- Build skill pattern candidates once and reuse them in actions and summaries.
- Count action kinds in one pass instead of repeatedly filtering full action lists.
- Remove `locals()` as the implicit action-builder contract if this can be done without expanding the change surface; otherwise document it as the next structural phase.

`locals()` removal is deferred to the structural governance split because it does not reduce query or computation cost by itself.

## Phase 5: Profile-guided follow-up - Complete

- Reuse one graph-quality snapshot in graph signal quality instead of rebuilding it.
- Reuse one query result for query-miss focus and suggested terms.
- Replace the three-table missing-business-semantics `UNION DISTINCT` with bounded per-table reads and an equivalent global merge.
- Reuse graph governance aggregation for edge totals and low-confidence counts.
- Keep six indexed stale-edge probes after a one-query six-join experiment measured slower on the large corpus.

## Verification

- Run focused performance regression tests first.
- Run the complete unit test suite.
- Verify all Python files remain at or below 500 lines and `git diff --check` is clean.
- Re-run representative query and semantic-index benchmarks; report SQL call-count reductions separately from wall-clock results.

## Results

- Static semantic container-field scans: 40 to 1 in the regression fixture.
- Experience type classifications for 200 rows: 20,100 to 200.
- Exact context comparisons for 200 disjoint experiences: 19,900 to 0.
- Query feedback/usage connections: 6 to 2.
- Related-edge SQL per type batch: 2 to 1.
- Profiled `maintain-plan` SQLite execute calls on the 312 MiB corpus: 235 to 178.
- Large-corpus warm search: 0.52 seconds.
- Final full suite: 306 tests passed in 349.807 seconds.
