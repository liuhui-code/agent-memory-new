# Agent Memory MVP

## Project Mission

Build a local Agent Memory system that any coding agent can use through skills and a stable local runtime script.

The first MVP is not a full autonomous knowledge graph. It is a practical memory and reflection loop:

```text
Agent starts task
  -> memory skill queries local runtime
  -> runtime returns concise context
  -> Agent works with retrieved memory
  -> update / reflect skills store durable lessons
  -> Obsidian vault mirrors memory for human review
```

## MVP Scope

The MVP must support:

1. Initialize global memory-home storage with per-project isolation.
2. Store semantic facts, episodes, reflections, and lightweight codebase wiki entries.
3. Query relevant memory through a JSON-capable CLI.
4. Generate concise task context for an Agent.
5. Export Markdown into an Obsidian-compatible vault.
6. Provide four user-facing skills that call the runtime script.
7. Provide an installer and a doctor command.
8. Extract code log statements during code learning and connect them to files/functions through lightweight edges.

The MVP must not depend on:

- Vector databases
- Neo4j
- Daemon services
- A specific Agent CLI wrapper
- Obsidian as the source of truth
- A complete AST call graph

## Core Architecture

```text
LLM / Local Agent
  -> Agent Memory Skills
  -> tools/agent_memory.py
  -> ~/.agent-memory/projects/<project_id>/memory.db
  -> ~/.agent-memory/projects/<project_id>/vault/
```

Responsibilities:

- Skills define when and how an Agent should call memory operations.
- `tools/agent_memory.py` is the stable local API.
- SQLite is the machine-readable source of truth.
- Obsidian Markdown is a read-only human review mirror.
- The learned project directory is the input source; memory data is stored in a configurable global memory home.
- Natural language plus skills is the intended user interface; direct CLI usage is the backend and debugging interface.

## Runtime Commands

The runtime should expose these commands:

```bash
python tools/agent_memory.py init --project .
python tools/agent_memory.py doctor --project .
python tools/agent_memory.py update --project . --type semantic --fact "..."
python tools/agent_memory.py update --project . --type episode --task "..." --summary "..."
python tools/agent_memory.py context --project . --query "..." --json
python tools/agent_memory.py search --project . --query "..." --json
python tools/agent_memory.py reflect --project . --task "..." --summary "..." --lesson "..."
python tools/agent_memory.py reflect-review --project . --json
python tools/agent_memory.py vault-export --project .
python tools/agent_memory.py learn-entry --project . --entry "<file>" --depth 2 --json
python tools/agent_memory.py learn-path --project . --path "<directory>"
python tools/agent_memory.py learn-path --project . --path "<directory>" --replace
python tools/agent_memory.py wiki-index --project .
python tools/agent_memory.py wiki-search --project . --query "..." --json
python tools/agent_memory.py list --project . --type code-log --json
python tools/agent_memory.py list --project . --type memory-edge --json
python tools/agent_memory.py maintain-health --project . --json
python tools/agent_memory.py maintain-review --project . --json
python tools/agent_memory.py maintain-plan --project . --json
python tools/agent_memory.py miss-list --project . --status open --json
python tools/agent_memory.py miss-status --project . --id 1 --status resolved --resolution "..."
python tools/agent_memory.py maintain-status --project . --type semantic --id 1 --status stale --reason "..."
python tools/agent_memory.py maintain-merge --project . --type semantic --ids 1,2 --fact "..." --json
python tools/agent_memory.py maintain-promote --project . --episode-id 1 --fact "..." --json
python tools/agent_memory.py maintain-promote --project . --reflection-id 1 --fact "..." --json
```

All query commands must support `--json`.

## Skill Set

Create four user-facing skills:

- `agent-memory-learn`: learn code around an entry file, directory, or whole project.
- `agent-memory-query`: retrieve memory and codebase wiki context.
- `agent-memory-maintain`: initialize, health-check, refresh, and export the memory system.
- `agent-memory-reflect`: store lessons after a task, bug, or failed attempt.

Skills should call the runtime script. They should not implement storage logic themselves.

## Installed Layout

```text
~/.agent-memory/
  config.json
  projects/
    <project_id>/
      memory.db
      config.json
      runtime/
        last_context.json
        last_reflection.json
      vault/
        index.md
        Episodes/
        Reflections/
        Semantic Facts/
        Codebase Wiki/
        Daily/

.agent-skills/
  agent-memory-learn/
  agent-memory-query/
  agent-memory-maintain/
  agent-memory-reflect/

tools/
  agent_memory.py
```

## Development Rules

1. Keep the runtime boring and deterministic.
2. Prefer keyword search before adding embeddings.
3. Keep memory injection under 1500 words.
4. Never treat historical memory as more authoritative than current source files.
5. Mark stale or low-confidence memory explicitly.
6. Make initialization and export commands idempotent.
7. Do not edit shell profiles automatically from the installer.
8. Record meaningful local development changes in `gitlog.md`.
9. Design new workflows so the LLM invokes skills first, and skills invoke runtime commands.
10. Keep query fast: consume governance metadata in query, run heavier review/merge/promote work through maintain.

## Primary Plan

See `docs/mvp-implementation-plan.md`.

## Usage Guide

See `docs/usage-guide.md`.
