# Agent Context Utility Development Gate

## Goal

Measure whether the Runtime's evidence context helps a local Agent CLI diagnose real
ArkTS defects. Runtime remains an evidence supplier. The Agent remains responsible for
reasoning, diagnosis, and the final causal claim.

## Fixed Inventory

The Development inventory was selected before any Runtime query:

- Moonlight Harmony: manual refresh terminates background mDNS, PiP uses an oversized
  window viewport, and QR scan is offered on devices without ScanBarcode capability.
- NGA Harmony: notification rows reuse identity after `seen` changes, and automatic
  check-in success is not surfaced.
- Legado Harmony: change-source candidates remain hidden until the full search ends.

All three repositories are public and carry SPDX-recognized GPL licenses. Tailscale-OHOS
was rejected because GitHub exposed no recognizable repository license. Broad mixed
commits and previously consumed projects were also rejected.

## Evidence Contract

1. Each task contains symptom text only. Later revisions, commit messages, expected
   files, and mechanism spans are hidden from the Agent.
2. The source is materialized at each case's `before_revision`.
3. Oracle spans were recorded from the reviewed pre-fix source before Runtime queries.
4. A Context result may support a hypothesis but cannot diagnose the issue itself.
5. This inventory is Development data. It is editable only through an explicit review;
   it is not a sealed holdout and cannot support a release claim.

## A/B Protocol

- Model: `gpt-5.5`, low reasoning effort.
- Four paired trials per case, with two baseline-first and two Context-first trials.
- The investigation protocol, source revision, timeout, response schema, and scoring
  remain identical. Only the Runtime Context payload changes.
- Retrieval and preparation time count toward the Context arm's end-to-end cost.
- Primary quality measures: expected-file recall, forbidden-file precision, root-cause
  category, causal support, and mechanism-span grounding.
- Cost measures: paired wall time, tokens, and end-to-end Context overhead.

## Decision Rules

- `go`: no material worst-case regression, mechanism grounding improves or remains
  stable, and median paired cost remains within the registered efficiency budget.
- `no-go`: Context decreases mechanism grounding, creates a repeated false direction,
  or fails the Context capability gate on multiple independent defect classes.
- `insufficient`: failures cannot be assigned to materialization, indexing, retrieval,
  composition, or Agent reasoning. Record the missing observation instead of changing
  serving behavior.

No serving-path change is permitted from this run alone. A production change still
requires reproduction in an independent fixture and the actual `query_handoff`, as
required by `docs/evaluation-and-change-policy.md`.

## Execution Closure

User consent was received to send the frozen GPL source contexts. The full balanced
schedule completed with 48 valid calls and 24 complete pairs. All counted observations
used Codex `gpt-5.5`, low reasoning effort, and protocol digest
`07b27c526bd43c7625b942608efd4927b196c860c29911a645edfccda31cc765`.

The aggregate outcome score improves by 0.0257 and expected-file recall by 0.0347, but
mechanism evidence falls by 0.0208. Two case means regress, trial stability fails, and
the efficiency gate fails despite a 5.68% median paired token reduction because median
end-to-end latency grows 13.04% and worst-pair token/latency overhead reaches 92.77% and
78.70%. The registered decision is therefore `no-go`; no serving change is allowed.

An initial pre-sample request failed with HTTP 400 due to an invalid strict nested JSON
Schema. It returned no model output and was not counted. The schema contract was fixed
and tested before the 48 valid observations; no gate threshold or Oracle was changed.
