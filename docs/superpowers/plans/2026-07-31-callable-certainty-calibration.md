# Callable Certainty Calibration Plan

## Objective

Separate callable ranking priors from the confidence used to narrow Agent-visible
source Context. Keep ranking order and all retrieval budgets unchanged.

## Evidence

The rejected broad projection exposed two independent false-certainty classes:

- multi-file component and property-flow queries collapsed to one callable;
- single-owner queries gained an unrelated or explicitly forbidden callable even when
  the existing compact anchor was correct.

Both classes were marked `certainty=bounded`. The localizer currently includes the
first-stage file-rank prior in `evidence_score` whenever direct scores are considered
safe. A rank prior can therefore create the two-point margin used by callable
certainty, despite the existing contract and test stating that a prior alone must not
establish bounded confidence.

## Architecture

Maintain two score domains behind `HierarchicalLocalizerPort`:

- `localization_score`: lexical, structural, graph, direct, and file-rank evidence used
  only to order bounded candidates;
- `evidence_score`: the same score with file-rank prior removed, used by selective
  projection and abstention calibration.

The Context facade, SQLite schema, query ranking, candidate order, graph depth, output
shape, and four Skills do not change. Structured explicit-owner evidence retains its
existing typed certainty rule.

## Validation

1. Add a unit case proving different file-rank priors change ranking but not calibrated
   evidence separation.
2. Run callable-focus and cascade-ranking regression tests.
3. Run the complete development differential against 185/231 and reject any formal
   check regression.
4. Run performance, compile, JSON, four-Skill, diff, and 500-line gates.

## Stop Rules

- Do not change candidate ordering, score weights, certainty threshold, or Oracle.
- Do not add query, path, project, filename, or language-specific conditions.
- Reject the change if reduced false certainty also removes a previously correct
  serving anchor or source window.
- Do not reintroduce broad callable projection in this phase.

## References

- Selective prediction and calibrated confidence: https://arxiv.org/abs/1705.08500
- Reciprocal Rank Fusion: https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf
- Repository evaluation policy: `docs/evaluation-and-change-policy.md`

## Rejected Subtraction Experiment

The first experiment removed the file-rank prior from `evidence_score` for every direct
query while leaving candidate order unchanged. Focused regression found a formal
serving regression: a two-component typography query changed from `uncertain` to
`bounded`, then compact projection collapsed two correct source anchors to one.

The implementation and its provisional test were reverted. A scalar subtraction is
not confidence calibration because candidates from different retrieval lanes retain
different score composition. The next admissible step is an explicit evidence-set
contract that models target multiplicity and competing support. It must first run in
shadow and demonstrate calibration on independent single-owner, multi-owner, graph,
and exclusion fixtures before it can control compact projection.

After restoration, a six-variant smoke over lifecycle persistence and cross-component
preview matches the accepted 185/231 baseline exactly for status, every formal check,
primary anchors, and first-loss attribution.
