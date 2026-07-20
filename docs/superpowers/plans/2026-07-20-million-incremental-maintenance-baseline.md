# Million-Scale Incremental Maintenance Baseline

## Goal

Verify that Git-driven Scope maintenance remains proportional to relevant
changes when the SQLite archive already contains one million searchable code
entities and three million active graph edges.

## Workloads

Run against the same isolated production-schema archive used by `eval-scale`:

1. no repository change;
2. a committed change outside the learned Scope;
3. one changed Scope file containing 20 methods;
4. one changed Scope file containing 500 methods.

Each workload uses a real temporary Git repository, persisted learn Scope,
baseline revision, SHA-256 snapshot, FTS5 triggers, graph retirement/rebuild,
semantic adapter, and atomic index generation. Repository mutation and `git
commit` happen before timing; only maintenance latency is measured.

## SLO

- No change p95: at most 500 ms.
- Scope-external change p95: at most 500 ms and zero refreshed files.
- One 20-method file p95: at most 2,000 ms.
- One 500-method file p95: at most 5,000 ms.
- Every run must use `git/v1`, remain below overflow, and update only the
  expected Scope file.

## Risks To Measure

- one Git HEAD plus three path-filtered Git commands per Scope;
- accidental full-Scope snapshot fallback;
- loading all project files during a scoped graph rebuild;
- full active-edge counting after a local write;
- FTS delete/insert amplification for method-heavy files;
- retained invalid graph edges after repeated refreshes.

## Architecture

- Add maintenance measurements behind the existing `eval-scale` facade.
- Keep scenario setup in a dedicated module below 500 lines.
- Reuse normal Scope recording and refresh entry points rather than a benchmark
  implementation of incremental logic.
- Store aggregate timings and bounded refresh evidence in the scale report.
- Keep all Git repositories, source files, and databases temporary.

## Optimization Rule

Establish the unchanged baseline first. Change only operations shown by timing
or query-plan evidence to scale with total project data. Preserve exact graph
and semantic behavior; do not replace maintenance with a benchmark-only fast
path.

## Result

The first million-scale run failed the 20-method gate at 4,428.580 ms p95.
Phase evidence attributed 4,071.153 ms to graph rebuilding: a scoped refresh
still loaded every project file and recomputed test pairing with repeated path
parsing. Git discovery, invalidation, and row insertion were already bounded.

Scoped graph rebuild now constructs a candidate set from the changed files,
referenced symbols, exact import and router targets, module markers, and
basename-compatible test files. Basename candidates use the existing
`code_file_fts` path index, followed by strict suffix filtering. Full graph
rebuilds retain the all-file path. This avoids a new table or migration while
preserving import, route, design, and same-module test relations.

The final isolated run passed with 1,000,000 searchable entities, 3,000,000
active edges, and a 2,113.0 MiB database:

- no change: 90.221 ms p95;
- committed change outside Scope: 89.841 ms p95, zero refreshed files;
- one 20-method Scope file: 452.654 ms p95;
- one 500-method Scope file: 1,685.729 ms p95.

The 20-method graph phase fell from 4,071.153 ms to 87.627 ms. Every query,
query-plan, refresh-evidence, and incremental-maintenance gate passed.
