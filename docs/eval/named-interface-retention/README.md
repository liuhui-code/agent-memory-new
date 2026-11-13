# Retain explicitly requested interface declarations in composite projection

Development only. Base a6c1d93, continuing the docs-only cb05197 diagnostic.
The independent UnitSpec/PacketScaler public failure was observed before production
changes. This patch does not change callable ranking, retrieval, source extraction,
portfolio certification, graph/log authority, or the 1500-token budget.

## Existing contract and first loss

Raw public anchors already contain both actual declarations with typed code_symbol
references and valid ranges. `query_definition_identity.TYPE_DEFINITION_KINDS`
already recognizes interfaces as declarations. But compact's existing
`multiple_requested_anchors_present` decline-to-narrow guard recognizes only class,
component and struct. Thus an explicit two-declaration request is narrowed to one
bounded callable file, discarding the interface. This is a missing consumer type
case, not a new permission to fabricate cross-file callable portfolios.

The production diff is one whitelist entry: `interface`. All existing positive
name boundaries, exclusions, quoted-text refusal, multiple-target requirement,
unique-name-to-path checks, valid ranges and no authority for generic terms remain.
Enums/objects and other new role classes are intentionally outside this patch.

## Frozen red and green

- eaf369c freezes protocol, probe and new tests before the production edit.
- a46e7a3 records before.json / red.txt: two tests fail on missing pair retention;
  the unrelated guards test passes. It also corrects an unexecuted budget assertion
  field from context_budget to the actual output_budget. No owner oracle changes.
- before.json / after.json have identical queries, required identities and sources.
  The explicit unique PacketScaler + UnitSpec case changes from PacketScaler only
  to both declarations, with actual UnitSpec source and valid typed record refs.
- Interface-only, two real callables, generic multi, two actions, explicit exclusion,
  quoted text, and same-name-other-file controls keep their exact path sets.
  The ambiguous pair remains unresolved, not falsely certified as disambiguated.
  Generic multi/two actions are conservation checks, not asserted complete answers.
- 80d4699 freezes a separately labeled budget-stress addendum after the narrow
  candidate was formed. Its baseline was executed in an untouched a6c1d93 worktree.
  A 160-field interface still loses identity before and retains it after. Candidate
  uses 1083 of 1500 tokens; this demonstrates identity retention with long source,
  NOT saturation at the budget ceiling or complete body delivery.

## Validation and limits

3 new tests pass. The first focused batch has 25 passes including those 3, existing
named components, typed references, callable portfolio and structural exclusions.
A separate projection/certificate/same-owner batch has 52 passes. Fingerprint check
passes. No full suite or consumed holdout was run.

Original native-color was rechecked only as a non-improvement control: still 2/3,
with the same English precision failure. No historical failure-count gain claimed.
The source excerpt completeness issue is separate and this patch does not touch it.
