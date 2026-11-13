# Member callback lexical admission: narrow accepted contract

Baseline: 134cfcb. Independent public freeze was committed before implementation
in 2cd511a. `callback-lexical-before.json` and `callback-red.txt` record the false
GuidePanel.onClick entity from a quoted example/comment. LivePanel is the real
control. Public init/learn-path/list/context now rejects that false entity while
retaining the real callback and original source lines.

Only member `.onX(...)` extraction changes. Equal-position admission masking
uses the existing quote/comment scanner after making simple template literals
opaque. Original newline positions are restored, including block comments.
Property callbacks, other callable parsing and global scanner are unchanged.

This is NOT a full ECMAScript lexer. Any non-comment slash, interpolated template,
unterminated quote/comment/template or oversized template makes admission unknown
and preserves the entire file's original member callback algorithm. This retains
real callbacks in interpolation and after regex/division; it also deliberately
retains prior false callbacks in those uncertain files. No absence certificate is
produced. Legacy implementation is frozen in legacy-ecma-callable-ranges.py.txt
for exact dictionary regression comparison without requiring a Git checkout.

## Rejected iterations retained

The first broader patch changed property multiplicity: 65 related tests had seven
failures. The property implementation and existing tests were restored verbatim;
no historical multiplicity expectation was edited. Initial property/suffix tests
are archived as withdrawn, not successful contracts.

Overlaying template masking after code_mask lost real callbacks following nested
template quotes/comments. Review also found regex quote/backtick contamination.
review-regressions-red.txt freezes nine failing checks before correction. Rather
than build a new regex/parser, the final implementation treats all uncertain files
transactionally as legacy. The earlier assumption that executable interpolation
could be discarded was rejected; withdrawn-interpolation-mask-tests.py.txt keeps
that incorrect experimental expectation, not an accepted test. Both real and
nested literal interpolation now require exact legacy output.

regex-existing-gap.json records a baseline regex-contained false callback. It is
not fixed or represented as safe syntax by this change.

## Focused results

- 66 related tests pass, including independent public red-to-green, strings,
  comments, simple templates, multiline handlers, original line ranges, real
  property callback controls and exact unknown-file legacy output.
- Existing 3 scenarios / 9 variants: 4 pass, 5 fail both before and after.
  command-binding 1/3; fallback-recovery 2/3; cross-component-preview 1/3.
  No original failure reduction is claimed. No full acceptance run was performed.
- Source file limits and Python compilation checked separately before commit.
