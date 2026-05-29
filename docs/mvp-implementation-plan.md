# Agent Memory MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build a generic Skill-driven Memory Runtime that local Agents can use for initialization, querying, updating, reflection, codebase wiki lookup, and Obsidian export.

**Architecture:** Skills are the LLM-facing protocol. `tools/agent_memory.py` is the stable local API. SQLite is the source of truth, and Obsidian Markdown is a generated review mirror.

**Tech Stack:** Python 3.9+, SQLite, Markdown frontmatter, local filesystem, keyword search.

---

## Target Layout

Development repository:

```text
install.py
tools/
  agent_memory.py
skills/
  agent-memory-learn/
    SKILL.md
  agent-memory-query/
    SKILL.md
  agent-memory-maintain/
    SKILL.md
  agent-memory-reflect/
    SKILL.md
references/
  schema.md
  skill-protocol.md
  obsidian-vault.md
  codebase-wiki.md
```

Installed project layout:

```text
.agent-memory/
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

## MVP Boundaries

Build:

- SQLite schema and project identity
- Runtime CLI with JSON output
- Semantic fact and episode writes
- Reflection writes
- Keyword search and context generation
- Obsidian vault export
- Lightweight codebase wiki
- Six skills that call the runtime
- Installer and doctor command

Do not build in MVP:

- Vector database
- Neo4j or graph traversal
- Long-running daemon
- Agent-specific wrapper as the primary integration
- Obsidian-to-SQLite reverse sync
- Complete AST call graph

## Phase 2 Direction

After the first MVP, the next layer is memory governance and consolidation. Keep the same four user-facing skills, but add runtime support for:

- status lifecycle: `active`, `stale`, `merged`, `archived`, `rejected`
- confidence, scope, evidence, review, merge, and usage metadata
- health and review queue commands
- guided review plans that propose confirmable actions without mutating memory
- reflection quality review and reuse feedback
- structured Agent-authored reflection payloads for diagnosis, design, execution, and workflow attempts
- experience-candidate reflection fields: hidden assumptions, negative preconditions, verification method, reuse feedback, source cases, and optional skill candidate
- query miss feedback for completely failed retrievals
- manual merge and episode-to-fact promotion
- generated Obsidian governance dashboard pages

See `docs/phase-2-memory-governance-plan.md`.
See `docs/experience-system-plan.md` for the experience layer direction above raw memory.

Partial learning behavior:

- `learn-entry` and `learn-path` merge into the existing codebase wiki by default.
- Add `--replace` only when the user explicitly wants to reset the learned code scope.

Code log statement network:

- `learn-entry`, `learn-path`, and `wiki-index` extract code log statements as part of learning.
- The runtime stores `code_log_statements` and deterministic `memory_edges`.
- Query commands expose `code_log_matches` and `edge_matches`.
- This stays inside the existing four-skill interface and does not add a separate log skill.

Parse feedback:

- `learn-entry --json` and `learn-path --json` return `parse_stats`.
- Counts include files indexed, languages, symbols by type, code logs by level, and memory edge total.
- Agents should report low or surprising counts before relying on learned context.

## Phase 1: Runtime Init and Doctor

**Files:**

- Create: `tools/agent_memory.py`
- Create: `references/schema.md`

- [x] Implement `init --project .`.

Required behavior:

```text
Create workspace memory home, defaulting to ./.agent-memory/
Create .agent-memory/projects/<project_id>/
Create runtime/
Create vault/
Create config.json files
Create memory.db
Create required SQLite tables
Create or update project row
```

- [x] Implement `doctor --project .`.

Required checks:

```text
memory home exists
project memory directory exists
workspace config.json exists
config.json exists
memory.db exists
required tables exist
vault directory exists
runtime directory exists
```

- [x] Verify:

```bash
python tools/agent_memory.py init --project .
python tools/agent_memory.py doctor --project .
```

Expected: all checks report OK.

## Phase 2: SQLite Schema

**Files:**

- Modify: `tools/agent_memory.py`
- Update: `references/schema.md`

- [x] Create these tables:

```sql
CREATE TABLE projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT UNIQUE NOT NULL,
  project_path TEXT NOT NULL,
  project_name TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE episodes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL,
  task TEXT NOT NULL,
  summary TEXT NOT NULL,
  outcome TEXT,
  files_touched TEXT,
  commands_run TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE semantic_facts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL,
  fact TEXT NOT NULL,
  source TEXT NOT NULL,
  confidence REAL DEFAULT 0.8,
  is_stale INTEGER DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE reflections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL,
  task TEXT NOT NULL,
  summary TEXT,
  mistake TEXT,
  lesson TEXT NOT NULL,
  future_rule TEXT,
  is_stale INTEGER DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE code_files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL,
  file_path TEXT NOT NULL,
  summary TEXT,
  language TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE code_symbols (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL,
  file_path TEXT NOT NULL,
  symbol TEXT NOT NULL,
  symbol_type TEXT,
  summary TEXT,
  calls TEXT,
  updated_at TEXT NOT NULL
);
```

- [x] Use `sha256(abs_project_path)` as `project_id`.

## Phase 3: Update Commands

**Files:**

- Modify: `tools/agent_memory.py`

- [x] Implement semantic fact writes:

```bash
python tools/agent_memory.py update \
  --project . \
  --type semantic \
  --fact "用户偏好第一版先做 MVP，不喜欢过早复杂化" \
  --source user \
  --confidence 1.0
```

- [x] Implement episode writes:

```bash
python tools/agent_memory.py update \
  --project . \
  --type episode \
  --task "设计 Memory Runtime" \
  --summary "确定 Skill-driven Memory Runtime 架构" \
  --outcome "planned"
```

- [x] Implement list and stale marking:

```bash
python tools/agent_memory.py list --project . --type semantic
python tools/agent_memory.py mark-stale --project . --type semantic --id 1
```

## Phase 4: Search and Context

**Files:**

- Modify: `tools/agent_memory.py`
- Create: `references/skill-protocol.md`

- [x] Implement `search --json`.

Search fields:

```text
semantic_facts.fact
reflections.lesson
reflections.future_rule
episodes.task
episodes.summary
code_files.file_path
code_symbols.symbol
```

- [x] Implement `context --json`.

Context limits:

```text
3 semantic facts
3 reflections
2 episodes
5 wiki matches
1500 words max
exclude stale records by default
```

Expected JSON shape:

```json
{
  "project_id": "...",
  "query": "...",
  "semantic_facts": [],
  "reflections": [],
  "episodes": [],
  "wiki_matches": []
}
```

## Phase 5: Reflection

**Files:**

- Modify: `tools/agent_memory.py`

- [x] Implement:

```bash
python tools/agent_memory.py reflect \
  --project . \
  --task "设计通用 Agent Memory 对接" \
  --summary "从 wrapper 方案改为 skill 调用 runtime 脚本" \
  --mistake "一开始过于绑定单一 CLI wrapper" \
  --lesson "通用对接应该暴露稳定 CLI/JSON API" \
  --future-rule "优先让 skill 调用 runtime，不绑定特定 Agent CLI"
```

- [x] Support structured Agent-authored reflection payloads:

```bash
python tools/agent_memory.py reflect --project . --payload "<json>"
python tools/agent_memory.py reflect --project . --payload-file "<review.json>"
```

- [x] Write the reflection to SQLite.

- [x] Write `runtime/last_reflection.json` under the project's workspace memory-home store.

## Phase 6: Obsidian Vault Export

**Files:**

- Modify: `tools/agent_memory.py`
- Create: `references/obsidian-vault.md`

- [x] Implement:

```bash
python tools/agent_memory.py vault-init --project .
python tools/agent_memory.py vault-export --project .
python tools/agent_memory.py vault-index --project .
```

- [x] Generate:

```text
.agent-memory/projects/<project_id>/vault/index.md
.agent-memory/projects/<project_id>/vault/Episodes/
.agent-memory/projects/<project_id>/vault/Reflections/
.agent-memory/projects/<project_id>/vault/Semantic Facts/
.agent-memory/projects/<project_id>/vault/Codebase Wiki/
.agent-memory/projects/<project_id>/vault/Daily/
```

- [x] Use Markdown frontmatter:

```md
---
type: reflection
project_id: xxx
created_at: 2026-05-26T10:00:00
tags:
  - agent-memory
  - reflection
---
```

## Phase 7: Lightweight Codebase Wiki

**Files:**

- Modify: `tools/agent_memory.py`
- Create: `references/codebase-wiki.md`

- [x] Implement:

```bash
python tools/agent_memory.py learn-entry --project . --entry tools/agent_memory.py --depth 2 --json
python tools/agent_memory.py learn-entry --project . --source /path/to/app --entry "<file>" --depth 2 --json
python tools/agent_memory.py learn-path --project . --path skills
python tools/agent_memory.py learn-path --project . --source /path/to/app --path "<directory>"
python tools/agent_memory.py wiki-index --project .
python tools/agent_memory.py wiki-index --project . --source /path/to/app
python tools/agent_memory.py wiki-search --project . --query "memory" --json
```

- [x] Ignore:

```text
.git/
node_modules/
build/
dist/
.dart_tool/
__pycache__/
.agent-memory/
```

- [x] Extract lightweight symbols:

```text
Python: def, class
TS/JS: function, class, const name =
ArkTS: .ets, struct components, class, function, lifecycle/build methods, router targets, resources
HarmonyOS config: .json5 abilities, permissions, dependencies, page profiles
Dart: class, Future<, void, Widget build
Swift: class, struct, func
Markdown: # headings
```

## Phase 8: Skills

**Files:**

- Create: `skills/agent-memory-learn/SKILL.md`
- Create: `skills/agent-memory-query/SKILL.md`
- Create: `skills/agent-memory-maintain/SKILL.md`
- Create: `skills/agent-memory-reflect/SKILL.md`

- [x] `agent-memory-learn` calls:

```bash
python tools/agent_memory.py learn-entry --project . --entry "<file>" --depth 2 --json
python tools/agent_memory.py learn-entry --project . --source "<external-project>" --entry "<file>" --depth 2 --json
python tools/agent_memory.py learn-path --project . --path "<directory>"
python tools/agent_memory.py learn-path --project . --source "<external-project>" --path "<directory>"
python tools/agent_memory.py wiki-index --project .
python tools/agent_memory.py wiki-index --project . --source "<external-project>"
```

- [x] `agent-memory-query` calls:

```bash
python tools/agent_memory.py context --project . --query "<user task>" --json
python tools/agent_memory.py wiki-search --project . --query "..." --json
```

- [x] `agent-memory-maintain` calls:

```bash
python tools/agent_memory.py init --project .
python tools/agent_memory.py doctor --project .
python tools/agent_memory.py vault-export --project .
```

- [x] `agent-memory-reflect` calls:

```bash
python tools/agent_memory.py reflect --project . --task "..." --summary "..." --lesson "..."
python tools/agent_memory.py reflect --project . --payload "<json>"
python tools/agent_memory.py update --project . --type semantic --fact "..." --source user --confidence 1.0
python tools/agent_memory.py vault-export --project .
```

## Phase 9: Installer

**Files:**

- Create: `install.py`

- [x] Implement:

```bash
python install.py --project . --local-skills
python install.py --project . --global-skills
python install.py --project . --force
```

- [x] Default to local skills.

- [x] Install flow:

```text
Check Python >= 3.9
Resolve project path
Create workspace memory home if missing
Initialize memory.db
Create vault/
Copy tools/agent_memory.py to project tools/
Copy skills to .agent-skills/
Write workspace and per-project config.json
Run doctor
Print usage examples
```

- [x] Do not modify `.zshrc` or shell profiles automatically.

## Phase 10: End-to-End Verification

Run:

```bash
python install.py --project . --local-skills
python tools/agent_memory.py doctor --project .
python tools/agent_memory.py update --project . --type semantic --fact "用户希望通过 skill 调用记忆系统脚本，而不是绑定单一 Agent CLI" --source user --confidence 1.0
python tools/agent_memory.py context --project . --query "如何对接本地 agent cli" --json
python tools/agent_memory.py reflect --project . --task "设计通用 agent memory 对接" --summary "改为 skill-driven memory runtime" --lesson "通用对接应暴露稳定 CLI/JSON API" --future-rule "不要把记忆系统绑定到单一 CLI wrapper"
python tools/agent_memory.py vault-export --project .
python tools/agent_memory.py learn-entry --project . --entry tools/agent_memory.py --depth 1 --json
python tools/agent_memory.py learn-path --project . --path skills
python tools/agent_memory.py wiki-index --project .
python tools/agent_memory.py wiki-search --project . --query "memory" --json
```

Expected:

```text
memory.db exists
semantic fact can be written
context returns the written fact
reflection can be written
vault/index.md exists
vault/Reflections contains Markdown
wiki-search returns files or symbols
doctor reports OK
```

## Implementation Priority

```text
1. init / doctor
2. SQLite schema
3. update semantic / episode
4. search / context
5. reflect
6. vault export
7. wiki index / search
8. skills
9. installer
10. end-to-end verification
```
