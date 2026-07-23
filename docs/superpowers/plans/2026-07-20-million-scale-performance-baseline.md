# Million-Scale Performance Baseline

## Goal

Prove, rather than assume, that method-level code context remains responsive at
large local-project scale. Keep the benchmark isolated from durable memory and
preserve the four Skill surface and `tools/agent_memory.py` runtime facade.

## Capacity Model

The baseline counts searchable entities separately from graph edges because a
method produces a symbol row, an FTS5 document, containment, and zero or more
semantic relations.

- `ci`: 100,000 searchable code entities and 300,000 active graph edges.
- `million`: 1,000,000 searchable code entities and 3,000,000 active graph
  edges.
- Entity mix: 5% files, 80% methods, and 15% code log statements.
- Edges include file containment and method call relations.
- Stable target records and high-frequency distractors make every run
  deterministic and comparable.

FTS5 internal posting rows are not counted as entities. Database size is
reported separately.

## Workloads

Measure warm p95 latency for:

1. bounded candidate recall for a precise hit;
2. bounded candidate recall for an absent term;
3. bounded abstention for a saturated generic method term;
4. qualified method lookup;
5. file-local method lookup;
6. active outgoing calls;
7. active incoming calls;
8. exact log-template FTS recall.

Run `EXPLAIN QUERY PLAN` for base-table lookups. Qualified method, file-local
symbol, and both graph directions must use named composite indexes. FTS virtual
table scans are expected; base-table scans are not.

## SLO

- Candidate recall hit and miss p95: at most 800 ms.
- Generic method-term abstention p95: at most 100 ms.
- Exact log FTS p95: at most 1,000 ms.
- Qualified method, file-local symbol, and graph-neighbor p95: at most 100 ms.
- Every required query-plan index must be present.

These primitive gates support, but do not replace, the existing user-facing
Context p95 target of 800 ms and Search target of 1,000 ms.

## Architecture

- `eval-scale` is an evaluation command behind the existing runtime facade; it
  is not a fifth Skill.
- A temporary per-run SQLite archive uses the production schema, indexes, FTS5
  triggers, WAL, and bounded candidate-recall implementation.
- Batched deterministic inserts build the corpus. Setup time is reported but is
  not mixed into query latency.
- The compact JSON report is written to `runtime/last_scale_benchmark.json`.
- `--fail-on-slo` turns latency or query-plan failures into a release gate.
- Normal unit tests use a tiny profile. Million-scale execution is explicit and
  belongs in release or scheduled validation, not every test discovery run.

## Optimization Order

1. Establish the unchanged query baseline.
2. Remove accidental full scans and project-wide work from bounded query paths.
3. Bound fallback retrieval when FTS returns no candidate.
4. Add active-edge retention and selective FTS only when measured write or
   storage amplification requires them.
5. Re-run the same seeded profile after every optimization.

## Acceptance

- Tiny-profile tests validate counts, deterministic target recall, report
  schema, SLO evaluation, and query-plan gates.
- The `ci` profile passes before running `million`.
- The `million` report contains exactly 1,000,000 searchable entities and
  3,000,000 active edges.
- No benchmark database is left in project memory.
- All Python source files remain at or below 500 lines.

## Result - 2026-07-20

The unchanged million profile failed despite all exact method and graph index
lookups remaining below 0.04 ms. Candidate hit, candidate miss, and saturated
method-prefix FTS measured 12,089 ms, 10,952 ms, and 11,317 ms p95. CamelCase
domain terms were falling through to `%LIKE%` scans, while a generic method
prefix forced BM25 work over 800,000 symbols.

The measured repair persists bounded identifier components in method summaries,
skips low-information method/class/function/symbol-only retrieval, limits
code-table LIKE compatibility fallback to a 50,000-row high watermark, and adds
a direct `(project_id, qualified_name)` method index.

The repeated million profile passed with exactly 1,000,000 entities and
3,000,000 active edges in a 2,008.3 MiB temporary database. Candidate hit p95
was 72.095 ms, candidate miss 24.571 ms, generic-term abstention 0.093 ms, exact
log FTS 0.265 ms, and every qualified/file-local/graph lookup at or below 0.024
ms. Setup took 194.364 seconds and total execution 208.269 seconds. All required
query plans used accepted composite indexes.
