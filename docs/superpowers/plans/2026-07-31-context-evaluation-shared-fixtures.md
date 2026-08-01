# Context Capability Shared-Fixture Execution Plan

## Objective

Make the complete Context capability gate finish in a bounded window without weakening
case isolation, source provenance, Oracle checks, or the existing
`eval-context-capability` facade. The evaluator must index each distinct materialized
source once, apply each distinct memory setup once, and execute every query against an
independent writable memory snapshot.

## Problem Boundary

The 75 development scenarios expand to 225 query variants, but currently every variant
copies the source and runs `init` plus `wiki-index`. The pack contains only four distinct
source configurations and three context setups. Query execution is not read-only:
experience usage counters, timestamps, and query misses can be updated. Reusing one live
database directly would make results order-dependent.

This stage changes evaluation orchestration only. It does not change retrieval ranking,
the memory schema, case Oracles, Runtime commands, external holdouts, or the four-Skill
user interface.

## Architecture

The existing `eval-context-capability` command remains the facade. A dedicated batch
runner owns four explicit lifecycle levels:

1. **Source group**: canonicalize the complete case `source` object. Materialize the
   working tree/revision, fixture group, and mutation once per unique fingerprint.
2. **Indexed base**: run `init` and `wiki-index` once inside that source group. This base
   is never queried.
3. **Setup snapshot**: group by task type and complete `context_setup`; clone the indexed
   base and apply bounded reflection fixtures once. This snapshot is also never queried.
4. **Case snapshot**: clone the setup snapshot for one expanded query variant, run its
   compact and audit queries, then delete the clone. Query-side writes cannot affect any
   other case.

Canonical JSON plus SHA-256 identifies groups. The digest is an execution identity, not
a cache key exposed to users. Snapshots remain temporary and are never persisted as
memory or benchmark evidence.

## Audit Contract

The result adds a bounded `execution` section containing:

- schema version and strategy name;
- expanded case, source-group, and setup-group counts;
- index-build and case-snapshot counts;
- avoided index-build count;
- total source/index, setup, snapshot, and batch elapsed milliseconds;
- per-source group digest and bounded counts, without source bodies or fixture payloads.

Per-case `memory_prepare_ms` retains cold-preparation semantics for compatibility. The
new execution section is authoritative for actual amortized batch cost.

## Phases

### Phase 1: Red contracts

- Assert variants with identical source/setup share one source and setup group.
- Assert different fixture groups, mutations, task types, or reflection payloads do not
  share the corresponding lifecycle level.
- Assert every expanded case receives its own case snapshot.
- Assert query writes in one snapshot cannot be observed by the next case.

### Phase 2: Batch runner

- Add a small runner module behind the existing facade.
- Reuse `materialized_workspace`, `prepare_isolated_memory`, and
  `apply_context_setup`; do not duplicate indexing or fixture validation.
- Clone only temporary memory homes, clean each case clone eagerly, and fail closed on
  missing or overlapping snapshot paths.
- Preserve input order so case/result joins and robustness grouping remain unchanged.

### Phase 3: Verification

- Compare isolated and shared execution observations on representative code, log,
  experience, and fixture-group cases while ignoring timing-only fields.
- Run the complete classified development pack once with a bounded timeout.
- Require all existing capability checks to retain their prior outcomes; this stage may
  improve runtime but must not tune retrieval results.
- Run focused unit tests, scale/query-plan gates, JSON validation, Python compile,
  `git diff --check`, four-Skill check, and the 500-line gate.

## Stop Rules

- Stop if shared execution changes a non-timing observation for the same case.
- Stop if a case can mutate an indexed base or setup snapshot.
- Stop if grouping depends on selected field subsets instead of the complete source and
  setup objects.
- Stop if the optimization requires persistent caches, daemon state, parallel queries,
  or a new CLI switch.
- Do not run a consumed external holdout to validate evaluator performance.

## Mature Practice References

- pytest fixture scopes and cached fixture values:
  https://docs.pytest.org/en/stable/how-to/fixtures.html#scope-sharing-fixtures-across-classes-modules-packages-or-session
- Bazel Test Encyclopedia on hermetic test execution and undeclared state:
  https://bazel.build/reference/test-encyclopedia
- Bazel remote caching on content-addressed action/result identity:
  https://bazel.build/remote/caching

The project applies these practices locally: expensive immutable preparation is shared
by exact content identity, while mutable execution receives an isolated snapshot. No
remote cache or new build system is introduced.

## Execution Result

- The existing `eval-context-capability` facade now delegates preparation to a dedicated
  batch runner. The result includes `agent-context-capability-execution/v1`; no CLI flag,
  Runtime command, database schema, or Skill changed.
- Three evidence-funnel scenarios retain 9/9 variants and are identical to the prior
  isolated result after timing fields are removed. Their index builds fall from nine to
  one.
- Six affected existing scenarios retain 16/18 variants and are also identical to the
  prior isolated result after timing fields are removed. Their two historical failures
  are unchanged.
- Two distinct reflection setups plus a no-setup case pass 9/9. The audit reports one
  source group, three setup groups, and the expected 2/2/0 reflection counts, proving
  setup identity is not collapsed.
- The complete 75-scenario/225-variant development pack finishes in 316,578 ms, inside
  the previous 12-minute bound. Four source groups produce four index builds, six setup
  groups, and 225 isolated case snapshots; 221 repeated index builds are avoided.
- The complete capability gate fails honestly at 173/225 variants and 39/75 stable
  scenarios. There are 52 failed variants and 139 failed checks: 23 candidate-generation,
  44 passage-selection, 68 ranking-precision, and 4 abstention-calibration failures.
  These results establish the next development baseline and were not tuned in this
  infrastructure stage.
- The CI scale profile passes latency, query-plan, and incremental-maintenance gates at
  100,000 searchable entities and 300,000 edges. Callable-pool P95 is 5.349 ms and
  one-hop-owner P95 is 5.764 ms against 150 ms SLOs.
- Seventy-eight Context tests and 37 benchmark/governance tests pass. Python compile,
  100 evaluation-JSON parses, diff validation, and the 500-line gate pass.
- No consumed external holdout was read or rerun. A new external gate remains blocked
  while the complete development capability gate fails.
