# State declaration modifier identity repair

Development-only evidence, base `623981f`. No full gate was run and no historical
failure count is increased. The selected original comparison group remains 2/3.

## First loss and independent freeze

The original `@State private detailsExpanded` was indexed as state `private`, not
`detailsExpanded`, with no correct state read/write edges. This is a declaration
identity producer defect, not evidence that a new value-flow schema is needed.
The initial independent same-state comparison fixture (`protocol.json`, frozen in
`078cc97`) has a separate generic Chinese query with empty anchors. Exact named
controls and explicit edit/create recall work; that generic failure is not fixed
or reclassified by this change.

`modifier-protocol.json` was frozen in `2cf6411`; regression tests were frozen in
`0bb3548`, before production edits. The same DisclosureState source/query varies
only the declaration modifier. Actual public init/learn/context/list shows plain
state identity and edges present, but private/public/protected become the state
name and lose the edges. See modifier-before.json and modifier-red.txt (4 tests,
47 subtest failures). Context still returns the class file: this is a public
symbol/edge correction, not a demonstrated context anchor gain.

## Minimal repair and failed intermediate candidate

Both semantic_ecma STATE_RE and the legacy code_wiki_extractors declaration
extractor now skip the same modifier vocabulary already accepted by FIELD_RE:
public/private/protected/readonly/static. The first semantic-only candidate failed
four public assertions because semantic enrichment joins existing legacy symbols
by file/name; its evidence is retained in semantic-only-candidate.txt and
semantic-only-after.json. Correcting both producers restores actual field name,
qualified owner, state type, line range, and reads_state/writes_state targets.
No ranking, query expansion, evaluator, schema, or source projection changed.

Regex backtracking retains real keyword-named fields (`@State private: ...`) and
repeated modifier/name (`@State private private: ...`). Tests cover both producers,
prefix combinations, two owners with same field name, and legal readonly read-only
public fixtures. The modifier vocabulary is lexical compatibility, not a new
compiler grammar validator. Existing physical-line semantic versus whole-text
legacy extraction differences remain. Raw strings/comments containing decorator
text and unknown decorator handling are not repaired or claimed safe here.

## Results and index activation

- modifier-before/after.json: three modifier variants wrong identity/no edges →
  correct expanded identity and read/write edges; plain control preserved.
  Context class-file anchors are unchanged. modifier-summary.json is an index.
- related-final.txt: 39 focused tests passed, including 5 new tests. The earlier
  related.txt/modifier-green.txt precede the additional readonly assertion.
- original-current.json versus original-after.json: 2/3 both; remaining precision
  failure is retained. Source range metric overlap does not prove full source.
- index-upgrade.json: old-code learn stores DisclosureState.private; installing
  this code without relearn leaves it unchanged. Ordinary merge learn-path
  (without --replace) removes that wrong entity and restores expanded plus edges.
  Existing archives therefore require relearn; installation alone is not a fix.
- Independent read-only review found no blocking issue; reviewer ran the 5 new
  tests separately. No full suite or aggregate score is claimed.

Probe scripts retain command arguments and raw outputs. The fixture, query, and
oracle were not changed to manufacture a red or hide an unrelated precision loss.
