# Context Utility Development Gate

## Scope

This Development gate asks whether Runtime Context supplies useful evidence to a local
Agent CLI. It does not ask Runtime to diagnose defects. Six reviewed pre-fix cases were
selected from three previously unused, licensed ArkTS projects before any Runtime query.

| Project | Cases | Context pass | License |
| --- | ---: | ---: | --- |
| AlkaidLab/moonlight-harmony | 3 | 0 | GPL-3.0 |
| apap6628114/nga_harmony | 2 | 1 | GPL-2.0 |
| wip3l/legado-harmony | 1 | 0 | GPL-3.0 |

The source revisions, symptom-only tasks, lineage, expected files, and pre-fix mechanism
spans are recorded in the three `*-context-utility-development-cases.json` files. These
are classified Development data, not sealed holdouts.

## Context Result

| Metric | Result |
| --- | ---: |
| Cases passed | 1 / 6 |
| Candidate file recall@20 | 0.8056 |
| Final anchor recall | 0.4861 |
| Primary anchor recall | 0.4028 |
| Anchor precision | 0.4306 |
| Source excerpt recall | 0.4028 |
| Average Context tokens | 1,428 |
| Average index preparation | 78.862 s/case |
| Average query time | 8.284 s/case |
| Total local batch time | 571.550 s |

Only the single-file NGA notification identity case passed. Three cases first lost an
expected file in candidate generation, two first lost an expected file in localizer
selection, and one retained the expected anchor but did not establish primary evidence.

The strongest repeated defect is not total search failure. PiP and Legado both achieved
candidate recall@20 of 1.0, then lost `StreamPage.ets` and `ReadBook.ets` while reducing
the candidate set to compact evidence. Cross-file producer-consumer and UI-to-service
chains are therefore not reliably preserved by current ranking and composition.

## Decision

The Context gate is `no-go` for serving promotion:

- five of six cases fail;
- candidate-generation loss occurs across three cases;
- localizer loss reproduces in two independent projects;
- compactness passes, but the retained 1,428-token payload is not sufficiently complete.

No serving-path change is justified by these results alone. Any repair must reproduce
the missing contract in project-neutral Development fixtures and the actual
`query_handoff`, then pass regression and a new independent gate. Project identifiers,
task phrases, Oracle paths, and case-specific boosts are prohibited.

## Agent A/B Status

The preregistered v2 schedule is four paired trials per case, two baseline-first and two
Context-first, for 48 Agent calls. The external run has not started: sending the three
new frozen source contexts to Codex requires explicit user consent. No model output,
quality uplift, mechanism uplift, token delta, or end-to-end A/B cost claim is made yet.

Machine-readable aggregate evidence is in
`docs/eval/context-utility-development-aggregate.json`; full per-project Context results
are preserved beside their case packs.
