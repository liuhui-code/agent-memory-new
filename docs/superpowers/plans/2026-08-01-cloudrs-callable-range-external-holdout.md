# Cloudrs Callable-Range External Holdout Plan

## Objective

Evaluate the frozen ArkTS file, callable, and source-range retrieval capability against
five independent defects from a previously unused external project. The Runtime must
surface compact source context; diagnosis and causal judgment remain the Agent CLI's
responsibility.

This stage is evidence collection. It does not authorize changes to serving ranking,
query expansion, callable extraction, source windows, thresholds, or budgets.

## Source And Independence

- repository: `https://github.com/Cloudrs/Cloudrs-ohos.git`;
- branch: `main`;
- reviewed head: `d9fa4ca4a0179723666296aec57f980cf7dfe9b1`;
- license: GPL-3.0;
- source size: 115 ArkTS/TypeScript files;
- local full clone: `/tmp/agent-memory-cloudrs-ohos-holdout`;
- independence: Cloudrs was absent from the repository's consumed evaluation inventory
  when the five cases were selected.

All five cases and their task wording, expected files, callables, and source ranges were
fixed before Context execution. Ten before/after revisions were independently
materialized with `git archive`, and each declared target file was checked against the
real fix diff.

During source review, the frozen low-level callable-range parser was invoked once on the
five pre-fix source snapshots to confirm line-boundary notation. This was a static
preflight only: it did not run the public Context pipeline, expose an Oracle to Runtime,
change case selection, or trigger an implementation change. One unsupported builder
header was retained unchanged, so the probe cannot improve the measured outcome.

## Case Portfolio

1. a short batch completes before its progress sheet finishes opening;
2. conditional tab construction destroys the album component and flashes empty state;
3. lossy filename sanitization aliases distinct Chinese draft identifiers;
4. cross-session download resume reuses an expired signed URL and trusts a short file;
5. a settings-sheet close animation races with a new open request.

The portfolio spans UI timing, component lifecycle, persistence identity, transfer
integrity, and lifecycle races. It includes dense source files, a multiline method
header, and an ArkUI `@Builder` callable.

## Execution Contract

1. Validate source provenance, exact diffs, revisions, JSON, and ArkTS coverage without
   running Context.
2. Seal through `tools/agent_memory.py eval-seal-cases`; the sealed digest is immutable.
3. Execute `eval-context-capability` exactly once against the sealed pack.
4. Persist the complete raw JSON result immediately, including failures.
5. Do not edit, replace, soften, or rerun a consumed case.
6. Any observed defect must first become project-neutral development evidence in a later
   stage before production behavior may change.

## Validity And Stop Rules

- A missing revision, failed source materialization, empty isolated index, invalid seal,
  or incomplete case snapshot invalidates but still consumes the run.
- A valid retrieval failure is capability evidence, not permission for a local patch.
- No same-project follow-up holdout is admissible after this execution.
- A future gate must use a new project and be defined before any new implementation.
- Fixed four Skills, SQLite truth, one Runtime entry point, and the 500-line Python limit
  remain mandatory.

## References

- BEIR heterogeneous retrieval evaluation: https://arxiv.org/abs/2104.08663
- TREC reusable evaluation methodology: https://trec.nist.gov/howto.html
- Selective prediction and abstention: https://arxiv.org/abs/1705.08500
- Repository policy: `docs/evaluation-and-change-policy.md`

## Execution Result

The pack was sealed with digest
`661cfe13bd116f6642651f9dc9ba460ab1fa64aff7734ed0822df2ff2564ac79` and executed
exactly once. All five immutable source revisions materialized, all five isolated
indexes were built, and every case returned non-empty file and callable candidate
pools. The observation is therefore valid rather than an infrastructure failure.

The formal Context gate failed 0/5. Candidate-file recall at 20 and hierarchical file
recall are both 0.8, while callable and range recall are both 0.0. One case returned the
correct source span and top-ranked expected file, but failed precision because four
anchors survived the compact projection; the other four cases did not return the
required source excerpt. Average compact Context is 1,463.2/1,500 estimated tokens and
passes the budget gate.

The evidence funnel attributes first loss to callable localization in three cases,
candidate-file retrieval in one case, and localizer-file ranking in one case. All five
shadow evidence sets conservatively report `insufficient`, with 0.6 member recall and
0.6 primary precision; serving projection remains unchanged. The result is frozen in
`docs/eval/cloudrs-callable-range-external-holdout-result.json`. No production behavior,
case, Oracle, threshold, or budget was changed after observation.

Post-run benchmark workspace and Context runner tests pass 29/29. Python compilation
passes with its cache redirected to `/tmp`; all evaluation JSON, diff hygiene, exactly
four Skills, and the 500-line Python limit pass.
