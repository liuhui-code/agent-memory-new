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
