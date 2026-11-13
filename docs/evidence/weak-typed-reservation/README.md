# Preserve existing anchors for explicitly weak uncertain type matches

Base ea5e486, the separately accepted raw symbol identity stage. This stage uses the exact same fb6436e source and query, byte-copied into protocol.json and frozen with tests at e6226dd. No producer, lexical match, ranking, receiver-flow proof, query classification or budget changes.

## Public red and narrow permission fix

After the raw fix, code anchors already include CommentOnly.forward3–6 and the actually required Direct.forward10–12. Callable evidence still selects CommentOnly with typed_contract_match=true, typed_contract_weak=true and certainty=uncertain. This is deliberately weak lexical evidence, not a receiver certificate. The old uncertain branch calls reserve_uncertain_primary and replaces all same-path ranges with CommentOnly's range; therefore compact loses Direct.

New behavior applies only when certainty is exactly `uncertain`, weak is the boolean `True`, no path scope is activated, and the primary's valid complete range is already contained in a valid same-path existing anchor: preserve the original anchors rather than perform this reservation. Missing/partial/invalid primary coverage still invokes the old reservation. Strong typed matches, missing/malformed weak flags, missing/unknown certainty, activated incomplete paths and exclusive complete paths retain their old behavior. The existing bounded branch is untouched. This is not a general competing-source veto or a new rule for all uncertain evidence.

Two formal red tests (public missing required range and direct consumer replacement) became green. Path/strong/legacy controls passed before and after. Review added exact-boolean, unknown-certainty and actual source-content/budget controls; initial protocol/query/source remains unchanged.

## Actual outcome and limits

- Same-file compact now retains both source ranges and includes the real `target.rejected('bad payload')` source line. Actual compact output is 1068 estimated tokens against1500, untruncated. Cross-file real source remains retained.
- Primary is STILL CommentOnly and certainty STILL uncertain. This fixes evidence retention, not ranking, unique-owner selection, dataflow or the original generic listener failure.
- before.json is the final public output saved at raw-stage ea5e486, not a retrospectively modified baseline. after.json reruns the identical public inputs on this stage.
- Four new focused tests pass. Final related set:55 tests,54 pass and one existing expected failure in the preserved generic-log caller expectation.
- The existing independent native-listener five controls were rerun on both ea5e486 and candidate: four pass and generic bind/contract remains failed on both. This includes ordinary literal-text and explicit parameter controls; their queries/source were not changed. Review correctly found that this old literal query does NOT activate the weak-typed branch (weak is absent, certainty bounded), so it is not coverage for changed literal authority.
- Separately frozen at06e0c9a before execution: NoticeFactory.create really returns 'NoticeToken', queried as a string literal NoticeToken. Both baseline and candidate actually enter typed_contract_weak=True / certainty=uncertain and preserve the real return source; literal-before-after.json records both. This supplements, not rewrites, the earlier protocol.
- Original native-listener and causal-profile-path targeted groups remain2/3 and3/3 respectively. No full gate or original failure-count improvement is claimed.

No index refresh is required for this query-time consumer change. No source schema, source identity or permissions are newly certified.

## Review-discovered compatibility regression and correction

The first candidate skipped weak reservation even when primary was not already represented. Besides a direct compatibility probe, the existing unchanged supported query `Find the callable that accepts ResultListener and invokes onFailure on that parameter.` exposed an actual public regression: baseline raw has onFailure12–14, and old compact reservation correctly adds attach7–16; the first candidate only kept12–14. The failed candidate is preserved as native-operation-preservation.json, not relabeled a pass.

The final guard requires full existing primary range coverage using the existing strict valid_retained_range (positive non-bool integer bounds). Partial inner callback, missing path or invalid bounds keep the old insertion responsibility. native-operation-final.json compares baseline and corrected candidate; both retain attach7–16. No query, source or budget was changed to address this failure.
