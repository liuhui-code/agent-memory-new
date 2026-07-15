---
name: agent-memory-query
description: Use when the user asks to query, search, recall, inspect, design against, or retrieve project memory, current code structure, logs, incidents, impact evidence, or codebase wiki context.
---

# Agent Memory Query

Route the request to one focused protocol, retrieve bounded evidence, and keep current source more authoritative than memory.

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

## Default Command

Use coordinated evidence for substantial work:

```bash
python tools/agent_memory.py evidence-context --project . --query "<goal>" --json
```

Pass an explicit goal only when the intent is clear:

```bash
python tools/agent_memory.py design-assist --project . --query "<design goal>" --mode design-only --json
```

For design intent, prefer `design-assist` as the simple natural-language entry.
It returns a compact repository baseline, recognized structural patterns,
applicable pattern candidates, principle checks, required decisions, and an
unclaimed Delta template. Load `references/code-design.md` before authoring a
candidate. Use the lower-level design commands only as that protocol requires.

Use `context`, `search`, or `wiki-search` only when the selected protocol calls for a narrower view.

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
- Prefer exact file, symbol, route, resource, log, request, or session anchors for follow-up queries.
- Respect query round, cursor, graph-depth, and result limits.
- Read `evidence_gaps` and causal levels before concluding.
- Never present `association` as verified causality.
- Do not run merge, promotion, stale marking, or vault export from this skill.

## Output

Return only evidence needed for the selected intent. Cite inspectable files, symbols, edges, logs, or record ids. Separate current facts, assumptions, historical advice, risks, and verification actions. If evidence is incomplete, say what must be inspected instead of filling the gap with a remembered pattern.
