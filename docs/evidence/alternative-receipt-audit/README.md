# Alternative method receipt audit — 2026-11-14

Baseline 67da8b534baaa6f8d10be004351e827aefc2e0d9. Read-only runtime investigation;
no tools/tests changes, no aggregate evaluation and no original repair-count gain.

## Actual original-query observation

`protocol.json` was written before the single unchanged public context run. A new
archive was initialized and learned through tools/agent_memory.py. `trace.py.txt`
is a return-only profiler; it never substitutes function arguments or results.
Setup is preserved in setup.json; public.json is the actual compact response.

The internal selected collect candidate has ID 403, symbol_key
symbol:fd68059c2833c041126346ce, full method bounds 2–12 and digest
f3b1a6dad256dd3b15547fa2b0450152d828562fe3cfbf5464fd3820ff0de92b.
This is an actual code_symbols row, not the class/file record120 relabeled as a
method. compact_callable drops digest/key but retains ID and bounds;
resolve_candidate_range returns the unique ID403 callable_symbol_range2–12.
compact_candidate subsequently drops ID. There is no private method receipt in
the current handoff-to-compact flow.

The separate excerpt selected_ranges output is collect2–12,
callable_mechanism_window, without any method ID or digest. The class/file anchor
is still SharedRecordCollector1–13, record_ids=[120], record_type=code_file.
The final public excerpt stops at line10 with truncated=true and budget1421/1500.
The callable primary remains recordSuccessfulUse; collect remains alternative.
This observation does not score the case or establish aggregation-owner proof.

## First truncation and proposed smaller buffer alternative

Static inspection of context_source_excerpt.read_excerpt shows that it opens the
source and accumulates lines until adding the next line would exceed char_budget;
it then breaks immediately. Thus selected_ranges already selected2–12, but the
final actual response contains2–10. It is not a mechanism window capped at10.
There is no retained full suffix buffer in this read to reuse after budgeting.
The planning path multi_excerpt_reserve_tokens performs a separate read, not a
same-read receipt. Neither selected source range has candidate ID. Reusing its
text/name as an exact method identity would silently weaken the proposed guard.

A pre-localization method receipt could preserve existing real ID/key/digest/bounds,
but would require an explicit private projection change and same-snapshot bounded
binding. That is feasible data availability, not implementation authorization or
proof that the final reader already has a validated receipt. No guard was removed.

## Frozen independent qualification attempt

`docs/eval/alternative-receipt/protocol.json` and three new temperature-source files
were frozen before their single public init/learn/context run. Hashes are retained
in development-freeze.json. Query and fixture were not tuned after the result.
The fixture tests numeric last-value reduction independently of the retained
shared-record source. The prior exploratory assembly query was not reused or
reclassified.

Result: same-layer qualification NOT established. reduce is indeed a callable
alternative, but its anchor is an exact method code_symbol (ID8,2–12), not the
required class/file anchor. Its excerpt1–13 is complete, truncated=false. The
compact response is1219/1500, truncated=false, with526 excerpt characters.
This is a useful negative qualification, not an acceptance red or a repair.
No extra noise, longer names, query edits or padding were added to chase failure.

## Boundary and next evidence needed

Stop implementation of this extension here: current original trace establishes a
projection identity gap, but the independent public attempt does not reproduce
the required same-layer truncation. A future independently motivated real public
example must establish that class/file anchored selected-alternative truncation
before an extension is implemented. It must not be selected by iterative noise or
query tuning. All existing recovery equality guards remain unchanged. The original
shared-record failure remains open; this finding does not block unrelated work.
