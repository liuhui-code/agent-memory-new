# V2 review corrections

Independent review initially rejected three actual probes: spaced/bracket writes
bypassed a narrow this.field counter; shadowed Button remained accepted; nested
detached build methods were mistaken for the owner's UI build. These are now
explicit regressions. The witness rejects bracket access, counts spaced field
references, requires Button/ForEach each occur once in the active lexical source,
and verifies the build brace's direct parent is the exact owning struct brace.

Review also rejected literal-only detection of unknown competitors. The corrected
selection preserves the complete baseline for every unknown lexical source or
nonmatching source containing any array bracket or ForEach. It only skips a known
source lacking this entire initializer/consumer shape, not an unrecognized label.
Template, concatenated and escaped labels are explicit competitor regressions.
These are conservative restrictions of the finite proof, not general runtime
absence, value-flow, event execution or causal correctness claims.

Further independent review rejected property/constructor ForEach substrings and
array-expression suffixes. The final candidate validates the complete build
statement template (only direct ForEach inside zero-argument Row/Column wrappers)
and the complete initializer terminator before the direct build declaration.
Thus `other.ForEach`, `new ForEach`, expression calls, chained `.slice/.map`,
logical operators and newline continuations are unknown and fall back. Bare-this
escapes, duplicate field/build occurrences and wrapper primitive shadowing are
also conservative exclusions. These checks deliberately admit a narrow static
source template and do not claim arbitrary TypeScript parsing or runtime safety.
