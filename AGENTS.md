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
