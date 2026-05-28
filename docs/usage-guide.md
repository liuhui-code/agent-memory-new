# Agent Memory Usage Guide

This project is designed for skill-first usage.

The user should not need to remember low-level commands during normal work. The intended flow is:

```text
User says what they want in natural language
  -> LLM chooses one of four Agent Memory skills
  -> Skill calls tools/agent_memory.py
  -> Runtime reads or writes SQLite
  -> Obsidian vault is exported for human review
```

The CLI remains the stable backend API and a debugging escape hatch.

## The Four Skills

| Skill | User intent | Main runtime commands |
|---|---|---|
| `agent-memory-learn` | Learn code from an entry file, directory, or whole project | `learn-entry`, `learn-path`, `wiki-index` |
| `agent-memory-query` | Search or retrieve memory context | `context`, `search`, `wiki-search` |
| `agent-memory-maintain` | Initialize, health-check, refresh, or sync | `init`, `doctor`, `wiki-index`, `vault-export` |
| `agent-memory-reflect` | Save lessons, facts, and task reflections | `reflect`, `update`, `vault-export` |

## 1. Install Into A Project

Run this once from the project root:

```bash
python install.py --project . --local-skills
```

This creates:

```text
~/.agent-memory/
  config.json
  projects/<project_id>/
    memory.db
    runtime/
    vault/
.agent-skills/
tools/agent_memory.py
```

The project directory is the code source. Memory data is stored in the global memory home. Override it with `--memory-home <path>` or `AGENT_MEMORY_HOME=<path>`.

Verify:

```bash
python tools/agent_memory.py doctor --project .
```

## 2. Learn Part Of A Project

Prefer asking the Agent in natural language:

```text
Learn the code around tools/agent_memory.py.
```

Expected skill path:

```text
agent-memory-learn
  -> python tools/agent_memory.py learn-entry --project . --entry tools/agent_memory.py --depth 2 --json
```

The runtime will:

```text
Read the entry file
  -> extract project-local imports
  -> follow related files up to depth
  -> merge that file set into the codebase wiki
  -> extract code log statements and rebuild file/function/log edges
  -> return parse_stats with file, symbol, log, language, and edge counts
  -> save an episode describing what was learned
```

`learn-entry --json` returns parse feedback:

```json
{
  "parse_stats": {
    "files_indexed": 1,
    "languages": { "ArkTS": 1 },
    "symbols_total": 4,
    "symbols_by_type": { "component": 1, "route": 1, "resource": 1 },
    "code_logs_total": 1,
    "code_logs_by_level": { "error": 1 },
    "memory_edges_total": 6
  }
}
```

Use `--replace` only when you want this learned scope to replace the current codebase wiki:

```bash
python tools/agent_memory.py learn-entry --project . --entry tools/agent_memory.py --depth 2 --replace --json
```

For a directory:

```text
Learn the skills directory.
```

Expected skill path:

```text
agent-memory-learn
  -> python tools/agent_memory.py learn-path --project . --path skills --json
```

Partial learning is incremental by default. A second `learn-path` call adds or refreshes that directory without removing previously learned files. Use `--replace` only for an explicit reset:

```bash
python tools/agent_memory.py learn-path --project . --path skills --replace --json
```

Learning also stores code log statements such as `print(...)`, `logger.error(...)`, `console.warn(...)`, and ArkTS `hilog.info(...)`. These are connected to learned files and nearest detected functions through `memory_edges`.

For HarmonyOS projects, learning also indexes `.json5` config files, ArkTS router targets, and `$r(...)` resource references as code wiki symbols. `learn-entry` can follow ArkTS router targets such as `router.pushUrl({ url: 'pages/Detail' })` to the related `.ets` page.

For the whole project:

```text
Refresh the whole codebase wiki.
```

Expected skill path:

```text
agent-memory-learn
  -> python tools/agent_memory.py wiki-index --project .
```

## 3. Query Memory

Ask:

```text
Before editing, check whether we have relevant memory for this task.
```

Expected skill path:

```text
agent-memory-query
  -> python tools/agent_memory.py context --project . --query "<task>" --json
```

If a query returns no semantic facts, reflections, episodes, or wiki matches, the runtime records a query miss automatically. The user does not need to maintain keywords.

When diagnosing an error message or observed output, query the message text directly. `context` may return `code_log_matches` and `edge_matches` that point to the likely file and function.

Ask:

```text
Search the codebase wiki for memory runtime commands.
```

Expected skill path:

```text
agent-memory-query
  -> python tools/agent_memory.py wiki-search --project . --query "memory runtime commands" --json
```

`wiki-search` also returns matching code log statements with `kind: "log_statement"`.

For workflows that need repeated query refinement, use the integration templates:

```text
Bug diagnosis:
  docs/templates/diagnosis-memory-query-template.md

Design or modification planning:
  docs/templates/change-design-memory-query-template.md

General memory-aware answering with logs:
  docs/templates/memory-query-answer-skill-template.md
```

These templates are meant to be copied into other skills. They keep `agent-memory-query` simple while allowing recursive memory-aware reasoning.

## 4. Maintain Memory System

Ask:

```text
Initialize memory for this project.
```

Expected skill path:

```text
agent-memory-maintain
  -> python tools/agent_memory.py init --project .
  -> python tools/agent_memory.py doctor --project .
```

Ask:

```text
Check memory system health.
```

Expected skill path:

```text
agent-memory-maintain
  -> python tools/agent_memory.py doctor --project .
  -> python tools/agent_memory.py maintain-health --project . --json
```

Ask:

```text
检查记忆系统健康状况，并整理需要 review 的记忆。
```

Expected skill path:

```text
agent-memory-maintain
  -> python tools/agent_memory.py maintain-health --project . --json
  -> python tools/agent_memory.py maintain-plan --project . --json
```

The Agent should group the proposed actions by risk and ask for confirmation before mutating memory. Query miss actions are low-risk signals that suggest the Agent may need to learn a path, add a durable fact, or ignore the miss. It may then execute confirmed actions:

```bash
python tools/agent_memory.py maintain-status --project . --type semantic --id 12 --status stale --reason "source changed"
python tools/agent_memory.py maintain-merge --project . --type semantic --ids 3,8 --fact "..."
python tools/agent_memory.py maintain-promote --project . --episode-id 9 --fact "..."
python tools/agent_memory.py miss-status --project . --id 7 --status resolved --resolution "learned relevant directory"
```

`maintain-plan` is read-only. Actions with `command: null` need the Agent to draft a replacement fact or durable lesson before execution.

Ask:

```text
Sync memory to Obsidian.
```

Expected skill path:

```text
agent-memory-maintain
  -> python tools/agent_memory.py vault-export --project .
```

## 5. Reflect And Remember

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

Prefer structured reflection fields when possible:

```bash
python tools/agent_memory.py reflect \
  --project . \
  --task "<task>" \
  --summary "<what happened>" \
  --mistake "<what went wrong or empty>" \
  --lesson "<durable lesson>" \
  --future-rule "<rule for next time>" \
  --scope "<where this applies>" \
  --evidence "<file, command, or episode>" \
  --trigger-condition "<when to remember this>" \
  --anti-pattern "<mistake pattern to avoid>" \
  --repair-action "<concrete next action>" \
  --applies-to "<valid scope>" \
  --does-not-apply-to "<invalid scope>" \
  --confidence 0.8
```

When a task used older reflections, record whether they helped:

```bash
python tools/agent_memory.py reflect \
  --project . \
  --task "<task>" \
  --lesson "<new lesson>" \
  --used-reflection-ids "3,8" \
  --reflection-outcome helped
```

Review reflection quality:

```bash
python tools/agent_memory.py reflect-review --project . --json
```

Ask:

```text
Remember that this project treats SQLite as the source of truth.
```

Expected skill path:

```text
agent-memory-reflect
  -> python tools/agent_memory.py update --project . --type semantic --fact "..." --source user --confidence 1.0
```

## 6. Manual CLI Fallback

When debugging or scripting, call the runtime directly:

```bash
python tools/agent_memory.py learn-entry --project . --entry tools/agent_memory.py --depth 2 --json
python tools/agent_memory.py learn-path --project . --path skills
python tools/agent_memory.py learn-path --project . --path skills --replace
python tools/agent_memory.py context --project . --query "..." --json
python tools/agent_memory.py update --project . --type semantic --fact "..." --source user --confidence 1.0
python tools/agent_memory.py reflect --project . --task "..." --lesson "..."
python tools/agent_memory.py reflect-review --project . --json
python tools/agent_memory.py maintain-health --project . --json
python tools/agent_memory.py maintain-review --project . --json
python tools/agent_memory.py maintain-plan --project . --json
python tools/agent_memory.py miss-list --project . --status open --json
python tools/agent_memory.py miss-status --project . --id 1 --status ignored --resolution "not useful"
python tools/agent_memory.py vault-export --project .
```

## 7. Obsidian Review

Export the vault:

```bash
python tools/agent_memory.py vault-export --project .
```

Open this directory in Obsidian:

```text
~/.agent-memory/projects/<project_id>/vault/
```

Obsidian is a read-only review mirror in the MVP. Edit memory through skills or CLI commands, then export again.

## 8. Design Rule

When adding new features, preserve this direction:

```text
Natural language request first
One of four skills chooses action
Runtime command performs deterministic work
SQLite remains source of truth
Obsidian remains review mirror
```

## 9. Governance Performance Rule

Keep regular retrieval fast:

```text
agent-memory-query consumes governance metadata.
agent-memory-reflect writes local lessons and lightweight metadata.
agent-memory-maintain performs heavier review, merge, stale, promote, and export work.
```

Do not run duplicate detection, promotion, or vault dashboard generation on every query.
