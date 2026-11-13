# Read-only audit of the fixed two-target source omission

No new query or source execution. This audit reads the saved two-target raw/compact
pair and the ed3fd70 implementation. The original five-query protocol is unchanged.

Raw identity/range is present: CatalogRestorer.onCreate is code_symbol record 8,
lines 6–10. Its class record 7 covers 4–11. Compact groups both records on one
anchor, preserves both source_ranges and read_window 4–11, but the actual excerpt
is 1–7, truncated=true. Therefore required behavior lines 8–9 are genuinely absent
from the returned text, not missing from the index or wrongly scored by the oracle.

The named-two-target guard returns existing anchors before callable projection;
the saved focus trace ends at line 60. The selected callable primary is instead
CatalogPanel.aboutToAppear (7–9). Public passage_portfolio is composed, but neither
its serialized form nor the presence of role=primary on multiple anchors grants
private certification or a full-source entitlement. The ordinary named-target
protection preserves identities, not unconditional full text for all targets.

The current recover_partial_primary contract is deliberately narrower:
- With multiple anchors it binds only the callable primary, not every display
  anchor labeled primary and not arbitrary alternatives.
- Its unique match requires a single exact symbol/range. The Panel anchor has
  TWO ranges (method 7–9 and component 5–11), so matches is empty and recovery
  returns before any new source read. The reader is not that callable primary.
- Further guards would require a same-range prefix and matched indexed raw ID,
  kind/path/symbol/bounds/source_digest. Reader's excerpt begins at 1 while its
  method starts at 6, so it is not the supported prefix-recovery shape either.
- Removing these guards would expand projection/source-reading policy; it is not
  application of an existing private receipt. No such authority is inferred here.

Budget facts: saved final estimate is 1491/1500 tokens, truncated=true, with three
excerpts totaling 818 characters. A read-only deep-copy calculation keeping every
other field and appending reader lines 8–10 from frozen protocol bytes produces
936 source characters and 1522 tokens (recomputed with estimate_payload_tokens).
This calculation is NOT a source-reading proposal or CLI rerun; it shows a simple
append would violate the current overall limit. Existing compact callable rows
have already lost numerical ranking details, so those cannot be traded again.

attach_source_excerpts divides available character capacity between anchors;
query_term_window_within_anchor may include surrounding lines for non-precise
anchors. enforce_budget can subsequently trim excerpts. The frozen trace did NOT
instrument either function, so it does not distinguish the exact allocation versus
later trim step that first removed lines 8–9. Do not invent that finer first-loss
claim. The known final state is explicit truncation at a nearly full hard budget.

Conclusion: the full-span oracle fails, but this is not a demonstrated misuse of
multi-anchor primary recovery. Supporting every requested alternative's minimal
body would require separately reviewed allocation/projection policy, source identity
and hard-budget tradeoffs. Do not silently shrink other log/graph evidence or widen
caps. Preserve this control red and stop; no serving fix follows from this audit.
