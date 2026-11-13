# Cache callable evidence experiment: public closure not achieved

Baseline a6c1d93. This follows the old 85534be investigation without pretending
that real FIFO eviction is absent or enabling a timestamp-only uniqueness rule.

## Frozen independent evidence

73af349 commits the independent protocol, original baseline and public red before
runtime modification. Sources include direct timestamp scan/delete ExpiryStore,
genuine first-key FIFO ArrivalPool, text-only CacheMonitor, same-file split inspect
and remove methods, deferred nested operations, and ordinary removal. Two generic
executable/timestamp queries select only the monitor's descriptive string. Explicit
FIFO and monitor queries are positive controls, not entities to be excluded.

The experiment adds the existing CACHE_SIZE + for-of + delete + CACHE_AGE conjunction
to method evidence only, behind the reviewed lexical mask and controlled-body scope.
It does not add source-operation roles, prove data flow, infer policy correctness,
assert FIFO absent, or alter selection/ranking weights. String, split and nested
controls do not receive the added hint. File-level cacheeviction is only a coarse
retrieval hint, not a previously guaranteed method/data-flow certificate.

## Actual outcome and first remaining layer

The focused producer regression becomes green. Public acceptance remains red:
both frozen queries still return CacheMonitor alone. For the first query, the
candidate does improve ExpiryStore.trim into the raw callable alternatives, scoring
17.29 versus monitor 34.0; raw code anchors retain its correct 3..14 bounds. Its
method evidence really contains cacheeviction. Localizer represents its guard
mechanism window at 3..6 while monitor's string matches remain primary. For the
second query the analogous scores are 13.57 versus 22.11. These observations are
not a reason to tune weights or alter frozen expectations.

Both explicit FIFO and monitor controls remain correct. Original bounded-cache
three variants stay 2/3, with identical average token count; no original acceptance
gain. Unit success is not public closure: candidate.txt explicitly retains the
public failure. No full test gate was run.

## Disposition

The experimental runtime change is reverted to a6c1d93. rejected-hint.patch and
frozen-tests.py.txt retain the attempted implementation and unchanged public red
expectations. The latter is archived, not represented as an accepted active test:
the entire serving candidate was rejected. No serving changes in final HEAD.

The actionable missing piece is source-versus-description localization authority
for already recalled callables, with genuine FIFO and explicit textual targets
preserved. A plain marker cannot provide that authority. Any later contract must
separately support timestamp-specific requests without globally erasing valid FIFO
or treating unsupported operation families as absent. It should address both
frozen public reds and retain the explicit positive controls before integration.
