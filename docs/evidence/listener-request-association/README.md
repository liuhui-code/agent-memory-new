# Offline listener request/name association: fixed observation result

Plan ddf4de1, corrected semantic labels and full inputs9d1a316, implementation
f830c1d. One pure offline execution;35/35 synthetic controls match their frozen
lane/status expectations. Six saved-query observations have expected=null and
pass=null: they are NOT six passing retrieval tests. No public CLI rerun, runtime,
ranking/selector wiring, benchmark/oracle change or original failure improvement.

## What was observed

| Saved request | Target-member lane | Extra dual-name hypothesis |
|---|---|---|
| Independent binds...DeliverySink rejected contract | exact-name association, one observed identity | same |
| Explicit Relay.connect | unsupported descriptor | same |
| Accepts DeliverySink | unsupported descriptor | same |
| Explicit Recovery.retryRejectedDelivery | unsupported descriptor | same |
| Literal descriptive text | unsupported descriptor | same |
| Original binds...host ResultListener failure contract | uncertain segment association, one observed identity | same |

The last row uses raw CamelCase boundaries (on / Failure), not old stopword token
expansion, a hardcoded on-prefix rule or a failure synonym. Single failureCount
and retryFailure also weakly associate in frozen controls. When several distinct
spellings compete, the segment lane reports collision-unknown instead of choosing
the shortest or expected one. Exact case remains separate. HTTP acronym and
snake_case boundaries are explicit controls, not claims of general semantic names.

Two actual-forwarder identities remain multiple-observed. Partial/capped/old-index
domains never imply global uniqueness or absence. The empty complete synthetic
fixture status is only no-name-association, not no source implementation.

## Correctly unresolved meaning

Every result, including exact-name, sets relation_satisfied=false,
eligible_for_ranking=false and global_uniqueness_claim=false. Original source noun
phrases and target qualifiers (including host) remain unresolved_qualifiers. The
experiment does not establish engine/native/runtime/host semantic attachment or
that the full user's requested relation is satisfied.

The target member need not name the callback property. Consequently the primary
observation tests the invoked member only, while a separately reported restrictive
hypothesis also matches the property. It always marks property_selector_assumed
and relation_attachment_unresolved. accepted→rejected yields a target-member exact
association but no dual-name match. Neither lane is promoted into serving authority.

Whole-sentence grammar rejects the frozen quoted/negated/caller/wrapper/return/
declaration/multiple-type/multiple-member/extra-command/unknown-relation controls.
This is a bounded experimental grammar, not proof that all arbitrary natural
language requests or embedded commands are safely classified. No word-count rule,
original noun whitelist or after-result lexical adjustment was used. Source noun
meaning is deliberately unverified rather than guessed from the grammar.

## Provenance and stage limit

Synthetic facts are explicitly labeled synthetic name-association fixtures, not
runtime observations. The six original query observations use unchanged saved
queries and facts read from prior v2 indexed JSON, with input hashes. No new query
was sent to the runtime. Public original red remains untouched and cannot be
counted as improved because this offline descriptor can name-associate a fact.

This result makes exact versus uncertain association and unmet predicates visible.
It does not close request permission, type resolution, full relation attachment,
index completeness, source-certificate trust, budget or exclusive-owner contracts.
A future consumer proposal must solve those obligations independently;35 matching
controls are not deployment authorization. All outputs and unresolved flags are
retained in results.json without replacing any prior failed evidence.
