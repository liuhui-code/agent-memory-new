# Agent Memory MVP

A local memory and reflection runtime for coding agents.

The system lets a local Agent query previous project facts, task episodes, reflections, and lightweight codebase wiki entries through skills that call a stable local script.

The primary user experience is skill-first: users ask the Agent in natural language, the Agent chooses the relevant memory skill, and the skill calls `tools/agent_memory.py`.

## Architecture

```text
LLM / Local Agent
  -> Agent Memory Skills
  -> tools/agent_memory.py
  -> SQLite
  -> Obsidian Vault mirror
```

## MVP Features

- Project-local memory initialization
- Semantic facts
- Task episodes
- Reflections and future rules
- Keyword-based memory context retrieval
- Lightweight codebase wiki indexing
- Obsidian-compatible Markdown export
- Install script for runtime and skills
- Doctor command for verification

## Planned Runtime Commands

```bash
python tools/agent_memory.py init --project .
python tools/agent_memory.py doctor --project .
python tools/agent_memory.py update --project . --type semantic --fact "..."
python tools/agent_memory.py context --project . --query "..." --json
python tools/agent_memory.py reflect --project . --task "..." --summary "..." --lesson "..."
python tools/agent_memory.py vault-export --project .
python tools/agent_memory.py wiki-index --project .
python tools/agent_memory.py wiki-search --project . --query "..." --json
```

## Documentation

- `agent.md`: project mission and agent-facing rules
- `AGENTS.md`: concise repository instructions for coding agents
- `docs/usage-guide.md`: skill-first usage guide and entry-file learning direction
- `docs/mvp-implementation-plan.md`: detailed MVP implementation plan
- `docs/runtime.md`: runtime protocol notes
- `gitlog.md`: local development log for changes and rollback notes

## Current Status

Planning phase. The first implementation milestone is `tools/agent_memory.py init` plus `doctor`.
