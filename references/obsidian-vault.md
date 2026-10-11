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
- `Normative Context/`
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

`Normative Context/index.md` is a generated reference list for explicitly learned ADRs
and Feature Specs. Up to 500 source snapshots include declared status, scope, approval
references, source digest/revision and snapshot freshness. The original reviewed Git
document controls normative text and approval; editing a mirror cannot approve a spec
or change its Runtime status. This minimal implementation has not been validated.

Each document mirror links to its original local Git file. The generated reference
index shows source freshness; changed, missing or unverified sources are explicitly
marked before their indexed snapshot. The stored snapshot remains available for
human review, with its observed revision and digest, and is not current-source or
approval evidence merely because it appears in the Vault.
Mirror fields distinguish the indexed source digest from the export-time observed
digest. An unavailable bounded read is labeled `unavailable`; the freshness decision
and observed digest use the same read. Export does not refresh the SQLite document
or bind the new bytes to the indexed approval declaration.

The MVP does not sync Obsidian edits back into SQLite or reviewed Git documents.
