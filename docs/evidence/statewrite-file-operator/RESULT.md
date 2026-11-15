# Final file statewrite operator correction

Independent Development, basee545aea. Original Equality.ets source unchanged. Actual public list code-file before wrongly labels Equality (`===`) and Loose (`==`) as statewrite. Frozen14 sources/3 queries and6 new tests preceded production changes; new test before had12 failed assertions. These are file-summary labels, not semantic edge/callable repairs already shipped separately.

The dedicated private file predicate preserves the exact ASCII field spelling and (=,+=,-=,++,--) family. Only bare '=' rejects immediately following '=' or '>'. Final file statewrite branch uses it; shared STATE_WRITE_RE/statehandoff and collection writes remain unchanged. Actual arrow-function value assignment is still a write; malformed member-followed-arrow text is only a token-boundary unit control, not a valid-program public success.

Known noncode masking remains intact. Unknown lexical syntax still supplies complete raw text but the corrected operator predicate applies to it, so unknown comparison-only false positives may disappear. Unknown fake assignment text can still produce a false hint. No lexical scope, same-owner or execution certificate added.

Public after: only Equality/Loose lose statewrite;7 true write controls retain it and other comparison/string controls remain absent. Actual baseline module comparison proves other markers unchanged for all14 frozen sources. Three compact targets stay equal, with original source bytes retained. Paths/digests remain stable through same-memory activation; installation alone leaves old summaries, ordinary merge rebuilds IDs1–14→15–28, generation1→2 and removes the two false labels.

Live tests from the prior lexical-only stage intentionally expected Equality's then-legacy behavior. Their two expectations are explicitly migrated to the independently proven new operator result. Old protocol, before/after and reported lexical results remain unchanged. This is not an oracle rewrite of the prior run. No other test assertions weakened.

Verification:15 focused compatibility tests pass.83 focused+necessary related tests pass, repeated on final code after correcting an obsolete unknown-fallback comment. No full suite, aggregate gain or original38 rerun. Earlier helper comment claiming complete legacy marker output under unknown source was inaccurate after the operator change; it now correctly states raw fallback with caller operator classification.
