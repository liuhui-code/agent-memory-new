# Memory Calibration Layer Design

## Goal

Add a lightweight calibration layer to query results so Agents can tell whether a memory item is proof, a reusable experience, a weak hint, a warning, or a conflict-sensitive result before using it.

## Approach

The runtime will not add another storage table for this stage. It will annotate existing `context` and `search` results with:

- `trust_level`
- `trust_score`
- `trust_reasons`
- `retrieval_explanation`

The annotation is computed from existing fields: status, stale flag, confidence, quality score, rerank score, source/evidence/source cases, memory lane, feedback penalty, conflict notes, match reasons, and score.

## Trust Levels

- `source_truth`: current learned code/wiki/log evidence or semantic records with explicit evidence and high confidence.
- `verified_experience`: reflections with high quality, verification method, source cases, and no negative feedback.
- `usable_hint`: relevant records that are plausible but lack enough evidence to drive a conclusion.
- `weak_hint`: low confidence, low quality, weak evidence, or feedback-penalized records.
- `possibly_stale`: stale or archived/merged/rejected records returned for review context.
- `conflict_warning`: correction guards, semantic patch notes, or records with explicit conflict/misleading signals.

## Query Output

`context` and `search` will annotate these result groups:

- `semantic_facts`
- `reflections`
- `episodes`
- `wiki_matches`
- `code_log_matches`
- `edge_matches`
- `incident_trace_matches`
- `correction_guards`

Top-level output will also include `memory_use_policy`, a compact ordering rule:

```text
current_source > user_instruction > source_truth > verified_experience > usable_hint > weak_hint
```

Weak hints and conflict warnings may guide inspection, but they must not be treated as final conclusions.

## Skill Policy

`skills/agent-memory-query/SKILL.md` will tell Agents to read `trust_level`, `trust_reasons`, and `retrieval_explanation` before injecting a record into the answer. Current source and user instruction stay more authoritative than memory.

## Testing

Add unit tests that:

1. A verified procedure reflection receives `verified_experience`.
2. A stale/feedback-penalized reflection receives a weak or stale trust level.
3. `context --json` includes `memory_use_policy` and annotated result rows.

## Non-goals

- No vector database.
- No new long-lived calibration table.
- No automatic mutation of memory based on trust level.
- No change to the four user-facing skills.
