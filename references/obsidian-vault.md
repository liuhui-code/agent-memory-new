# Obsidian Vault Mirror

The vault is a generated Markdown mirror of SQLite data.

Path:

```text
.agent-memory/projects/<project_id>/vault/
```

The default memory home is the current workspace `.agent-memory/`. It can be changed with `--memory-home` or `AGENT_MEMORY_HOME`.

Sections:

- `Episodes/`
- `Reflections/`
- `Semantic Facts/`
- `Codebase Wiki/`
- `Governance/`
- `Daily/`

Generated governance pages include:

- `Governance/Health.md`
- `Governance/Review Queue.md`
- `Governance/Stale Memories.md`
- `Governance/Merge Candidates.md`
- `Governance/Low Confidence.md`
- `Governance/Reflection Quality.md`
- `Governance/Experience Candidates.md`
- `Governance/Reflection Reuse.md`
- `Governance/Query Misses.md`

The MVP does not sync Obsidian edits back into SQLite.
