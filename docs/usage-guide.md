# Agent Memory Usage Guide

This project is designed for skill-first usage.

The user should not need to remember low-level commands during normal work. The intended flow is:

```text
User says what they want in natural language
  -> LLM chooses an Agent Memory skill
  -> Skill calls tools/agent_memory.py
  -> Runtime reads or writes SQLite
  -> Obsidian vault is exported for human review
```

The CLI remains the stable backend API and a debugging escape hatch.

## 1. Install Into A Project

Run this once from the project root:

```bash
python install.py --project . --local-skills
```

This creates:

```text
.agent-memory/
.agent-skills/
tools/agent_memory.py
```

Verify:

```bash
python tools/agent_memory.py doctor --project .
```

## 2. Normal Skill-First Usage

Prefer asking the Agent in natural language:

```text
Initialize memory for this project.
```

Expected skill path:

```text
agent-memory-init
  -> python tools/agent_memory.py init --project .
  -> python tools/agent_memory.py doctor --project .
```

Ask:

```text
Before editing, check whether we have relevant memory for this task.
```

Expected skill path:

```text
agent-memory-query
  -> python tools/agent_memory.py context --project . --query "<task>" --json
```

Ask:

```text
Remember that this project treats SQLite as the source of truth.
```

Expected skill path:

```text
agent-memory-update
  -> python tools/agent_memory.py update --project . --type semantic --fact "..." --source user --confidence 1.0
```

Ask:

```text
Reflect on this task and save the lesson.
```

Expected skill path:

```text
agent-memory-reflect
  -> python tools/agent_memory.py reflect ...
  -> python tools/agent_memory.py vault-export --project .
```

## 3. Current Codebase Wiki Usage

For the current MVP, codebase memory is lightweight and project-scoped.

Ask:

```text
Index this project into the codebase wiki.
```

Expected skill path:

```text
agent-memory-wiki
  -> python tools/agent_memory.py wiki-index --project .
```

Ask:

```text
Search the codebase wiki for memory runtime commands.
```

Expected skill path:

```text
agent-memory-wiki
  -> python tools/agent_memory.py wiki-search --project . --query "memory runtime commands" --json
```

## 4. Planned Entry-File Learning

The next usability improvement should let users add only part of a project to memory by naming an entry file.

Target user request:

```text
Learn the code around tools/agent_memory.py and add it to memory.
```

Target skill path:

```text
agent-memory-wiki
  -> python tools/agent_memory.py learn-entry --project . --entry tools/agent_memory.py --depth 2
```

Target behavior:

```text
Read the entry file
  -> extract project-local imports
  -> follow related files up to depth
  -> index only that file set
  -> write wiki entries
  -> save an episode explaining what was learned
```

Target request for a directory:

```text
Learn the memory skills directory.
```

Target skill path:

```text
agent-memory-wiki
  -> python tools/agent_memory.py learn-path --project . --path skills
```

## 5. Manual CLI Fallback

When debugging or scripting, call the runtime directly:

```bash
python tools/agent_memory.py update --project . --type semantic --fact "..." --source user --confidence 1.0
python tools/agent_memory.py context --project . --query "..." --json
python tools/agent_memory.py reflect --project . --task "..." --lesson "..."
python tools/agent_memory.py vault-export --project .
```

## 6. Obsidian Review

Export the vault:

```bash
python tools/agent_memory.py vault-export --project .
```

Open this directory in Obsidian:

```text
.agent-memory/vault/
```

Obsidian is a read-only review mirror in the MVP. Edit memory through skills or CLI commands, then export again.

## 7. Design Rule

When adding new features, preserve this direction:

```text
Natural language request first
Skill chooses action
Runtime command performs deterministic work
SQLite remains source of truth
Obsidian remains review mirror
```
