# Independent review boundaries

The reviewer identified a blocking downstream case: the legacy callable-envelope
producer used broad splitlines, accepted an unchanged prefix, then could mark an
incorrect suffix as complete when LS/PS occurred after that prefix. The candidate
now declines expansion for all extra splitlines separators. This preserves the old
expanded_from decoder, rather than changing its meaning. A focused regression
uses a matching physical prefix and an LS/PS-containing undisplayed suffix.

The ordinary excerpt reader already uses physical CR/LF coordinates. Mechanism
extraction's primary path consumes the parsed line list; the secondary broad
splitlines operation path is not the primary coordinate producer. Graph-field
and field-alternative authentication rejects LS/PS; that eligibility is unchanged.
Plain wiki and other language parsers are not claimed unified or improved.

Final reviewer caught the existing `.tsx` TypeScript adapter extension: evidence
slicing must also use the physical table there. Corrected with case-normalized
suffix detection and a real learn-path ordinary-class TSX regression. This does
not introduce JSX parsing. Final targeted result is 38 methods; earlier 37-method
logs are retained rather than overwritten.
