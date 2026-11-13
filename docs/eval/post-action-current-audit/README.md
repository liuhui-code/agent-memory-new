# Post-action refresh: current first loss and fixed independent control

Base bc92352 (runtime equivalent to production 8ce567b). Only the selected original
Development group and four independently frozen public queries were run. No runtime
or test changes, no full gate, no new original failure count.

## Current original result

The three original variants remain 2/3. English paraphrase retains the required
LightingStore but also InteractionState and CommandOutputPage; precision is 1/3.
The oracle source-span check passes because it tests overlap. It does NOT prove
full required source: compact LightingStore source_range/read_window is 1–13 but
its actual current-worktree excerpt is 1–9, truncated=true, missing required lines
10–13. The excerpt ends at the refreshState signature, without its body. Budget
1479/1500 and output_budget.truncated=false do not imply complete excerpts.

Current selector trace chooses LightingStore via structural focus, then salient
supplementation adds the other two sources. Separately, callable localization ranks
DraftPage.reloadPreview primary (34.735), a path absent from selected raw anchors.
Both raw and compact retain that callable primary. This is the same alignment gap
as the prior diagnosis, not a newly discovered call-edge or lexical producer bug.
summary.json retains exact primary/anchor/range/budget fields.

## Recovery contract is not an invitation to invent a source

For multiple anchors, recover_partial_primary requires exactly one existing primary
anchor matching callable primary file/symbol/exact range. The DraftPage path occurs
zero times, so it returns the original payload before source opening. It must not
substitute a guessed primary, fabricate JSON provenance, or read an unselected path.
The established private source-row binding, same bounded read/digest verification,
2 MiB verification cap, total-source caps, 1500 budget and rank-only trade remain
unchanged. Correctly abstaining here is not evidence that the consumer implementation
violates its current contract. It leaves both precision and source completeness
unsolved for this case.

## One independent experiment, frozen then stopped

c97faa3 froze all source bytes, four queries, required/forbidden owners, literal
source fragments and stop rule before any independent public execution. It uses
FanStateStore for dispatch/reload, a real NotePreviewPage refresh, CommandReceiptPage
and PointerSelection. Public init/learn/raw context/compact context were saved.

All four meet their frozen oracle. Generic raw contains Store + Receipt + Preview,
but its primary is the correct FanStateStore.reloadStatus and belongs to raw anchors.
Compact selects Store alone, with dispatch and reload bodies intact, within budget.
The explicit owner/preview/multiple-owner controls also keep primary in raw anchors.
Extra paths on two recall-only controls are reported, not retroactively made failures.
See independent/alignment-summary.json; do not equate recall controls with precision.

Thus this fixture does NOT reproduce the original absent-primary condition. No extra
noise, name change, query reformulation or ranking adjustment was added to force it.
No same-layer independent red supports a recovery/selection patch. A further design
would first need a bounded, preregistered alignment authority contract and an actual
independent violating example, not merely 'pick the first anchor'. This stage stops
at the frozen limit; it does not declare other residual categories blocked or task
completion. The original precision and missing-body problems remain open.

## Verification

The wrappers observe selection/rank results without replacing return values. Actual
public selected paths agree with the original single-group result. The two existing
rank-trade regression modules passed 12 targeted contract checks (related.txt);
fingerprint verification also passed.
No whole-file operation hints were promoted to callable proof and no rejected veto
or threshold experiment was revived.
