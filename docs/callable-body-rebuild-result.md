# Callable body reconstruction: focused result

On d7c156d, five pre-fixed queries against a new CapabilityReader source showed
that label's selected range (11–13) became an excerpt of 1–11. The target return
and closing brace disappeared despite a small source. Three single-label queries
and a two-method query reproduced this; the resolver-only control was intact.

The first proven layer is focused_source_range: neighborhood scoring expands a
small source method toward an adjacent executable call. Its replacement window
loses the original method end. Overlap elimination then suppresses other ranges.

The repair only extends a focused window's end when an exact parsed callable
identity and extent certify that the omitted tail belongs to the original range.
It never prepends content, never changes ranking or method ownership, and only
extends within the existing line cap. Unsupported languages, clipped parser
inputs, mismatched symbols/ranges, already-complete windows, and overlong unions
remain unchanged. This is a partial excerpt-quality repair, not a new ranking
policy or promise of complete bodies under arbitrary token budgets.

All five public checks pass, preserve every original source line, and retain
exact callable evidence. Seventeen related tests pass. Modified runtime modules
remain at 499 and 23 lines. Full-suite and aggregate capability evaluation are
intentionally deferred under the user's latest instruction.
