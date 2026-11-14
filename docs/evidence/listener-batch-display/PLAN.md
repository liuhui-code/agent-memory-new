# Bounded batch and non-exclusive display experiment

Base b6d958b. Development only: committed files stay under docs plus gitlog;
install only in a disposable runtime copied from this base. No production,
selector, ranking, source-role or negative/unique authority change.

## Model boundary

Before per-witness validation, require an actual list with at most 64 records
and a JSON UTF-8 encoded size at most 65536 bytes. These are new experimental
transport limits, not evidence of global coverage. Bool is not an integer.
Require referenced entity kind to be method/function and all existing exact
source/signature/digest/formal/interval validation. Reject malformed batches.
Identity is outer source key + source digest + invocation half-open interval.
Byte-identical duplicate facts normalize to one in original order before
packing. Same identity with differing payload rejects the optional batch;
never choose one version or consume optional budget twice. Producer optional
failure yields unknown optional evidence without aborting legacy extraction.

## Non-exclusive display

Use the existing real CLI `list --type code-symbol` result as the sole display
surface in this stage. Do NOT add output to compact context or modify its
1500-token allocation. Add an experimental read projection from actual current
SQLite rows, not synthetic reduced facts. For each optional fact validate its
shape against that row's source key, declared signature, kind, range and digest;
then read the actual source snapshot, verify its digest and source intervals.
Missing source, stale digest, old schema, missing payload, malformed payload or
partial/capped payload is unknown, never absence or uniqueness. Display exact
source-bound invocation facts plus explicit coverage `bounded-record`, cap
status `not-global`, `relation_satisfied=false`, `eligible_for_ranking=false`,
and `unresolved_qualifiers=['request not evaluated']`. This first display does
not parse requests or attach the offline name-association output: doing so
would need a separate query-bound interface. No statement of SDK execution,
argument value flow, dynamic receiver or global completeness.

## Frozen verification scope

Keep original 20 source controls and fixed five queries byte-identical. Re-run
real baseline and disposable-overlay learn/list/context plus ordinary merge.
Require old mechanism bytes/order/search terms identical, total old+optional
encoded storage <=4096, and original five bodies/ranges/primary/outcomes
unchanged (record ids may rebuild); compact <=1500. Code-only old index has
unknown display; merge activates source-bound display. Test current row/digest
mismatch, unavailable source, malformed field, unknown version and cap domain.
New model controls: 64 vs65 before iteration; byte boundary; wrong list type;
exact duplicate; conflict duplicate; noncallable entity; bool intervals/index;
source mismatch. Preserve previous failed outputs and all new failures.

## Decision boundaries

This is an actual temporary schema/model/list-projection change, not zero-schema.
Decoder is structural/provider-trusting; only display source validation has
current source bytes. No production architectural approval is inferred.
If display requires dropping mandatory old content, stop; do not raise caps.
Reviewer approves this plan before protocol freeze/implementation. No new
public queries, noise, tuning or aggregate evaluation.
