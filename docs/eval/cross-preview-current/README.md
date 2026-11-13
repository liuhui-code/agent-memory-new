# Current cross-component preview first-loss audit

Base8ce567b. Original pack governance was checked as development/editable,
project_neutral reviewed synthetic. Only context-cross-component-preview's three
variants were evaluated. Result remains1/3; no aggregate or holdout run.

## Current state differs from old ledger

Both English raw wiki results now contain MessageRow AND QuotedMessagePreview.
The public symbol/edge list proves the actual import, parent build call to child,
file-to-component renders_component and passes_property, and each build's reads
of its own property. These are static source relations, not runtime causality.
The original request explicitly asks both UI source contexts; the paraphrase asks
for typography code for both row and preview. Neither supplies complete identifiers.

The first current loss is compact focus_callable_anchors: bounded MessageRow.build
causes file-based narrowing, leaving MessageRow.quotedText anchor. The exact named
Chinese pair passes the existing explicit-pair refusal-to-narrow guard. No producer
repair or extra relationship generation is necessary to make the relation exist.

## Score/provenance hypothesis, not an accepted change

Existing graph metadata can refuse narrowing. promote_neighbor records a candidate
only when its graph score exceeds already matched score. Original query trace:
- parent file→child passes_property:50.17 vs child's67.5; no candidate;
- reverse:54.52296 vs parent's56; no candidate;
- renders_component:47.6/52.4875, likewise below existing scores.
Thus already strongly recalled related entities have no graph_neighbor provenance,
although genuine static edges are present. Compact does not independently consult
those edges and narrows. This establishes the current original path, not a generally
safe change to how graph evidence authorizes source retention.

## Independent frozen controls did NOT reproduce the loss

A separate ArticleTile/CitationBlurb fixture was frozen before execution with four
queries: two natural pair requests, named pair, single child. All4 retain required
sources on baseline. Actual parent render/property and real typography are present.
A prespecified semantic-equivalence addendum renames the child property content→text
and caller key together, leaving all four queries and required paths unchanged.
All4 still retain required sources. Child is graph_neighbor:passes_property in both
versions, so these are green controls, NOT an independent red reproduction. Source
hashes/keys may change with renaming; cross-version numeric identity is not asserted.

No scores, queries, thresholds, source code or oracle were tuned after these results.
No production/test behavior was changed. The hypothesis lacks an independent public
same-layer red; do not publish an unverified provenance fix from this audit alone.
A future experiment must prove the score/provenance condition without choosing
query-specific thresholds, then preserve single-owner/unrelated-import/true-pair
controls before any metadata change can be accepted.

Artifacts: original-current.json; public.json; graph.json; trace4/5 etc.;
graph-trace-4.json (original raw only); independent-protocol/before and
prop-equivalence-protocol/before. Trace scripts read runtime frames but do not alter
serving output. Initial four-query controls and the addendum were separately frozen.
