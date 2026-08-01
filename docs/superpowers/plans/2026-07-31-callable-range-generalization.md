# ArkTS Callable And Range Generalization Plan

## Objective

Restore callable and source-range localization for realistic ArkTS syntax and dense
files without changing the public Context facade, compact budget, SQLite authority,
fixed four Skills, or Agent-owned reasoning boundary.

## Independent Defect Classes

1. **Header extraction loss.** The current ECMA front end recognizes a method only when
   modifiers, name, parameters, return type, and opening brace share one line. Valid
   ArkTS with multiline parameters or return types is absent from `code_symbols`, so no
   ranking strategy can recover it.
2. **Prefix pool loss.** The hierarchical localizer bounds each candidate file by source
   order before query scoring. In a dense service, later methods can never enter the
   callable pool even when the file is correctly recalled.
3. **Surrogate identity coupling.** Extracting previously omitted callables legitimately
   changes SQLite row IDs. Causal paths currently hash those row IDs and use the hash as
   an equal-score ordering key; compact projection can therefore keep a different branch
   after a rebuild even though source semantics are unchanged.

The defects are reproduced in a new project-neutral fixture family. No consumed source
identifier, path, wording, result, or Oracle is reused.

## Long-Term Architecture

### Language Front End

Introduce a shared callable-header scanner behind the existing language adapter. It
collects a bounded logical header across lines, tracks parentheses, stops at an opening
brace or declaration terminator, and returns normalized name/modifier/parameter/return
metadata. `semantic_ecma` and `ecma_callable_ranges` consume the same contract so symbol
extraction and source-window ownership cannot drift.

This is a conservative bridge toward a parser-backed adapter. Tree-sitter produces a
concrete syntax tree with named syntax nodes and queryable error/missing nodes; a future
ArkTS grammar can implement the same normalized front-end port without changing SQLite
or query consumers. The current phase adds no parser dependency.

### Bounded Candidate Pool

Replace source-prefix truncation with a deterministic stratified pool:

- preserve direct query-matched symbol IDs first;
- divide each file's ordered callables into bounded source-position strata;
- retain representatives across the whole file instead of only its prefix;
- rank the resulting fixed-size pool with the existing lexical, mechanism, role, graph,
  and file-prior evidence;
- keep all global budgets unchanged.

This follows a retrieve-then-rerank architecture: candidate generation must preserve
coverage before the more expensive ranking stage. BEIR demonstrates that heterogeneous
zero-shot retrieval requires cross-domain evaluation and that reranking quality cannot
repair candidates that were never retrieved.

### Stable Path Identity And Compact Branch Diversity

Path identity is derived from canonical source semantics (entity type, current path,
qualified name, source position, and relations), never SQLite surrogate IDs. Equal-score
paths remain structurally ranked; compact projection retains two distinct entry branches
by removing evidence duplicated from the primary branch before considering branch
truncation. This keeps the graph advisory: the Runtime exposes plausible alternatives and
the Agent compares them with the user's real log order.

## Phases

1. Add development fixtures for multiline static async methods and late methods in a
   dense service.
2. Run the public Context evaluator before changes and record first-loss stages.
3. Add the normalized bounded header scanner with unit tests.
4. Add stratified per-file callable pooling with focused SQL and selection tests.
5. Re-run only development cases, then full serving and performance regressions.
6. Permit a future external holdout only when both defect classes pass without prior
   baseline regression or budget expansion.

## Stop Rules

- Do not read, edit, or rerun any consumed external holdout.
- Do not add project/path/name special cases or change an Oracle after observation.
- Do not increase candidate, range, graph, compact-token, or SQL query budgets.
- Do not promote shadow evidence-set output into compact serving.
- Stop if a fix improves evaluator bookkeeping without improving public source evidence.

## References

- Tree-sitter parser model: https://tree-sitter.github.io/tree-sitter/using-parsers/
- Tree-sitter query syntax and error nodes:
  https://tree-sitter.github.io/tree-sitter/using-parsers/queries/1-syntax.html
- BEIR heterogeneous zero-shot retrieval: https://arxiv.org/abs/2104.08663
- Repository policy: `docs/evaluation-and-change-policy.md`

## Execution Result

Implemented the shared bounded callable-header front end and routed both semantic symbol
extraction and callable-range ownership through it. Multiline methods and top-level
functions are now normalized without adding a parser dependency; declarations without a
body and ArkUI chained callbacks remain excluded. Replaced source-prefix callable loading
with a fixed-size stratified SQL pool that preserves direct matches and representatives
across the full file.

The two project-neutral development cases moved from 1/2 formal passes with 0 callable
and range recall to 2/2 with file, callable, range, and source-span recall all at 1.0.
Average compact output decreased from 1,482 to 1,399 estimated tokens. Candidate, range,
graph, and compact limits were not increased.

The first complete 231-variant run exposed the surrogate identity defect: overall results
fell from the accepted 185/231 and 46/77 baseline to 183/231 and 45/77 even though
callable/range recall improved. Stable source-semantic path IDs and duplicate-aware compact
branch projection restored all prior passing variants. The final run is 186/231 and 46/77,
with no pass-to-fail swaps; callable recall is 0.9804 and range recall is 0.9412 versus the
accepted 0.9632 and 0.9338. Average compact output is 1,296.3 of 1,500 tokens.

The million profile passes all latency, query-plan, and incremental-maintenance gates at
1,000,000 searchable entities and 3,000,000 graph edges. Hierarchical callable-pool P95 is
10.695 ms against 150 ms; candidate-hit P95 is 124.653 ms against 800 ms. Single-file and
large-method incremental P95 are 793.928 ms and 3,479.244 ms against 2,000 ms and 5,000 ms.

The full test run covered 802 tests: 799 passed in the restricted sandbox, two loopback
server tests were blocked only by local socket permissions, and one governance test found
five missing fingerprint headers in earlier untracked modules. After adding the headers,
24 affected/governance tests pass; all three loopback runner tests pass with loopback
permission. Python compilation, 110 evaluation JSON files, `git diff --check`, the fixed
four Skills, and the 500-line limit pass. No consumed external holdout was read, modified,
or rerun.
