# Direct field map and named-import integration

The independently frozen field-scope and direct named-import repairs are combined.
Their only merge conflict was append-only development log content; both entries
are retained. Together semantic_ecma.py reached 501 lines. The unchanged field
map loop was moved into ecma_field_scope.collect_field_types, taking the same
FIELD_RE object. semantic_ecma.container_fields remains a thin wrapper, keeping
its callers and test API unchanged. The semantic module is now 494 lines.

The combined focused command covers container-field scope, named-import alias
identity, state declaration lexical/modifier handling, state edge equality and
lexical handling, callable state handoff, and the project Python fingerprint.
All 32 tests passed; see focused.txt. git diff --check passed. This is not a full
suite or aggregate acceptance. Original shared-record and Builder groups remain
1/3 and 2/3 respectively; no new historical failure reduction is claimed.
