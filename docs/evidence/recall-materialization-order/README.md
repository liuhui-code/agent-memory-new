# Recall materialization can reorder equal-score candidates

Investigation only, on repair revision `6fdaefcf8f561d1d19f849b77fa328d19b69bb4f`. No serving or evaluator change. This is a generic internal control, not Case 08 acceptance.

## Observed boundary

[Recall](../../../tools/agent_memory_runtime/query_candidate_recall.py#L135-L167) collects ordered IDs from the provider, then passes them to [`fetch_rows_by_ids`](../../../tools/agent_memory_runtime/query_candidate_recall.py#L464). The loader uses `IN` without `ORDER BY`; SQL does not promise the input ID order. The [candidate audit](../../../tools/agent_memory_runtime/query_fielded_retrieval.py#L179-L198) maps those rows by ID and walks the selected IDs instead, so it is not a record of the sequence handed to scoring. The [source freshness filter](../../../tools/agent_memory_runtime/index_freshness.py#L62-L103) runs after that audit and preserves the relative order of surviving hydrated rows.

On SQLite 3.53.1, an in-memory control gave:

| Bucket | Ordered audit | Hydrated | Live after source freshness | Ordered audit restricted to live IDs |
|---|---|---|---|---|
| Code symbols | 42, 11, 7 | 7, 11, 42 | 7, 42 | 42, 7 |
| Semantic facts | 42, 11, 7 | 7, 11, 42 | 7, 11, 42 | 42, 11, 7 |

For code, ID 11's source digest no longer matched; removal did not cause the order mismatch. For facts, an additional requested ID 60 with `is_stale=1` was excluded by the SQL membership filter. Active fact 11 remained even though a code candidate for the same path was dropped: source freshness filters derived code rows, not the facts bucket. Shared-loader changes would therefore reach non-code candidates too.

A separate in-memory check used real reciprocal rank fusion to select `[42, 11, 7, 60]` and observed SQL returning `[7, 11, 42, 60]`. With equal scores and dates for the first three fused IDs and a strictly higher score for 60, the collector's stable sort key produced `[60, 7, 11, 42]`. A local counterfactual restoring fused order before rescoring gave `[60, 42, 11, 7]`. It did not change the strictly higher result. A membership control excluded missing, inactive and foreign-project IDs and returned duplicate requests only once. These sequences are observations for the control, not guarantees about SQLite scan order.

## Reproduction recipe

In a disposable directory, create three ordinary source files A.ts, B.ts and C.ts. Seed in-memory `code_symbols` and `semantic_facts` tables with integer primary keys 7, 11 and 42 in that file order, all in the same project. Give each symbol the original source digest, then change B.ts. Add fact 60 marked stale. Create empty `learn_scopes` and `code_index_state` tables and set SQLite `query_only` after setup. Pass selected IDs `[42, 11, 7, 60]` to the production loader with each table's `ACTIVE_FILTERS`, compute `candidate_refs` from the result and those selected IDs, then call `filter_fresh_candidate_rows`. Compare memberships first and then compare active rows to the audit restricted to those same IDs. To check stability independently, fuse lanes `[42, 11, 7, 60]` and `[42, 7, 11, 60]` with default weights, give 60 score 13 and the others score 12 with equal dates, then compare the collector's stable key on hydrated rows and on a locally reordered copy.

## Case 08 status and stop decision

The [last saved standard single-group result](../../releases/aggregate08-current-20261119/README.md) remains **1/3**: the original passes, the English paraphrase retains extras and delivers a partial target excerpt, and the Chinese variant loses its target at the tied strongest two-path cutoff. The original trace established that cutoff, not that SQL order determines the original wrong outcome. The independent frozen public attempt did not reproduce the same competitive cutoff: it stopped at earlier recall. Do not treat the generic internal order finding as a public failure or as a completed fix.

The retrieval design separates fusion and owner reranking but does not explicitly define how fused rank breaks subsequent owner-score ties. No caller intentionally requesting SQLite's physical order was identified; that does not prove a shared adjustment is harmless. Under the [evaluation and change policy](../../evaluation-and-change-policy.md), stop serving changes until an independent public handoff reproduces the same loss. A qualifying control would hold live membership and owner scores constant, trace provider IDs through hydration and the real cutoff, and protect unequal scores, two genuine paths, stale membership and non-code evidence. No new standard or full acceptance result, benchmark score, or production change is claimed here.
