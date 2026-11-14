# Category04 explicit-negative and weak-log current check

Baselinef3e217b. Three unchanged original Development variants, then one unchanged
Chinese raw/compact pair with return-only observation. No full/holdout run, runtime
change, score/oracle modification, independent fixture invention or remote write.

## Original group remains0/3, with different failure reasons

- original: wrong owner; expected InventoryList source absent.
- English paraphrase: InventoryList source/span present, but InventoryItem forbidden
  hit and precision1/3. This query contains no explicit negative clause.
- Chinese: expected InventoryList source/span present and both explicit excluded
  owners absent; only precision1/3 fails the0.5 requirement.

The Chinese query is unchanged: 库存列表分隔线粗细错误，请定位 divider 的源码，不要返回
InventoryRecord 或 InventoryItem。 positive_retrieval_query retains the positive
request plus inventory topic, and excluded_result_identifiers gives exactly
inventoryrecord/inventoryitem. Actual project_code_exclusions removes InventoryItem
from the four projected sources. InventoryRecord is not in final compact either.
All raw identity_match/graph_neighbor flags are false, graph_relation is null;
path is inactive and no log has a strong event identity. Therefore the proposed
negative-mention/graph-protection bug does NOT occur here. Do not "fix" this already
working exclusion or add an Inventory-specific rule.

Final Chinese compact contains InventoryList, InventoryOverlayPanel and
DispatchProfileService. InventoryList excerpt5–15 fully covers required6–14. The
remaining two are not owners explicitly excluded by the request. Treating the
exclusion list as a global single-owner instruction would change its meaning.

## Exact weak-log branch

Saved raw inputs replay admitted_log_owners unchanged (no new query):
behavior_marker_terms=[], target scope unknown. The len(expected)<2 initial guard
returns all logs before any complete-method check. All five event priorities are0;
DispatchProfileService.run is inferred_wrapped, lexically matching expanded error
vocabulary. Callable primary is ConsoleFailureReporter.report, uncertain, with
InventoryList.build as an alternative. Thus this is not a correct bounded method
whose existing full-behavior certificate is being ignored.

InventoryList's wiki winner is a **file** with exact_behavior_operation. Overlay is
a real topical salient file, not absent evidence. Existing weak-wrapper-log repair
requires a retrieved function/method covering all requested multi-markers; its
extended positive/literal/real-log/multiple/partial controls explicitly preserve
logs when that proof is missing. The targeted existing guard test passes. No weight,
marker threshold, source scope, log/path evidence or graph guard was changed.

## Source evidence availability for a possible narrower contract

Read-only current parse_source on the exact InventoryList and Overlay bytes gives
mechanisms=[] for both. InventoryList has ArkTS `List(){...}` followed by the
`.divider(...)` modifier. Its file summary names that operation, but current method
operation evidence does not express this modifier call. A file hint cannot be
upgraded to a current-digest method certificate by copying it into every method.
This adapter observation is not an additional public failure or architectural
qualification; actual public results above are recorded separately.

A bounded possible future contract would suppress only weak priority0 log-to-code
owner promotion after an unquoted, nonconflicting, single code-operation request
has an already selected source-bound typed method witness. Strong event identity,
explicit log owner, independently recalled wiki owner, multi-target and unknown
requests would preserve old behavior; all log_anchors/path data would remain.
This is a proposed new restricted permission, not an existing violated contract.
Current divider source lacks that method witness, so this proposal cannot be
implemented by merely lowering weak-log's two-marker guard. Independent actual
Development evidence and positive/quoted/real-log controls are required before any
implementation. Global ArkTS language-only splitting and startup exceptions remain
rejected. There is no code repair or new original gain in this stage; count remains20.

## Saved artifacts

protocol.json binds the original case/governance. before-original.json is the actual
single-group result; public.json and trace.json preserve actual query returns and
exclusion arguments/results. admission-summary.json is an explicitly labeled saved-
input replay. source-operation-observation.json is offline current adapter evidence.
No original source/query was altered or padded to obtain a red.
