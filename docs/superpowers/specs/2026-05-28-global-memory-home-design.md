# Global Memory Home Design

## Goal

Store learned memory data in a user-level global memory home instead of writing `.agent-memory` into the learned project directory.

## Approved Approach

Use a shared global root with per-project isolated stores:

```text
~/.agent-memory/
  config.json
  projects/
    <project_id>/
      memory.db
      config.json
      runtime/
      vault/
```

The learned project path remains the project identity and source root. SQLite, runtime cache, and generated Obsidian vault files live under the global memory home.

## Configuration

Memory home resolution order:

1. `--memory-home <path>`
2. `AGENT_MEMORY_HOME`
3. `~/.agent-memory`

`--project <path>` continues to select which project is being learned or queried.

## Compatibility

This change does not add vector databases, daemon processes, graph databases, or agent-specific wrappers. The runtime remains `tools/agent_memory.py`, SQLite remains the source of truth, and Obsidian remains a generated mirror.

