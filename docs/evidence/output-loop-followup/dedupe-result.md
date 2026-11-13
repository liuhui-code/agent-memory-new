# Narrow deferred source-projection budget candidate

This candidate is separate from the rejected outputreadloop marker patch. The
marker patch remains reverted. Only existing deferred budget refill changes.

## Contract

Keep existing scores, focus, 5-item budget, graph policy and explicit paths.
When refilling from deferred items, rank distinct source locations before a file
projection already represented by a symbol with exactly the same path, symbol,
source digest and valid inclusive range. Do not combine distinct methods/ranges.
Only a file with no business fields and the standard language/line-count summary
qualifies. Rich file summaries, different digests, missing bounds and graph
provenance remain untouched. Explicit paths bypass this reorder.
No candidate is deleted or merged; repeated representations follow distinct ones
and are still returned when the budget allows. No alias/source path is rewritten.

## Verified public effect and remaining failure

Previously the independent raw wiki budget included both OutputDescription's
class and the identical projected file but omitted PipeCollector.collect.
With this candidate, collect enters the actual raw wiki's fifth position. The
compact result still chooses OutputDescription.label. The frozen strict public
expectation therefore remains FAILED and the original group stays 1/3.
Do not claim this is a complete process-output repair or an aggregate gain.

The next boundary is independent: compact/localizer lexical scoring can still
prefer a descriptive string callable over the now-retained operation. A new
operation proof or precedence contract cannot be inferred merely from freeing a
budget slot; this stage does not implement one.

## Validation

Initial frozen budget test fails before this edit, passes after. 42 focused
regressions pass, including explicit file/class, informative file metadata,
unknown/different ranges/digests, multiple method spans and sufficient budget
retention. Initial graph-control failure revealed that existing graph helper
allowed direct overrides; candidate now conservatively preserves any graph
provenance. Historical failed output is retained in dedupe-tests.txt.
Only original output-loop group was rerun (1/3); no full suite or remote write.

## Publication review correction: directional information coverage

The initial helper was incorrectly symmetric. A file projection lacks the
symbol's callable roles and method/operation evidence, so it cannot cover a later
symbol even at the identical range/digest. Now only a later plain file projection
can be considered repeated behind an existing symbol, never the reverse.
The conservative file-first order is unchanged rather than introducing a swap.
Added red/green reverse-order proof and actual five-slot refill controls carrying
source-operation/method metadata. Final necessary related checks: 44 pass.
