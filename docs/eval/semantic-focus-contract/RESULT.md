# Rejected after public acceptance failures

One isolated implementation of PLAN was attempted. It left max-coverage selection
and scores unchanged, compared selected method markers with existing bounded
non-graph symbol/file evidence, and returned the existing full list with focus=false
when another path contained a distinct requested marker. It neither aggregated
methods nor assigned new roles/proofs. Patch preserved as rejected-candidate.patch.

Both required acceptance reds remain red:
- visual-background still returns GestureLayer alone, not AmountSurface.
- lifecycle-1 now returns BufferSession plus PendingQueue, SplitRoles, TextPanel.
  Desired-owner recall improves, but the frozen oracle excludes TextPanel, so the
  result is still FAIL. It is not converted to a containment-only success.

The first ten completed cases and full responses are preserved in candidate.json
and candidate.txt. The run was interrupted once the rejection was observed; the
remaining four controls (including the old literal red) were not run on candidate.
Their baseline outcomes remain intact. Do not report a complete candidate matrix
or assume unknown regressions are absent. No further threshold/score/keyword/role
or downstream localization tuning was attempted. No original pack was evaluated.

Production was immediately restored from the fixed baseline. `git diff 14064c5 --
tools tests` is empty. No accepted serving change or repair benefit is claimed.
The evidence falsifies this tested non-erasure policy as sufficient for both public
failures. Lifecycle shows the predicted recall/precision tradeoff; visual shows
that preserving initial evidence alone cannot promise final source selection.
Determining later visual selection loss would be a new investigation, not license
to keep tuning this rejected candidate. Typed aggregation is still a separate
unimplemented design and cannot be claimed to resolve either red.
