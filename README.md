# Agent Memory MVP

Agent Memory is a local memory, reflection, and governance runtime for coding agents.

It gives an agent a stable way to remember project facts, task episodes, lessons, codebase context, and retrieval misses without requiring a vector database, daemon, graph database, or agent-specific wrapper.

The intended interface is skill-first:

```text
User speaks naturally
  -> agent chooses one of four memory skills
  -> skill calls tools/agent_memory.py
  -> runtime reads/writes SQLite
  -> Obsidian vault is generated for human review
```

SQLite is the source of truth. Obsidian is a readable mirror.

## Features

- Global memory home with isolated per-project SQLite stores.
- Four skill-facing workflows: learn, query, maintain, reflect.
- Semantic facts, task episodes, reflections, and future rules.
- Entry-file and directory-based code learning.
- Lightweight codebase wiki indexing and search.
- Code log statement extraction with file/function/log edges for diagnosis.
- HarmonyOS ArkTS `.ets` learning support for components, imports, router/resource references, JSON5 config, and console/hilog logs.
- JSON-capable context retrieval for agent integration.
- Query miss feedback when retrieval returns nothing.
- Reflection quality review and reuse feedback.
- Guided memory governance: health, review, plan, stale, archive, merge, promote, reject.
- Obsidian-compatible Markdown export.
- Installer and doctor command for project setup.

## Why Use It

Coding agents lose useful context between sessions. Chat history is noisy, and full RAG infrastructure is often too heavy for a local MVP.

Agent Memory focuses on a smaller, inspectable loop:

```text
learn relevant project scope
  -> query concise memory before work
  -> reflect after work
  -> promote durable lessons
  -> review stale, weak, or missing memory
```

This keeps memory useful without making it more authoritative than current source files or explicit user instructions.

## Architecture

```text
Local Agent / LLM
  -> Agent Memory Skills
  -> tools/agent_memory.py
  -> ~/.agent-memory/projects/<project_id>/memory.db
  -> ~/.agent-memory/projects/<project_id>/vault/
```

The learned project directory is the input source. Memory data is stored under a configurable global memory home, not inside the learned project. Resolution order is `--memory-home`, `AGENT_MEMORY_HOME`, then `~/.agent-memory`.

## Quick Start

Install into a project:

```bash
python install.py --project . --local-skills
```

Optional custom memory home:

```bash
python install.py --project . --memory-home ~/AgentMemory --local-skills
```

Check the installation:

```bash
python tools/agent_memory.py doctor --project .
```

Learn a local project scope:

```bash
python tools/agent_memory.py learn-entry --project . --entry tools/agent_memory.py --depth 2 --json
python tools/agent_memory.py learn-path --project . --path skills --json
```

Learning returns `parse_stats` with file, language, symbol, log, and edge counts. It also records log-like statements in code, such as `logger.error(...)`, `console.warn(...)`, ArkTS `hilog.info(...)`, and `print(...)`, then connects them to the learned file and nearest detected function. For HarmonyOS projects, it also indexes `.json5` module/package config, ArkTS router targets, and `$r(...)` resource references.

Query memory:

```bash
python tools/agent_memory.py context --project . --query "memory governance workflow" --json
```

For diagnosis, query an observed log or output string directly:

```bash
python tools/agent_memory.py context --project . --query "retrying job" --json
```

Network context is bounded: the runtime returns only allowed one-hop edges and compact evidence chains. Recursive investigation happens by asking a sharper follow-up query.

Reflect after a task:

```bash
python tools/agent_memory.py reflect \
  --project . \
  --task "add guided review workflow" \
  --lesson "Governance actions should be proposed before mutation." \
  --future-rule "Run maintain-plan before status, merge, or promote." \
  --trigger-condition "When cleaning or organizing memory" \
  --repair-action "Generate an action plan and ask for confirmation"
```

Export the review vault:

```bash
python tools/agent_memory.py vault-export --project .
```

## How To Use

Normal usage should go through four skills:

| Skill | Purpose | Typical commands |
|---|---|---|
| `agent-memory-learn` | Add project code context to memory | `learn-entry`, `learn-path`, `wiki-index` |
| `agent-memory-query` | Retrieve project memory and wiki context | `context`, `search`, `wiki-search` |
| `agent-memory-maintain` | Initialize, check, review, govern, and export memory | `doctor`, `maintain-plan`, `vault-export` |
| `agent-memory-reflect` | Save lessons, facts, and reflection feedback | `reflect`, `reflect-review`, `update` |

The CLI is the stable backend API and debugging escape hatch.

## Common Commands

```bash
python tools/agent_memory.py init --project .
python tools/agent_memory.py doctor --project .

python tools/agent_memory.py learn-entry --project . --entry "<file>" --depth 2 --json
python tools/agent_memory.py learn-path --project . --path "<directory>" --json
python tools/agent_memory.py wiki-index --project .

python tools/agent_memory.py context --project . --query "..." --json
python tools/agent_memory.py search --project . --query "..." --json
python tools/agent_memory.py wiki-search --project . --query "..." --json

python tools/agent_memory.py update --project . --type semantic --fact "..." --source user --confidence 1.0
python tools/agent_memory.py reflect --project . --task "..." --lesson "..."
python tools/agent_memory.py reflect-review --project . --json

python tools/agent_memory.py maintain-health --project . --json
python tools/agent_memory.py maintain-review --project . --json
python tools/agent_memory.py maintain-plan --project . --json
python tools/agent_memory.py maintain-status --project . --type semantic --id 1 --status stale --reason "..."
python tools/agent_memory.py maintain-merge --project . --type semantic --ids 1,2 --fact "..." --json
python tools/agent_memory.py maintain-promote --project . --episode-id 1 --fact "..." --json
python tools/agent_memory.py maintain-promote --project . --reflection-id 1 --fact "..." --json

python tools/agent_memory.py miss-list --project . --status open --json
python tools/agent_memory.py miss-status --project . --id 1 --status resolved --resolution "..."

python tools/agent_memory.py vault-export --project .
```

## Documentation

- `agent.md`: project mission and agent-facing rules.
- `AGENTS.md`: repository instructions for coding agents.
- `docs/usage-guide.md`: skill-first usage guide.
- `docs/runtime.md`: runtime protocol notes.
- `references/schema.md`: SQLite schema notes.
- `docs/phase-2-memory-governance-plan.md`: memory governance plan.
- `docs/guided-memory-review-workflow.md`: guided review workflow.
- `docs/reflection-quality-loop.md`: reflection quality loop.
- `docs/query-miss-feedback-loop.md`: query miss feedback loop.
- `docs/code-log-statement-network.md`: code log statement extraction and memory edges.
- `docs/templates/diagnosis-memory-query-template.md`: recursive diagnosis template.
- `docs/templates/change-design-memory-query-template.md`: recursive change-design template.
- `gitlog.md`: local development log and rollback notes.

## Roadmap

- Better conflict detection between memories.
- Better reflection rewrite and validation workflows.
- More precise import and link discovery for local code learning.
- More examples for integrating with different local agent CLIs.
- Optional richer retrieval backends after the deterministic runtime is stable.
- Cross-project memory only after per-project isolated memory is proven reliable.

---

# Agent Memory MVP 中文版

Agent Memory 是一个面向 coding agent 的本地记忆、反思和治理运行时。

它让 Agent 能通过稳定脚本记住项目事实、任务经历、反思规则、代码上下文和查询失败记录。系统不依赖向量数据库、daemon、图数据库，也不绑定某一个 Agent CLI。

推荐使用方式是 skill-first：

```text
用户用自然语言提出需求
  -> Agent 选择四个 memory skill 之一
  -> skill 调用 tools/agent_memory.py
  -> runtime 读写 SQLite
  -> 导出 Obsidian vault 供人类 review
```

SQLite 是真实数据源。Obsidian 是可读镜像。

## 特性

- 全局记忆目录，按项目隔离 SQLite、runtime cache 和 Obsidian 镜像。
- 四个 skill 工作流：学习、查询、维护、反思。
- 支持语义事实、任务 episode、反思和 future rule。
- 支持从入口文件、目录、全项目学习代码。
- 轻量 codebase wiki 索引和搜索。
- 支持抽取代码日志语句，并建立文件/函数/日志边关系，辅助定位问题。
- 支持 HarmonyOS ArkTS `.ets` 代码学习，包括组件、相对 import、路由/资源引用、JSON5 配置、console/hilog 日志。
- 支持 JSON 输出，方便 Agent 调用。
- 查询无结果时自动记录 query miss。
- 支持反思质量检查和反思复用反馈。
- 支持记忆治理：health、review、plan、stale、archive、merge、promote、reject。
- 可导出 Obsidian Markdown 镜像。
- 提供安装脚本和 doctor 检查命令。

## 为何使用

Coding agent 很容易在会话之间丢失项目上下文。直接依赖聊天历史太嘈杂，第一版就引入完整 RAG 基础设施又太重。

Agent Memory 选择一个小而稳定的闭环：

```text
学习相关项目范围
  -> 工作前查询精简记忆
  -> 工作后写入反思
  -> 将稳定经验提升为长期事实
  -> review 过期、薄弱或缺失的记忆
```

记忆只提供建议。当前源码和用户明确指令永远优先。

## 快速开始

安装到项目：

```bash
python install.py --project . --local-skills
```

检查安装：

```bash
python tools/agent_memory.py doctor --project .
```

默认记忆会写入 `~/.agent-memory/projects/<project_id>/`，不会写入被学习项目的 `.agent-memory/`。可通过 `--memory-home` 或 `AGENT_MEMORY_HOME` 修改全局记忆目录。

学习局部代码：

```bash
python tools/agent_memory.py learn-entry --project . --entry tools/agent_memory.py --depth 2 --json
python tools/agent_memory.py learn-path --project . --path skills --json
```

学习命令会返回 `parse_stats`，包含文件、语言、符号、日志和边数量统计。学习代码时也会记录代码里的日志输出语句，例如 `logger.error(...)`、`console.warn(...)`、ArkTS `hilog.info(...)`、`print(...)`，并把它们连接到对应文件和最近的函数。对 HarmonyOS 项目，还会索引 `.json5` 模块/依赖配置、ArkTS 路由目标和 `$r(...)` 资源引用。

查询记忆：

```bash
python tools/agent_memory.py context --project . --query "memory governance workflow" --json
```

定位问题时，可以直接查询观察到的日志或输出文本：

```bash
python tools/agent_memory.py context --project . --query "retrying job" --json
```

网络上下文是受限的：runtime 只返回允许的一跳边和简短证据链。递归定位由 Agent 通过更精确的下一次 query 完成。

任务结束后写入反思：

```bash
python tools/agent_memory.py reflect \
  --project . \
  --task "add guided review workflow" \
  --lesson "治理动作应先生成计划，再执行修改。" \
  --future-rule "执行 status、merge、promote 前先运行 maintain-plan。" \
  --trigger-condition "当用户要求整理或治理记忆时" \
  --repair-action "生成行动计划并等待用户确认"
```

导出 Obsidian 镜像：

```bash
python tools/agent_memory.py vault-export --project .
```

## 如何使用

日常使用建议通过四个 skill：

| Skill | 用途 | 常用命令 |
|---|---|---|
| `agent-memory-learn` | 将项目代码上下文加入记忆 | `learn-entry`, `learn-path`, `wiki-index` |
| `agent-memory-query` | 查询项目记忆和 wiki 上下文 | `context`, `search`, `wiki-search` |
| `agent-memory-maintain` | 初始化、检查、review、治理、导出 | `doctor`, `maintain-plan`, `vault-export` |
| `agent-memory-reflect` | 保存经验、事实和反思反馈 | `reflect`, `reflect-review`, `update` |

CLI 是稳定后端和调试入口。用户正常使用时不需要记住全部命令。

## 常用命令

```bash
python tools/agent_memory.py doctor --project .
python tools/agent_memory.py learn-entry --project . --entry "<file>" --depth 2 --json
python tools/agent_memory.py learn-path --project . --path "<directory>" --json
python tools/agent_memory.py context --project . --query "..." --json
python tools/agent_memory.py reflect --project . --task "..." --lesson "..."
python tools/agent_memory.py maintain-plan --project . --json
python tools/agent_memory.py vault-export --project .
```

## 将来规划

- 更好的记忆冲突检测。
- 更好的反思重写和验证流程。
- 更精确的代码 import/link 发现。
- 更多本地 Agent CLI 对接示例。
- 在确定性 runtime 稳定后，再考虑可选的高级检索后端。
- 跨项目记忆要等项目隔离记忆足够可靠后再做。
