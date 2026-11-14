# Phase R pre-public implementation review

Parent directly probed the initial uncommitted local descriptor: Card.ets / owner
Card was not excluded while CardView was, because identifier_tokens only yielded
split components. This contradicted the frozen Card/CardView control. Corrected
locally by including whole tokenize tokens as well as identifier parts; Postcard
stays non-card. No global excluded_code_candidate change. qualified_name is used
as the source symbol's owner-qualified name when the raw symbol row has no
owner_name; no arbitrary string/body fields are scanned. No public candidate
query ran before this correction. Preserve this discovery rather than describing
the initial implementation as passing.

Compound reviewer then demonstrated two finite contract violations in 948020a:
different original negative ASTs can normalize to the same positive query, so a
clean-query-only valid_for check admitted descriptor reuse; qualified_name included
the method's final segment and Plain.card falsely looked like a card owner.
Correction passes an independent original-query value through the built-in recall
constructor/table helper and code scorer, requires exact original receipt equality,
and only uses qualified_name's owner prefix when owner_name is unavailable. Added
both reproductions before the first public candidate run. This is not an expansion
of the frozen request surface or exclusions.

Reviewer tightened the owner correction before public after: the real schema has
owner_name, so SQL now selects that field and missing owner means file-only matching.
No qualified_name fallback remains, including nested Plain.card.inner. Unit SQLite
schema was corrected to the actual owner_name column rather than constraining the
implementation to its initial fake table. Same 30 focused tests pass again.
