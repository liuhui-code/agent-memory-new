# Evidence Funnel Generalization Plan

## Goal

Repair project-neutral Context supply only where independent development fixtures prove
that a relevant file reaches bounded retrieval but its callable, primary evidence, source
passage, or stable log event is lost before `query_handoff`.

The Runtime remains a context provider. It does not infer a root cause or choose a real
runtime path for the Agent.

## Evidence Boundary

- The consumed AGenUI holdout supplies only failure classes: callable loss, primary
  evidence loss, passage loss, and missing static log evidence.
- Development fixtures use unrelated names, paths, domains, event markers, and source.
- No AGenUI result, threshold, file name, or phrase may enter ranking features.
- A fix is allowed only after the defect is visible in final `context --compact` output.

## Architecture

```text
bounded FTS candidates
  -> diverse files
  -> file-local callable candidates
  -> typed late evidence interaction
  -> primary + alternatives
  -> compact code/log anchors
  -> bounded current-source passages
```

The long-term contract has three replaceable ports:

1. `HierarchicalLocalizerPort` owns bounded file/callable/range candidates.
2. Callable evidence projects typed primary and alternative source locations; it must
   not silently become a diagnosis.
3. The language semantic adapter resolves log receiver bindings to a normalized log API
   identity. The extractor consumes that identity instead of adding project logger names.

This follows heterogeneous two-stage retrieval: robust broad recall first, bounded
interaction/reranking second. BEIR reports stronger zero-shot performance from reranking
and late-interaction systems, with an explicit efficiency tradeoff. ColBERT provides the
late-interaction model; this project uses deterministic lexical and typed-field interaction
instead of adding a neural model or vector store.

For ArkTS/TypeScript, receiver resolution follows compiler symbol binding. TypeScript's
Compiler API represents entities as type-checker symbols, including imported bindings;
the MVP implements a bounded import-alias adapter while preserving the language-neutral
normalized log model.

Log evidence keeps stable event identity separate from display body and runtime values,
matching the OpenTelemetry Logs Data Model distinction between `EventName`, `Body`, and
attributes. No temporary user log is persisted.

## Phases

### Phase 1: Independent red baselines

- Add isolated async-listener, deferred-measurement, and aliased-log fixtures.
- Assert candidate-file, callable, final-anchor, source-span, and static-log stages
  independently.
- Run only the new development scenarios and retain the first-loss report.
- Stop if the final public output already passes or the failure is evaluator-only.

### Phase 2: Existing-contract repair

- Prefer changes inside existing localization, callable evidence, compact anchor, and
  semantic adapter boundaries.
- Preserve fixed pools, per-file caps, compact Token budget, SQLite query bounds, and
  current-source freshness checks.
- Do not introduce a new database, daemon, model call, or project-specific receiver.

### Phase 3: Verification

- Run focused extractor/localizer/compact tests.
- Run all new query variants and compare shared development cases for regressions.
- Run the complete classified development gate, scale/query-plan gate, Python compile,
  JSON validation, diff check, four-Skill check, and 500-line check.
- Do not rerun AGenUI or any consumed holdout.

### Phase 4: External evidence

- Select and source-review a new independent ArkTS project only after development and
  scale gates pass.
- Freeze Runtime, seal before execution, and run once.
- Agent A/B remains blocked unless the new Context gate passes.

## Stop Rules

- Stop when only a specific project name, source path, logger receiver, or query phrase
  improves the result.
- Stop when two independent failures do not support a shared missing contract.
- Stop when candidate-file recall is absent but the proposed change only affects final
  ranking.
- Stop when a wider pool or arbitrary file prefix is the only way to pass.

## Primary References

- BEIR: https://arxiv.org/abs/2104.08663
- ColBERT: https://arxiv.org/abs/2004.12832
- TypeScript Compiler API: https://github.com/microsoft/TypeScript/wiki/Using-the-Compiler-API
- OpenTelemetry Logs Data Model: https://opentelemetry.io/docs/specs/otel/logs/data-model/
- OpenTelemetry event conventions: https://opentelemetry.io/docs/specs/semconv/general/events/

## Execution Result

- The first isolated run passed 3/9 variants. Candidate-file, localizer-file,
  callable, and range recall were all 1.0; six variants first lost the target at
  `evidence_primary`. The aliased sink produced no static log path.
- The existing positive-query contract now applies to hierarchical callable ranking,
  including upstream direct-score isolation when exclusion clauses were removed.
- Owner profiles now represent adapter, boundary, and policy roles. Explicit owner-role
  matches are a typed ranking signal, and unique typed matches use the same bounded
  certainty contract in compact projection.
- The log API catalog resolves bounded ECMA named/default import aliases to canonical
  receivers before the existing scanner and wrapper graph run.
- One development Oracle was corrected after source review: the nested owner is
  `onAreaChange`, not `build`, and the requested wrapper is an expected file. The broad
  measurement case retains Top-2, forbidden-file, and source-span gates but does not
  require all four intentionally diverse compact anchors to be the same file.
- The final isolated gate passes 9/9 variants and 3/3 stable scenarios. Anchor recall,
  primary recall, MRR, source excerpt/span recall, log-path recall, and log-path precision
  are 1.0; average compact size is 1,333.5556 Tokens.
- The CI scale profile passes latency, query plans, and incremental maintenance. Callable
  pool P95 is 7.336 ms and one-hop owner P95 is 8.026 ms against 150 ms SLOs.
- Six affected pre-existing scenarios were run against both frozen Runtime `b26de18` and
  the repaired Runtime. Both runs pass 16/18 variants, with the same two Chinese-noise
  variants and the same individual checks failing. The repair therefore introduces no
  observed regression in this bounded comparison; those failures remain baseline debt.
- Seventy-two focused tests pass, including named and default ECMA import-alias contracts.
- The full 75-scenario/225-variant development run produced no result within the
  12-minute bounded window and was terminated. It is not counted as pass or regression
  proof. No consumed holdout was read, changed, or rerun.
