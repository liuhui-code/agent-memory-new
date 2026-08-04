# Context Evidence Continuity Repair

## Decision

Repair the staged retrieval boundary before attempting another external Agent A/B.
The consumed RNOH gate is hypothesis evidence only. Serving changes are justified by
the independent `localizer-cascade-development` fixtures and must pass the complete
development capability pack without a pass-to-fail regression.

## Observed contract gap

Both independent development scenarios achieve candidate-file recall 1.0,
hierarchical-localizer file recall 1.0, and evidence-set member recall 1.0, but the
compact handoff recalls no expected anchor. Relevant, locatable evidence is lost
between reranking and the bounded Agent projection.

This is a cascade contract failure, not a request to add more retrieval lanes:

1. high-recall candidate generation already succeeds;
2. callable localization already produces bounded source ranges;
3. shadow set calibration sees the required members;
4. serving projection ignores uncertain callable evidence and only composes passages
   from one file and one owner;
5. the final 1,500-token handoff therefore spends budget on weaker lexical anchors.

## Industry basis

- Multi-phase retrieval keeps a broad first phase and reranks a bounded candidate
  set before final projection: [Vespa phased ranking](https://docs.vespa.ai/en/ranking/phased-ranking.html).
- Late interaction preserves query-to-passage evidence until reranking instead of
  collapsing it too early: [ColBERTv2](https://aclanthology.org/2022.naacl-main.272/).
- Result selection should balance relevance with non-redundant coverage:
  [Carbonell and Goldstein, MMR](https://doi.org/10.1145/290941.291025).
- Compact, deliberately ordered evidence is preferable to indiscriminately longer
  context because relevant middle content can be underused:
  [Lost in the Middle](https://arxiv.org/abs/2307.03172).

These references constrain the design; they do not replace repository-specific
evaluation evidence.

## Architecture

### Shared target-scope port

Create a language-neutral target-scope classifier that distinguishes:

- explicit single-target requests;
- explicit multi-target/path requests;
- conjoined evidence criteria whose conjunction alone does not prove multiple
  owners;
- unresolved scope.

Shadow calibration and serving portfolio composition consume this shared contract.
Serving must not consume a shadow result.

### Serving evidence reservation

For an activated but incomplete path, reserve one locatable callable candidate when
callable evidence is uncertain. Preserve the top path anchor first and place the
callable reservation next; a query with no path keeps the accepted projection.

### Serving evidence portfolio

For an explicit multi-target request, compose at most three distinct, locatable,
query-supported callable passages to supplement an incomplete path. Cross-file
composition requires an explicit cardinality or plural-owner basis and independent
support per member. `flow`, `trace`, `path`, and conjunctions alone cannot authorize
cross-file projection. Existing same-owner passage composition remains unchanged.

### Path and callable fusion

A complete, non-truncated reconstructed path or a statically resolved wrapped-log call
path keeps exclusive scope. An activated direct-emitter path with no known caller is
not a proof boundary: preserve one path anchor while reserving the locatable callable
primary or explicit multi-target portfolio. This prevents a lexical emitter match
from hiding stronger source evidence without diluting resolved wrapper paths.

### Fixed boundaries

- candidate generation and graph expansion remain unchanged;
- compact output remains capped at three final anchors and 1,500 estimated tokens;
- Runtime returns evidence context only; Agent CLI performs diagnosis;
- no RNOH query terms, paths, repositories, or Oracle values enter production code;
- shadow outputs remain informational and cannot directly alter serving.

## Execution gates

1. Preserve the pre-change development result in
   `docs/eval/localizer-cascade-development-baseline.json`.
2. Add focused contract tests before production edits.
3. Implement the shared scope port and bounded serving projection.
4. Require both localizer-cascade scenarios to pass through actual `query_handoff`.
5. Run focused tests, all tests, compile, JSON, four-Skill, 500-line, scale, and CI
   gates.
6. Run the complete development capability pack and reject any pass-to-fail change.
7. Only after all gates pass, preregister a completely new external source family.
8. Seal and consume its Context gate exactly once; run Agent A/B only if it passes.
