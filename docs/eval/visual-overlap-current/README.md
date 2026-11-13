# Visual-overlap: exact first loss, no serving candidate

Fixed runtime3d62965; three original variants inspected via public raw/compact,
then Chinese only repeated with finer return tracing. This is not an evaluation
or aggregate rerun. The trace observes function returns, never changes values.

## Original Chinese first loss

InventoryOverlayPanel.build IS present at focus entry (score32.5), together with
its file projection (28.0). Therefore the prior raw-handoff absence does not mean
FTS/producer failed to recall the source. `strongest_owner_contract_candidates`
returns empty. `strongest_semantic_behavior_candidates` immediately returns only
TouchOverlay.build (35.5, semantic coverage2), before method/structural focus.
`focus_code_candidates` returns this focused set. Later salient supplements add
ArchivePackageProfile and DomainLogger, not InventoryOverlayPanel. Diversity
faithfully retains those outputs; it is not the first loss.

The query activates one broad layout concept with markers
`overlay backgroundcolor zindex stack position`.
TouchOverlay's actual source uses Stack and showOverlay: indexed evidence matches
`overlay stack`. InventoryOverlayPanel has actual backgroundColor and shadow,
but matches only `backgroundcolor`. The existing semantic focus accepts coverage
>=2 and selects maximal coverage. Nothing in the current fields distinguishes
alternative layout mechanisms from independently required user operations, or
binds the queried background to the specific category/quantity controls.

## Independent frozen public reproduction

`independent-protocol.json` was written before calls. AmountSurface has category
picker and amount input, shadow/backgroundColor; GestureLayer has Stack/onTouch/
showOverlay. The generic Chinese layout-background query returns only GestureLayer,
strictly failing expected AmountSurface. Exact AmountSurface, exact GestureLayer,
and explicitly requested both return their expected identities. Full raw and compact
outputs are preserved in `independent-current.json`.

Thus the wrong semantic-focus narrowing is independently reproducible, and source
ranges are not missing. This does NOT establish that changing the >=2 threshold,
weights, Chinese aliases, or removing Stack/overlay is safe. Both candidates have
real layout operations; a new query-to-mechanism/target-role contract is needed to
say why two alternatives should not defeat one specifically requested operation.
The current concept grouping and max-coverage behavior agree with their code; no
pre-existing promise to prioritize backgroundColor over Stack was found here.
No production code, oracle, ranking or parser changed. No original improvement
claimed. An implementable next proposal must preserve genuine Stack/overlay and
multi-layout requests and avoid certifying exclusive owner from same-method words.
