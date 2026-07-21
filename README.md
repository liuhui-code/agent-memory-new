# Agent Memory MVP

[中文说明](README.zh-CN.md)

Agent Memory is a local project-memory and context runtime for coding agents,
with an ArkTS/HarmonyOS-first semantic layer and language-neutral retrieval
contracts.

It gives a local Agent CLI a stable way to retrieve project facts, code and log
anchors, typed graph context, design constraints, and reusable lessons without a
vector database, daemon, graph database, or agent-specific wrapper. The Agent
performs diagnosis and design reasoning; the Runtime supplies bounded,
inspectable context.

![Agent Memory overview](docs/assets/agent-memory-overview.png)

## Why Agents Need Memory

Current coding agents are strong inside one session, but weak across sessions and repeated tasks.

Common problems:

- they re-read the same files and rediscover the same routes, symbols, and logs
- they forget why a previous diagnosis worked
- they do not retain project-specific business semantics well
- they can inspect raw logs, but often lack a stable bridge from user symptoms to code logs to bounded runtime evidence
- chat history grows, but becomes noisy, fragile, and hard to govern

A practical memory system should do more than store text. It should help the agent:

- learn project scope incrementally
- retrieve concise context before work
- reflect after work
- govern stale or weak memory
- connect code logs and runtime evidence back into reusable experience

That is the role of Agent Memory.

## What This Project Solves

Agent Memory is designed to solve these practical problems:

1. **Project context loss**
   - repeated rediscovery of the same files, symbols, routes, resources, and logs

2. **Weak reusable diagnosis memory**
   - a successful bug investigation often disappears after the session ends

3. **Code understanding without heavy infrastructure**
   - teams want inspectable local memory without introducing services or heavyweight retrieval systems

4. **Runtime-log diagnosis drift**
   - raw logs are noisy; agents need help moving from symptoms to code log
     anchors and current source without delegating diagnosis to the Runtime

5. **Memory quality decay**
   - as projects change, old structure, old semantics, and old experience can become stale

6. **Design without repository constraints**
   - generic design advice misses current consumers, state owners, accepted
     constraints, semantic corrections, and evidence gaps

## Design Principles

Agent Memory stays intentionally conservative:

- SQLite is the source of truth
- Obsidian vault is a generated human-readable mirror
- `tools/agent_memory.py` is the only runtime entry point
- the user-facing interface stays fixed at **four skills**
- raw runtime logs are temporary evidence, not long-term memory
- current source files always override historical memory
- governance is read-first and confirmation-oriented

This is a memory runtime, not a full autonomous knowledge graph.

## Project Feature Overview

```text
User task / symptom
  -> agent chooses one of four skills
  -> skill calls tools/agent_memory.py
  -> runtime reads/writes SQLite memory
  -> runtime emits bounded context, review actions, or reflection payloads
  -> Obsidian vault mirrors the current state for human review
```

The project is especially optimized for:

- **code-aware memory**
- **goal-oriented log context for Agent-led diagnosis**
- **experience and skill evolution**
- **governed refresh and drift review**
- **Agent-owned repository design using supplied context**
- **bounded context that reduces repeated token spend**

## Feature Matrix

| Capability | Current implementation |
|---|---|
| Local storage and retrieval | Per-project SQLite stores with FTS5 and incremental indexes |
| ArkTS code understanding | Pages, components, routes, resources, Ability/config, state, async, API, and log relations |
| Code and log graph | Files, symbols, code logs, and versioned typed `memory_edges` |
| Incident context | Log keywords, source anchors, candidate call paths, corrections, experience, and gaps |
| Design context | Repository structure, task/project constraints, quality questions, design knowledge, and provenance |
| Experience model | Procedure, correction, and semantic-patch experience lanes |
| Skill evolution | Reviewed multi-case procedure experience can become a Skill candidate or package |
| Governance | Refresh, stale/merge/conflict/miss/feedback review, graph health, and action plans |
| Change impact | Git changes mapped to symbols, dependents, logs, tests, history, and coverage gaps |
| Quality evaluation | Retrieval, trust, log, graph, semantic, design-context, and Agent A/B checks |
| Token control | Compact diagnosis and design contexts capped near 1,500 estimated tokens |
| Human review | Generated Obsidian mirror plus health, review, and plan commands |

## Memory System Design

The memory layer is split by responsibility.

### 1. Semantic Facts

Durable project knowledge that should survive beyond one task.

Representative fields:

- `fact`
- `source`
- `confidence`
- `scope`
- `evidence`
- `status`
- `use_count`
- `last_used_at`

### 2. Episodes

Task- or incident-level summaries.

Representative fields:

- `task`
- `summary`
- `outcome`
- `files_touched`
- `commands_run`
- `importance`

### 3. Reflections

Structured lessons after diagnosis, design, execution, or workflow attempts.

Representative fields:

- `task_type`
- `experience_type`
- `problem`
- `reasoning_summary`
- `what_worked`
- `what_failed`
- `verification_method`
- `repair_action`
- `useful_followup_focus`
- `useful_followup_terms`
- `misleading_followup_terms`
- `inspection_targets`
- `final_verification_path`

### 4. Codebase Wiki

A lightweight learned model of the codebase.

It stores:

- files
- symbols
- code log statements
- deterministic memory edges

This supports incremental code learning without requiring a full call graph or
external search service. Edges carry source revision, extractor version,
evidence class, validity interval, and verification time so refresh and rebuild
can retire stale derived structure.

### 5. Code Log Memory

One of the project-specific strengths of this system is that logs are first-class memory anchors.

During learning, the runtime extracts code log statements and links them back to:

- file
- function or symbol
- route
- resource
- nearby business semantics

This lets the agent move from:

```text
user symptom
-> relevant code log anchors
-> temporary-log search plan
-> current source and candidate call paths
-> Agent comparison against real log order
```

instead of treating logs as raw text blobs.

### 6. Runtime Usage Sample

The system also keeps a lightweight runtime-only usage summary:

- recent commands used
- query rounds
- followup focus
- suggested terms
- dominant runtime signals
- bounded recent context references
- governance lanes touched

This is stored as a runtime file, not as a new long-term database table.

Its purpose is to reduce reflection overhead by letting `reflect` auto-fill missing structured fields from the most recent bounded work trail.

## Experience System Design

The experience layer is intentionally split into two kinds.

### Procedure Experience

Reusable workflows.

This is the branch that can evolve into:

```text
reflection
-> procedure_experience
-> skill pattern
-> skill draft
-> skill candidate package
-> formal skill
```

### Correction Experience

Memory correction and semantic repair.

This branch feeds:

```text
correction_experience
-> learn governance
-> semantic repair
-> better future memory quality
```

Correction experience is a scoped query guardrail. It cannot evolve into a
Skill, create graph edges, or establish current architecture without source
confirmation.

### Semantic Patch Experience

A focused proposal to repair business meaning attached to a learned file,
symbol, code log, or edge. It identifies the anchor, semantic field, old/new
value, reason, applicability, and verification source. Maintain reviews it
before applying the patch.

### Incident Strategy And Recurring Fingerprints

For runtime-log-backed diagnosis, the system also clusters repeated patterns into:

- **incident strategy candidates**
- **recurring incident fingerprints**

These are intentionally lighter than full formal skills. They preserve repeated diagnosis structure without forcing premature promotion.

## Governance Design

Memory is only useful if it can be maintained.

Agent Memory includes governance for:

### 1. Drift And Refresh

Projects change. Learned scopes can be refreshed.

The system can:

- re-index changed structure
- detect removed files
- identify semantic review targets
- suggest stale review for affected experiences

### 2. Stale / Weak / Duplicate Review

The runtime can identify:

- stale records
- low-confidence records
- duplicate candidates
- incomplete reflections
- query misses

### 3. Semantic Conflict Review

When a new semantic write conflicts with an existing summary, the system does not silently overwrite it. It records a reviewable semantic conflict.

### 4. Skill And Strategy Governance

The runtime can produce review artifacts for:

- skill pattern candidates
- incident strategy candidates
- recurring incident fingerprints
- log design gaps

These are review-first outputs. Promotion stays controlled.

### 5. Log Design Feedback

The system does not only consume logs. It can also point out where the codebase is missing high-value logging, such as:

- start markers
- branch decision checkpoints
- request/session correlation
- stable failure wording

This helps future diagnosis quality improve over time.

### 6. Quality And Signal Gates

The runtime now exposes measurable gates for the main quality loops:

- retrieval gates: expected hit rate, exact anchor rank, blocked bad matches, and experience noise rate
- trust gates: expected trust rate and blocked overtrust rate
- log signal gates: good signal rate and low signal event rate
- graph signal review: weak anchors, missing business semantics, missing log signal fields, and focused repair targets

These gates are local JSON checks. They do not mutate memory. Their job is to catch regressions before a ranking, learning, graph, log, or calibration change makes Agents noisier.

### 7. Delayed Feedback Confirmation

Retrieval and use observations are not immediate truth updates:

- one unverified observation does not change ranking
- a verified event or the same scoped signal from two independent tasks becomes stable
- task-derived event keys make retries idempotent
- resolved or ignored feedback is excluded
- query reads are candidate-directed instead of scanning a global recent tail

## The Four Skills

The user-facing interface stays intentionally small:

| Skill | Role |
|---|---|
| `agent-memory-learn` | Learn code structure, code semantics, code logs, and project scope |
| `agent-memory-query` | Retrieve memory, code/log anchors, impact evidence, and Agent-owned design context |
| `agent-memory-maintain` | Run doctor, health, review, refresh, governance planning, and vault export |
| `agent-memory-reflect` | Store structured lessons, reusable experiences, and correction evidence |

Everything goes through these four skills. The system grows under the hood without forcing the user to learn a new interface.

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

Learn an external project into the current archive:

```bash
python tools/agent_memory.py learn-entry --project . --source /path/to/app --entry entry/src/main/ets/pages/Index.ets --depth 2 --json
python tools/agent_memory.py learn-path --project . --source /path/to/app --path entry/src/main/ets --json
```

Learning returns `parse_stats` with file, language, symbol, log, edge, and `semantic_index` coverage counts. It also records log-like statements in code, such as `logger.error(...)`, `console.warn(...)`, ArkTS `hilog.info(...)`, and `print(...)`, then connects them to the learned file and nearest detected function. ArkTS and TypeScript adapters add bounded symbol-level calls, state flow, callbacks, inheritance, API boundaries, and async relations through the language-neutral `semantic-index/v1` contract. Callable source ranges also contribute bounded member-call terms to a separate sparse FTS5 lane; multi-term evidence can recall a generic owner such as `execute` without changing ordinary symbol ranking. Known preview, cache, and generated source directories are excluded during learning; query-time path classification also protects archives created before that policy. Explicit language terms such as ArkTS, TypeScript, Python, Dart, and Swift select matching implementations only when the query names one language. For HarmonyOS projects, learning also indexes `.json5` module/package config, ArkTS router targets, and `$r(...)` resource references. See [Semantic Index](docs/semantic-index.md).

The optional `providers/arkts-arkanalyzer` package builds a real ArkAnalyzer Scene, runs type inference, and emits validated `exact` batches. Configure it only through `AGENT_MEMORY_SEMANTIC_PROVIDER_ARKTS`; missing dependencies or analysis failure remain visible and fall back to the built-in static adapter. Use `eval-semantic` before relying on exact mode. See [External Semantic Provider](docs/semantic-provider.md).

Query memory:

```bash
python tools/agent_memory.py context --project . --query "memory governance workflow" --json
python tools/agent_memory.py context --project . --query "个人中心空白，profile load failed" --json
```

`context` retrieves advisory history, learned log keywords/statements, current
source anchors, and bounded raw graph edges. Its `query_handoff` tells the local
Agent what was found and what can be queried next. It does not read temporary
user logs or generate evidence chains, hypotheses, or root causes. The Agent CLI
reads the temporary stream log directly, summarizes observations, forms
multiple candidate causes, queries each candidate separately, inspects current
source, and infers call and causal chains.

It also routes concrete questions to local retrieval and architecture/recurring-theme questions to bounded global aggregates. Retrieval uses at most three deterministic subqueries, stops when cross-lane coverage is sufficient or no new evidence appears, and limits duplicate experience/file patterns before building the final context.

Retrieve design context from the current repository before the Agent designs:

```bash
python tools/agent_memory.py design-context --project . \
  --query "design profile caching without moving persistence into the page" \
  --compact --json
python tools/agent_memory.py design-context --project . \
  --query "design profile caching without moving persistence into the page" \
  --concern performance --concern compatibility \
  --anchor service/ProfileService.ets --compact --json
```

`design-context` returns repository facts, task and project constraints, quality-attribute questions, versioned design knowledge, historical warnings, evidence gaps, and provenance. The first query orients the Agent; a second query uses Agent-confirmed concerns and source anchors. Pattern entries expose applicability, contraindications, tradeoffs, and questions but are never Runtime recommendations. The Agent CLI owns alternatives, tradeoff analysis, selection, implementation planning, and verification reasoning. Legacy design decision commands remain callable only for compatibility. See [Design Context Provider](docs/superpowers/specs/2026-07-16-design-context-provider.md).

General design knowledge is shipped as a versioned catalog and remains separate
from project SQLite memory. Task feedback cannot automatically rewrite it.
Unverified semantic corrections are returned below current graph evidence as
source-check guardrails, not accepted architecture decisions.

The Query Skill uses progressive disclosure: its main `SKILL.md` is a thin intent router, while code understanding, diagnosis, impact, evidence policy, and code design live in one-level `references/` files loaded only when relevant. The public interface remains four skills.

Assess a change before editing or review:

```bash
python tools/agent_memory.py impact-scope --project . --base HEAD~1 --query "profile loading change" --json
```

`impact-scope` maps changed files to learned symbols and logs, one-hop file- and symbol-level reverse dependencies, related incidents, and experience. Unlearned files are reported as coverage gaps; they are never silently treated as low risk.

Record the compact test outcome so later similar changes can improve test selection:

```bash
python tools/agent_memory.py impact-feedback --project . --outcome fail \
  --executed-tests tests/ProfileServiceTest.ets \
  --failed-tests tests/ProfileServiceTest.ets --json
```

The feedback row contains changed/test path summaries only. Source diffs and test output are not stored.

For diagnosis, query an observed log or output string directly:

```bash
python tools/agent_memory.py context --project . --query "retrying job" --json
```

Network context is bounded: the runtime returns only allowed raw edges. Recursive investigation happens when the Agent asks a sharper follow-up query and checks current source.

Reflect after a task:

```bash
python tools/agent_memory.py reflect \
  --project . \
  --payload '{
    "task_type": "execution",
    "outcome": "success",
    "problem": "Add guided review workflow.",
    "task": "add guided review workflow",
    "summary": "Implemented maintain-plan before mutation.",
    "reasoning_summary": "The workflow is safer when review actions are generated before writes.",
    "context_used": ["query: memory governance workflow"],
    "what_worked": ["Use a read-only plan before status changes"],
    "what_failed": [],
    "lesson": "Governance actions should be proposed before mutation.",
    "future_rule": "Run maintain-plan before status, merge, or promote.",
    "trigger_condition": "When cleaning or organizing memory",
    "repair_action": "Generate an action plan and ask for confirmation"
  }'
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
| `agent-memory-query` | Retrieve memory, log/code anchors, impact, and design context | `context`, `design-context`, `impact-scope`, `search` |
| `agent-memory-maintain` | Initialize, check, review, govern, and export memory | `doctor`, `maintain-plan`, `vault-export` |
| `agent-memory-reflect` | Save lessons, facts, and reflection feedback | `reflect`, `reflect-review`, `update` |

The CLI is the stable backend API and debugging escape hatch.

## Common Commands

```bash
python tools/agent_memory.py init --project .
python tools/agent_memory.py doctor --project .

python tools/agent_memory.py learn-entry --project . --entry "<file>" --depth 2 --json
python tools/agent_memory.py learn-entry --project . --source "<external-project>" --entry "<file>" --depth 2 --json
python tools/agent_memory.py learn-path --project . --path "<directory>" --json
python tools/agent_memory.py learn-path --project . --source "<external-project>" --path "<directory>" --json
python tools/agent_memory.py wiki-index --project .
python tools/agent_memory.py wiki-index --project . --source "<external-project>"

python tools/agent_memory.py context --project . --query "..." --json
python tools/agent_memory.py design-context --project . --query "..." --compact --json
python tools/agent_memory.py impact-scope --project . --base HEAD~1 --query "..." --json
python tools/agent_memory.py impact-feedback --project . --outcome pass --executed-tests "..." --json
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
- `docs/agent-cli-query-skill-guide.zh-CN.md`: Agent CLI 调用 Query Skill 进行问题定位和代码设计的详细中文指南。
- `docs/design-usage-guide.md`: dedicated Chinese guide for the Agent-owned, two-pass Design Context workflow.
- `docs/context-provider-boundary.md`: hard Runtime/Agent boundary for diagnosis and design.
- `docs/agent-benchmark.md`: Git history harvesting, ArkTS mutation cases, and Agent Query Skill A/B validation.
- `docs/local-agent-incident-workflow.md`: local Agent diagnosis, verification, impact-feedback, and reflection loop.
- `docs/runtime.md`: runtime protocol notes.
- `references/schema.md`: SQLite schema notes.
- `docs/phase-2-memory-governance-plan.md`: memory governance plan.
- `docs/guided-memory-review-workflow.md`: guided review workflow.
- `docs/reflection-quality-loop.md`: reflection quality loop.
- `docs/query-miss-feedback-loop.md`: query miss feedback loop.
- `docs/code-log-statement-network.md`: code log statement extraction and memory edges.
- `docs/templates/diagnosis-memory-query-template.md`: recursive diagnosis template.
- `docs/templates/change-design-memory-query-template.md`: repository-grounded design and Delta Graph template.
- `docs/templates/memory-query-answer-skill-template.md`: copyable skill template for query, logs, recursive search, and final answers.
- `docs/superpowers/specs/2026-07-16-long-term-data-governance-kernel.md`: long-term observation, stable-signal, and governance architecture.
- `docs/superpowers/specs/2026-07-16-design-context-provider.md`: long-term Agent-owned design-context architecture and industry references.
- `gitlog.md`: local development log and rollback notes.

## Roadmap

- Ingest accepted and superseded ADRs as project design constraints.
- Split legacy design scoring from objective source/API/graph/test validation.
- Improve stable symbol identity and language-neutral semantic providers.
- Expand real-repository Agent A/B cases for diagnosis and design quality.
- Add durable governance cases and selective audit events only when workload volume justifies them.
- Add retention and rollups after feedback correctness and stable entity identity are proven.
- Consider richer retrieval only after deterministic FTS5 quality and cost gates remain stable.
