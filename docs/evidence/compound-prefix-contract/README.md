# Compound prefix qualification on 14663ac

No production change. Independent Development qualification, not a holdout or a
new original failure repair. Sources/queries were frozen in b49fe9c, with a
pre-execution multiple-source control and runner in bbe83d2. No query/source/oracle
was changed after observing output. Four raw and four compact invocations completed.

## Mechanism is explicit, not a missing word-boundary check

`salient_query_tokens` emits ordinary word tokens and also retains punctuation
compounds. `source_matches` and `apply_salience_score` tokenize source evidence
into words, then use the explicitly symmetric `prefix_match`: length below3 is
exact, otherwise either side may start with the other. Therefore a whole
`system-bar` term can match source token `system`. This is not equality checking
that accidentally omitted a boundary. Current docs/runtime.md deliberately
supports prefix recall to compound identifiers, though that broad recall contract
does not automatically justify representing a whole compound as novel evidence.

The internal fixed matrix demonstrates this asymmetry: buffer-full matches source
buffer, buffer full and buffer-full, but not raw bufferFull (ordinary tokenize
casefolds rather than CamelCase-splits here). bu does not match buffer; buffer
matches buffering. Chinese 缓存-满 does not match two-character 缓存 because the
short-token exact rule applies. These are internal observations, not public tests
or proof that all these semantics are desirable.

## Saved native-color contribution, explicitly historical

The readable a6c1d93 trace first selects parseNativeColor, then graph imports add
FacetRecord. Salient supplementation adds MessageActionBar with missing method
provenance and ClipboardContentReader whose sole source match is system-bar via
system. Its real method evidence includes getSystemPasteboard expansion; it has
no system-bar source literal. The matched term is novel relative to the focused
source and the guard retains it. This is a demonstrated historical salience
contribution, not a new 14663ac original score or proof that it alone causes the
remaining final failure. Current code hashes and the saved trace hash are retained.

## One independent public qualification attempt

All three sources directly compare different real literals; required ownership
is grounded in those equality expressions, not source names or inferred causality.
The proposed exclusive-source-set condition is tracked separately from required
retention; it is not silently promoted to an existing runtime guarantee.

|fixed query|compact sources|required retention|exact set proposal|tokens|
|---|---|---|---|---|
|buffer-full literal|BufferNote|FAIL: CapacityGuard missing|fail|1064|
|buffer literal|BufferNote|pass|pass|1061|
|buffer-empty literal|BufferNote, EmptyGuard|pass|fail|1210|
|both full and empty literals|EmptyGuard|FAIL: CapacityGuard missing|fail|1052|

Each response is within1500. No literal was renamed, extra source added or query
rephrased to force the desired layer after these results.

The compound failure is real but **not the original28 same-layer qualification**:
raw anchors retain CapacityGuard.check, while callable evidence already prefers
BufferNote.check as bounded (21.14 versus15.92). Compact follows that primary and
removes CapacityGuard. BufferNote also has path/name matches, not only a false
compound salience match. The first observed source disappearance is raw-to-compact;
the wrong primary is already present upstream. No return-only focus trace was
captured here, so this report does not invent a more precise first internal line.
The both-literal case has a composed portfolio yet CapacityGuard is already absent
from raw anchors. That is another layer, not the native-color supplement scenario.

## Decision

Stop this candidate: the fixed attempt identifies literal-target/selection gaps
but does not isolate a correct-focus-then-novel-compound supplement failure.
Changing symmetric prefix matching now would affect scoring and source retention
without a demonstrated same-layer public repair. No native keyword split,
compound-specific exception, weight adjustment, scope broadening or source filter
was applied. An eventual local compound-coverage contract must distinguish broad
prefix recall from a whole-compound novelty claim and preserve genuine prefix,
CamelCase/split forms, literal and multiple-owner behavior. This report does not
supply that contract or authorize treating one fragment as an absence proof.

Twenty existing structural-query/salient-retention/public tests passed unchanged.
No full suite, original group rerun, remote write or CI run. Original repaired count
remains20. Preserve this negative qualification rather than adding noise or another
query until the same hypothesis appears green. This stops only this hypothesis,
not the whole engineering task.
