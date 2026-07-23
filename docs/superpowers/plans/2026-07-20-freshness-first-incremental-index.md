# Freshness-First Incremental Semantic Index

## Goal

Guarantee that source-derived Context evidence is versioned, incrementally
replaceable, and never presented as current after its source changes. Preserve
the four Skill surface, `tools/agent_memory.py` facade, SQLite source of truth,
and Agent-owned reasoning boundary.

Method-level behavior facts are a later consumer of this protocol, not the
first implementation step.

Implementation status: Phase 1, the Phase 2 Scope-provider/explicit-maintain
slice, and direct resolved-import boundary observation completed on 2026-07-20.
Automatic pre-query refresh, compiler-exact exported signatures, reverse
dependent expansion, method facts, and retention remain explicit follow-up
work and are not silently enabled by the runtime.

## Mature Foundations

- Git treats repository objects as content-addressed values. Derived records
  therefore bind to a source content digest rather than timestamps alone:
  <https://git-scm.com/book/en/Git-Internals-Git-Objects>.
- Bazel Skyframe records dependencies and invalidates only the reverse
  transitive closure of changed inputs. Unregistered reads make incremental
  results incorrect: <https://bazel.build/versions/8.4.0/reference/skyframe>.
- Tree-sitter edits and reuses an old syntax tree for incremental parsing:
  <https://tree-sitter.github.io/tree-sitter/using-parsers/3-advanced-parsing.html>.
- SCIP attaches symbol occurrences to source ranges for a specific index;
  Sourcegraph falls back to search when precise navigation is unavailable:
  <https://sourcegraph.com/docs/code-navigation/precise-code-navigation> and
  <https://sourcegraph.com/docs/code-navigation/writing-an-indexer>.
- SQLite readers observe committed snapshots, so a generation can become
  active atomically: <https://www.sqlite.org/isolation.html>.

## Invariants

1. Current worktree content overrides every source-derived record.
2. `source_digest` is authoritative; `mtime` is at most a scan optimization.
3. A query validates only recalled candidate files, never scans the repository.
4. Changed or deleted candidate files cannot contribute code, log, source, or
   path evidence until refreshed.
5. Legacy rows without a digest are labeled `unverified`; they are never
   described as current.
6. Refresh replaces all derived rows for each changed file in one transaction.
7. A failed refresh leaves the previous committed generation readable.
8. Derived code data is rebuildable cache. Experience and semantic corrections
   keep their independent governance lifecycle.

## Phase 1 - Candidate Freshness Gate

- Add `source_digest` and `index_generation` to code files, symbols, and logs.
- Add one `code_index_state` row per project with active generation, source
  revision, extractor version, status, and timestamp.
- Stamp all rows written by learning or refresh with the same generation.
- Validate the unique source files represented in a recalled candidate set.
- Block rows whose source is missing or whose digest changed.
- Retain digest-less legacy rows with an explicit `unverified` state.
- Remove blocked paths from path reconstruction before Context composition.
- Expose a bounded `source_freshness` object in full and compact Context.
- Report generation and unverified-row coverage from `maintain-health`.

## Phase 2 - Incremental Refresh Policy

- Add a provider-neutral `ScopeChangeProvider` contract for Git and non-Git
  roots. Providers receive one persisted learn Scope; they never decide the
  business boundary from repository-wide activity.
- Define the relevant set as `git_changes AND (scope_paths OR registered
  boundary_dependencies)`. Git is a candidate provider; SHA-256 remains the
  authority for whether content changed.
- Persist a Git baseline per Scope after successful learning or refresh. Compare
  that baseline directly with the current worktree, so many intermediate team
  commits collapse into one final net change set.
- Use exact learned paths for entry Scopes, the learned subtree for path Scopes,
  and repository scope only for an explicit project Scope. Include untracked
  files inside the Scope and retain snapshot fallback for non-Git roots,
  missing baselines, rebases, and provider failures.
- Bound synchronous incremental work by relevant candidate count. An overflow
  keeps the old checkpoint, marks the Scope dirty, and relies on the query
  freshness gate until a confirmed batch refresh; unrelated repository changes
  never consume this budget.
- Automatically refresh before retrieval only after latency and rollback tests
  pass. Phase 2 maintenance integration remains explicit and daemon-free.
- Invalidate graph relations for changed endpoints. A later boundary-dependency
  stage may expand to direct reverse dependents only when exported signatures
  change.

Completed boundary slice:

- Register resolved project imports outside each learned Scope as observation
  boundaries without indexing or learning those dependency files.
- Union exact boundary paths into Git candidate discovery and keep Scope and
  boundary candidates separately visible.
- Compare dependency content and extractor-level symbol-surface digests. Treat
  the latter as a structural approximation, not a compiler ABI assertion.
- Surface `boundary_drift` through maintenance results, relevant Context
  freshness, and governance health; require reviewed full refresh to accept a
  new boundary baseline.

## Phase 3 - Method-Level Derived Facts

- Extend language adapters to emit generic behavior facts bound to symbol key,
  source digest, and exact range.
- Store behavior facts as disposable derived rows in the active generation.
- Rank fresh method passages first, then attach bounded code graph, log, and
  experience context.
- Keep ArkTS extraction behind the language-neutral semantic adapter contract.

## Phase 4 - Retention And Scale

- Keep the active generation and at most one rollback generation if generation
  history is materialized later.
- Garbage-collect older derived generations; never copy them into durable
  experience memory.
- Benchmark 500,000 derived rows, dirty worktrees, file moves, deletes, partial
  provider failure, interrupted refresh, and concurrent readers.

## Release Gates

- Zero stale anchors after edit, delete, rename, and method move mutations.
- Unchanged queries perform no repository-wide hash scan.
- Single-file refresh work is proportional to the file and registered reverse
  dependencies, not total repository size.
- Readers never observe mixed generations.
- Full and compact Context report `current`, `partial_current`, `unverified`,
  or relevant `boundary_drift`.
- Query and storage budgets do not regress beyond the established performance
  gate.
- A new sealed real-project pack and Agent A/B must both improve before
  promotion. Consumed holdouts remain immutable and are never rerun.
