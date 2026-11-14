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
