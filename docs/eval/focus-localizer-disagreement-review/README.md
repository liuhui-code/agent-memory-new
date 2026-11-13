# Focus/localizer disagreement: architecture proposal not approved

## Scope and decision

Read-only design review of existing evidence, based on integration `56e084f`.
No new query, source fixture, test execution, runtime change, scoring change or
original oracle change was made. This document does not approve implementation.
The proposed shared nonexclusive portfolio architecture is **not approved**:
there is currently only one independently demonstrated downstream exclusive
source-loss class among the two evidence families reviewed here.

## Source replacement: observed exclusive source loss

Original evidence: `docs/evidence/source-replacement-first-loss/README.md`,
`compact-trace.json`, `raw-trace.json` and `clean-public.json` in that directory.
The trace shows initial selection of SourceSwapCoordinator.replaceSource, then
salient evidence admission and a later lexical localizer choice of
WrappedProfileService.load. Path activation is false, and no existing typed
owner or event certificate was lost. The original required source disappears
at bounded callable narrowing, not at extraction or raw-source production.

Independent evidence: `docs/evidence/history-action-before/README.md`,
`historical-action-compact-trace.json`, `historical-action-raw-trace.json`,
`actual-load-compact-trace.json` and `actual-literal-compact-trace.json`.
The sources, queries and oracles were frozen at `568597d` before observation;
results were recorded at `34f3edb`. The actual function-return trace shows:

- `focus_code_candidates` returns only DocumentSession.swapDocument and
  `focused=True`. Its indexed symbol ID 3, range 5–9 and actual reset source
  survive into raw anchors. IDs describe this fresh index, not global identity.
- Salience also admits ThumbnailLoader.load, ID 7, range 2–8.
- Callable localization chooses load at 36.57 above swapDocument at 28.415.
  Reasons are lexical; path activation is false. The score-gap rule returns
  `bounded`, and `focus_callable_anchors` removes DocumentSession from compact.
- Actual load and actual log/literal controls pass their frozen source checks.
  They are protected controls, not evidence of a new implementation passing.

This is an independent reproduction of exclusive source loss. It does **not**
prove that early focus is an authoritative statement of the user's target.
That focus itself is heuristic retrieval evidence, not a unique-owner, causal,
explicit-request or source-operation certificate.

## Scroll: real disagreement, but a different failing contract

Evidence: `docs/evidence/scroll-structure-current/README.md`, `independent.json`,
`independent-checks.json` and `trace.json`. This saved experiment has an older
baseline (`623981f`); this review did not rerun it on current production.

The frozen abstract query selects ActivityPane.build as the first raw anchor,
while callable primary is AccessCodeGenerator.generateAccessCode. The localizer
scores are 20.84 and 21.39 respectively. **Certainty is uncertain, not bounded.**
Both files remain in compact. ActivityPane retains its build source range 4–12
and the actual List mechanism excerpt at 6–10; the generator also retains source.
The failed frozen oracle asks for ActivityPane as primary. It is not an oracle
for missing compact source. A nonexclusive portfolio cannot be claimed to fix
this primary-identity failure merely by keeping sources already retained.

The saved trace reconstructs ranking contributions from retrieved records; it
does not observe `focus_code_candidates` returning `focused=True`. Raw first
position must not be relabeled as authenticated early-focus provenance.
Explicit layout, generator, real Scroll and two-layout controls were green.
They do not establish the missing exclusive-loss precondition.

Thus these families share a lexical-localizer disagreement symptom, but do not
establish two independent defects in one exclusive-narrowing contract. A common
function or stage name is insufficient to meet the architecture gate.

## Minimal reviewable contract, not permission to implement

A future display-conflict proposal could distinguish observed early focus from
later lexical localization without declaring either to be target authority.
It would need to preserve these boundaries:

1. Observe actual same-request focus selection; do not use raw list position as
   a substitute. Keep heuristic selection provenance separate from identity.
2. Validate actual retrieved code-symbol identities in their project/table/index
   context, including path, key, digest and valid source ranges. Numeric IDs or
   copied JSON do not by themselves authorize a source read or certificate.
3. Preserve already-authorized evidence only. Do not expand filesystem access,
   read a previously unbound primary, or bypass bounded-read/digest protections.
4. Do not masquerade as CertifiedPortfolio, explicit multiple-target ownership,
   source-operation evidence or a causal relation. Do not silently alter the
   existing strong typed, private-owner or log-path policies.
5. State the intended outcome precisely: source retention versus correct primary.
   Keeping both sources while retaining a wrong primary is not a localization fix.
6. Keep existing source and total budgets. Do not select a fixed two anchors to
   fit an oracle; membership must follow a defined evidence contract, and actual
   excerpt coverage must be checked rather than range-overlap metrics alone.

This would be a new consumer policy, not restoration of an already-promised
certificate that the current implementation accidentally discarded. It is also
not permission to revive the rejected early semantic-focus non-erasure veto.

## Missing controls and stop conditions

Before a production proposal, obtain a second independently frozen example of
this same exclusive-loss contract or explicitly reject the two-family premise.
Scroll as currently observed does not supply it. No additional query or fixture
was created in this review.

A future fixed control protocol must include the important **reverse conflict**:
early focus is wrong and a legitimate later localizer corrects it. The two
current history-action positives do not establish behavior under that conflict.
Also required are actual load requests, exact identifiers, genuine log literals,
explicit single and multiple targets, comparison/exclusion requests, strong
typed/source-operation matches, private owner certificates, complete log paths,
unknown/missing provenance, forged or cross-table IDs, stale digests and same-name
owners. Budget controls must test actual required body retention and displacement
of other legitimate evidence under the unchanged 1500-token limit.

Stop if the proposed rule merely preserves a source already present in a failing
case, worsens a true target correction, requires invented authority, or can only
pass by changing the frozen oracle, query, score weights or anchor count. Failure
to approve this proposal is not a claim that all remaining categories are blocked
or that the overall repair task is complete.
