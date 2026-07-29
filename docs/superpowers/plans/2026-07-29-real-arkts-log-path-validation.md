# Real ArkTS Log-Path External Validation

## Goal

Measure whether the frozen Context Provider can recover useful code ownership,
source spans, and bounded logger-wrapper paths from real ArkTS runtime-log text.
The Runtime supplies evidence; the Agent remains responsible for comparing it
with temporary logs and selecting an executed path.

## Frozen Baseline

- Runtime commit: `56cac1b`.
- External project: `azhu003/localsend-harmony` at reviewed head
  `ef7151ba27e317dac76ccb73474de12e1f540e82`.
- The project was not used by earlier development fixtures or sealed holdouts.
- Three cases use source-reviewed pre-fix revisions and real business log calls.
- Sealed pack digest:
  `11bb5d370bc7b9b62c4e16c5faf76925933f420e4ec812871e9c8f6af573cdc7`.
- Raw runtime logs are not stored; only reviewed static message fragments and
  source/path Oracles are present.

## Case Coverage

1. Small-file upload failure: `WebClient.upload -> logger.warn -> hilog.warn`.
2. Registration response with missing hostname:
   `WebClient.register -> logger.info -> hilog.info`.
3. Concurrent receive write failure:
   `FlushService.process -> logger.debug -> hilog.debug`.

Each scenario has a short runtime-line query and a longer symptom-context query.
The Oracle requires the outer code owner, current source span, evidence class,
ordered wrapper locations, complete allowed path set, and no hidden truncation.

## Immutable First Observation

The sealed pack was executed exactly once. It passes 0/6 variants:

- anchor recall: 0.5;
- candidate file Recall@20: 0.3333;
- anchor precision: 0.25;
- source excerpt/span recall: 0.5;
- log-path recall: 0.5;
- log-path precision: 0.25;
- average compact Context: 1,459.1667 Tokens;
- average query time: 819.3333 ms;
- no path reported truncation.

The aggregate score hides useful distinctions:

- registration locates the correct code owner and source span in both phrasings,
  but the compact wrapper path does not match the reviewed path;
- exact upload and write-error queries recover the reviewed path but retain one
  additional path, producing 0.5 path precision;
- longer symptom wording loses upload and write-error code ownership even when
  a relevant log path remains available;
- one upload symptom Context reaches 1,537 Tokens and violates the budget.

This project and pack are consumed. They must not be rerun, modified, or used
to select project words, ranking weights, or thresholds.

## Failure Model

The observation supports architecture-level reproduction, not a project-specific
fix. The next development fixtures must independently isolate:

1. **Template identity**: a runtime line contains variable values while the
   learned source contains static literal segments and placeholders.
2. **Competing event identity**: two logs share domain/error tokens but only one
   static event and wrapper path matches the observed line.
3. **Nested ownership and import provenance**: a log call inside a Promise or
   callback must remain owned by its enclosing callable and bind to the imported
   logger module rather than a same-method logger implementation.
4. **Query dilution**: adding symptom terms must not demote a high-entropy log
   fragment already present in the query.
5. **Budget integrity**: redundant logs and excerpts must be removed before a
   required event, owner, source span, or truncation signal.

## Long-Term Architecture Direction

Introduce no new public command or Skill. Evolve the existing learning and
Context ports in independent development fixtures:

- derive a language-neutral `LogEventIdentity` from level, logger/tag, ordered
  static literal segments, placeholder skeleton, caller, and source digest;
- rank event identity by exact skeleton, distinctive contiguous literal segment,
  then broad lexical evidence, with explicit confidence and broad fallback;
- group all bounded paths under the selected event identity before compact
  budgeting, preserving legitimate polymorphic paths without mixing events;
- retain enclosing callable ownership for nested callbacks and use import/source
  provenance before global qualified-name fallback;
- align code anchors and source excerpts only after event identity selection;
- expose ambiguity and truncation instead of choosing an executed path.

The event identity is a derived retrieval projection, not a runtime incident,
root cause, or persisted user log.

## Promotion Gates

1. Independent development reproductions fail before implementation and pass
   after the architecture change.
2. The measured 68-scenario/204-variant baseline has no changed checks or new
   regressions; historical baseline failures remain a separate workstream.
3. Query diversity, source-range, semantic graph, incremental freshness, and
   million-scale gates remain within their existing bounds.
4. A different, previously unused ArkTS project is reviewed and sealed.
5. That new project is executed once; LocalSend is never rerun.
6. Agent A/B starts only after the system Context gate supplies stable evidence.

## References

- OpenTelemetry Logs Data Model: stable separation of body, severity, event,
  resource, scope, and attributes.
- GitHub CodeQL path queries: explicit source, sink, step, and path explanations.
- BEIR and TREC: separate candidate recall from final ranking and evaluate on
  held-out queries rather than tuning the observation set.

## Implementation Outcome

The query Runtime now derives a language-neutral event identity from a log
template and selects exact static templates or distinctive dynamic literal
segments before compact path budgeting. It preserves broad fallback for short
generic terms and keeps all bounded paths belonging to the selected event.

Two independent ArkTS scenarios cover dynamic values, a competing event,
nested Promise ownership, aliased imports, and a same-method shadow logger. All
6 variants pass with anchor, source-span, and log-path recall/precision of 1.0.
Scenario-only source is supplied through bounded `fixture_group` overlays so a
new fixture cannot change the common FTS corpus. Against Runtime `56cac1b`, all
204 common variants have identical failed-check sets and zero regressions; the
expanded pack passes 141/210 versus the measured baseline 135/204. The 69
historical failures are not attributed to or repaired by this change.
