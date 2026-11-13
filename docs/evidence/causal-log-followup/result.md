# Lossless source-range budget normalization

Baseline: 7850d2a. Development evidence only; no full gate executed.

## Frozen independent defect

`protocol.json` freezes a real exact log emitter and two static callers, plus
single caller, three caller, nested layout and longer exact-log pressure controls.
The original flat and nested fixtures already retained two paths: they are NOT
claimed as independent path-loss reproductions. The independent public defect is
redundant `source_ranges`: a plain symbol/span dictionary repeats all its data in
a richer dictionary on the same anchor. All five layouts reproduced that defect
before implementation (`range-red.txt`). No oracle or budget was changed.

## Minimal change

Before lossy budget reduction, fold only a valid symbol/span range wholly covered
by another range on the SAME anchor. Keep all additional fields. Differing ranges,
reasons, freshness metadata, unknown/invalid bounds remain. JSON-value equality
preserves nested boolean/number distinctions. The richer range occupies the first
covered slot; reverse order also keeps its data. Code anchors, excerpts, logs,
paths and graph uncertainty are not modified by normalization.

Normalization also runs below budget, rather than leaving duplicate metadata in
single-caller results. This does not raise the budget or promise that three paths
or arbitrarily long logs fit. Public controls require real retained path IDs,
never synthesized paths, and the existing strict 1500 token maximum.

## Original single-group result

`context-causal-profile-path`: baseline 1/3, candidate 3/3. The old two failures
were missing ProfilePage in compact path output, despite two raw paths existing.
Deduplicating covered range metadata before source-excerpt reservation avoids
prematurely dropping its alternate path. Existing assertions are unchanged.
This is a targeted result, not an aggregate 231-case result.

## Validation

43 focused tests pass: lossless range/public controls, primary budget, log path
quality, log anchored paths, and source excerpt quality. Additional controls cover
reverse input order, distinct spans, conflicting metadata, invalid bounds, nested
boolean versus integer values, multiple excerpts and retained digest.

The public fixtures remain strict-budget controls, not a general guarantee of
retaining all caller paths when real evidence exceeds available space.
