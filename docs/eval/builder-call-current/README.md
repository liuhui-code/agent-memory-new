# Direct named-import alias callee identity

Fixed baseline80feab8. Original Builder group remains2/3; this independent graph
identity repair is not an original owner-selection improvement. No full gate.

## Frozen public defect

alias-protocol.json and alias-before.json were committed010b3be before production
edits. A true imported Builder paintLine is locally named renderLine. Its module
also exports an unrelated renderLine. Public learn/list typed calls incorrectly
connect AliasView.build to the unrelated renderLine, whereas direct import and
nested local formatLabel calls resolve correctly. This is not a missing Builder
role, owner-selection score, or source range problem.

parse_imports already records(original name, local alias, module path); file context
previously discarded the original name and emitted local alias as remote target.
The candidate retains that existing tuple's name for a bounded directly called
named alias. It does not create alias runtime objects or parse a new schema.
Module-scoped alias targets cannot fall through to another file's global same-name
symbol when the imported module lacks a unique matching callee.

## Strict supported subset and unknowns

Only original-name != local-name imports use the new path. Existing default and
namespace import behavior is not enhanced. Calls with visible same-name local
symbols/parameters, any local const/let/var declaration, nested function/class,
catch, arrow body, qualified member access, rebinding or destructuring uncertainty
are not certified through this alias. The entire callable abstains from this new
binding rather than inventing an unrelated callee. Slash/interpolation lexical
unknown is also not certified. This is NOT complete lexical scope analysis or
proof that a missing edge means a call is absent. Bodies containing unrelated
local declarations deliberately remain outside this narrow new capability.
Duplicate local import bindings map to unknown, not last-import-wins authority.
Same-name declarations in other modules remain isolated by exact module path.

## Iterations and controls

Initial alias-only public red turned green. Additional tests exposed an overly
broad function-keyword guard rejecting top-level functions; restrict the guard to
callable body, preserving the initial failing log. Reviewer then found newline let
and multiline comma bindings bypassing declaration-name regexes. Those controls are
fixed tests, and final code conservatively rejects ANY local binding declaration,
not a growing list of shadow syntax guesses. Earlier related logs are preserved
but are not the final validation. Supplemental controls were introduced after the
initial implementation and are not misrepresented as part of the original freeze.

Final tests cover: actual public alias vs decoy and nested local call preservation;
remote absent with global same-name decoy; two modules exporting the same name;
public parameter/function/destructuring shadows; newline/for-of/comma bindings;
qualified member, catch, arrow, interpolation, duplicate aliases; unchanged
non-alias context. No query, oracle or score changes were made.

upgrade.json records old archived AliasView→renderLine after installation alone,
then correct AliasView→paintLine after ordinary same-byte merge learn-path. No
special migration or forced indexing is required. Source IDs/ranges remain those
of the existing producers. The independent list/calls result, not merely names
in a context summary, is the acceptance signal.

Final validation:50 relevant tests,49 pass and one pre-existing optional ArkAnalyzer
provider smoke skipped because that provider is not installed. Seven new alias
tests pass. Final independent public replay, same-byte merge replay and original
Builder three-variant check rerun after the conservative declaration guard. Python
compilation and whitespace checks pass; semantic_ecma is500 lines, semantic_index426,
new helper39. No full suite or aggregate score inferred.
