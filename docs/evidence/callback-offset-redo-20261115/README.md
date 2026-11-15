# Callback physical-line coordinates: fresh redo

This is new work from published fced64c4 via 066cc1a, not recovery of lost
55-commit history. Both semantic splitlines() and excerpt readlines() represent
one physical line per item. Joining retained terminators with another newline
made callback3–5 become5–9. Normalize terminators before the existing lexical
mask; do not change source body bytes or unknown-syntax fallback.

Two independent range families (property and member callback) fail before and
pass after. The third regression exercises the ArkTS range extractor used by
excerpt selection and verifies the exact callback body slice. Initial third test
incorrectly assumed bare onClick(run) established the richer UI callback marker;
that setup failed even after the fix. first-attempt.txt preserves it. Corrected
before runs all three tests on unchanged baseline modules: 0/3. Final focused
suite:48/48, including existing lexical unknown, opening-column, multiplicity,
and binding/excerpt controls. No full evaluation or new original repair count.
