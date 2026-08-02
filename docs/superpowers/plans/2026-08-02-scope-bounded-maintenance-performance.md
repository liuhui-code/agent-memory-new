# Scope-Bounded Maintenance Performance Plan

## Objective

Keep changed-only maintenance proportional to the changed learn Scope and its
statically supported references. Preserve exact project statistics without scanning
millions of graph rows after every local refresh.

## Evidence Before Change

The million profile observed two independent failures through the production refresh
facade:

1. A 20-method single-file refresh spent up to 20,675 ms in the phase named
   `summarize`. That phase contains an exact project-wide `COUNT(*)` over three million
   `memory_edges`; it is unrelated to source summarization. An isolated SQLite fixture
   increased cold count time from 11.955 ms at 100,000 rows to 107.067 ms at 1,000,000
   rows while retaining an indexed project lookup.
2. A 500-method refresh spent up to 9,708 ms rebuilding the graph. The current fallback
   collects every lexical identifier as a possible global symbol reference. An
   independent fixture with 100 repeated method names expanded one changed file into
   5,001 symbol rows before graph construction.

The CI profile passes, so this is a scale-boundedness defect rather than a functional
refresh failure. No query, retrieval, Oracle, or consumed holdout evidence is involved.

## Method Basis

- SQLite documents that scans visit all qualifying rows and that lookup by a key is
  logarithmic rather than linear in table size:
  <https://www.sqlite.org/queryplanner.html>.
- SQLite `EXPLAIN QUERY PLAN` distinguishes a bounded `SEARCH` from a `SCAN`, but an
  indexed project predicate can still visit every row belonging to that project:
  <https://sqlite.org/eqp.html>.
- SCIP models code navigation from document occurrences and stable symbols rather than
  treating every lexical token as a cross-file reference:
  <https://github.com/scip-code/scip>.
- Sourcegraph's indexer guidance separates document occurrences, symbol definitions,
  and semantic symbol roles, providing a migration path for future precise language
  providers:
  <https://sourcegraph.com/docs/code-navigation/writing-an-indexer>.

## Architecture Contract

### Project Counters

Add a generic SQLite `project_counters` table. A schema adapter owns migration and
one-time backfill. A graph-refresh Unit of Work uses connection-local TEMP delta triggers
only for the changed transaction, then applies one aggregate counter update before
commit. Incremental indexing reads the exact count by `(project_id, counter_name)` primary
key. The edge table remains the source of truth; the counter is a transactionally
maintained derived statistic and can be rebuilt from it. Persistent per-row triggers are
prohibited because the first CI experiment tripled bulk edge-load time.

### Graph Symbol Candidate Resolution

Keep local Scope symbols unconditionally. Extract only import names, constructors,
static type/member owners, inheritance targets, component-style calls, and declared
type references from code with strings/comments masked. Cap extracted names before SQL.
Resolve external fallback symbols only when `(symbol, symbol_type)` is unique in the
project, matching the existing downstream `unique_target` contract. Precise semantic
adapters continue to resolve symbol keys, qualified names, and file-qualified names.

This fallback must remain language-neutral for ECMAScript-family syntax and must fail
closed on ambiguity. It must not add a global fuzzy scan, graph database, vector store,
or language-specific Runtime command.

## Execution

1. Add RED tests for exact counter backfill/mutation, primary-key lookup plan, bounded
   reference extraction, and ambiguous global symbol suppression.
2. Implement counter schema and access in a dedicated module; replace the incremental
   global edge count while retaining the public `memory_edges_total` value.
3. Implement bounded reference-name extraction and unique typed candidate SQL in the
   existing graph-candidate module; route scoped graph rebuild through it.
4. Record candidate-resolution audit counts in semantic graph stats so future scale
   failures can distinguish local, reference-name, and resolved-external cardinality.
5. Run focused refresh/graph/schema tests, the CI scale profile, the million profile,
   complete regression, JSON/fingerprint/four-Skill/500-line gates.
6. Stop without threshold changes if the million failure remains outside the two proved
   layers. Do not tune on or rerun any consumed Context holdout.

## Acceptance

- Exact edge totals survive insert, delete, project move, migration backfill, and
  changed-only refresh without a `COUNT(memory_edges)` query in the hot path.
- A changed file with repeated local method declarations does not load same-name symbols
  from unrelated files.
- A unique statically referenced external component/service remains available for edge
  construction; ambiguous references fail closed.
- Existing graph relations and public refresh evidence remain correct.
- CI and million query plans pass; incremental single-file and 500-method P95 satisfy
  their existing 2,000/5,000 ms SLOs without increasing limits.
- Every Python file remains at or below 500 lines and the user surface remains four
  Skills.

## Completed Outcome

- Added project-neutral RED fixtures for counter backfill/mutation/query plan, exact
  production refresh totals, bounded declaration handling, and ambiguous external
  symbols. All four pass.
- The CI profile passes all three gates. Single-file incremental P95 is 710.654 ms and
  500-method P95 is 3,335.938 ms; the corresponding summarize phases are 2.550 ms and
  17.832 ms.
- The million profile passes all three gates with 1,000,000 searchable entities,
  3,000,000 edges, and a 2,262,933,504-byte archive. Candidate hit/miss P95 is
  170.911/62.114 ms. Single-file incremental P95 is 458.742 ms and 500-method P95 is
  1,837.784 ms; summarize phases are 1.201/9.260 ms.
- The existing limits were unchanged. The focused refresh, graph, semantic, passage,
  method-evidence, and scale suites pass 49/49. No consumed Context holdout was read,
  modified, or rerun.
- The restricted complete suite passes 809/811; both errors occur before application
  code when the sandbox rejects a temporary `127.0.0.1` test server. The complete
  loopback module passes 3/3 with local binding permission. Python compilation, 154
  JSON files, diff hygiene, exactly four Skills, and the 500-line gate pass.
