# Property callback lexical admission

Base 9d2dba8. New independent task; this is not automatic reinstatement of the
previously withdrawn broad property experiment.

## Public red and controls

879064f freezes ExampleGuide's pure template phantomHandler and block-comment
execute, plus two real execute callbacks belonging to separate classes in
TwoOwners. Before: SQLite creates ExampleGuide.phantomHandler@3 as a static
function and context certifies it bounded/exact_symbol. The real two callbacks
are present with distinct symbol keys, owners and ranges 2..4 / 7..9.

After that first freeze, MixedOwners was added as an additional frozen control;
the original two sources, query and expectations were not changed. It inserts a
same-name comment between two real class callbacks. `mixed-before.json` uses the
unchanged baseline extractor and proves only PrimaryAction.execute was indexed;
the real SecondaryAction.execute at 12..14 was missing. `after.json` retains both
and removes the fake guide functions. The active public regression checks exact
owner/range/key multiplicity, not just names.

## Minimal implementation and intentional contract updates

Only property_callback_ranges changes. It uses the existing reviewed equal-offset
callback mask for proven ordinary quotes/comments/simple templates, retaining
line positions and handling string delimiters before finding the callback body.
If mask returns unknown (slash/regex/division, interpolation, unterminated or
oversized template), the entire file uses the original property algorithm. Old
false entities in uncertain files remain unresolved; no full lexer is claimed.
Member extraction, global scanners and scoring are unchanged.

The former multiplicity tests explicitly preserved known contaminated counts.
Their expectations now count real bodies: comment/template + one real remains 1;
one real + fake + one real becomes 2; comment-only `other` becomes 0. The public
MixedOwners red independently establishes that retaining the former 1 would
continue losing a real owner. Tests are not removed. Binding's fake-object test
now asserts no callback range and separately supplies the legacy range to assert
it still cannot bind the non-code object. First transitional failures (7 old
count expectations, binding StopIteration, initial public-test None handling)
are retained in first-green-legacy-failures.txt, not represented as success.

## Validation and activation

69 focused tests pass, including public red-to-green, duplicate owners/ranges,
unknown exact legacy behavior, member regressions, existing callback/body/header
and scan-cost tests. Original command-binding is still 1/3 both before and after;
no original failure reduction or full-gate result is claimed.

`upgrade.json` uses exactly the same sources and memory: baseline index -> new
code without relearn -> ordinary learn-path merge. Merely replacing code leaves
old rows intact. Normal learn-path removes old fake guide callbacks and restores
MixedOwners' second real method; no --replace or schema migration is required.
