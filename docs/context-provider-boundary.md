# Agent 上下文供给边界

## 项目立意

Agent Memory 不是诊断 Agent，也不是规则式根因定位器。它是本地 Agent
CLI 的项目上下文层：从 SQLite 中检索历史经验、业务语义纠正、代码日志
模板、日志关键词、当前源码锚点和原始图关系，帮助 Agent 缩小调查范围。

临时用户流水日志不属于项目记忆。Runtime 不读取、不解析、不保存这些日志。
本地 Agent CLI 直接读取日志，并负责全部诊断推理。

## 协作流程

```text
用户问题
  -> context：历史经验 + 日志关键词 + 代码锚点 + 原始边
  -> Agent CLI 读取临时流水日志并汇总观察
  -> Agent CLI 提出多个候选原因
  -> 每个候选原因分别调用 context
  -> Agent CLI 阅读当前源码，拼接可能的代码调用链
  -> Agent CLI 用日志时序、源码机制和反证推断因果链
  -> 复现、修改、测试和验证
```

第一轮查询的目标是找到“日志里应该搜什么”和“源码从哪里开始读”，不是
返回诊断答案。第二轮查询必须一次只描述一个候选原因，避免多个假设的关键词
互相污染召回结果。

## Runtime 允许做什么

- 使用 FTS5 和现有排序召回相关历史记录。
- 返回代码中已学习的日志模板、logger、进程提示、事件和阶段。
- 返回文件、符号、函数和行号等源码锚点。
- 返回有界的原始代码图、日志图和 Incident 关系边。
- 标注来源、时效、权威性、冲突、覆盖缺口和匹配原因。
- 返回已学习的 ADR / Feature Spec 引用、声明状态、批准字段、适用范围和源文状态；批准真实性与契约适用性由 Agent 核查。
- 在 `query_handoff` 中给出下一轮查询契约。

排序只决定 Agent 先看什么。原始边只说明存储中存在某种关系；它不是当前
故障的调用链或因果结论。

## Runtime 禁止做什么

- 读取或结构化分析临时用户日志。
- 生成候选根因、根因排名或停止条件。
- 返回 Runtime 组装的 evidence chain、candidate chain 或 causal chain。
- 把静态可达、时间相邻或关键词相似表述成当前因果关系。
- 根据历史经验直接决定修改文件。
- 持久化 Agent 私有思维过程或临时日志原文。
- 让旧记忆覆盖当前源码、当前日志或用户明确约束。

## `query_handoff` 输出契约

- `log_keywords`：Agent 可用于临时日志检索的词。
- `log_anchors`：代码中已学习的日志模板及其文件、函数、阶段等事实。
- `code_anchors`：当前调查建议优先读取的源码位置。
- `experience_refs`：相关历史经验引用，只作提示或约束。
- `semantic_refs`：业务语义事实和纠正引用。
- `normative_context`：可选的规范性文档引用；字段是待审查的来源声明，不是 Runtime 确认的批准或验收结论。
- `next_query_contract`：要求候选原因逐个调用 `context`。
- `role_boundary`：明确 Runtime 不读临时日志、不构建因果链。

Query Skill 使用选择性渐进披露。精确的源码局部问题先执行有界直接检查；日志、
跨模块、异步、历史语义或直接检查未解决的问题使用 `context --compact`。紧凑视图
在 1500 Token 估算预算内保留锚点、候选路径、纠正、关系提示和缺口。同一个精确
查询去掉 `--compact` 即为完整审计展开，但不会改变 Runtime 的权限边界。

截断标记与紧凑投影分开解释，现有 JSON 字段和 schema 版本不变：

- `agent-context-compact/v1` 表示固定的紧凑视图，包括字段投影和条数上限；
  不因使用这个视图就把 `output_budget.truncated` 设为 `true`。
- `output_budget.truncated` 只表示紧凑视图在本次输出预算处理时实际发生了进一步
  缩减，包括为源码摘录预留空间时的缩减。预算内且未进一步缩减时为 `false`。
  该值不是“超过目标预算”的状态；应另比较 `estimated_tokens` 与 `target_tokens`。
- `source_excerpts[].truncated` 表示请求的源码窗口中确有内容因行数或字符预算被省略。
  请求窗口延伸到文件末尾之外，但实际存在的内容完整返回时为 `false`。
  `start_line` / `end_line` 仍指向实际返回的源码范围。
- 两类标记作用域不同：预算标记不是摘录标记的汇总，`false` 也不证明返回了完整
  检索记录、完整源码文件或整个仓库。紧凑视图、摘录选择和检索本身仍有各自边界。

## 自验证边界

A/B Benchmark 比较同一个外部 Agent：

```text
Baseline = Agent CLI + 冻结源码
Context  = Agent CLI + 冻结源码 + context 查询结果
```

外部 Agent Runner 负责读日志、推理根因、选择文件和给出验证结果。Benchmark
使用隐藏 Oracle 评价最终结果，衡量上下文是否提升关键词、源码定位和调查效率，
而不是证明 Runtime 具备诊断能力。

日志锚定的 Top-K 调用路径能力采用相同边界，并通过现有 `context` 门面提供。
详细接口、算法、模块和分阶段计划见
[`log-anchored-call-path-design.md`](log-anchored-call-path-design.md)。

## 设计上下文边界

代码设计复用相同原则。`design-context` 根据用户需求返回当前代码图、源码锚点、
任务和项目约束、业务语义纠正、质量属性问题、通用设计知识、历史警告和证据
缺口。第一轮用于定向，第二轮由 Agent 提供确认后的 concern 和 anchor 聚焦。

Runtime 不推荐设计模式，不生成或比较候选，不选择方案，也不生成实施计划。
Agent CLI 阅读当前源码，判断适用原则，分析候选与权衡，并负责最终设计和验证。
长期协议与业界依据见
[`Design Context Provider`](superpowers/specs/2026-07-16-design-context-provider.md)。

`context.query_handoff` 与 `design-context.project_context` 可包含
`normative_context`。ADR 和 Feature Spec 原文及批准依据在 Git 中维护，SQLite
只保存可再生成的索引和有界快照，Obsidian 只镜像这些记录。Runtime 不认证批准，
不推断验收通过，也不裁决源码与规格冲突。草案只能形成假设，历史规格不能作为
当前硬约束；截断引用需展开查询或读取原文。此最小接入按用户要求编写，未执行
验证，完整契约见[规范性上下文文档](normative-context-adr-feature-spec-decision.zh-CN.md)。
