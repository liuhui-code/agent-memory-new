# Task-Specific Context Sufficiency Protocol

## Objective

Make the three existing context products explicit about the first round of
retrieval: whether an Agent can begin source inspection, what evidence is
missing, and the one bounded expansion action. The Runtime remains an evidence
provider. It must not diagnose, choose a design, reconstruct a runtime trace,
or decide change impact.

The protocol is intentionally task-specific. Diagnosis, design, and change
impact need different minimum evidence, so a generic global score would hide
meaningful differences and invite false confidence.

## Contract

Every compatible output carries a read-only `sufficiency` object with:

- `kind`: `diagnosis`, `design`, or `impact`.
- `status`: readiness state for the next Agent action, not outcome quality.
- `next_action`: one bounded retrieval or inspection action.
- `reason_codes`: stable observable evidence gaps for evaluation attribution.
- `coverage`: compact counts and booleans derived from already returned data.
- `scope` and `agent_ownership`: an explicit boundary that preserves Agent
  reasoning ownership.

`context --compact` reports source-anchor readiness for Agent-led log/source
inspection. It is ready only when at least one code anchor can be located in a
source file; log and path evidence enrich inspection but do not establish a
diagnosis. Freshness drift requires a refresh before inspection.

`design-context` reports orientation readiness when repository source anchors
exist. Explicit constraints and Agent-confirmed anchors promote the state to
agent-directed refinement. It never recommends a pattern, compares candidates,
or selects a design.

`impact-scope` reports verification readiness only for learned changed files
with direct scope evidence. Any unlearned changed file requires a refresh.
Dependencies and recommended tests remain leads for the Agent to validate, not
an accepted impact conclusion.

## Architecture

`context_sufficiency.py` is a narrow pure adapter over existing output fields.
It issues no query, writes no memory, calls no model, and adds no new skill or
CLI command. Existing facades remain the only user-facing entry points:

```text
existing evidence and freshness
        |
        +--> context --compact ------> diagnosis readiness
        +--> design-context ---------> design readiness
        +--> impact-scope -----------> impact readiness
                                      |
                                      +--> Agent CLI inspects and reasons
```

This keeps the project boundary intact: SQLite-backed Runtime retrieval supplies
bounded current-source, graph, log-code, and memory context; the local Agent
owns temporary-log analysis, hypothesis formation, tradeoffs, and verification.

## Execution Plan

- [x] Audit current diagnosis, design, and impact output contracts and their
  evaluation boundary.
- [x] Define independent minimum-evidence states rather than a global score.
- [x] Add a pure, read-only sufficiency adapter and attach it to all three
  existing outputs.
- [x] Add project-neutral ArkTS integration regressions plus no-evidence,
  freshness-drift, and unlearned-change unit cases.
- [x] Run the protocol in shadow mode through `eval-context-capability`.
  It reports per-status and reason-code distributions but does not gate a
  release; calibration packs will provide the first longitudinal observation.
- [ ] After frozen calibration labels exist, add per-kind precision/recall and
  false-ready metrics. Promote only if they improve without reducing strict
  context-gate recall or violating the 1,500-token compact budget.
- [ ] Evaluate a fresh sealed external holdout once. Never tune from its
  observed output; create a new development pack for any repair.

## Evaluation and Governance

The first implementation is an informational observation, analogous to the
existing evidence funnel. Stable reason codes permit later attribution without
recording Agent reasoning or asking users to label every query. A readiness
state is correct only if its stated minimum evidence is present; it is not a
claim that the Agent reaches the right root cause, design, or impact result.

Follow the existing split discipline: editable development cases for repairs,
frozen calibration for threshold selection, and sealed holdouts for the final
external observation. Do not reuse prior observed external cases as tuning
data.

## References

- OpenAI, [A shared playbook for trustworthy third-party evaluations](https://openai.com/index/trustworthy-third-party-evaluations-foundations/): report the harness, task distribution, system settings, budgets, elicitation, and validity checks behind a claim.
- Anthropic, [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents): use task-specific, multi-dimensional evaluation rather than one generic success number.
- TREC, [How to build a test collection](https://trec.nist.gov/howto.html): keep development data separate from final relevance judgments.
- BEIR, [A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models](https://arxiv.org/abs/2104.08663): test retrieval robustness across distinct domains instead of a single tuned corpus.
