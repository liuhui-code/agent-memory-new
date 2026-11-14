# Phase S implementation observations before public run

The initial manual13-control harness used zero-based next-method index minus1 as
a one-based end line, making two legitimate positive controls false (end9 rather
than actual method closing10). The frozen source and expected values were not
changed. The corrected harness uses the method's actual closing line and is also
covered by test_thirteen_frozen_sources; all13 now match. Initial JSON remains as
a setup error, not evidence that source rules needed changing.

Parent identified malformed private modifier tuples could raise before snapshot
comparison. Shape/type validation precedes dereference; emptytuple/None/non-tuples
and request/member mutations have explicit fail-closed tests.

Compound reviewer checked full body and noted masked literal prefix and malformed
mixed parameter delimiters could pass the standalone helper. Normal producer's
full mixed stack already rejects the malformed parameter case, so it was not a
demonstrated public bug. The witness now checks full masked mixed delimiters and
uses literal-visible headers too, without expanding the producer. Top-level
literals remain executable tokens rather than disappearing as whitespace;
strings in opaque balanced arguments/DSL bodies do not contribute modifier facts.

No public Phase S output or original23 has run at this point. The initial28 and
subsequent41/42 focused test groups differ by newly added binding/header checks;
they overlap and must not be summed. PhaseR accepted outputs remain the baseline.

Fixeda9124e6 public S24 + English24/old5 completed. The strict S checker found ONE
mandatory failure: supported-negative returned the correct file but no callable
qualification marker (evidence unavailable). The remaining23 S checks, English24
and old5 matched their criteria. This cannot be waived based on file precision.

Read-only localization_input trace explains the gap: full original collection
uses the bound property descriptor and returns Palette. The negative-clause path
then recollects on a stripped positive string, including trailing comma, where the
full AST is correctly unavailable. Thus localization loses its source candidates.
Proposed correction is transport of the already original-bound collection for an
eligible descriptor, with explicit original/local negative filters retained, not
parsing or granting authority from cleaned text. Original23 remains unrun.
