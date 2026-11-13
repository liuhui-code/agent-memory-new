# Transactional partial-source recovery (isolated strategy candidate)

Serving base23e00f1. This is a deliberately LOSSY ranking-detail versus source-body
priority trade, not lossless compression and not a change to the1500-token limit.
The earlier whole callable minimizer is rejected because it deletes unique identities,
mechanism roles and alternatives. Existing compact finalizers already treat ranking
scores/reasons as optional; raw Context keeps these diagnostics.

## Narrow transaction
After the normal finalized compact payload, consider only one existing primary
anchor with one bounded range and one truncated prefix excerpt. Require current
freshness, a matching raw wiki record type/id/path/symbol/exact range, one SHA256
source_digest, and exact same-source prefix. Read at most2MiB once; verify digest
and derive the text from those same bytes. Missing proof, changed tail, stale source,
unknown range, missing file or unsafe path aborts. Restore only the existing range,
never inferred owner, method or new source. Respect existing40-line,1500-character
per-source and2600-character total caps (and stricter supplied caps).

Deep-copy the output. Omit numeric score/evidence_score and ONLY these optional
ranking/match-explanation labels: expanded_query:symbol, expanded_query:summary,
expanded_query:method_evidence, first_stage_rank_prior. Unknown reasons, exact
identity reasons, owner metadata, structural coverage, callable_roles, certificates,
uncertainty, boundary, every alternative and all source/log/path/freshness identities
remain. The entire change commits only if the completed payload fits1500; otherwise
return the identical original object. No default intent or evaluator query changes.
output_budget.truncated remains true to disclose omitted ranking detail.

## Independent public reproduction and controls
The frozen32-line synthetic store has configuration fields before dispatch/refresh.
Actual baseline Context shows only header lines1-18, no methods. Candidate shows1-32,
including both operations, at1495/1500, with logs/path unchanged. A33-line version
would need1506 and is unchanged. These exercise a real capacity boundary, not a
raised budget. Initial small-source probes already fit and are not claimed failures;
an exploratory reused directory briefly retained renamed fixture files and was
discarded in favor of fresh per-run directories before freezing public evidence.
Explicit source+log and multiowner public controls have byte-equivalent query_handoff
JSON before/after. Unit controls cover smaller source caps, line caps, tiny token
budget, already complete excerpt, absent source proof, tail change with unchanged
prefix, missing/escaping file, unknown reasons/certificates and exact preservation
of every field other than explicitly permitted ranking/primary-body/budget fields.

## Results
- Post-action selected original1/3->2/3: original now includes full LightingStore
  source; Chinese remains passing; English still fails extra-owner precision.
- Previously repaired causal-profile group stays3/3.
-48 focused tests pass (typed references, source-operation identity/contract/projection,
  existing explicit-intent compatibility, primary budget and lossless-range tests).
  Includes7 new recovery tests with capacity, digest, source-byte fidelity and typed-record negative controls.
- Compile/diff checks pass; changed runtime files stay below500 lines.
- No full suite, holdout, remote write or promotion claim. Parent must review before
  integration/publication; this checkpoint does not authorize a wider priority rule.

Focused command: PYTHONPATH=tests:. python -m unittest tests.test_partial_source_rank_trade tests.test_context_typed_references tests.test_lossless_range_budget tests.test_source_operation_anchor_identity tests.test_source_operation_contract tests.test_source_operation_projection tests.test_explicit_context_intent tests.test_context_primary_budget -v
