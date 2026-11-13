# Persistence dynamic-access abstention follow-up

Base 3c616ca. This separate patch does not alter the preceding evidence archive.

- Computed/optional calls are unresolved persistence syntax, never certified reads.
- A recognized persistence receiver reference without a proven direct read, or a
  read/get/load-shaped method on an unknown receiver, is unresolved as well.
- Frozen controls cover preferences['get'], prefs?.get, preferences?.get, local
  receiver aliases, extracted methods and externalAlias.read. Each prevents a
  competing directly proven reader from gaining exclusivity. No new positive
  persistence syntax recognition and no query scoring/threshold changes.
- Alias/data-flow binding resolution is NOT implemented. The fallback covers
  observed receiver references and read-shaped calls; it does not establish the
  semantics of arbitrary externally bound names. Proof remains a static syntax
  match, not proof of platform binding or global absence of semantic reads.
- Producer/consumer checked marker advances to v2. Old v1 records are unknown,
  tested explicitly; re-learn is required for this tightened contract.
- Initial experiment marked every unrelated computed/optional call unresolved
  for runtime capability as well. This caused a new capability regression and
  was rejected (optional-read-target.json). The final fallback affects persistence
  only; the existing runtime named-receiver uncertainty rule is unchanged.
- Final six selected variants retain 3/6: capability 2/3, restore 1/3. No new
  regression. 41 focused tests pass. No full suite or remote write.

Command: PYTHONPATH=tests:. python -m unittest tests.test_source_operation_contract tests.test_runtime_capability_public tests.test_semantic_callable_profile tests.test_query_callable_evidence tests.test_context_callable_focus -v
