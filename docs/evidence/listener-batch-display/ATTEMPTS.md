First model runner: 20/21 checks passed. Diagnostic cap test incorrectly fed
100 already-displayed rows, each carrying the previously generated field,
whereas CLI feeds SQLite rows without that field. It counted untouched input
fields as newly emitted diagnostics. Original failed output retained. Correct
fixture strips only the derived diagnostic field before constructing raw-row
input; implementation/caps/expected inequality unchanged. Re-run this focused
model runner, not the public sources or queries.
