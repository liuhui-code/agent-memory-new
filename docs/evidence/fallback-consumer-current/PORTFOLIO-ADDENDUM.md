# Exact portfolio admission and legacy projection boundary

Read-only replay of saved localization and evidence into the unchanged
build_callable_passage_portfolio helper; result equals the saved actual public
portfolio exactly. This is internal diagnosis, not a new public query or red.
Full input/check output is portfolio-internal-replay.json.

## Why selectRepository is absent

The serialized candidate is known symbol_id370, qualified_name
TransportRegistry.selectRepository, range4–10, score13.03. It is ninth of twelve
selected callables. It is not excluded by query and its identity is consistent.
There are **two independent failed eligibility requirements**:

1. query_supported is false. Reasons are expanded_query:summary,
   first_stage_rank_prior, source_locatable, file_path, symbol_summary,
   search_terms, exact_path_segment, semantic_behavior. None intersects
   QUERY_SUPPORT_REASONS (exact_function/identifier/symbol, semantic_mechanism,
   salient_query_evidence, multi_term_method_evidence). Symbol terms `select` and
   `repository` are not both query terms, so no query_symbol_terms is added.
2. identity is absent from localization.source_ranges. The existing producer
   selects12 callables but valid_source_ranges stops at MAX_SOURCE_RANGES=8.
   Registry is ninth; all first eight produced valid ranges. Thus this is the
   documented source-range capacity boundary, not missing stored range or an ID
   mismatch. Raising that cap alone would still fail query_supported.

The and-expression rejects at query_supported before checking its range, but the
range requirement independently also fails. No ambiguity downgrade, same-owner
filter or three-member portfolio capacity is the immediate rejection of registry.
The portfolio's final three-file diversity operates only after eligibility.
No field was silently renamed/dropped between two supposedly equal identities.
An explicit new role-binding contract might choose to supply support, but that
would not be repair of an already issued registry-role certificate. Do not tune
support whitelist or source-range/member caps to pass this original query.

## Is ordinary cross-file portfolio already projection permission?

No unconditional permission is documented. Current context_callable_focus has
an explicit `cross_file and activated` path branch. Without it, only separately
certified indexed-owner authority, same-owner retained subsets, or actual named
already-covered pair guards supply additional rights; this saved portfolio has
none. The legacy path reaches primary-file focus as designed.

Evidence strength is qualified:
- docs/verified-repair-resumption-20261109.md explicitly documents this exact
  no-path legacy limitation and counterexamples: unrelated third portfolio member,
  multi-term filtering dropping a real service, exact-symbol admitting an unrelated
  action button, and single-owner multi-action queries classified multiple.
- tests/test_context_callable_focus.py covers uncertain cross-file refusal and
  bounded incomplete-path cross-file fusion; tests/test_callable_passage_portfolio.py
  proves producer composition, not general consumer authorization.
- These adjacent tests and explicit implementation/history establish a deliberate
  conservative boundary. I did not find a dedicated test asserting the exact
  bounded/no-path/composed tuple must always narrow. Therefore do not overstate
  test coverage as a complete semantic specification or infer absence of any bug.

The real improvement prerequisite remains role-to-existing-identity support, not
blindly consuming `state=composed`. The actual static edges still contain only
contains/exposes/state-write for these endpoints, no proof that registry passes
its selected repository to this store. No runtime changes or new tests executed.
