# Original23 fresh pair: candidate remains isolated

Fresh published-baseline0a8a8fd and fixed candidate13e5101 each ran only the existing
original23 Development scenario's three variants. No fixture/query/oracle changes,
no full gate. Baseline2/3 and candidate2/3, but the Chinese failed case WORSENED:
precision0.5 (ShipmentTimeline + WorkGallery,1347 tokens) becomes0.3333
(ShipmentTimeline + CatalogFilterPanel + WorkGallery,1341 tokens). English/other
variants remain pass with1204/1189 tokens. Original repaired count remains20.
This is a real quantitative regression even though the binary pass count is equal.
The independent frozen controls passing does not authorize publishing this candidate.

Evidence: baseline-fresh-baseline-original23.json, phase-s-original23.json and
original23-fresh-pair.json. Baseline/candidate source fixtures have no git diff.
Runtime worktrees remain immutable. All prior failed/intermediate results retained.

## Read-only, unscored attribution traces

The current candidate's original query still has exactly TWO positive known Builder
rows, WorkGallery499 and NavigationToolbar34; both survive selected. WorkGallery
same-chain witness succeeds with(listDirection,height); Toolbar has no witness.
The private qualified selection succeeds withknown_matches1 in raw and compact.
Therefore no grammar, range, capacity or all-known-selected gate failed.

The extra CatalogFilterPanel anchor has graph_neighbor=true and graph_relation=
imports. The actual edge is CatalogFilterPanel.ets -> FilterToggle.ets (source
file136 to targetfile139; current edge618). FilterToggle.build is directly recalled
through behavior_method_fts (method evidence includesheight), so reverse import
promotion reaches CatalogFilterPanel. No invented edge or identifier inference.
Candidate compact builder_anchors returns its original anchors at line171 due to
the explicit graph protection. The protection is not changed or bypassed.

A separate normal-learn/raw+compact diagnostic on fixed PhaseR63e0fdc already
returns the same three files without a Chinese source-selection marker. Therefore
the extra source is present before PhaseS; it is not caused by a false same-chain
witness. The original retained0a trace had the imports edge too, but only two
returned sources. Edge existence alone does not establish why a returned anchor
became newly retained. Current relation_hints is empty despite raw edge evidence;
do not promise that dropping code anchors would preserve compact graph context.

## Narrow next hypothesis, not an applied fix

Read-only helper probes show structural_boundary_query('Builder') and even
structural_boundary_query('a bodybuilder profile') are true because 'build' is
matched as a substring. preserve_structural_boundary_neighbors uses that flag to
retain imports/configuration neighbors. This is a plausible narrower language-
classification defect than changing general graph protections, but its exact
contribution to this regression has not yet been isolated. A new prospective
independent public fixture plus real build/native/explicit-graph controls is needed
before any fix. Do not silently add a Catalog/query-specific exception or relax
oldgraph authority. R/S stay isolated until a reviewed non-regressing solution.
