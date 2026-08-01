# Cascade Ranking Calibration Plan

## Objective

Remove the two regressions exposed by the complete `b26de18` differential while
preserving all seven improvements from the evidence-funnel work. The repair must address
shared cascade-ranking contracts, not add project names, source paths, or query phrases.

## Differential Evidence

With the same 225-case pack and shared evaluator, frozen Runtime `b26de18` passes 168
variants and the current Runtime passes 173. Seven variants improve, two regress, and
three already-failing variants lose additional checks.

The regressions have two independent causes:

1. When an exclusion clause changes the positive query, callable ranking discards every
   upstream direct score. Correct files remain first-stage rank 1, but generic reporter
   callables can win the second stage through expanded lexical terms.
2. Any owner-kind token anywhere in the query is treated as a hard ordering constraint.
   A problem clause mentioning a service can override a target clause that explicitly
   requests a coordinator.

## Architecture

Keep the existing bounded two-stage retrieval and `HierarchicalLocalizerPort`.

- Use a bounded, smoothed reciprocal-rank prior when no safe direct score exists. When
  an exclusion changes the query, rerun the existing first stage with the positive
  query, retain original-query exclusion governance, and mark those direct scores safe.
- Give explicit target-intent roles precedence over problem-context roles. Fall back to
  whole-query role evidence only when no explicit target role exists, and distinguish
  singular targets from chains, flows, conjunctions, and language-specific cardinality.
- Add coordinator as a language-neutral owner kind and map view/page requests to the
  existing component kind. Keep role aliases in the semantic adapter, outside ranking.
- Preserve explicit adapter/boundary/policy target matches and the bounded-certainty
  contract introduced by the independent evidence-funnel fixtures.

This follows established cascade retrieval: broad first-stage recall contributes a
bounded rank prior, while later stages use query-dependent field interaction. It also
uses explicit query intent rather than treating all terms as equivalent constraints.

## Phases

### Phase 1: Independent red cases

- Add an activation-coordinator case where a transport service appears in the problem
  clause but the target instruction requests a coordinator.
- Add a markup-preview case with an excluded record and a lexically dense generic
  reporter; the view is first-stage rank 1 but initially loses callable primary.
- Require three variants per scenario and retain file/callable/range/final stage gates.

### Phase 2: Typed cascade repair

- Add target-clause owner intent to the semantic callable profile.
- Add a deterministic reciprocal file-rank prior with an explicit maximum.
- Keep direct symbol scores when they came from either the unchanged query or an
  independently executed positive-query first stage. Never restore raw pre-exclusion
  scores.
- Do not alter pools, graph depth, compact budgets, Oracle thresholds, or database data.

### Phase 3: Differential verification

- Require the six new variants to pass.
- Rerun all 12 variants whose checks changed between `b26de18` and the current Runtime.
- Require zero newly regressed variants, both prior regressions restored, and all seven
  prior improvements retained.
- Run the complete development gate and compare per-case checks, not only aggregate
  scores.
- Run Context/benchmark tests, CI scale, Python compile, JSON, diff, four-Skill, and
  500-line gates.

## Stop Rules

- Stop if a fix names ConsoleFailureReporter, ArticleMarkupView, a fixture path, or a
  case-specific token.
- Stop if the raw pre-exclusion score is restored.
- Stop if a target role is inferred from the whole query rather than a target clause.
- Stop if net score improves while any previously passing variant regresses.
- Do not run or inspect a consumed external holdout.

## Primary References

- Reciprocal Rank Fusion: https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf
- BEIR heterogeneous retrieval and reranking evaluation:
  https://arxiv.org/abs/2104.08663
- ColBERT late interaction: https://arxiv.org/abs/2004.12832

## Execution Result

The first broad implementation was rejected. It applied the reciprocal prior and
callable projection too widely, passed 172/231 variants, and introduced 14 regressions
among the existing cases. The narrowed architecture separates five contracts:

1. positive retrieval from original-query exclusion governance;
2. general owner relevance from explicit singular-target authority;
3. target role from target cardinality;
4. internal calibrated evidence score from the Agent-facing evidence projection; and
5. callable-local source provenance from ordinary source-window selection.

Two independent scenarios and six query variants initially passed 2/6 and finish at
6/6. The final complete development run passes 183/231 variants and 44/77 stable
scenarios. Across the 225 existing variants, pass count rises from 173 to 177 with zero
pass-to-fail regressions. Against frozen `b26de18`, pass count rises from 168 to 177 with
nine improvements and zero regressions. All six new variants pass.

The shared runner builds five source indexes, creates 231 isolated case snapshots, and
avoids 226 repeated index builds in 354,771 ms. Average Context query time rises from
672.6711 to 735.6364 ms (9.36%); average Context size rises from 1,266.7289 to
1,291.1948 Tokens. This is accepted because only explicit exclusion queries execute the
additional positive first stage. The overall development capability gate still fails
honestly at 183/231 and is not eligible for external promotion.

Verification passes: 81 Context tests, 68 query/localization tests, 91
benchmark/governance tests, the CI scale SLO, Python compilation, 200 evaluation-JSON
parses, diff validation, the four-Skill invariant, and the 500-line limit. At 100,000
searchable entities and 300,000 graph edges, callable-pool P95 is 4.286 ms and one-hop
owner P95 is 5.141 ms. No consumed external holdout was read, changed, or rerun.
