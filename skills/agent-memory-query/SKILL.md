---
name: agent-memory-query
description: Use when the user asks to query, search, recall, inspect, design against, or retrieve project memory, current code structure, logs, incidents, impact evidence, or codebase wiki context.
---

# Agent Memory Query

Route the request to one focused protocol and query bounded project memory for the local Agent CLI. The Runtime returns historical experience, code-log keywords, current code anchors, and stored graph edges. The Agent CLI owns temporary-log analysis, candidate causes, call/causal chains, diagnosis, design decisions, and verification.

## Route

Choose one primary protocol. Do not load every reference.

| Intent | Primary protocol |
|---|---|
| Understand files, symbols, routes, resources, or current behavior | `references/code-understanding.md` |
| Diagnose an error, symptom, runtime log, or incident | `references/incident-diagnosis.md` |
| Review a change, regression risk, affected files, or test scope | `references/change-impact.md` |
| Design a feature, refactor, interface, state flow, or module boundary | `references/code-design.md` |
| Recall or judge historical memory, corrections, or trust | `references/evidence-policy.md` |

If multiple intents apply, start with the user's requested outcome. Load a second protocol only when the first protocol explicitly requires that handoff.

## Selective Retrieval

Use the cheapest investigation level that can answer the request:

- **L0 current source first:** when the user supplies a file/line, compiler symbol, failing test, route, resource key, or configuration value that can be checked within three files and two source searches. Do not call Memory if current source and a direct verification settle the issue.
- **L1 compact context:** when the request contains a runtime log/error code, has no known emitter, crosses modules, lifecycle/callback/async boundaries, has competing causes, depends on business meaning, asks about history, or remains unresolved after the L0 budget.
- **L2 focused expansion:** query one exact log phrase, symbol, or Agent-produced candidate at a time with `--compact`. Remove `--compact` only to inspect full records, ranking audit, or one unresolved evidence conflict.

Memory selection is an Agent workflow decision, not a Runtime diagnosis. Never skip an explicit user request to query memory.

## Default Command

Use the compact historical query entry for L1 diagnosis and code understanding:

```bash
python tools/agent_memory.py context --project . --query "<user problem or Agent-extracted term>" --compact --json
```

For L2 audit expansion, run the same focused query without `--compact`. The full view is not the default Agent injection path.

For a design request, use the dedicated context facade:

```bash
python tools/agent_memory.py design-context --project . --query "<design goal>" --compact --json
```

The Runtime returns repository facts, project constraints, quality questions,
general design references, history, and evidence gaps. It does not recommend a
pattern or produce a design. Load `references/code-design.md`; the Agent owns
concern selection, alternatives, tradeoffs, the final design, and its plan.

Use `search` or `wiki-search` only when the selected protocol calls for a broader or code-only view. Do not pass temporary runtime-log files to Agent Memory.

## Authority

Use evidence in this order:

```text
explicit user constraints
  -> current source and current configuration
  -> active typed graph edges and current code logs
  -> observed runtime/incident evidence
  -> anchored semantic corrections
  -> verified experience
  -> advisory experience and episodes
```

Current source can invalidate memory. Recency cannot override intent, status, confidence, counter-evidence, or a current code anchor. An absent graph edge is an evidence gap, not proof that no dependency exists.

Treat experience candidates as advisory decision frames; verify them against current source, logs, tests, and code wiki evidence before use.

Read `references/evidence-policy.md` when the answer relies materially on reflections, semantic patches, conflict notes, trust labels, or retrieval feedback.

## Bounded Work

- Start from the user's natural-language goal.
- Apply the L0 budget before Memory only when the problem already has a precise current-source anchor.
- Prefer exact file, symbol, route, resource, log, request, or session anchors for follow-up queries.
- Respect query round, cursor, graph-depth, and result limits.
- Read compact `query_handoff.log_keywords`, code/log anchors, path candidates, relation hints, correction guards, and evidence gaps first.
- Analyze temporary runtime logs directly in the Agent session.
- Query each Agent-produced candidate cause separately; do not combine all candidates into one broad query.
- Infer call chains and causal chains from current source and runtime order in the Agent session.
- Never treat ranking, stored edges, or historical experience as a Runtime-produced diagnosis.
- Do not run merge, promotion, stale marking, or vault export from this skill.

## Output

Return only query results needed for the selected intent. Cite inspectable files, symbols, stored edges, code-log templates, or record ids. Separate current code, historical advice, and search misses. The local Agent CLI must summarize the user log, form competing causes, reconstruct call/causal chains from source, and verify its conclusion.
