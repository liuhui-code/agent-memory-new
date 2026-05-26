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
- Entry-file and directory-based codebase learning
- Lightweight codebase wiki indexing and search
- Obsidian-compatible Markdown export
- Memory governance: health, review, stale, merge, promote, archive/reject status
- Install script for runtime and skills
- Doctor command for verification

## Runtime Commands

```bash
python tools/agent_memory.py init --project .
python tools/agent_memory.py doctor --project .
python tools/agent_memory.py update --project . --type semantic --fact "..."
python tools/agent_memory.py context --project . --query "..." --json
python tools/agent_memory.py reflect --project . --task "..." --summary "..." --lesson "..."
python tools/agent_memory.py vault-export --project .
python tools/agent_memory.py learn-entry --project . --entry tools/agent_memory.py --depth 2 --json
python tools/agent_memory.py learn-path --project . --path skills
python tools/agent_memory.py learn-path --project . --path skills --replace
python tools/agent_memory.py wiki-index --project .
python tools/agent_memory.py wiki-search --project . --query "..." --json
python tools/agent_memory.py maintain-health --project . --json
python tools/agent_memory.py maintain-review --project . --json
python tools/agent_memory.py maintain-status --project . --type semantic --id 1 --status stale --reason "..."
python tools/agent_memory.py maintain-merge --project . --type semantic --ids 1,2 --fact "..." --json
python tools/agent_memory.py maintain-promote --project . --episode-id 1 --fact "..." --json
```

## Documentation

- `agent.md`: project mission and agent-facing rules
- `AGENTS.md`: concise repository instructions for coding agents
- `docs/usage-guide.md`: skill-first usage guide and entry-file learning direction
- `docs/templates/diagnosis-memory-query-template.md`: recursive memory-query template for bug diagnosis skills
- `docs/templates/change-design-memory-query-template.md`: recursive memory-query template for design/change planning skills
- `docs/mvp-implementation-plan.md`: detailed MVP implementation plan
- `docs/runtime.md`: runtime protocol notes
- `docs/phase-2-memory-governance-plan.md`: Phase 2 governance and consolidation plan
- `gitlog.md`: local development log for changes and rollback notes

## Current Status

MVP runtime is implemented. Phase 2 adds memory governance while preserving the four-skill user interface.
