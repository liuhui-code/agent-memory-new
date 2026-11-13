# Callable-local async ordering evidence repair

Base 43921fc, independent clone. Existing context-async-navigation-state-owner
confirmed 1/3 before implementation. Independent competing sources/queries frozen
in 13785c7; first public failures preserved in 99ce95d.

TabReader.select owns an async read, local-versus-instance request guard and state
assignment; EntryWriter performs an async write without guard; TabIndicator only
sets request state. Existing source-level behavior has orderingguard, but bounded
callable evidence omitted it. The query already requests this existing marker.

Minimal change: reuse ASYNC_ORDER_GUARD_RE inside the existing non-code-masked,
ECMA-only, nested-scope/regex-ambiguous-abstaining method evidence path, and require
async/await in that same callable. No vocabulary, ranking weight, evaluator or
schema change. The marker certifies only recognized comparison syntax plus an
async boundary, not correctness of cancellation, latest-wins logic or causality.

Independent Chinese owner query now returns only TabReader with full lines 4–11
in both .ts and .ets. Explicit writer controls remain correct. The frozen English
query STILL FAILS and is retained as an explicit expectedFailure. Original frozen
acceptance was not relaxed or reworded.

46 focused/related tests: 45 pass, 1 expected failure. Controls exclude synchronous
guards, unguarded async methods, comments, strings, nested callbacks, ambiguous
regex and unsupported language. Relevant lifecycle and behavior tests pass.
Module 94 lines, diff whitespace check passes. No full suite/performance gate or
full 231 evaluation.

Existing three variants improve 1/3 to 2/3: zh-noise fixed, en-paraphrase unchanged
pass, original still fails due extra DownloadsPage anchor. This is one verified
original failure improvement, NOT a fresh aggregate total or external validity.
