# Weak log matches must not automatically become behavior owners

Base 17083b2. This branch excludes the unintegrated conditional and joint budget
candidates. Independent competing async owner/unguarded writer/setter plus
Telemetry/RetryPanel logs frozen in 0e0177d; extended controls frozen in 32fe9b7.

## Reproduction and actual failing layer

The original async-navigation failure's DownloadsPage is NOT a salient-code
reintroduction. Its raw anchor source is wrapped_log_caller. It comes from
AttachmentService's unrelated template "attachment download failed after cache
write", matching the query's connective "after". Path context reports
no_strong_log_anchor, yet generic handoff promotion creates the additional code
owner. This statement does not imply weak logs are useless.

Independent Telemetry template "packet buffered after reconnect" and RetryPanel
wrapper reproduce the same weak overlap. The real TabReader fully covers the
requested asyncboundary/orderingguard/statewrite evidence, but the wrapper is
added as another source owner. Existing strong and explicit caller controls pass.

## Narrow admission contract

Leave code_log_matches, log_anchors and path_context untouched. Only the log-to-code
anchor promotion list is filtered, and only when an existing retrieved function
or method covers ALL requested behavior markers (using the existing multi-marker
behavior-focus convention). No new score weight, lexical blacklist or threshold
was tuned. With no complete behavior evidence or with an explicit multiple-target
request, preserve previous behavior.

Preserve log owners with independent wiki path+symbol evidence, a matched event
identity (including known dynamic-template literal segments), explicit caller/
function/path identity, or incomplete owner metadata. Qualified method mentions
are conservative preservation cues, not proof of runtime receiver identity.
No record, log, path or graph edge is deleted or invented. No log match is re-labeled
as diagnosis. This change controls promotion into code owners, not relevance of
underlying log evidence.

## Verification

Independent primary failure now passes in .ts and .ets, with full target lines
4–11. Strong literal, dynamic message with new value ABC, case/punctuation,
explicit caller, combined behavior+strong log, multiple targets, absent behavior,
partial behavior and actual indexed independent owner controls preserve evidence.
All eight .ets public query outputs retain byte-equivalent log_anchors and
path_context. Direct tests prove input lists unchanged; actual raw indexed
wiki.symbol=select and log.function=select exercise owner-tuple preservation.

One preexisting strict generic-log caller expectation still fails: "buffered
packets" returned only Telemetry both before and after. Its original expectation
is kept as expectedFailure, while the conservation test verifies the unchanged
emitter result. The separate opaque dynamic-template compact failure also remains.
42 related tests: 40 pass, 2 explicitly expected failures. Red public tests on base
handoff fail for the weak-wrapper case in both suffixes. No blanket all-green claim.

Original context-async-navigation-state-owner improves 2/3 to 3/3; final rerun
recorded separately. This closes one additional original variant, not a freshly
measured aggregate 231 score. No full suite, full 231 or external validation.
Runtime files remain below 500 lines; diff whitespace check passes.
