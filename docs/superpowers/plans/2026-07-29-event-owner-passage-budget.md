# Event Owner Passage and Deterministic Context Budget

## Goal

When an Agent supplies a distinctive runtime log line, the Runtime should return the
learned static event template, its emitting source passage, and bounded supporting
context. It must not require runtime-only placeholder values to exist in source, and
the final compact JSON must stay within 1,500 estimated Tokens.

This remains context supply. The Runtime does not ingest the user's temporary log,
select a root cause, or decide which candidate path actually executed.

## Industry basis

- [OpenTelemetry Logs Data Model](https://opentelemetry.io/docs/specs/otel/logs/data-model/)
  separates stable event identity and attributes from an occurrence-varying body.
  The evaluation contract therefore distinguishes stable source-template literals
  from runtime-observed terms.
- [OpenTelemetry event semantic conventions](https://opentelemetry.io/docs/specs/semconv/general/events/)
  treat an event name as a stable identity and occurrence data as attributes. The
  local `LogEventIdentity` projection follows that boundary without adopting an OTel
  storage dependency.
- [BEIR](https://arxiv.org/abs/2104.08663) supports robust first-stage lexical
  retrieval followed by a more precise reranking stage. Here candidate retrieval
  remains broad, while the selected event owner becomes a high-confidence passage
  seed before lexical fallback.
- [RECOMP](https://arxiv.org/abs/2310.04408) supports selective and extractive context
  compression. Compact budgeting therefore removes or shrinks optional evidence in
  deterministic value order while retaining the selected event owner.

## Architecture

```text
query/runtime line
  -> broad FTS/code/log candidate retrieval
  -> LogEventIdentity selection
  -> EventOwnerPassageSeed(file, function, line)
  -> owner passage first; mechanism/query passages as fallback
  -> compact evidence composition
  -> deterministic final-serialization budget
  -> Agent CLI compares supplied context with the real log stream
```

The implementation uses two narrow modules:

- `context_event_owner.py`: converts only a high-confidence selected event into a
  bounded owner range. It does not rank unrelated code or expand the graph.
- `context_budget.py`: owns compact reductions and final estimate convergence. It
  preserves source-excerpt accounting and is independent of retrieval logic.

## Contracts

### Source passage

1. Exact static templates or distinctive dynamic-template literals may seed an owner.
2. A matching callable range is preferred; otherwise the learned emitting line gets a
   bounded radius.
3. Owner-seeded ranges sort before mechanism and query-term ranges and are not
   redirected by symptom words.
4. Weak or generic log matches keep the existing broad fallback.

### Evaluation

- `required_log_template_literals`: gated stable text expected in learned source logs.
- `runtime_observed_terms`: informational values from one runtime occurrence; copied
  to the result for audit but never matched against source.
- `required_log_keywords`: backward-compatible legacy gate for existing packs.

Consumed sealed packs are immutable. A flawed legacy Oracle remains historical
evidence and is not rewritten under the new schema.

### Budget

1. Compose bounded evidence.
2. Add sufficiency and output-budget metadata.
3. Estimate the final serialized object with the same estimator used by evaluation.
4. If over budget, remove optional follow-ups, trim lower-value excerpts, then trim
   owner excerpts around their focus line; keep deterministic ordering.
5. Iterate the self-reported estimate until it equals the final payload estimate.

## Execution phases

1. Add failing unit cases for owner passage, final estimate accuracy, and schema split.
2. Add isolated ArkTS fixture groups so new cases cannot alter shared BM25 statistics.
3. Implement owner passage binding and budget ownership behind existing compact entry.
4. Run focused tests and six independent query variants.
5. Differential-check every common development variant against the pre-change result.
6. Run scale, privacy, syntax, whitespace, four-Skill, and 500-line gates.
7. Record results without rerunning consumed LocalSend or OHOTP packs.

## Promotion rule

Development fixtures can close regression classes but cannot prove external
generalization. A future release claim requires a new, previously unused ArkTS project
with reviewed stable-template and runtime-observation fields, sealed before its single
execution. No failed external pack may be tuned or rerun.

## Completion evidence

- Independent owner/budget fixtures: 6/6 variants pass; template, source-span, and
  anchor precision are 1.0; compact output is 1,217–1,278 Tokens.
- Full development differential: 210 common variants have zero newly failed checks;
  22 old budget checks improve and 6 new variants pass. Expanded result is 158/216;
  the two final hard-limit scenarios peak at 1,499 Tokens.
- Focused context, log-path, source-privacy, and fixture tests: 110/110 pass.
- CI scale profile: 100,000 searchable entities and 300,000 graph edges pass latency,
  query-plan, and incremental-maintenance gates.
- Python compilation, JSON, whitespace, four-Skill, and 500-line gates pass.
- Consumed LocalSend and OHOTP packs were not modified or rerun.
