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
