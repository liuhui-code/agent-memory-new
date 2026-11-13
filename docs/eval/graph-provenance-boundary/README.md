# Internal graph promotion boundary: observation, not public repair evidence

Base f8191a5. Protocol/probe frozen at95054ab before one internal execution. No
public CLI, original group, source/query mutation or production edit. The synthetic
IDs11/22 are deterministic internal inputs, not claimed indexed real-world entities.
Only the existing score of neighbor22 varies; same typed endpoints/edge/confidence,
origin score100, direction and passes_property relation remain fixed.

## Actual fields observed

| Existing neighbor score | Candidate proposal emitted | Existing row after normal boost helpers |
| --- | --- | --- |
| 10 | 47.85, passes_property, depth1 | score47.85; reasons symbol_summary + graph_neighbor + graph_relation:passes_property |
| 60 | 69.60000000000001 (resolved69.6), same relation/depth | score69.6; same added reasons |
| 90 | none | score90; only original symbol_summary |

Actual formula uses passes_property max ratio0.95 and decay0.82; lexical support
also depends on neighbor score. At90 the computed87*0.95=82.65 does not beat90,
so promote_neighbor returns before adding the candidate. This probe covers promoted
versus suppressed, not an exact-equality floating-point case. No inputs were tuned
after the observation. All edge and matched dictionaries remain unchanged.

neighbor_item adds graph_depth1 to the newly resolved candidate; boost_match merges
only score and match_reasons into an existing row, not graph_depth or typed endpoints.
Thus the actual downstream flag for an already matched row comes from the reasons.
The helper composition in probe.py does not execute database resolution, relation
budget selection or file representative mapping; it is not an end-to-end assertion.

## Is a promised invariant violated?

The fact of the supplied edge is unchanged. What disappears at higher score is
promotion provenance on the matched row, not the stored relation itself. Code
explicitly gates candidate emission on improved score; relation_diverse_neighbors
then caps candidates at2 and existing_matches_by_path may choose a representative.
This interface is not a complete per-endpoint edge inventory.

Read tests/test_query_graph_neighbors.py: tests assert promoted imports become
source-locatable and actual route/property relations exist. A repository search
found no tests of promote_neighbor/boost_match directly, nor a promised invariant
that every already matched endpoint must retain every real relation independent
of score. This bounded inspection cannot prove no prose elsewhere discusses it;
it establishes no explicit current code/test guarantee of monotonic provenance.

A proposed invariant "increasing lexical score must not erase verified relational
facts from result metadata" is sensible to review, but is NEW for this promotion
field. Calling this an already-broken guarantee would misstate current semantics.
The original cross-preview public branch remains a separate observed hypothesis;
its independent public double-suppression coverage is still missing. This internal
check cannot substitute for that missing public red.

## Why retaining these fields is not metadata-only today

- query_handoff builds graph_neighbor from match_reasons and graph_relation from
  graph_relation:*; it is consumed even when boost_match did not set graph_depth.
- query_code_selection uses graph status for reserved/weak-neighbor lanes and
  protected selection behavior. Adding it can preserve or suppress different rows,
  not simply append a neutral fact.
- query_salient_source_retention exempts graph provenance from redundant supplement
  removal, potentially retaining additional source candidates.
- context_callable_focus refuses ordinary bounded narrowing when any graph_neighbor
  exists without overriding owner/artifact qualifications; it also protects against
  some certified portfolio projection. This can preserve other anchors too.

Therefore simply adding graph_neighbor/relation reasons at score90 grants existing
retention/selection permissions and can alter compact excerpts or budgets. It does
not grant filesystem permissions directly, but can affect which already-authorized
source is selected/read. It must not silently become proof of requested relevance,
causality, all-caller enumeration or unique ownership.

## Reviewable next boundary, not implementation approval

A neutral relation-observation channel would need typed endpoint/source provenance
and explicit non-authority semantics, separate from the existing promotion flag.
Its consumers and serialization must be audited before it could be used to support
request-conditioned retention. That is a design change, not a one-line flag fix.
Alternatively changing existing flag semantics requires positive unrelated-graph,
multiple-target, log and budget controls plus an independent public same-layer red.
No such experiment is run or newly authorized here. Preserve this exact internal
observation and stop rather than tune queries/noise to manufacture the public case.
