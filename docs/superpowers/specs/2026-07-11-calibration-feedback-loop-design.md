# Calibration Feedback Loop Design

## Goal

Let query trust labels learn from usage feedback without adding a new long-term feedback system.

## Design

Calibration feedback reuses the existing `retrieval_feedback` table and command. The runtime adds calibration-specific reason codes:

- `useful`
- `verified_useful`
- `overtrusted`
- `undertrusted`

Negative retrieval reasons still down-rank results for similar queries. Positive calibration reasons raise answer-time trust for similar queries only. `overtrusted` lowers trust and emits a governance action because the row looked too strong for the actual outcome. `undertrusted` raises trust slightly and emits a governance action because the row was more useful than the runtime believed.

## Query Behavior

`context` and `search` already expose `trust_level`, `trust_score`, and `retrieval_explanation`. The feedback loop adds:

- `calibration_feedback_bonus`
- `calibration_feedback_penalty`
- `calibration_feedback_reasons`
- `calibration_feedback_ids`

The existing trust calculation consumes those fields. It does not mutate the source record.

## Governance

`maintain-plan` continues to emit `review_retrieval_feedback` for ordinary weak/misleading retrieval feedback. It also emits:

- `review_overtrusted_memory`
- `review_undertrusted_memory`

These actions are review prompts. They may lead to confidence updates, trigger tightening, evidence strengthening, stale marking, or doing nothing if the feedback was not reproducible.

## Non-goals

- No new table.
- No automatic confidence mutation.
- No new user-facing skill.
- No change to raw query ranking beyond existing feedback penalties.
