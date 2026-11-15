# Dedicated final file-statewrite operator predicate

Basee545aea, independent Development. Frozen original Equality.ets source is unchanged. Public file summary, not callable markers or state edges, is the acceptance surface. Existing state-edge-equality and validation-marker-equality establish comparisons are not writes; callable precedent explicitly excludes '=' or '>' after bare '=', preserves ASCII field spelling and original (=,+=,-=,++,--) family.

Proposed change: private dedicated predicate in arkts_state_write_source consumes the existing known-code-or-legacy-text function. Final file statewrite branch calls this predicate. Do not modify shared STATE_WRITE_RE (used by statehandoff), COLLECTION_WRITE_RE, source operation vocabulary, scoring or query terms. True assignment of arrow function value retains '=' followed by whitespace/parenthesis. Bare 'this.field=>...' is only a token-boundary helper control, not a claimed valid public program.

Unknown lexical input still falls back to complete raw source, then the corrected operator predicate applies. This can remove false comparison hints even in unknown source; a regex literal containing fake assignment can retain a false write. No unknown-source absence or scope proof is asserted.

Freeze14 public sources/3 queries, six new test methods, and before failures before candidate. Public controls cover five real write operators, mixed comparison/write, arrow value, unchanged comparison nonwrites and known string masking. Helper controls cover whitespace/newline, =>, Unicode field non-expansion, unsupported compound operator non-expansion, unknown raw semantics and shared regex unchanged.

Prior file lexical test explicitly expected Equality legacy positive as a stage boundary. Keep its protocol/results byte-identical. After independent new public red review, migrate only that live test's equality expectation and separate equality out of its unknown-preservation loop; document this intentional accepted operator correction, not an evaluator/oracle change to old results. No other assertion is weakened. Full old/new focused tests must pass together.
