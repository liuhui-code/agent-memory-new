# Code Graph And Query Performance Plan

**Goal:** Keep query and partial code learning bounded as SQLite grows beyond 500,000 graph rows, without losing business semantics or weakening exact code evidence.

**Constraints:** Keep `tools/agent_memory.py` as the only runtime entry point, SQLite as the source of truth, four user-facing skills, and every Python source file below 500 lines.

## Baseline

Two temporary real-project benchmarks established the starting point:

- `didi/dimina`: 939 parsed files, 6,361 symbols, 11,057 edges, 13 MiB database.
- `openharmony/applications_app_samples`: 16,300 parsed files, 84,227 symbols, 18,240 logs, 965,501 edges, 752 MiB database.
- Large-project search took about 6.7 seconds, although the actual retrieval pass took about 0.31 seconds.
- A 33-line partial refresh took 22.05 seconds.
- 792,404 edges were `tested_by` links created by global basename matching across unrelated sample modules.

## Phase 1: FTS Lifecycle

- [x] Store an explicit FTS schema version in SQLite.
- [x] Build FTS tables and triggers idempotently.
- [x] Rebuild FTS content only on first creation, version change, or explicit repair.
- [x] Keep trigger-maintained incremental writes as the normal path.
- [x] Test that a second `ensure_initialized` call does not rebuild populated FTS tables.
- [x] Test that explicit repair restores deliberately damaged FTS content.

## Phase 2: High-Precision Test Relations

- [x] Recognize tests from explicit test directory segments and test/spec filename conventions.
- [x] Exclude configuration and documentation files from `tested_by` inference.
- [x] Derive a bounded module root from HarmonyOS package markers and source layout.
- [x] Pair production and test files only inside the same module boundary.
- [x] Prefer normalized production/test stems and skip ambiguous many-to-many matches.
- [x] Test repeated `Index.ets`, `module.json5`, and `TestRely` paths from independent modules.

## Phase 3: Safe Derived Rebuild

- [x] Add one maintain runtime command for rebuilding derived search or graph data.
- [x] Preserve code rows, business summaries, business terms, semantic facts, episodes, and reflections.
- [x] Rebuild graph edges transactionally from current code rows and source files.
- [x] Return before/after relation counts and a graph amplification audit.
- [x] Support external learning sources through the existing `--source` convention.
- [x] Document that full `wiki-index --replace` is not required for graph repair.

## Phase 4: Scoped And Batched Refresh

- [x] Push changed-file filtering into SQL instead of loading every symbol and log row.
- [x] Load only the global lookup data required by cross-file relations.
- [x] Batch containment and log-edge inserts with `executemany`.
- [x] Compute source revision once per rebuild.
- [x] Write extractor metadata during insertion instead of timestamp-based post-annotation.
- [x] Keep reverse-dependent expansion bounded and deterministic.

## Phase 5: Quality And Scale Gates

- [x] Add graph amplification metrics, including edges per node and relation dominance.
- [x] Flag a single heuristic relation that dominates the graph.
- [x] Add synthetic independent-module fixtures to prevent cross-module graph pollution.
- [x] Verify query results still include valid same-module test relationships.
- [x] Verify partial refresh preserves business semantics.
- [x] Verify all Python source files remain below 500 lines.

## Phase 6: Verification

- [x] Run focused FTS, graph, refresh, query, and design tests.
- [x] Run the complete unit test suite.
- [x] Rebuild the OpenHarmony benchmark graph with the corrected matcher.
- [x] Record full index, partial refresh, hit query, miss query, health, edge count, and database size.
- [x] Update runtime documentation, schema reference, skill guidance, and `gitlog.md`.

## Acceptance Criteria

- Repeated query commands do not rewrite FTS tables.
- Large-project query initialization overhead is removed.
- `tested_by` never links configuration files or unrelated modules.
- Safe graph rebuild preserves all non-derived memory and code business fields.
- Partial refresh reads scoped symbol/log rows rather than full project rows.
- Existing retrieval, design, incident, refresh, and governance tests remain green.

## Completed Results

- Large-project active graph: 202,298 edges after a full rebuild, down from 965,501.
- `tested_by`: 311 high-precision module-local edges after safe graph rebuild, down from 792,404 polluted edges.
- Large-project miss query: 0.66 seconds after version migration, down from 6.77 seconds.
- Large-project hit query: 1.89 seconds, down from 6.67 seconds.
- 33-line partial refresh: 1.99 seconds, down from 22.05 seconds.
- `maintain-health` after graph repair and SQLite compaction: 2.24 seconds, down from 17.40 seconds.
- Full 16,300-file index: 132.50-137.74 seconds, down from 175.29 seconds.
- Compacted database: 312-328 MiB, down from 752 MiB.
- Semantic rebuild: 9,485 ArkTS/TypeScript files, 36,935 entities, 59,442 extracted relations, and no adapter errors.
- Verification: 298 tests, compilation, line-limit check, four-Skill check, CLI help, and diff check passed.
