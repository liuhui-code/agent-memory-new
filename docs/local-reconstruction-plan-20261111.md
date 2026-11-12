# Reconstruct from locally verified history

## Available source and boundary

This independent checkout was cloned from verified-repair-resumed.bundle at
25ae6bae986d6eb8a476eaa97954cf5f8c63c6a4. Every tracked file matches the untouched
source checkout. The bundle SHA-256 is
cdd773da5cb62c148338f8754894d226a45f7049623cbe9b29107d9b113efcf0.
The new branch is repair/reconstruct-local-20261111. No original repository,
remote, or access control is changed.

Historical reports describe later revisions, including typed-callee context,
neutral Chinese locator handling, sink-template preservation and subsequent
work. Those reports are leads, not recovered source or current test results.
In particular, neither 177/231 nor 194/231 is claimed for this checkout. The
local bundle only establishes the history through 25ae6ba. No unavailable
archive is fetched through an alternate route.

## Work order and acceptance

1. Run the unmodified classified 231-query Development pack to establish a fresh
   baseline. Preserve all source, queries, Oracles, budgets and thresholds.
2. Inspect available local history, tests and fixtures. Distinguish actual bytes
   from historical claims; do not reconstruct unknown code by asserting that an
   old score was recovered.
3. Reproduce each proposed mechanism independently in frozen Development source
   using public raw/compact output and exact source-body checks before changing
   service behavior. An unreproduced lead does not authorize a patch.
4. Stage minimal general fixes separately. Preserve already-working positive
   and negative controls; reject new check/recall/precision/MRR regressions.
5. Run complete regression, source/body review, existing performance and fan-in
   gates, Python line limits and whitespace checks before accepting a stage.
6. Commit source and evidence decisions. Never push without new authorization.

Previously rejected broad identity/and matching and callback-range candidates
must not be revived without materially new evidence. Source window wording must
not be confused with business-window intent, but the historical report alone
is not permission to invent a current parsing fix. No consumed holdout is rerun;
without qualified external evidence, conclusions remain Development only.
