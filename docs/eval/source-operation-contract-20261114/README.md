# Source-operation evidence admission (Development only)

Base 3a2693d. Two independently reproduced losses: runtime capability inspection
and persistence restore ownership. Static source operations were outranked by
metadata/string statements. This stage closes only two capability variants.

## Contract and limitations
- Producer emits versioned callable roles, distinct from searchable identifier
  tokens. Only TS/ArkTS, existing runtime call-name / persistence-read patterns,
  masked non-code, bounded source bodies. These are static syntactic operation
  matches, NOT resolution of imports, runtime API binding, platform availability,
  or proof that a request has exactly one owner in the repository.
- Three states: checked absence, checked supported syntax, unresolved/missing
  proof. Templates, malformed bodies, nested execution and obvious shadowing are
  conservative. Missing fields, old index, unknown adapters/languages, unknown or
  partially supported request mechanisms cannot grant priority.
- Consumer requires complete supported mechanism coverage, no quoted literals,
  typed/exact competing target, multiple scope or declaration/text target intent.
  Exactly one eligible candidate within the current valid recalled set may gain
  precedence. Unknown/invalid/graph competing evidence blocks it. No scores,
  retrieval vocabulary, >=2 focus threshold, recall or portfolio permissions change.
- Derived query authority is cleared on every request, including JSON/dict reuse.
  Boundedness uses the same witness, propagated through the localizer projection.

## Results
- capability: 0/3 -> 2/3. Original and Chinese now return FeatureCapabilityProbe
  with required source bodies. English remains blocked by conservative target
  intent veto (its request also mentions metadata/settings).
- persistence restore: 1/3 -> 1/3, no new regression. Original remains passed;
  English and Chinese remain failures. Conjoined/partially supported contracts
  are not relaxed to improve this result.
- Independent executable-vs-string fixture: English and Chinese misselected
  ProbeNotes before; all three behavior queries now return ExtensionInspector.
- Two real operation owners, requested text/declaration, exact mixed source
  targets and ordinary literal controls retain their baseline outcomes. Some
  baseline multi-owner/text controls are themselves imperfect; equality is not
  claimed as full correctness. See public-observations and frozen controls.
- 97 focused tests pass; 35 additional localizer/provider/graph tests complete with 34 passing and one optional ArkAnalyzer provider test skipped (not installed). No full suite, consumed holdout or remote write.

## Failed experiments retained
The first added method marker alone passed 4 scope tests but failed public query
and left the original capability set 0/3. It is not in runtime. A first operation
precedence candidate regressed restore original by treating an unproved nested
callback owner as absent. contract-target.json records that failure. Three-state
handling restored the original pass; a dedicated test fixes this counterexample.
Review also exposed template interpolation loss, partial mechanism certification,
query-reuse authority, invalid/graph competitors and obvious receiver shadowing;
all now have fixed negative tests.

## Index compatibility
No schema migration. Existing index lacking checked roles keeps old behavior.
Running current learn-path --path . (merge, without --replace) regenerates roles
and enables the new contract. Real before/install/relearn proof is preserved in
index-upgrade-symbols.json and console output. All 7 symbol keys, paths, ranges,
digests and adapters are unchanged; table schema hash is unchanged. Only intended
callable roles differ. Old archives are not silently treated as certified.

## Focused command
PYTHONPATH=tests:. python -m unittest tests.test_source_operation_contract tests.test_runtime_capability_public tests.test_semantic_callable_profile tests.test_query_callable_evidence tests.test_context_callable_focus tests.test_ecma_callable_body_ranges tests.test_query_typed_contract tests.test_typed_contract_projection tests.test_salient_source_public tests.test_callable_behavior_hints tests.test_callable_collection_evidence tests.test_callable_cleanup_evidence -v

Runners use an external sibling evidence directory and can take RUNTIME_REPO for
baseline pairing. Frozen JSON supplies source bytes; runtime entrypoint is always
tools/agent_memory.py. Full local outputs have bounded projections plus hashes.

Additional command: PYTHONPATH=tests:. python -m unittest tests.test_hierarchical_localization tests.test_context_hierarchical_metrics tests.test_semantic_provider tests.test_query_graph_neighbors -v
