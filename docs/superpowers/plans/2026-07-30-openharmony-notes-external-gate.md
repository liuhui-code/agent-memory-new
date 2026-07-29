# OpenHarmony Notes External Event-Owner Gate

## Goal

Measure whether Runtime revision `c242de2` generalizes from independent development
fixtures to a previously unused ArkTS application. The gate evaluates context supply:
stable log identity, emitting source owner, and the reviewed source passage. It does
not evaluate Runtime-generated diagnosis.

## Selection policy

The source is the official
[OpenHarmony Notes application](https://github.com/openharmony/applications_notes).
It was selected before execution because it is a non-fork Apache-2.0 project, was not
present in prior case packs, has a bounded source tree, and preserves source-reviewed
crash and freeze fixes with relevant logs already present in each parent revision.

Rejected candidates remain excluded:

- ClashBox removed most source from its current branch and lacked a suitable history.
- HomoLauncher had only initialization and documentation commits.
- HarmonyOS-EhViewer's strongest candidate introduced the relevant logs in the fix,
  which would leak post-fix evidence into the Oracle.
- Homogram is related to the already consumed Gramony corpus.

## Evidence contract

The three scenarios cover independent event-owner shapes:

1. A dynamic image-path callback log immediately before a state mutation crash.
2. A WebView page-end log before unguarded platform calls restore editor state.
3. A window-size listener log associated with repeated-event UI freeze.

The contract follows the event identity boundary documented in
`2026-07-29-event-owner-passage-budget.md`:

- `required_log_template_literals` contains only text stable in source.
- `runtime_observed_terms` records occurrence-specific values and is informational.
- Every Oracle span is measured against the pre-fix revision.
- Post-fix revisions, commit messages, and Oracle fields are hidden from the runner.

## One-time protocol

1. Freeze Runtime revision `c242de2` before source selection.
2. Review each Git diff and parent source without running Context retrieval.
3. Audit all revisions and declared changed files with `eval-seal-cases`.
4. Seal the six query variants before execution.
5. Run `eval-context-capability` exactly once against isolated pre-fix workspaces.
6. Record the immutable result. Do not tune on or rerun this project.

## Promotion rule

The result is evidence of external generalization only when the sealed system-context
gate passes. A failure remains a consumed observation: repairs must use independent
fixtures and a different future holdout.

## Result

The sealed gate was executed once on 2026-07-30 and is now consumed. Seal digest:
`ffc8c7085e542f408e34e754978df73ec7c257e85cd7daa9c4c9542b9bfc197e`.

- System Context passes 0/6 variants; promotion is denied.
- Candidate file Recall@20 is 0.8333, but anchor recall is 0.1667 and anchor
  precision is 0.0555.
- Log graph observation, callable recall, and reviewed source-span recall are all 0.
- Compactness remains healthy: average output is 1,209.8333 Tokens, below the
  1,500-Token limit.
- The evidence funnel first loses five variants at callable localization and one at
  candidate-file recall. Failure analysis assigns 23 checks to candidate generation,
  11 to passage selection, and 11 to ranking precision.

The immutable machine-readable observation is stored in
`docs/eval/openharmony-notes-log-owner-unseen-holdout-result.json`. The case pack,
Oracle, and result must not be edited or rerun.

## Root-cause audit

The failure is upstream of event-owner passage selection:

1. `direct_log_pattern()` recognizes `hilog.*` for ECMAScript-family files.
2. `log_statement_on_line()` independently parses TypeScript calls but does not
   recognize `hilog.*` in its TypeScript branch.
3. The project's `LogUtil.ts` sink therefore produces zero direct log statements.
4. Without that sink, transitive `LogUtil.info/error` calls cannot become wrapped log
   effects, so no selected event exists to seed an owner passage.
5. Property arrow callbacks such as `callbackImagePath` and nested builder callbacks
   such as `.onPageEnd(...)` also lack callable intervals, explaining the separate
   callable and range losses.

This is an abstraction mismatch, not an OpenHarmony Notes special case.

## Repair architecture

Repairs must use independent development fixtures and preserve the public Context
facade:

- Replace duplicated scanner/parser conditionals with one declarative log API model
  that owns receiver names, levels, argument roles, and supported ECMAScript-family
  dialects. GitHub CodeQL's
  [JavaScript library models](https://codeql.github.com/docs/codeql-language-guides/customizing-library-models-for-javascript/)
  provide the mature models-as-data precedent for framework API and wrapper support.
- Add a language-adapter callable-interval contract for methods, property arrow
  callbacks, and nested callback expressions. Tree-sitter's
  [structural query captures](https://tree-sitter.github.io/tree-sitter/using-parsers/queries/index.html)
  are the long-term reference; the first bounded implementation may remain local and
  dependency-free behind that interface.
- Keep stable event identity separate from occurrence values, consistent with the
  [OpenTelemetry Logs Data Model](https://opentelemetry.io/docs/specs/otel/logs/data-model/).
- Prove sink extraction, wrapper propagation, callback ownership, and passage binding
  independently before running the full development differential. Use a different
  unseen repository for any later external promotion gate.

## Independent repair implementation

The consumed OpenHarmony Notes pack was not rerun or edited. Repairs were developed
against a new local contract fixture and the existing unsealed development pack:

- `LogApiModel` is now the single source for scan and parse behavior across ArkTS,
  TypeScript, JavaScript, Python, Dart, and Swift. The model owns receiver aliases,
  levels, and the message argument position, including the third `hilog` argument.
- A shared ECMAScript callable-range adapter supplies named methods, property arrow
  callbacks, `.on(...)` subscriptions, and `.onXxx(...)` ArkUI callbacks to source
  focus, symbol extraction, log ownership, and semantic indexing.
- Anonymous control-flow callbacks such as `.then(...)` remain attributed to their
  nearest stable enclosing method. This keeps call paths addressable while avoiding
  synthetic `then` or `resolve` owners.
- Dynamic passthrough arguments are stored as placeholders such as `{message}`.
  They remain valid wrapper sinks but cannot compete as stable event literals unless
  the query explicitly identifies their owner. Query-time raw-statement inspection
  applies the same rule to legacy indexes that stored the bare identifier.
- Query-time owner ranges use one bounded batch lookup over at most 40 log effects;
  source files are not reparsed and no per-result SQL loop is introduced.

## Development validation

- The independent contract tests cover TypeScript `hilog`, property callbacks,
  ArkUI member callbacks, anonymous Promise ownership, dynamic-template identity,
  wrapped effects, and compact callback source passages.
- The three affected development scenarios recover to 8/9 variants. The only failure
  is the same cross-component original wording that failed before this repair.
- The complete 216-variant differential is exactly 158/216, with zero previously
  passing variants regressed and the same 58 historical failures.
- The CI scale profile passes at 100,000 searchable entities, 80,000 symbols, 15,000
  logs, and 300,000 edges. Candidate recall P95 is 48.483 ms, exact-log FTS P95 is
  0.82 ms, and hierarchical owner lookup P95 is 20.415 ms.
- Full discovery executed 742 tests. Its two behavioral failures were repaired and
  passed focused regression; two loopback-server errors passed 3/3 outside the
  socket-restricted sandbox.

This repair restores the missing extraction and ownership abstractions. It is not a
new external promotion result; a different unseen repository is still required for
that gate.
