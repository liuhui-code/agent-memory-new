# Log Wrapper Effect Analysis

## Objective

Recover code-log anchors when ArkTS/TypeScript logging is hidden behind one or
more project wrappers. The Runtime supplies bounded, inspectable static context;
the Agent CLI still reads temporary runtime logs, compares candidate paths with
observed order and values, and decides what source to inspect next.

This design does not treat every method containing a log sink as an observed
runtime event. A derived record means only that the caller **may emit** the sink
through a statically resolved wrapper path.

## Why Regex Alone Is Insufficient

A sink call such as `Logger.error(...)` can span lines, occur in strings or
comments, or be wrapped by business methods. A single source regex cannot
reliably distinguish those cases and cannot propagate an effect through calls.
The implementation separates four concerns:

1. lexical source masking removes comments and string bodies while preserving
   offsets;
2. a language API Catalog identifies known direct logging sinks;
3. the language semantic adapter resolves callable ownership and `calls` edges;
4. a bounded interprocedural summary projects caller-to-sink `LogEffect` rows.

This follows the source/step/sink model used by path-oriented static analysis.
CodeQL likewise models path queries with explicit sources, sinks, and graph
steps, and warns that global flow costs more and may produce spurious paths.
The bounded local projection is intentional for the lightweight SQLite runtime.

## Architecture

```text
ArkTS / TypeScript source
  -> lexical call scanner
  -> direct sink API Catalog
  -> code_log_statements (direct evidence)

language semantic adapter
  -> code_symbols + calls edges
  -> bounded summary propagation (resolved calls, depth <= 3)
  -> code_log_effects (static_wrapped / inferred_wrapped evidence)
  -> code_log_effect_fts
  -> existing context/search facade
  -> Agent compares candidate call_path with temporary runtime logs
```

The feature does not add a command or skill. `tools/agent_memory.py` remains the
only Runtime entry point and the user-facing skill count remains four.

## Data Contract

`code_log_effects` is a derived projection separate from direct log statements:

- `file_path`, `line`, `function`: outer caller and statically observed call site;
- `wrapper_symbol`: immediate wrapper called by the outer caller;
- `sink_log_id`: stable link to the direct `code_log_statements` row;
- `level`, `logger`, `message_template`: searchable sink context, with a literal
  call-site message preferred when statically available;
- `evidence_class=static_wrapped|inferred_wrapped`: explicit non-runtime
  evidence class, with the weakest call-edge evidence propagated to the effect;
- `wrapper_depth`: number of wrapper calls between outer caller and direct sink;
- `call_path`: ordered caller, wrappers, and sink API;
- `call_path_locations`: matching `file#symbol` locations for source inspection;
- `truncated`: explicit notice that a per-caller or forward-closure bound omitted
  additional candidates;
- `source_digest`, `index_generation`: freshness and incremental lifecycle;
- `raw_call`: inspectable outer call evidence.

FTS is a recall index only. Query ranking applies a small penalty to wrapped
effects relative to direct logs and graph expansion uses `sink_log_id`, so the
projection cannot masquerade as a new direct log node.

## Bounds And Failure Policy

- maximum wrapper depth: 3;
- statically resolved same-file and cross-file calls;
- nominal interface/base dispatch from explicit `implements`/`extends`, method
  name, and argument count, with at most eight candidates per call site;
- candidate projection respects the 100,000-relation SemanticBatch ceiling and
  records at most 1,000 explicit truncation gaps;
- maximum effects per caller: 32;
- cycle detection by visited symbol id;
- path search stops after one overflow witness;
- full rebuild scans all learned files without a giant SQL `IN` clause;
- incremental rebuild chunks changed files in groups of 400;
- cross-file invalidation follows active reverse `calls` edges to the same depth;
- focused effect reconstruction follows active forward `calls` edges to depth
  three under a 2,000-symbol expansion budget, while writing only affected callers;
- hierarchy invalidation groups `dispatches_via`, known implementations, and
  callers under a 2,000-path budget;
- no reflection, structural dispatch, unresolved import, or function alias inference;
- unresolved paths remain absent rather than receiving guessed edges;
- temporary user logs remain outside SQLite.

The bounds prevent branch explosion at million-row scale. A future exact parser
or compiler provider can implement the existing semantic call contract without
changing storage, query, or Agent-facing output.

## Execution Plan

- [x] Add comment/string-aware balanced call scanning and direct sink Catalog.
- [x] Replace ArkTS/TypeScript semantic call regexes with the shared scanner and
  persist exact call lines.
- [x] Add the `code_log_effects` schema, migrations, indexes, freshness fields,
  and FTS5 triggers.
- [x] Implement bounded same-file summary propagation with depth and cycle
  limits.
- [x] Integrate effects into existing query scoring, compact log anchors, sink
  graph expansion, and nested parse statistics.
- [x] Add multiline, lexical false-positive, multi-wrapper, compact-context,
  and stale-relearn regressions.
- [x] Add cross-module summary propagation after a reviewed three-file ArkTS
  fixture, including transitive caller invalidation, source locations, stale
  sink replacement, and scale regression.
- [x] Reuse the existing optional exact ArkTS Provider boundary and add a
  differential qualification gate; retain the current scanner as fallback and
  comparison oracle when exact output loses files or observed relation families.
- [x] Add a language-neutral, cross-batch DispatchCatalog and ArkTS/TypeScript
  bounded CHA candidate projection with argument-count filtering.
- [x] Preserve parallel candidates as inferred edges/effects, reserve at most
  two wrapped anchors in compact Context, and keep the Agent as path selector.
- [x] Rebuild callers and all known implementations when an implementation is
  added or removed during focused learning.
- [x] Add model-free log-path Recall/Precision, evidence-class, candidate-bound,
  and truncation Oracles to the existing Context capability gate.
- [x] Preserve unchanged cross-file sinks when only an outer caller is relearned.
- [x] Add a conservative exact-log-phrase cascade with broad-query fallback,
  retain parallel same-message paths, and align compact code anchors with the
  exact log caller unless an explicit structural path already owns focus.

## Acceptance Criteria

- multiline direct sinks are complete and string/comment examples are ignored;
- a two-wrapper path returns the outer business message and full static path;
- changing only a bottom cross-file sink refreshes every bounded upper caller;
- changing only an outer caller retains its unchanged cross-file sink and
  refreshes the call-site message;
- direct and wrapped evidence remain distinguishable in compact context;
- interface dispatch returns bounded parallel paths without selecting a winner;
- exact log queries keep code anchors, log anchors, and source excerpts on the
  same caller while short generic queries retain broad recall;
- relearning a changed file removes the old derived message;
- existing semantic, log-path, freshness, and scope tests remain green;
- every Python implementation file remains at or below 500 lines.

## References

- GitHub CodeQL, [Creating path queries](https://codeql.github.com/docs/writing-codeql-queries/creating-path-queries/): explicit source, sink, step, and path explanation model.
- GitHub CodeQL, [Analyzing data flow in JavaScript and TypeScript](https://codeql.github.com/docs/codeql-language-guides/analyzing-data-flow-in-javascript-and-typescript/): local/global precision and performance tradeoffs, call nodes, barriers, and bounded configurations.
- OpenTelemetry, [Logs data model](https://opentelemetry.io/docs/specs/otel/logs/data-model/): stable separation of body, severity, event name, resource, scope, and attributes.
- OpenTelemetry, [Semantic conventions for events](https://opentelemetry.io/docs/specs/semconv/general/events/): named occurrence and occurrence-specific event context.
- LLVM, [Analysis and transform passes](https://releases.llvm.org/11.0.1/docs/Passes.html): interprocedural sparse conditional propagation as precedent for propagating bounded summaries across calls.
- Grove and Chambers, [A Framework for Call Graph Construction Algorithms](https://projectsweb.cs.washington.edu/research/projects/cecil/pubs/cgc-toplas.pdf): explicit call-graph approximation dimensions and conservative target sets.
- Bacon and Sweeney, [Fast Static Analysis of C++ Virtual Function Calls](https://doi.org/10.1145/236337.236371): class-hierarchy and rapid-type-analysis precision/performance tradeoffs; this lightweight Runtime implements only bounded learned-scope hierarchy candidates, not RTA.
