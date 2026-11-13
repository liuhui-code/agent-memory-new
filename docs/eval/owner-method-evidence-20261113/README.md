# Callable-local owner evidence Development repair

## Plan and boundaries

1. Reproduce on fixed d7c156d with independent synthetic TS/ETS classes.
2. Add bounded method evidence, with scalar, writer-only, split-method, comment/string,
   regex-literal and nested-scope negatives. Do not change file weights or query words.
3. Exercise existing public handoff selection; fix only the proven loss/reintroduction layer.
4. Run the selected existing adjacent-collection scenario and related unit/public controls.
5. Preserve staged commits locally for integration. No remote write, full suite, consumed
   holdout, evaluator modification or external generalization claim.

## Stage 1 (715ee21)

The callable index omitted eventboundary and collectionwrite even when source ranges
proved them. Added these two labels to existing hints only for TS/ETS. Non-code is
masked; nested functions/callbacks/object methods/accessors and slash-ambiguous bodies
fail closed for collection-write attribution. This intentionally misses some valid
nested/direct mixed methods; it does not infer callback execution ownership.

Independent compact queries improve, but the existing three-variant scenario remains
1/3: method evidence alone is not a completed fix. `target-result.json` records that.

## Stage 2

`preserve_salient_evidence_candidates` reintroduced lower-coverage neighboring files
following complete callable focus. Preserve prior salience behavior unless the focused
callable covers every requested mechanism (at least two). Under that condition, lower
method coverage alone cannot add another file. Explicit qualified targets are exempt
using the existing exact target matcher, so no project vocabulary or new score is added.

The first candidate missed an explicitly requested second method owner. This was caught
by the parent-requested public control, retained in `multisource-public.txt`, and fixed.
The d7c156d baseline fails that new control, stage 1 passes it, and the initial stage 2
regressed stage 1. The final code restores it. No successful result replaces these failures.

## Verified result

- Final focused run: 68 tests pass, including 12 frozen compact TS/ETS query subcases,
  a public two-owner qualified target query without file paths, scope-negative controls,
  prior salience, method focus and same-owner retention regressions.
- Existing `context-adjacent-collection-owner-precision`: **3/3**, previously 1/3 for
  the evidence-only candidate. Both original and English paraphrase now pass; Chinese
  remains passing. No scenario/oracle/query was altered.
- Compilation and changed-file line limits pass; diff whitespace check passes.
- No full 231-case evaluation or promotion claim. Other failures remain outside this scope.

## Remaining limitation

The separately generated `callable_evidence.primary` still sometimes names the scalar
widget although returned code anchors now correctly select the combined owner. This
is a distinct downstream consistency issue, not silently fixed or claimed by these
commits. `public-observations.json` retains both anchor paths and callable primary.

Raw public call artifacts remain alongside this independent workspace; the tracked
observation projection includes their SHA-256 values, frozen inputs and observed values.
All source inputs here are new synthetic Development fixtures, not user production source.
