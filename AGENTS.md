# Agent Instructions

This repository builds the Agent Memory MVP described in `agent.md`.

When working in this repo:

1. Read `agent.md` and `docs/mvp-implementation-plan.md` before implementation.
2. Keep the first version focused on Skill-driven Memory Runtime.
3. Use `tools/agent_memory.py` as the only runtime entry point.
4. Keep SQLite as the source of truth.
5. Treat Obsidian Vault output as a generated human-readable mirror.
6. Update `gitlog.md` after meaningful local changes.

Avoid adding vector databases, daemon processes, graph databases, or Agent-specific wrappers until the MVP is complete and verified.

## Non-Negotiable Evaluation and Change Policy

Read `docs/evaluation-and-change-policy.md` before changing retrieval, ranking,
graph, source excerpt, semantic extraction, or evaluation behavior. Its rules are
mandatory.

In particular:

1. Do not invent logs, symptoms, causal links, or Oracle evidence.
2. Do not call an unclassified evaluation pack a holdout or external gate.
3. A seal proves immutability, not case validity or causal correctness.
4. Shadow and informational outputs may form hypotheses only; they cannot justify a serving-path change or promotion claim.
5. Reproduce a suspected serving defect in an independent development fixture and in the actual `query_handoff` before changing production behavior.
6. Change an evaluator only when it misclassifies a controlled case with a known expected result.
7. Change architecture only when at least two independent defect classes demonstrate the same missing contract.
8. Never tune on, edit, or rerun a consumed sealed holdout.
9. Stop when evidence cannot identify the failing layer. Record the gap instead of adding a speculative feature.
10. Keep Runtime responsible for evidence context; keep diagnosis and design reasoning in the local Agent CLI.
