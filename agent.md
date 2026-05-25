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

1. Initialize project-local memory storage.
2. Store semantic facts, episodes, reflections, and lightweight codebase wiki entries.
3. Query relevant memory through a JSON-capable CLI.
4. Generate concise task context for an Agent.
5. Export Markdown into an Obsidian-compatible vault.
6. Provide skills that call the runtime script.
7. Provide an installer and a doctor command.

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
  -> .agent-memory/memory.db
  -> .agent-memory/vault/
```

Responsibilities:

- Skills define when and how an Agent should call memory operations.
- `tools/agent_memory.py` is the stable local API.
- SQLite is the machine-readable source of truth.
- Obsidian Markdown is a read-only human review mirror.

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
python tools/agent_memory.py vault-export --project .
python tools/agent_memory.py wiki-index --project .
python tools/agent_memory.py wiki-search --project . --query "..." --json
```

All query commands must support `--json`.

## Skill Set

Create six skills:

- `agent-memory-init`: initialize and verify memory storage.
- `agent-memory-query`: retrieve context before substantial work.
- `agent-memory-update`: store durable facts and episodes.
- `agent-memory-reflect`: store lessons after a task, bug, or failed attempt.
- `agent-memory-wiki`: index and search the lightweight codebase wiki.
- `agent-memory-vault`: export SQLite memory into Obsidian Markdown.

Skills should call the runtime script. They should not implement storage logic themselves.

## Project-Local Installed Layout

```text
.agent-memory/
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
  agent-memory-init/
  agent-memory-query/
  agent-memory-update/
  agent-memory-reflect/
  agent-memory-wiki/
  agent-memory-vault/

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

## Primary Plan

See `docs/mvp-implementation-plan.md`.
