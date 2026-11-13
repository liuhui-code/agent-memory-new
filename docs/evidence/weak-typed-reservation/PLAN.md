# Weak typed reservation consumer stage

Base ea5e486 includes the separately delivered raw identity fix. No source/query changes: original frozen samefile protocol fb6436e is copied byte-for-byte. Raw now has Direct.forward10–12, but compact uncertain weak primary CommentOnly.forward3–6 reserves the same path and discards the target range. This stage tests only no-activated-path, uncertain, explicitly weak typed match behavior. The existing docstring limits narrowing to bounded evidence, and typed operation/literal matches deliberately have weak authority.

Proposed minimum: leave existing anchors untouched for uncertain explicitly weak typed matches when no path is activated. Keep path-activated reservation, exclusive-path safeguards, strong/missing-weak legacy reservation, bounded behavior, ordering and all budgets unchanged. No declaration/receiver/flow authority is added, and no weak score/ranking is altered. Crossfile controls retain both, true explicit pair remains retained. Unknown old metadata is not reinterpreted as weak.

Freeze focused negative and positive controls before runtime modification; formal public red must preserve the exact original query/source and assert the required actual operation range10–12 remains in compact. If some later layer still loses it, report that separately instead of expanding this patch.
