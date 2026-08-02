# Staged Context Value Closure

## Scope

This run evaluates whether the public Runtime can supply evidence for two Agent-led
investigation stages without asking the Runtime to diagnose the incident:

- `orientation`: identify the likely code area from the reported symptom or log;
- `focused`: inspect one candidate mechanism selected by the Agent.

The base Oracle remains reserved for a later Agent A/B. A stage override changes only
the Context evidence expected for that query. All source revisions and changed files
were verified before sealing.

## Results

| Source | Governance | Orientation | Focused | Avg tokens | Decision |
| --- | --- | ---: | ---: | ---: | --- |
| HPRichText | valid, consumed once | fail | pass | 1,186.5 | Context gate failed |
| DSBridge-HarmonyOS | valid, consumed once | fail | fail | 1,467.5 | Context gate failed |
| Melotopia-HMOS | invalid, duplicate execution | not interpretable | not interpretable | not interpretable | excluded |

HPRichText retained the expected files in candidate and localizer stages, but the
orientation result lost one expected file during compact evidence selection. Its
focused parser query passed. DSBridge retained the expected file in the candidate and
file-localizer stages, but callable/range evidence did not identify the relevant class
field arrow implementation and the final anchor set was imprecise.

These failures do not establish one shared missing serving contract: HPRichText first
loses evidence during compact composition, while DSBridge first loses callable/range
localization. The policy therefore forbids a production architecture change based on
these holdouts. Neither valid pack may be rerun or used for tuning.

## Decision

The Context promotion gate is closed, so no source-only versus source-plus-Context Agent
A/B was run. This is a valid negative result, not an optimization failure claim: the
Runtime has not yet demonstrated that it can reliably supply the evidence an Agent
would need for these new tasks.

The next repair loop must first reproduce each failure in independent development
fixtures. Only a missing contract demonstrated by at least two independent defect
classes may change serving architecture. A subsequent promotion attempt must use a new,
previously unused sealed external source.

The duplicate Melotopia execution is preserved in
`melotopia-staged-context-holdout-invalid-run.json`; its measurements cannot support
retrieval, promotion, or regression claims.

## Verification

The directly affected evaluation and governance chain passes 98/98 tests. JSON,
compilation, diff hygiene, exactly four Skills, and the 500-line code limit pass. The
CI scale profile passes on an independent second run at 100,000 searchable entities and
300,000 edges; the first run narrowly exceeded two incremental-maintenance latency
thresholds and remains recorded as a performance-variance signal. No serving or SQL
change was made in response.
