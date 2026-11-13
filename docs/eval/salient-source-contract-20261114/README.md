# Bounded salient-source retention contract

Baseline 17083b2 in an independent clone. No score, recall, source-directory priority,
query vocabulary, log admission, wrapper promotion or source-budget change.

## Contract and plan

Freeze ordinary source competition, a redundant source-string supplement, novel and
explicit literal requests, qualified multi-target requests, same-mechanism distinct
entities, and an ordinary non-opaque log template with its real static wrapper. Compare
both runtime versions, then the two existing scenarios and necessary related regressions.

After the existing method focus and bounded salient shortlist have been selected,
retract a supplement only when all of the following hold:

- A selected symbol already has the existing multi_term_method_evidence proof plus
  valid source bounds and actual method/string evidence fields.
- The supplement is also a bounded symbol with available source fields; its matched
  original salient query evidence adds no term beyond the selected source evidence.
- It is not a graph neighbor, explicitly requested symbol/owner/path, quoted-literal
  match, or part of an explicitly multiple target scope.

Missing source metadata, file-only/path evidence, novel literals and graph lineage
fail open. Unknown cardinality is not reclassified as single. Already focused entities
are never removed. There is no backfill: final output is a subset of the previous
bounded supplement set, not an opportunity to promote lower-ranked candidates.

This is not deletion of zero-method-coverage evidence. A zero-method novel literal and
explicit same-word literal are retained. It is not deletion of duplicate entities:
multiple naturally requested implementations with identical mechanisms remain present.

## Retained intermediate failures

The first candidate filtered inside the admission loop. It removed the original noise
but backfilled even lower-ranked unrelated source, leaving the old scenario failing.
The final implementation performs a post-selection subset instead; candidate-target.json
and monotone-target.json keep both observations.

Two early unit failures modeled string_evidence as only snapshot_key, omitting the
actual indexed token expansion (snapshot/key). The test data was corrected to the real
index shape; production behavior was not loosened. Actual public indexing corroborates
the final contract. The first regression command hit an existing module import assumption;
PYTHONPATH=tests:. resolves it without changing that test. Both outputs are retained.

## Verified result

- Existing scenarios: **4/6 -> 5/6**. Production-over-example Chinese now passes with
  ThumbnailPool source and required snippet; all three production variants pass.
  Canonical recovery English remains failing under the preserved multiple/graph contract.
- **112 necessary regression tests pass**, including public raw/compact owner+body,
  precise literal plus second source, ordinary-template wrapper/emitter, typed contracts,
  query diversity, and previously repaired owner cases.
- Natural-language comparison of two identical-mechanism stores WITHOUT “both” or
  qualified names preserves both stores in raw and compact outputs, before and after.
- Non-opaque “notice update dispatched” keeps both emitter and static wrapper. Explicit
  quoted literal + qualified second owner also retains both in compact output.
- A generic novel-literal request retains its raw evidence in both versions; its existing
  compact loss is NOT claimed fixed. Some broader fixture queries still include file-only
  noise or existing compact multi-target failures, and remain visible in observations.
- Correct primary source is never replaced by an empty result; public tests assert actual
  source body operations, not merely absence of distractors.
- Compilation, whitespace and changed-file 500-line checks pass. No full gate or holdout.

Raw output hashes and bounded projections are retained beside frozen inputs. Runtime
code hashes identify the final working tree. All new source/log inputs are synthetic
Development fixtures; no user incident logs were fabricated. run*.py copies document
the original experiment directory layout.
