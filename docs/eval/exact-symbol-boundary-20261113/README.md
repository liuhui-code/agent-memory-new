# Exact symbol boundary repair: focused Development

Baseline 6c666ab; isolated clone; no shared checkout or remote write.

## Independent reproduction

Four new ETS source files separate a combined list Builder, a plain tile build(), a
model accessor, and split Builder methods. Six queries were frozen before code changes.
The Chinese request for a Builder method incorrectly projected TileView.build. Its
localization reason was exact_symbol even though the query contained only `Builder`,
not the identifier `build`.

The generic scorer awarded exact-symbol weight for arbitrary substring containment in
either direction. Thus `Builder` matched `build`, and `load` matched `loadRecords`.
This is an identity-contract bug, not a missing query synonym.

## Change

Only the `exact_symbol` branch now requires the complete literal symbol at identifier
boundaries. Other exact fields retain previous behavior. Lexical token matching and
candidate recall are unchanged: Builder may still lexically recall build, but it cannot
claim exact identity or receive its bonus. Case-insensitive, qualified, punctuation,
$ and underscore, natural-language multiword mentions, and Unicode controls are tested.

## Rejected experiment and residual limits

A preliminary method-axis evidence experiment did not close the original failures and
is rolled back. Its patch and results remain labeled as an experiment; it is not runtime.

The independent fixture has remaining failures: original semantic wording still selects
split ownership, and explicitly named TileView.build still has an extra raw-derived
anchor. These failed before this patch and remain visible in observations. The Chinese
Builder-role control is fixed; previously passing controls remain passing. Four of six
compact frozen owner checks now pass versus three of six before; this is not a claim
that Builder ownership is solved in general.

## Verification

- Existing `context-builder-layout-source-focus`: **1/3 -> 2/3**. English paraphrase
  now passes; original stays passing. Chinese still fails precision with two source files.
- Necessary exact-symbol, text normalization, typed-contract, definition, localization,
  diversity, source-owner and callable-focus regressions: **130 tests pass**.
- Python compilation, diff whitespace check and 500-line changed-runtime limit pass.
- No full suite, consumed holdout, evaluator/oracle changes or external promotion claim.

The frozen inputs, before/experiment/after selected scenario results and public observation
projection are retained. Projection hashes identify full raw call outputs beside this
independent evidence workspace. All newly authored source inputs are synthetic Development
fixtures. The run.py copy records the original experiment directory layout.
