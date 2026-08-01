# KeePassHO Callable Evidence-Set External Holdout Plan

## Objective

Replace the infrastructure-invalid ClashBox observation with a new, independent ArkTS
external holdout. Evaluate the frozen shadow evidence-set contract without changing
serving Context, compact projection, retrieval ranking, thresholds, budgets, or Oracles.

## Source And Independence

- repository: `https://github.com/aimilin6688/KeePassHO.git`;
- branch: `main`;
- reviewed head: `f4e80a3116d77492f54a382a87e66c3747f018de`;
- license: GPL-3.0;
- source size: 252 ArkTS files;
- local full clone: `/tmp/keepassho-evidence-set-holdout`;
- independence: no KeePassHO source, identifier, case, or prior result exists in the
  repository's consumed evaluation inventory.

All five pre-fix revisions were independently materialized with `git archive` before
case sealing. This preflight does not execute Context and does not expose the Oracle to
the Runtime.

## Case Portfolio

The reviewed history supplies five independent defect families:

1. search utility and page orchestration must jointly exclude recycle-bin records;
2. distributed KV callbacks must unpack typed `Value` objects before processing;
3. a new file Intent while locked spans Ability lifecycle and lock-window ownership;
4. S3 multipart initiation must distinguish canonical signing query from request URL;
5. WebDAV initialization must preserve an equivalent in-flight client session.

The portfolio covers single and multiple target scopes, file/callable/expression
localization, page/service/store/utility/adapter roles, and persistence, UI state,
event, navigation, platform, async, resource-I/O, and error-contract mechanisms.

## Execution Contract

1. Validate JSON and the calibrated ArkTS coverage contract without querying source.
2. Seal through `tools/agent_memory.py eval-seal-cases`, including Git revision and
   changed-file audits.
3. Verify the sealed digest and execute `eval-context-capability` exactly once.
4. Record formal Context and informational evidence-set metrics separately.
5. Never tune, edit, replace, or rerun any case after execution.
6. Keep the evidence-set provider shadow-only regardless of the observed result.

## Stop Rules

- Any source materialization failure invalidates and consumes the pack.
- A retrieval failure becomes a new project-neutral development reproduction, not a
  direct production patch.
- Promotion requires formal system gates and evidence-set gates; shadow success alone
  is insufficient.
- Runtime output remains evidence context. The Agent CLI retains diagnosis and causal
  reasoning responsibility.

## References

- BEIR heterogeneous retrieval evaluation: https://arxiv.org/abs/2104.08663
- Selective prediction: https://arxiv.org/abs/1705.08500
- TREC evaluation methodology: https://trec.nist.gov/howto.html
- Repository policy: `docs/evaluation-and-change-policy.md`

## Execution Result

The pack was sealed with digest
`d3be3e541193749ea96a061838726f3290cc9773bec0f8641cebb796d2376ec3` and executed
exactly once. Source materialization, five isolated index builds, case snapshots, and
seal verification all completed, so the observation is valid. The formal Context gate
failed 0/5 and promotion remains denied.

The failure is layered rather than an empty-index artifact. Hierarchical file recall is
0.8, while callable and range recall are both 0.0. The informational evidence-set
profile reports 0.2 target-scope accuracy, 0.5 member recall, 0.6 primary precision, and
0.0 state accuracy; all five cases conservatively resolve to `insufficient` and serving
projection remains unchanged. Compactness passes at 1,443.8 estimated tokens.

The consumed result is frozen in
`docs/eval/keepassho-evidence-set-unseen-holdout-result.json`. No case, Oracle, threshold,
ranking rule, or Provider behavior was changed after observation. The next admissible
repair must reproduce at least two independent callable/range defect classes in new
project-neutral development fixtures and revalidate the public serving output before a
future, different external holdout.

Post-run verification passes 93/93 focused workspace, Context, evidence-set, exclusion,
semantic callable, hierarchical localization, source-window, and log-contract tests.
Repository-wide Python compilation, evaluation JSON parsing, diff hygiene, fixed four
Skills, and the 500-line Python limit also pass.
