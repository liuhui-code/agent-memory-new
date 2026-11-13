# Explicit result alternative normalization (Development)

Base 4005b65. Independent public context fixture reproduces a missing exclusion
syntax: executable source "instead of manifest metadata or settings text" selected
settings, while the equivalent existing "rather than" query selected the correct
API-call source. The capability English variant showed the same consumer veto.

Only explicit result alternatives are normalized into the EXISTING rather-than
contract. The new normalization requires a sentence/clause-boundary retrieval
command, a nominal returned-result category or qualified symbol, no intervening
operation/conversion/relative/content clause, and no overlap with quoted text.
It applies consistently to positive retrieval and the existing result-exclusion
role/identifier helpers. No sourceop v2, candidate scores, thresholds, graph guards,
portfolio permissions or behavior vocabulary changes.

Ambiguous bare A/B, code-that-uses-X-instead-of-Y, conversion, content-containing,
with/from/to/using clauses, literal original text, and no-positive-target requests
remain unchanged. This intentionally does not implement general English parsing.
Original rather-than and all-negative fallback behavior remain unchanged.

Results:
- capability original/English/Chinese: 2/3 -> 3/3; true owner and required snippet
  retained for all. This is a selected development group, not a full-suite score.
- independent source request: settings -> ExtensionInspector, with actual
  bundleManager.getBundleInfoForSelf excerpt. Rather-than control identical.
- explicit settings target instead of runtime source now returns settings only.
- literal, declaration-directed and true double-target controls preserve their
  baseline non-source-priority behavior. Existing metadata query imperfections
  are not described as fixed merely because they are unchanged.
- 73 focused tests pass; compile and diff checks pass. No full suite/holdout/remote.

Command: PYTHONPATH=tests:. python -m unittest tests.test_query_result_alternative tests.test_query_language tests.test_query_language_exclusions tests.test_source_operation_contract tests.test_runtime_capability_public tests.test_query_typed_contract tests.test_typed_contract_projection tests.test_structural_query_exclusions tests.test_query_result_diversity -v

Frozen protocol contains synthetic fixture source and queries. Public outputs are
bounded projections plus SHA256 of full stdout. Runner uses the existing runtime
entrypoint and accepts RUNTIME_REPO for baseline pairing in a fresh evidence dir.
