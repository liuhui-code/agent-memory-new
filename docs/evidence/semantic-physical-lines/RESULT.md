# Physical source coordinates in ECMA typed indexing

## Development, not external/generalization acceptance

Baseline remote 59103398, equivalent local d90537ad. Two controlled public CLI
projects establish the mechanism: DocumentStore's normal quoted LS/PS label and
QueuePolicy's template PS label. They are independent minimal Development fixtures,
not external real-world projects and not any old failure group's replacement.
Original query/scoring definitions and all protected old reports are unchanged.

DocumentStore.save is physically lines 3–5. Baseline public raw and compact typed
ranges report 4–6 after an LS/PS in a string; class 1–7 rather than 1–6. QueuePolicy
permits is physically 3–6, baseline compact reports 4–7; class 1–8 rather than 1–7.
Actual file excerpts use CR/LF lines, demonstrating an inconsistent locator, not
an inferred runtime bug. Current ECMAScript permits these separators within string
literals (ECMA-262 String Literals); older engines/ArkTS language conformance are
not asserted. The shared ArkTS parser receives the coordinate correction only.

## Change

Use a small physical_source_lines helper for the typed ECMA parser and TS/TSX/ETS
method evidence slicing. CRLF and bare CR retain prior universal-newline handling;
raw-byte digests stay unchanged. Other-language evidence slicing stays unchanged.
Legacy callable-envelope expansion explicitly declines extra splitlines separators
because its existing expanded_from readers do not share physical slicing. Ordinary
source excerpts remain available. No lexer eligibility, role ranking, query parser,
output budget, score, source body, or source digest was altered.

## Results

- Three tests initially pass, including 18 parser combinations (three separators,
  three newline forms, trailing newline present/absent) and two actual public CLI
  LS/PS learn/context cycles. Together with existing targeted suites and the new
  prefix/envelope negative case, 38 unittest methods pass (focused-final-38.log).
- Three archived old databases copied and merged with unchanged source bytes:
  old LS/PS 4–6 becomes 3–5 at generation 2; space stays 3–5. Digests unchanged.
  Installation alone does not rewrite an old index; explicit normal learn-path
  refresh is needed. No new schema or adapter-version requirement was introduced.
- Exploratory body/template/comment cases preserve correct physical save ranges.
  A second member after LS on the same physical line remains unlocated, not falsely
  given a typed range. These are parser boundaries, not runtime causal claims.
- The independent QueuePolicy baseline/candidate CLI confirms 4–7 → 3–6, with
  the original guard/source bytes preserved. No original group is closed by this
  independent source-location fix; 13/32/default tradeoffs remain unresolved.

## Reproduction and retained evidence

run.py and FREEZE.json capture the initial baseline. Do not overwrite their results
by running them on a new version. independent.py selects baseline-runtime/tools
and the candidate repo sibling. baseline-runtime was made via git archive d90537ad
for tools only. upgrade.py copies each archived baseline memory directory before
refresh. The JSON/stderr/log files are exact outputs; absolute scratch paths are
execution provenance, not portable required paths. Unit tests are portable.

No full acceptance suite or consumed holdout was executed.
