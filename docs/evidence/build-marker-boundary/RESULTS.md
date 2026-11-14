# Build marker boundary: fixed candidate results

Development only. Runtime fixed at 0fab179 in an independent detached worktree.
No R/S code, original case rerun, full gate, or remote publication is included.

The two frozen public reds now meet their original path criteria:
- Builder source: only ProfileTile.renderTile, complete lines 5–10.
- bodybuilder profile: ProfileScreen and ProfileTile, no spurious palette anchor.
Both actual traces change structural_boundary_query to false; preserve returns
its focused input unchanged. This is an existing boundary-classification repair,
not a new rule to discard arbitrary import neighbors.

All five unchanged controls retain exact raw and compact query_handoff objects.
In particular bare-declared retains its original three anchors: it never calls
the structural-preserve branch. Native-build still reaches the predicate as true.
All seven compact log keywords, log anchors and path contexts are unchanged.
Actual returned excerpts in the two target cases match frozen source line bytes.
The verifier's comparisons and trace counts are in after-fixed-verdicts.json.
Raw project IDs/paths, normal learn timestamps and usage records differ between
fresh projects; whole raw payload byte equivalence is not asserted.

19 focused tests pass (5 new, 4 structural-exclusion, 10 existing English Builder
consumer); independent reviewer separately ran 9 boundary/exclusion tests.
Python compilation passes. Runtime file remains below the 500-line limit.
Source stayed immutable throughout the public run. Existing broad markers other
than build are unchanged. Numeric suffix and rebuild/building behavior were
specified before execution, not inferred from these results.

This does not establish any original failure reduction. Original count remains
20. The quarantined property-recall/source-witness regression is not resolved by
analogy; it requires its own actual causal trace and any separately approved
combined experiment. No graph guard or frozen oracle was weakened.
