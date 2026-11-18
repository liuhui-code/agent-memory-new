# Local await classification repair

The typed-receiver await scan also matched `await this.method()`, after the local-method scan had already classified it. The two-line repair skips the literal `this` receiver in the typed scan. Local resolution remains responsible for local methods; genuinely missing local targets and unresolved typed receivers still produce their original gaps. No broader await grammar or source admission rule is added.

A separately frozen five-case parser component reproduced the duplicate gap and checked the repaired candidate. Independent review of all seven returned fields (path, text, digest, entities, relations, mechanisms, gaps) confirms only two deletions across the five returns: `this.helper` from the resolved-local case and `this.missing` from the missing-local case. The genuine `missing` gap and unresolved `service.load` gap remain; known typed and imported receiver outputs remain unchanged. Ordering, multiplicity and all other values are identical. This component made five top-level parser calls, zero CLI calls and zero database connections. Complete evidence was backed up and independently read back; hashes are provided separately.

The repeatable regression has one unittest method with five subtests. The adjacent named suite has 17 methods in total and includes ordinary CLI/SQLite integration work with temporary fixtures; its counts are separate from the parser component. Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest tests.test_local_await_classification tests.test_semantic_index tests.test_semantic_mechanisms
```

The final-tree targeted-run record and publication outcome are external audit records and commit metadata, not mutable claims in this fixed source tree. This is not a full-suite result. Original recovery item 10 remains open. The previous wrapped-origin STOP and its 64-row census limit are preserved, not retrospectively accepted or replayed by this repair.
