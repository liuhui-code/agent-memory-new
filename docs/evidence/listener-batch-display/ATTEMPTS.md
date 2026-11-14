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
