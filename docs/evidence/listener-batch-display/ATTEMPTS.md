First model runner: 20/21 checks passed. Diagnostic cap test incorrectly fed
100 already-displayed rows, each carrying the previously generated field,
whereas CLI feeds SQLite rows without that field. It counted untouched input
fields as newly emitted diagnostics. Original failed output retained. Correct
fixture strips only the derived diagnostic field before constructing raw-row
input; implementation/caps/expected inequality unchanged. Re-run this focused
model runner, not the public sources or queries.
Correction to preliminary count above: attempt 1 was 19/21, not 20/21.
Second fixture error: SemanticEntity is frozen; mutating kind raised before
calling the decoder. Attempt 2 after raw-row correction was 20/21. Replace
that fixture with dataclasses.replace(kind='class'); expected rejection and
legacy preservation unchanged. No production/overlay implementation changed.
Actual attempt 2 remained 19/21: repeat symlink setup was not idempotent. Attempt
3: class kind reached legacy mechanism validation, which already rejects attaching
callable mechanisms to a class; that does not test optional validation. Final
kind control calls optional_batch on a class entity directly, not an invalid
legacy semantic batch. Repeat symlink setup now removes its own test symlink.
Earlier preliminary 20/21 statement was incorrect; actual files are authoritative.
The budget is the encoded array of diagnostic VALUES only, not field-key bytes
or entire list response; this limit is diagnostic content, not response cap.
