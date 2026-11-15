# Visual09 English alternative request: bounded feasibility stop

Classification: independent synthetic Development. Not holdout, external gate,
causal proof, or a claim that all possible solutions have been exhausted.
Baseline: `db4e638cf070858626f0727f96e730aaa0603bc7`.
Protocol frozen as `dd201be` before the independent public before run.
No production code, original queries/oracles, thresholds, budgets or caps changed.
No full suite, consumed holdout or remote write; main unchanged.

## Current original failure, not an inherited diagnosis

The original Development09 group was rerun through the existing public evaluator:
**2/3**, unchanged. The English paraphrase returns three files:

- `src/coordinators/SourceSwapCoordinator.ets`
- `src/views/InventoryOverlayPanel.ets`
- `src/widgets/TouchOverlay.ets`

Its complete required InventoryOverlayPanel source range is present and top-k
passes. Only minimum anchor precision fails; context is 1393 estimated tokens,
and evidence funnel first_loss is null. This is **not missing target source** on
this baseline. Original English and Chinese still pass. Existing independent
background/named target/named competitor/both controls remain 4/4.
Full evaluator results are retained in the sibling rebuild evidence directory as
`alternative-baseline-original09.json` and `alternative-baseline-independent.json`.
The selected unchanged result fields are also in `original-summary.json`.

## Independent public before

`run.py` creates the frozen sources, learns them, and runs actual `context --json`
and `context --compact --json`. Raw and compact payloads are retained in
`before-public.json`; console outcomes are in `before-run.txt`.

Seven positive-source checks fail: alternative pair, background only, Stack only,
multiple background owners, unknown callback, unknown helper, renamed observation.
Negation, quotation and conjunction checks pass **only the no-alternative-authority
condition**; no claim that their search results are correct follows.

The expected positive set is the union of alternatives, not a background-only
answer. Unsupported source cannot become proven absent. Source controls use
independent names and literals, not the original observation sentence.

These public failures do not all match the original failure layer. In the pair,
background is in raw but not compact, while pure Stack is already absent from raw.
The callback-unknown owner is also absent from raw. They do not establish that a
new selection projection deleted unknowns, or license a common-layer repair.

## Contract audit and independent review

An independent read-only reviewer rejected the proposed shortcut of adapting
English OR to the existing background projection:

- `query_render_recall.request_terms` only recalls `backgroundcolor`.
- `retain_background_candidates` transports only backgroundcolor-marked paths.
- `BackgroundParser.parse` requires at least one backgroundColor modifier.
  Pure Stack has no positive certificate; onTouch is unsupported/unknown.
- `bind_render_context` skips unparsed owners then replaces anchors/wiki with the
  positive background witnesses. It does not preserve unknown alternatives.

Thus accepting this English request as `capability='background'` would erase the
stacking branch of OR. In particular, TouchOverlay contains an actual Stack but
its callback falls outside the closed parser. That is not source absence, nor
permission to drop it to make precision pass. SourceSwapCoordinator is outside
this UI parser too; no negative certificate or query-to-role proof was created.
No such unsafe candidate was implemented, and no parser side repair was made.
The review is recorded in `REVIEW.md`.

## Verified and unproved

- Existing focused background source/selection tests: 12 passed.
- Initial command also named nonexistent `test_render_recall`: one import error,
  retained in `related-contract-tests-first.txt`. Corrected command ran only the
  two existing background modules; this is not a green full gate.
- Frozen public before: 7 expected failures, 3 limited authorization passes.
- Original09 stays 2/3, **zero additional original repairs**. No aggregate score.
- No production edits means no new serving behavior is proposed for integration.

Stop applies to **reusing the existing background contract for English OR**, not
all future designs. A restart would need a reviewed bounded Stack witness, union
recall/consumption for both alternatives, and unknown fallback/retention with
query relevance and unchanged-budget feasibility. Those contracts are absent;
this investigation does not demonstrate that adding them will resolve original09.
Do not resume rejected global aliases or non-erasure, or tune against the original
sentence. The present evidence does not authorize such an expansion.
