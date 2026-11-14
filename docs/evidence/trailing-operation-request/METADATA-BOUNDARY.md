# Read-only metadata consumption boundary audit

Inspected existing runtime on isolated candidate d06114c, with no further edits.
The parent independently reached the same result.

`semantic_ecma_mechanisms.mechanism` deliberately includes `identifier_tokens` in
operation terms. `query_hierarchical_localization.matching_mechanisms` intersects
those terms with `query_tokens(query) | behavior_marker_terms(query)` and the
callable scorer adds up to 9.0 for the leading mechanism match. It does not have a
separate source-syntax-only fact class, exact-request eligibility bit, or a
quoted/conflicting-query exception for generic operation evidence. Passage indexing
also materializes mechanism terms. Source-operation support certificates are a
different bounded mechanism and do not prevent generic mechanism lexical ranking.

Consequently the added fontSize/fontColor observations predictably participate in
ordinary retrieval and localization for more than the positive source request.
The quoted/conflict behavior change is a violation of this experiment's frozen
compatibility requirement, **not proof of an existing runtime interface bug**.
There is no demonstrated existing qualification contract simply left unconsumed.
No new field, permission marker, global ranking edit or after-the-fact query rule
is justified by this experiment. Dropping all new terms just to preserve controls
would likewise be a different contract, not a proven repair.

The candidate remains rejected and isolated. Any future proposal separating syntax
observations from behavioral relevance must first establish an independently
specified supported contract and suitable actual before/counterexamples; this
record is not authorization to build that architecture. Other original failure
classes can progress independently.
