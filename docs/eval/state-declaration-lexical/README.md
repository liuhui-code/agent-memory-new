# State declaration lexical identity

Independent Development protocol frozen at 7242575, public red/tests at 938b2b2,
base 66050ad. This repairs formal symbol identity, not an inferred query ranking
improvement. Production remained unchanged until the actual public red was saved.

## Observations and narrow change

Public init / learn-path / list code-symbol produced eight states in StateBoard:
four literal/comment/template ghosts and four live rows. Two live identities were
unqualified; the remaining qualified identities pointed at strings (lines 7/12)
instead of real declarations (2/11). With the candidate, exactly two states remain,
StateBoard.live at line 2 and SecondBoard.live at line 11. Both producers therefore
need the same state-only admission rule; dropping ghost names alone is inadequate.

Reuse the already reviewed strict callback mask before state declaration matching.
Semantic extraction computes it once per file, outside the container loop. Legacy
extraction computes it once for its state pass. Original text, digest, method
parsing, Event/route parsing, decorators, modifier vocabulary and ranking remain
unchanged. Semantic still uses physical lines; legacy retains whole-text matching
including its existing split-line decorator behavior. No new scope is inferred.

Unknown lexical syntax (including slash ambiguity and interpolation) returns None
and preserves the entire file's legacy state extraction. UnknownBoard before/after
records match, including existing false states. This is not an absence proof or a
claim that all false declarations are fixed. Event ghosts are also out of scope.

## Validation

- Three new tests: two red before repair, all green after. Assertions include both
  true owner identities and exact ranges, not merely a deduplicated name list.
- 42 focused tests pass (new declarations, modifier identity, semantic index,
  callable profiles/body ranges). Separate 13 state-edge/equality/handoff and
  fingerprint checks pass. No full suite or aggregate score was run.
- Independent reviewer reran the three tests; additional read-only probes confirmed
  unknown whole-file fallback and multiline comment/template position stability.
- index-upgrade.json verifies old archives keep eight bad rows after installation
  alone; ordinary merge learn-path removes ghosts and restores both true owners.
- mask-cost.json: 100-container smoke check, one semantic mask call and 100 states;
  elapsed time is a local observation, not a performance guarantee. The first
  probe mistakenly accessed symbol_type rather than SemanticEntity.kind, raised
  AttributeError after parsing, and was corrected before obtaining the result.
- comparison-after.json: selected historical group remains 2/3. It is not a
  full gate and does not establish reduction in historical failures.
