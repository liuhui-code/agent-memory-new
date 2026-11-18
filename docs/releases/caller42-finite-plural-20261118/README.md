# Finite plural caller retention

The independent Development query `Find actual callers of ModalBridge.finish.` previously recalled both ConfirmPanel and ReviewPanel but publicly retained only ReviewPanel. A caller-local full-match grammar now allows the already-selected callers to keep their distinct indexed identities during diversity filtering. It accepts only `Find [the] actual callers of Owner.member[.]` (case-insensitive keywords, optional outer whitespace). It requires a unique project-wide owner/member resolution equal to the actual SQL target filter, never a same-shaped file token. Existing private query/source identity binding, order and caps remain. Global scope, ranking and existing both/list requests are unchanged.

## Verification and accounting
- Untouched baseline: 17 related methods pass. An earlier before run was not fenced against subsequent editing and is not used as the authoritative baseline; its original log is retained. The separately run untouched baseline is authoritative.
- Candidate focused regression: 19 methods pass, including two new parameterized methods. These include temporary-fixture CLI and SQLite activity, not solely pure tests.
- Independent public BEFORE: 10 CLI (2 init, 2 learn, 6 context); the main query omitted ConfirmPanel. Single and explicit-both controls passed.
- Independent public AFTER: exactly 6 context CLI, 0 init/learn, no retries or new observer. Each query/format used an independent byte-identical copy of its saved learned home, with unchanged absolute source project and query. Main raw now carries both caller identities; compact shows both exact callback bodies, 1487/1500 tokens. Single control is 1316 and explicit-both control 1458. Both control compact handoffs exactly equal their respective BEFORE values.
- Main and explicit-both compact outputs retain `truncated=true`; the required individual excerpts have `truncated=false`. This does not promise complete metadata or all available evidence. Public JSON exposes identity fields, not private class instances.
- Runtime 439-file pins and original source/learned-home bytes remained unchanged during the AFTER. Results were independently reviewed. Full homes, raw outputs and execution records are retained in the separate recovery archive, not this release directory.

## Scope and final-tree verification
This is a finite Development mechanism repair, not original42 closure or a full/aggregate suite. Quoted, negative, single/only, extra-task and ambiguous-member requests do not acquire this new qualification. Prior STOPs remain preserved. Source-supported similarity attribution is not a captured intermediate collector trace.

The final tree integrates the separately published named-exclusion repair without overwriting it. Final-tree regression uses the seven explicit modules below; its result is recorded in the external release audit and commit metadata, without replaying the saved public fixture:

```sh
python -B -m unittest tests.test_named_exclusion_boundaries tests.test_query_language tests.test_query_language_exclusions tests.test_query_result_alternative tests.test_finite_plural_callers tests.test_caller_target_identity tests.test_requested_caller_diversity
```
