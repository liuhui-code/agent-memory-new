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

## Agent A/B Result

The authorized preregistered v2 schedule completed all 48 valid Codex `gpt-5.5` calls:
four paired trials per case, two baseline-first and two Context-first. All 24 pairs are
complete. The model, reasoning effort, treatment boundary, response schema, and prompt
protocol digest are consistent across observations. Baseline observations contain zero
Runtime Context bytes; every Context observation contains a non-empty payload.

| Metric | Baseline | Context | Delta |
| --- | ---: | ---: | ---: |
| Agent outcome score | 0.6809 | 0.7066 | +0.0257 |
| Root-cause accuracy | 0.6667 | 0.7083 | +0.0416 |
| Expected-file recall | 0.5764 | 0.6111 | +0.0347 |
| Predicted-file precision | 1.0000 | 0.9792 | -0.0208 |
| Mechanism evidence score | 0.8472 | 0.8264 | -0.0208 |
| Average token estimate | 196,910 | 184,936 | -6.08% |
| Average end-to-end time | 70.429 s | 76.968 s | +9.28% |
| Average source searches | 2.00 | 1.50 | -25.00% |

The average outcome uplift is not stable enough to promote. Context regresses two of
six case means, including Legado outcome by 0.0437 and expected-file recall by 0.125.
Moonlight improves average outcome by 0.0660 but lowers mechanism evidence by 0.0416;
NGA has no quality gain while token cost increases by 16.24%. Across all paired runs,
median token overhead is -5.68%, but worst-pair token overhead is +92.77%. Median
end-to-end overhead is +13.04%, with a +78.70% worst pair.

The quality gate fails every-case outcome non-regression, trial stability, and bounded
source exploration. The efficiency gate fails per-case token, latency, search, and
source-read limits. Context reliably reduces non-anchor exploration on average, but it
does not yet convert that guidance into stable causal grounding or bounded total cost.

One attempted request before the 48 valid observations returned HTTP 400 because the
strict nested JSON Schema did not require its optional `symbol` property. It produced no
model response and is excluded from the sample. The schema was corrected before all
valid calls, regression-tested, and the same resulting protocol digest is present in
every counted observation.

## Final Decision

Both the model-free Context capability gate and the Agent A/B promotion gate are
`no-go`. No serving-path change is authorized. The evidence assigns the next work to
two contracts rather than a case-specific ranking patch:

1. Preserve producer-consumer and UI-to-service evidence through candidate generation
   and compact localizer composition.
2. Make the Agent consume supplied anchors with bounded expansion and explicit stop
   conditions, without lowering the preregistered quality or cost limits.

Repairs require independent Development reproductions and the actual `query_handoff`.
These six Development cases may diagnose the missing contracts, but they must not be
relabelled as a holdout or used for a promotion claim.

Machine-readable aggregate evidence is in
`docs/eval/context-utility-development-aggregate.json` and
`docs/eval/context-utility-agent-ab-result.json`; full observations and per-project
Context/A/B results are preserved beside their case packs.
