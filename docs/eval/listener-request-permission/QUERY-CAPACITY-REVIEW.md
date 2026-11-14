# Query diagnostic capacity addendum review

Read c364fbb capacity protocol/runner/results/report and corrected attribution;
no rerun or source/query changes. Prior five/four/Native results remain intact.

Envelope branch is actually covered:32 checked facts yield a hypothetical26876
byte standalone diagnostic envelope, actual output is unknown-cap. Both actual
controls preserve partial coverage, all false authority flags, exact raw equality
against same-snapshot baseline after dropping only the diagnostic, and identical
compact output without that field and within1500 tokens.

The intended >64-fact branch is NOT covered.124 learned symbol rows include
callback entities; context LIMIT64 ascending-ID rows produce40 checked facts.
The observed fallback is byte saturation. Preserve the initial pass=false; do not
combine this into two passing capacity-branch tests or claim the branch impossible.

The initial attribution erroneously reused list's diagnostic decoration of its
first64 descending-ID rows, then sorted rows ascending. The zero-fact attribution
was not a runtime result. Corrected40 comes from source checks over saved rows,
not a second public query. The envelope control's32/26876 remains the successful
covered branch. The attribution field named intended_fact_branch_confirmed is
true for envelope-cap; interpret it only by its case ID, not as a >64-fact pass.

Verdict: accept this precisely bounded addendum, one covered byte branch and one
uncovered fact branch. No need to tune quantities or rerun quality queries. Formal
promotion must retain the uncovered-fact-cap caveat or separately justify future
boundary tests; no production/selection permission follows from this review.
