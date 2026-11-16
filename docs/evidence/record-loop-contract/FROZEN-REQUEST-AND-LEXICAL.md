# Exact first-experiment grammar, frozen before public output

This supersedes open-ended contextual-clause/noun-class wording in DESIGN. This first experiment is additive positive preservation only. No projection supplies authority: evaluate the complete original string with only outer ASCII space trimming. No prefix/suffix clause, quoted phrase, explicit identifier/path, exclusion, comparison, negation, second command or generic aggregation-only phrase is admitted.

English request EBNF (ASCII case-insensitive words, exactly single spaces between grammar tokens; optional final period):

    verb = Find | Locate | Return
    article = "the " | empty
    object = record | item | entry | collection | batch
    relation = "iteration and accumulator" | "iteration and result"
    target = source | implementation | owner | owners | ownership
    request = verb " " article object " " relation " " target ["."]

Finite Chinese counterpart is deferred, not silently admitted by translation. Generic aggregation ownership without the explicit iteration/result relation is also deferred. Accepted examples include "Locate the record iteration and accumulator implementation.", "Find item iteration and result source.", "Return collection iteration and accumulator owners." These express a relation, not single-owner/exhaustive evidence. Existing global scope is untouched.

Refused examples: "Locate ChunkAssembler.assemble implementation."; "Find both ChunkAssembler.assemble and DeferredAssembly.schedule source."; "Locate the text \"record iteration and accumulator implementation\"."; "Do not locate the record iteration and accumulator implementation; return AfterIteration.summarize."; "Return aggregation ownership."; "Find item iteration and result source compared with the display." Every refusal is exact baseline, not a newly interpreted negative request.

## Lexical/source boundaries

Whole source parse must consume all tokens. Whitespace CR/LF is counted explicitly; other line separators unsupported. Normal single/double-quoted string literals and closed comments are supported; interpolation/regex/unterminated constructs unknown. Token operators +=,=== are contiguous, not whitespace-separated punctuation. Identifier declarations for parameter/item/output are distinct, with no nested shadowing. Conditional branches are complete if/else with one assignment each, not arbitrary nested blocks.

Return and the returned local must be on the same physical source line. Statement termination requires semicolon, a closing block, or a physical newline only when the next token cannot continue the previous expression. In particular a following +, member/index/call continuation cannot be reinterpreted as a new statement; uncertain ASI returns whole-source unknown. Comments containing newline count as physical separation but cannot turn an incomplete expression into a completed one. Assignments whose continuation cannot be fully consumed by the finite expression grammar are unknown. Any unsupported/unknown method or class segment makes the entire source unknown, not a partial-positive result.

Before acceptance gate: only a proved-positive source missing from final public anchors qualifies. An extra after-loop or unknown source is not itself a red and not permission to remove it. The fixed two-positive cohort must retain both positives for any later candidate. No statement asserts the last runtime value (zero iterations, exceptions and converter behavior remain unresolved).

This experiment does not claim original26 eligibility or repair: its full natural requests include contextual/exclusion clauses outside this first grammar. Broadening them after before is forbidden. Any future original26 request admission requires separate semantic review and new predeclared controls; otherwise original variants stay baseline. The purpose of this bounded before is to establish whether an independently requested relation has a true public positive omission before investing in a producer/view implementation.
