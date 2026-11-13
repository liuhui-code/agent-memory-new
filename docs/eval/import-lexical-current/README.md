# Import lexical admission investigation

Independent Development, base `0f0beb6`. Protocol and probe committed before the
first execution. Production is unchanged at this checkpoint.

Public `learn-path`, `list --type code-symbol`, and `list --type memory-edge`
produce four false module-bound `calls` relations: CommentNamed and TemplateNamed
run methods point to Painter.paint, and CommentDefault and TemplateDefault run
methods point to Painter.render. Their import-looking lines are block-comment or
plain-template text, not declarations. The unqualified calls deliberately have
no asserted external binding; this fixture does not infer their runtime result.
There is no source basis for certifying these remote definitions as their targets.
Actual named and legacy default import controls retain their expected identities.
The default control documents existing name resolution, not complete ESM default
export validation. Full actual context/query_handoff is retained in before.json.

Cause: semantic_ecma.parse_imports applies both IMPORT_RE and DEFAULT_IMPORT_RE
against raw text. Proposed narrow next step, pending review: admit each raw match
only when its import keyword survives the existing conservative equal-position
lexical mask. Preserve raw captures for the module string. Unknown regex/division,
interpolation, or malformed lexical input would preserve whole-file legacy
behavior, not certify absence. No full suite or original-pack scoring performed.

## Accepted narrow candidate

After the above red was committed, permission was given for the proposed lexical
admission. Both existing import regexes now receive their original raw match
objects after checking only that the `import` keyword is code in the strict mask.
The module path and all original captures/offsets remain raw. Unknown syntax uses
all legacy matches. No new scope, default-export or namespace resolution is added.
`after.json` retains only the two true import controls; all four false remote calls
are gone. This does not certify the unresolved global calls have no runtime target.

`upgrade.json` confirms installation without relearning leaves six old relations;
ordinary same-byte merge learn replaces them with the two real controls. No schema
migration is required. Consumers of old archives must relearn to obtain corrected
source-derived relations.

Focused final command:
```
PYTHONPATH=tests:. python -m unittest tests.test_import_lexical_admission tests.test_named_import_alias_identity tests.test_imported_module_callable_development tests.test_semantic_index tests.test_semantic_provider tests.test_context_typed_references -v
```
Final: 46 tests, 45 passed and one preexisting optional ArkAnalyzer skip. The four
new tests cover public identities, raw capture offsets, multiline/CRLF declarations,
and exact legacy match preservation for regex/division/interpolation/unclosed input.
No full suite or aggregate/original-pack score was run. Python compilation and
whitespace checks pass; semantic_ecma is 498 lines.

Scope caveat: this change covers semantic named/default import tuples and their
module-bound typed calls only. `code_wiki_imports.resolve_js_imports` still scans
raw `from`/dynamic-import/require forms for learning file traversal; it is not
changed or certified here. The retained public memory-edge outputs contain no
`imports` relation, so this stage does not establish that every file-level import
consumer is clean. It does not extend default-export or namespace support.
