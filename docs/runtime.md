# Agent Memory Runtime Specification

Version: 0.1
Status: Draft
Audience:
- Codex
- AI coding agents
- agent-memory runtime
- maintainers

Goal:
Define the execution protocol for:
- initialization
- querying
- updating
- reflection
- LLM interaction
- memory lifecycle

This document defines operational behavior, not implementation details.

---

# 1. System Overview

The system consists of four layers:

```text
LLM / Codex
    ↓
Skill / Protocol Layer
    ↓
tools/agent_memory.py
    ↓
SQLite + Obsidian Vault Mirror
```

The first MVP keeps the runtime intentionally small:

- SQLite is the source of truth.
- Obsidian Markdown is a generated mirror.
- Skills call `tools/agent_memory.py`.
- Query commands support `--json`.
- Keyword search ships before vector search.

See `docs/mvp-implementation-plan.md` for the full implementation plan.
