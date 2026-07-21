# Agent Memory MVP 中文说明

[English README](README.md)

Agent Memory 是面向 Coding Agent 的本地项目记忆与上下文运行时，当前重点优化
**ArkTS / HarmonyOS** 代码理解、日志定位、经验沉淀和代码设计上下文。

它不替代 Agent CLI 的推理能力：

- Runtime 负责学习、检索、关联、裁剪、治理和提供可检查证据。
- Agent CLI 负责阅读真实源码和临时日志、提出假设、还原调用关系、定位问题、
  设计方案、修改代码和验证结果。
- SQLite 保存长期项目记忆；临时用户日志、设计草案和 Agent 私有推理不入库。

![Agent Memory 项目特性示意图](docs/assets/agent-memory-overview.png)

## 为什么需要项目记忆

Coding Agent 在单次会话内很强，但跨会话、跨版本和重复任务中容易出现：

- 反复读取同一批页面、路由、资源、配置和服务代码；
- 已定位过的问题再次从头排查；
- 流水日志很多，却难以稳定找到日志对应的源码位置；
- 旧经验与当前代码冲突，反而干扰查询；
- 业务语义、历史约束和设计动机没有可靠载体；
- 上下文越来越长，真正相关的信息比例越来越低；
- 项目更新后，旧代码图和经验没有及时刷新或淘汰。

Agent Memory 的目标不是保存更多文本，而是向 Agent 提供**短、准、可追溯、
可治理**的项目上下文。

## 项目定位

```text
用户任务
  -> 固定四个 Skill
  -> tools/agent_memory.py
  -> SQLite + FTS5
       -> 项目记忆
       -> 代码/日志关系图
       -> 经验与纠正
       -> 治理观察
  -> 有界 Context
  -> Agent CLI 推理、实施和验证
  -> 结构化反思与维护
```

核心原则：

- `tools/agent_memory.py` 是唯一 Runtime 入口；
- SQLite 是唯一机器事实源；
- FTS5 是默认轻量查询引擎；
- Obsidian Vault 是生成的只读审查镜像；
- 用户始终只使用四个 Skill；
- 当前源码和用户约束高于历史记忆；
- 代码图、日志图、候选路径和经验都是辅助证据；
- 写操作经过显式命令或确认，维护流程先审查后变更；
- 不引入向量数据库、图数据库、常驻 daemon 或 Agent 专用 wrapper。

## 主要特性

| 能力 | 当前实现 |
| --- | --- |
| 轻量存储与查询 | SQLite + FTS5，按项目隔离，支持增量索引和候选定向查询 |
| ArkTS 代码理解 | 页面、组件、路由、资源、Ability、配置、状态、异步和 API 关系 |
| 代码图 | 文件、符号、日志和有类型的 `memory_edges` |
| 日志图 | 日志模板、logger、级别、函数、业务事件、阶段和相邻关键词 |
| 问题定位上下文 | 用户问题到日志关键词、代码锚点、候选调用路径和历史警告 |
| 设计上下文 | 代码结构、项目约束、质量属性问题、设计知识和证据缺口 |
| 影响范围 | Git 变更到依赖方、符号、日志、测试和覆盖缺口 |
| 经验系统 | procedure、correction、semantic patch 三类经验 |
| Skill 演化 | 多条已验证 procedure experience 可形成 Skill 候选和草案 |
| 数据治理 | stale、merge、conflict、miss、feedback、refresh 和 review |
| 质量门禁 | retrieval、trust、log signal、graph、design context 和 Agent A/B |
| Token 控制 | `context --compact` 与 `design-context --compact` 约束首轮注入 |
| 人工审查 | Obsidian Vault、maintain health/review/plan 和可解释治理动作 |

## 为什么重点支持 ArkTS

ArkTS / HarmonyOS 项目通常具有可利用的稳定结构：

- 页面和 `@Entry` / `@Component` 生命周期；
- Router 目标和页面注册；
- `$r(...)` 字符串、媒体等资源引用；
- Ability、module/package JSON5 配置；
- 状态字段、组件组合、服务调用、事件和异步关系；
- `hilog`、`console` 等代码日志；
- 页面、服务、仓储和数据层之间较明确的责任边界。

内置 ArkTS / TypeScript semantic adapter 会生成语言无关的
`semantic-index/v1` 数据。可选 ArkAnalyzer Provider 可提供更精确的 symbol、
call、inheritance 和 state evidence；Provider 不可用时会明确回退到静态适配器。
对方法名不具业务含义的代码，系统还会从 callable 源码范围提取有界调用词，写入
独立的稀疏 FTS5 索引；只有多个问题词共同命中时才补充方法锚点，不污染普通符号排序。
学习时会跳过明确的 preview、cache 和 generated 目录，旧索引查询时也会在存在正式
源码候选时过滤生成物。查询正向语义只明确指定一种语言时，可按扩展名注册表选择 ArkTS、
TypeScript、Python、Dart 或 Swift 实现；未指定或没有匹配候选时不会强制过滤。

长期架构仍保留其他语言扩展能力：上层查询、代码图、日志图、影响分析和设计上下文
只依赖标准化实体与关系，不依赖 ArkTS 专属接口。

## SQLite + FTS5 轻量查询

项目没有引入 embedding 服务或向量数据库。查询链路主要是：

```text
自然语言问题
  -> FTS5 候选召回
  -> 意图 lane 与状态过滤
  -> 当前代码、业务语义、日志、经验组合排序
  -> 反馈与使用结果校准
  -> 有界 Context 输出
```

FTS5 索引由 SQLite trigger 增量维护，不是第二事实源。索引只在首次创建、版本迁移
或显式执行 derived rebuild 时重建。

查询反馈采用延迟确认：

- 一条未验证反馈不会改变排序；
- 显式验证，或同一信号出现在至少两个独立任务后，才成为稳定信号；
- 同一任务重试通过 `event_key` 幂等；
- `resolved` / `ignored` 反馈不再参与查询；
- 查询只加载当前候选 ID 的反馈，不扫描全局最近事件。

## 记忆模型

### Semantic Facts

长期项目事实、业务规则、用户偏好和约束。

主要字段：

- `fact`
- `source`
- `confidence`
- `category`
- `scope`
- `evidence`
- `status`
- `use_count`
- `last_used_at`

### Episodes

任务或事件级摘要。

主要字段：

- `task`
- `summary`
- `outcome`
- `files_touched`
- `commands_run`
- `importance`

### Reflections

经过结构化的任务经验，而不是一段无边界的自然语言。

主要字段：

- `task_type`
- `experience_type`
- `problem`
- `reasoning_summary`
- `what_worked`
- `what_failed`
- `hidden_assumptions`
- `negative_preconditions`
- `trigger_condition`
- `repair_action`
- `verification_method`
- `inspection_targets`
- `useful_followup_terms`
- `misleading_followup_terms`
- `source_cases`
- `skill_candidate`

### Codebase Wiki

从当前代码学习出的轻量仓库模型：

- `code_files`
- `code_symbols`
- `code_log_statements`
- `memory_edges`
- `learn_scopes`

代码实体还可保存 Agent 补充的：

- `business_summary`
- `business_terms`

这些字段用于补足纯静态分析无法理解的业务含义。

## 代码图与日志图

学习代码时会提取：

```text
code_file --contains--> code_symbol
code_file --contains--> code_log_statement
code_symbol --emits_log--> code_log_statement
code_file --imports/routes_to/uses_resource--> code entity
code_file --defines_state/uses_service/renders_component--> code entity
code entity --calls/awaits/registers_callback--> code entity
```

每条边包含来源 revision、extractor version、evidence class、有效期和验证时间。
刷新和重建时旧边会失效，查询只使用当前有效边。

日志记录不仅保存原始语句，还可包含：

- `message_template`
- `logger`
- `level`
- `function`
- `business_event`
- `trigger_stage`
- `symptom_terms`
- `likely_causes`
- `process_hint`
- `neighbor_terms`

这样 Agent 可以从用户描述或真实日志的一行开始，找到代码日志、源码位置和多条可能
调用路径，再使用真实日志顺序和当前源码筛选路径。

## Agent 主导的问题定位

Runtime 不读取或保存临时用户流水日志，也不生成根因。

推荐流程：

```text
用户问题
  -> context --compact
  -> 获取日志关键词、代码锚点、候选路径、纠正和经验
  -> Agent 直接读取临时日志
  -> Agent 形成多个候选原因
  -> 每个候选原因分别再次 context 查询
  -> Agent 检查当前源码和真实日志顺序
  -> Agent 推断调用链与因果关系
  -> 修改、测试和验证
```

Query Skill 使用分层策略：

- **L0**：有明确文件、行号、符号、路由或配置时，先有限检查当前源码；
- **L1**：日志、跨模块、异步、历史语义或多候选问题使用
  `context --compact`；
- **L2**：对一个精确日志、符号或候选原因进行聚焦展开。

`context --compact` 的首轮 Agent 注入受约 1500 Token 估算预算约束。

## Agent 主导的代码设计

设计能力遵守相同职责边界：系统提供上下文，Agent 负责设计。

第一轮查询：

```bash
python tools/agent_memory.py design-context \
  --project . \
  --query "为 ProfileRepository 增加缓存并保持 ProfileService API 兼容" \
  --compact \
  --json
```

Agent 检查源码后，可按确认的质量属性和源码位置聚焦：

```bash
python tools/agent_memory.py design-context \
  --project . \
  --query "为 ProfileRepository 增加缓存并保持 ProfileService API 兼容" \
  --concern performance \
  --concern compatibility \
  --anchor data/ProfileRepository.ets \
  --constraint "页面不得拥有持久化状态" \
  --compact \
  --json
```

返回内容包括：

- 当前仓库 snapshot、入口、边界、状态所有者和消费者；
- 当前任务约束和项目业务语义纠正；
- 质量属性 routing hints 与场景问题；
- 带适用前提、反例、取舍和来源的设计知识；
- 历史经验警告、证据缺口和下一轮查询提示；
- 明确的 authority order 和 Agent/Runtime 职责边界。

Runtime 不推荐模式、不生成或排名候选、不选择设计、不生成实施计划。
旧 `design-assist/prepare/check/compare/progress` 命令仅为兼容保留。

详细中文指南：
[Agent CLI 代码设计能力使用指南](docs/design-usage-guide.md)。

## 经验系统与 Skill 演化

经验分为三类，避免相互干扰。

### `procedure_experience`

记录可复用执行流程：

```text
任务轨迹与结果
  -> 反思
  -> procedure experience
  -> 多案例复用与验证
  -> Skill pattern
  -> Skill draft/package
  -> 人工确认后正式 Skill
```

单次成功不会直接变成 Skill。系统会检查适用范围、反例、验证方式、来源案例和复用
结果，降低过拟合。

### `correction_experience`

纠正误导经验或错误业务理解。它是查询 guardrail，不会演化为 Skill，也不能改变
代码图结构。

### `semantic_patch_experience`

针对文件、符号、日志或边的具体业务语义字段提出修补，例如
`business_summary`、`business_terms`、`business_event` 或 `likely_causes`。
修补需要通过维护流程复核后应用。

## 项目更新、刷新与淘汰

`learn_scopes` 保存学习范围和文件摘要。项目更新后可以执行 changed-only refresh：

- 新文件进入学习范围；
- 修改文件重新索引；
- 删除文件及其派生实体和边失效；
- 原有业务语义在结构刷新后恢复；
- 相关经验和 semantic patch 进入 drift review；
- 不相关范围保持不动，避免全库重建。

派生代码图可以重建，长期语义事实、经验、治理观察和业务补充不会因此丢失。

## 数据治理

治理入口遵守 read-first：

```bash
python tools/agent_memory.py maintain-health --project . --json
python tools/agent_memory.py maintain-review --project . --json
python tools/agent_memory.py maintain-plan --project . --json
```

治理范围包括：

- stale、archived、merged、rejected 生命周期；
- 低质量、不完整、重复和过宽经验；
- 新旧经验冲突和 retrieval interference；
- 语义事实与代码业务语义冲突；
- 查询 miss、反馈 pending/stable/closed 状态；
- 图新鲜度、孤立日志、弱锚点和缺失业务语义；
- 学习范围刷新和派生图重建；
- procedure experience 的 Skill 候选；
- 日志可观测性缺口；
- Runtime Token、延迟和数据库体量指标。

`maintain-plan` 只生成有依据的动作建议，不静默修改数据。

## 影响分析与验证反馈

修改前或代码审查时：

```bash
python tools/agent_memory.py impact-scope \
  --project . \
  --base HEAD~1 \
  --query "Profile 加载流程修改" \
  --json
```

系统结合 Git 变更、代码图、符号、日志和经验返回：

- 直接修改文件和符号；
- 一跳反向依赖和下游依赖；
- 相关日志、测试和历史风险；
- 图覆盖缺口；
- 建议验证清单。

测试结束后可写入紧凑结果：

```bash
python tools/agent_memory.py impact-feedback \
  --project . \
  --outcome pass \
  --executed-tests tests/ProfileServiceTest.ets \
  --json
```

不会保存源码 diff 或原始测试日志。

## 质量评估与自验证

系统提供本地、可重复的质量评估：

- retrieval 命中率和精确 anchor 排名；
- 误导经验拦截和信任校准；
- 日志信号完整性；
- 代码图锚点、关系和业务语义覆盖；
- design context 的权威顺序、无设计结论和 Token 预算；
- Git 历史案例和 ArkTS 可控 mutation；
- 同一个 Agent 在有/无 Memory Context 下的 A/B 对比。

质量检查只评估系统是否提供了更好的上下文，不证明 Runtime 具备诊断或设计推理。

## 固定四个 Skill

| Skill | 职责 |
| --- | --- |
| `agent-memory-learn` | 学习代码、配置、业务语义、日志和项目范围 |
| `agent-memory-query` | 查询记忆、代码图、日志锚点、影响和设计上下文 |
| `agent-memory-maintain` | 初始化、健康检查、刷新、治理、重建和 Vault 导出 |
| `agent-memory-reflect` | 保存任务反思、procedure、correction 和 semantic patch |

新增能力全部在四个 Skill 内部渐进披露，不增加第五个用户入口。

## 快速开始

安装到当前项目：

```bash
python install.py --project . --local-skills
```

初始化和检查：

```bash
python tools/agent_memory.py init --project .
python tools/agent_memory.py doctor --project .
```

学习项目：

```bash
python tools/agent_memory.py learn-entry \
  --project . \
  --entry entry/src/main/ets/pages/Index.ets \
  --depth 2 \
  --json

python tools/agent_memory.py learn-path \
  --project . \
  --path entry/src/main/ets \
  --json
```

查询问题上下文：

```bash
python tools/agent_memory.py context \
  --project . \
  --query "个人中心空白，profile load failed" \
  --compact \
  --json
```

查询设计上下文：

```bash
python tools/agent_memory.py design-context \
  --project . \
  --query "重构 Profile 数据加载流程" \
  --compact \
  --json
```

任务完成后反思：

```bash
python tools/agent_memory.py reflect \
  --project . \
  --task "修复 Profile 页面空白" \
  --lesson "先用稳定日志锚点定位当前代码，再检查路由和资源关系"
```

导出人工审查镜像：

```bash
python tools/agent_memory.py vault-export --project .
```

正常使用应由 Agent 自动调用四个 Skill。CLI 是稳定后台接口和调试入口。

## 数据与隐私边界

默认保存在本地项目或指定 memory home：

```text
.agent-memory/
  projects/<project_id>/
    memory.db
    runtime/
    vault/
```

不会默认持久化：

- 用户临时流水日志全文；
- Agent 私有思维过程；
- 设计请求、候选方案和比较内容；
- 源码 diff；
- 原始测试日志；
- 外部 semantic provider 的 AST 和 stdout。

## 适合与暂不适合

更适合：

- ArkTS / HarmonyOS 项目；
- 页面、路由、资源、日志和模块结构明确的代码库；
- 需要重复定位、跨会话经验和持续治理的项目；
- 希望本地、低成本、可审计地增强 Agent CLI。

暂不追求：

- 分布式跨机器记忆服务；
- 完整 AST 图数据库；
- Runtime 自动诊断或自动设计；
- 无人工门禁的自修改代码或 Skill；
- 高成本 embedding / rerank 基础设施。

## 文档索引

- [Agent CLI Query Skill 中文指南](docs/agent-cli-query-skill-guide.zh-CN.md)
- [Agent CLI 代码设计能力使用指南](docs/design-usage-guide.md)
- [Agent 上下文供给边界](docs/context-provider-boundary.md)
- [本地 Agent 问题定位流程](docs/local-agent-incident-workflow.md)
- [日志锚定调用路径设计](docs/log-anchored-call-path-design.md)
- [Semantic Index](docs/semantic-index.md)
- [外部 Semantic Provider](docs/semantic-provider.md)
- [Agent A/B 自验证](docs/agent-benchmark.md)
- [Runtime 协议](docs/runtime.md)
- [SQLite Schema](references/schema.md)
- [长期数据治理内核](docs/superpowers/specs/2026-07-16-long-term-data-governance-kernel.md)
- [Design Context Provider](docs/superpowers/specs/2026-07-16-design-context-provider.md)

## 一句话概括

**用 SQLite + FTS5 + ArkTS 语义索引 + 代码日志锚点 + 轻量代码图 +
结构化经验治理，为本地 Agent CLI 提供真正相关且可验证的项目上下文。**
