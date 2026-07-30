# link-my-harmony External Context Gate

## Goal

Measure whether Runtime revision `0a1a4ec` generalizes to a previously unused ArkTS
application after the declarative log-API and callable-owner repair. The gate measures
context supply, not Runtime-generated diagnosis: stable event identity, event owner,
bounded source passage, and the nearby code path needed by an Agent CLI.

## Frozen boundary

- Runtime revision: `0a1a4ec`.
- External source: [xiebyapps/link-my-harmony](https://github.com/xiebyapps/link-my-harmony).
- Reviewed source head: `d618c879af84777d3bf7dcf4086ebb67d0b7ec4f` on `master`.
- License: MIT.
- The repository does not occur in an earlier case pack or result.
- Source selection, Git-diff review, and Oracle authoring happen before any Context
  retrieval against this repository.

This project was selected over shallow repositories and candidates without a clear
license because it preserves a non-trivial ArkTS history, pre-fix log statements, and
three independently reviewable fixes.

## Case contract

The three cases isolate different post-repair capabilities:

1. `ThemePickerComponent` uses a function-valued ArkUI property and invokes it from an
   `.onClick` callback. Its caller owns a `Theme persist failed:` log inside a property
   arrow callback. The fix replaces the unsupported bare function property with a
   handler object.
2. `fetchDashboardTotalsOrNull` emits a third-argument `hilog.warn` event and is called
   by `refreshDashboard`. The fix corrects offline link totals in that caller. This
   tests direct `hilog` extraction plus one-hop caller passage supply.
3. `persistHostMemory` emits a dynamic-template warning and constructs storage with
   the deprecated `getContext(this)` API. The fix replaces that context acquisition in
   the same owner and related persistence paths.

Each query starts from a plausible runtime line and symptom. The Oracle identifies
only source available in the parent revision. Commit messages, fixes, and Oracle
fields remain hidden from the runner.

## Mature-practice basis

- Stable source templates and occurrence-specific values are separated following the
  [OpenTelemetry Logs Data Model](https://opentelemetry.io/docs/specs/otel/logs/data-model/).
- Retrieval remains staged: lexical/event candidates first, structural owner and
  caller expansion second, then compact passage selection. This follows the
  multi-stage retrieval shape evaluated by
  [BEIR](https://arxiv.org/abs/2104.08663), without turning Runtime into a diagnosis
  engine.
- Framework APIs and callback shapes are represented as declarative models, following
  the models-as-data precedent of
  [CodeQL JavaScript library models](https://codeql.github.com/docs/codeql-language-guides/customizing-library-models-for-javascript/).
- The sealed holdout is immutable and single-use. A failed gate is retained as
  evidence and may only be repaired with independent fixtures and a different future
  project.

## One-time protocol

1. Freeze Runtime before selecting source fixes.
2. Verify every parent, fix revision, commit message, and declared changed file.
3. Verify every required log literal and source span against the parent revision.
4. Seal the reviewed case pack with `eval-seal-cases`.
5. Execute `eval-context-capability` exactly once in isolated temporary memory.
6. Record the immutable result and mark the repository consumed.
7. Do not tune against, edit, or rerun the sealed cases.

## Promotion rule

Promotion requires the sealed system-context gate to pass. Aggregate recall and funnel
metrics remain diagnostic only; they cannot override a failed gate. Compact output
must preserve required anchors and reviewed source spans within the existing Token
budget.

## Result

The gate was sealed with digest
`401dd0bede0e2a769460c4c9c5193ec4943341e2b1e125fac93424d52c719906` and
executed exactly once on 2026-07-30. The source is now consumed.

- System Context passes 0/6 variants, so promotion is denied.
- Candidate-file Recall@20 is 1.0. Anchor recall and primary-anchor recall are
  0.3333, Oracle precision is 0.4167, and MRR is 0.4167.
- Source-excerpt recall is 0.3333 and reviewed source-span recall is 0.1111.
- Hierarchical callable and range recall are both 0.2222. Every variant first loses
  evidence at the callable stage even though file localization succeeds.
- Four variants return log-graph evidence. Both host-memory variants return no log
  anchor, despite the reviewed event being present in the parent source.
- Compactness passes at an average 1,444.6667 Tokens under the 1,500-Token limit.
  Average memory preparation is 30.7655 seconds and compact query time is 11.3435
  seconds, which is too slow for an interactive Agent loop.
- Failure analysis records 28 failed checks: 11 candidate-generation, 9 passage-
  selection, and 8 ranking-precision failures.

The immutable machine-readable observation is
`docs/eval/link-my-harmony-log-owner-unseen-holdout-result.json`. Neither the sealed
pack nor this result may be changed or rerun.

## Root-cause audit

The result demonstrates position and evidence-propagation defects beyond the repaired
syntax adapters:

1. `load_file_callables` loads one global pool ordered by `file_path, start_line` and
   applies `LIMIT 128` before query scoring or per-file diversity. Large files and
   methods late in a file can therefore be absent before ranking. Raising the limit
   would preserve the positional bias and increase query cost.
2. Source focus reads at most the first 4,000 lines. One reviewed parent has a
   4,969-line `Index.ets`; future owners after that boundary cannot be focused even
   when symbol ranges are known.
3. The theme case returns the logging caller but not the child component. The graph
   lacks a typed property-flow path from component construction, through the callback
   property, to the `.onClick` invocation.
4. The host-memory variants deliver no log anchor. The persisted report cannot
   distinguish index extraction, candidate recall, evidence fusion, and compact
   removal for a missing log. That observability gap must be repaired before changing
   weights.
5. The case pack used generic `required_source_spans` for both callable auditing and
   final passage auditing. A component property declaration is valid supporting
   source but not a callable. Future packs must explicitly declare
   `hierarchical_callable_spans` separately. This evaluation-contract defect does not
   invalidate the 0/6 promotion decision because the other anchor, log, and passage
   checks also fail.

## Independent repair direction

Repairs must use new development fixtures and preserve the Context facade:

- Replace global-prefix callable loading with query/evidence-seeded, per-file bounded
  retrieval. Direct symbol and log-owner candidates must enter before a deterministic
  per-file quota; broad fallback may then fill remaining capacity.
- Introduce a source-access adapter backed by complete line offsets or bounded reads
  around persisted symbol ranges. Full-file search must not imply returning full-file
  content.
- Add typed ArkTS component property-flow edges for constructor property bindings,
  child `@Prop` declarations, and callback invocation sites.
- Persist stage-level log candidate IDs and removal reasons for extraction, FTS
  recall, event matching, fusion, and compact selection.
- Split callable, owner, and supporting-passage Oracle spans in all new development
  and holdout packs.
- Add latency gates for compact Context and hierarchical audit on a real large-file
  profile. Do not trade position independence for an unbounded scan.

No repair may use this consumed repository for tuning or acceptance. A later external
promotion decision requires another previously unused project.
