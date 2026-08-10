# 静态调用关系证据决策记录

## 决策

截至 2026-08-09，禁止因为 `wgli-collab/qs-arkts#1` 的观察而把静态
`calls` 边加入 `context --compact` 的 serving 输出。该观察只能证明一条已
入库的 `merge -> hasOwnKey` 静态边没有进入该次 `query_handoff`；它不能证明
Agent 因此无法定位问题、增加源码探索，或得出较差结论。

本记录不创建新的用户 Skill、Runtime 命令、诊断接口或 Agent wrapper。四个
Skill、`tools/agent_memory.py`、SQLite 事实源以及 Runtime/Agent 的职责边界保持不变。

## 已证实事实

| 事实 | 证据 | 级别 |
| --- | --- | --- |
| ArkTS Adapter 可为已解析的相对导入别名生成跨文件 `calls` 边。 | 项目中独立 Development fixture 与 qs 冻结归档重建。 | Development |
| qs 的 `merge -> hasOwnKey` 边存储于 SQLite。 | 冻结归档数据库查询。 | Development |
| 同一查询的正式 full `query_handoff.edge_matches` 有 10 条 `imports`，没有 `calls`。 | 冻结归档的 `context --json` 产物。 | Development |
| 最终 compact anchors 包含 `merge`、`parseKeys` 和 `hasOwnKey`。 | 同一正式 `context --compact --json` 产物。 | Development |

`edge_matches` 由早期候选图端点收集，而 callable primary 由后续定位产生。因此这是
候选图关系与最终 callable 定位之间的阶段不对齐观察；尚未证明它是用户可见能力缺陷。

## 明确未知项

- 没有同一调查合同下的 Agent 结果证明，当前 anchors 不足以支持该任务。
- 没有证据表明暴露一跳静态边会提高定位、减少源码读取或降低端到端成本。
- 不知道不同语言、重导出、动态派发、回调和函数值调用是否指向相同的缺失契约。
- 静态边不等于运行时执行路径，也不等于日志的因果链。

## 为什么不直接投影到 `relation_hints`

`relation_hints` 是早期召回候选的通用、锚点相关关系投影；它不是 final primary 的稳定
邻接关系接口。把 primary 驱动的关系混入该字段会混合两个阶段的语义。构造两跳或多跳
调用链则会让 Runtime 从“证据供给”越界为“路径推理”。

即使以后有足够证据，候选方案也只能返回带 `static_semantic` 来源、解析置信度、方向、
文件、符号、源码范围和索引 revision 的少量原子边。Agent CLI 必须结合当前源码和临时
日志决定是否组成路径、淘汰分支或形成根因假设。

## 后续准入合同

任何 serving 改动前，必须按 `docs/evaluation-and-change-policy.md` 完成以下闭环：

1. 创建一个项目无关的 Development fixture：最终 primary 可稳定定位，但当前公开
   handoff 缺少一条已解析的一跳静态边。
2. 为该 fixture 定义源代码、症状和 Oracle 均可审查的调查任务；不得把“应返回某条边”
   本身伪装为用户问题。
3. 在相同源码预算、模型、停止规则和调查协议下，比较现有 Context 与候选原子边证据；
   报告文件/机制命中、源码搜索和读取、Token、端到端耗时及最坏回归。
4. 在第二个独立缺陷类别中重复观察到相同的“final callable 邻接静态证据缺失”合同，才可
   调整架构抽象；单一案例最多支持最小 serving 修复。
5. 使用未参与调优的新来源执行一次性外部验证。没有合格来源时，结论止于 Development，
   不宣称质量提升或泛化。

当前真实连续任务 cohort 的就绪状态仍是 no-go，详见
`docs/real-campaign-readiness-audit.zh-CN.md`。在用户提供并确认活动项目、连续任务来源、
外部原始任务保管、验证规则和冻结源码发送授权之前，不创建真实 cohort，也不执行新的
Agent A/B 活动。

## 理论与实践依据

- [Microsoft ExP 的实验阶段原则](https://www.microsoft.com/en-us/research/group/experimentation-platform-exp/articles/patterns-of-trustworthy-experimentation-during-experiment-stage/)：先固定可证伪假设、主指标和护栏，再解释效果。
- [SWE-bench](https://arxiv.org/abs/2310.06770)：真实软件任务应绑定冻结源码与可验证结果，不能以结构邻接代替任务结论。
- [LongMemEval](https://arxiv.org/abs/2410.10813)：记忆系统应同时衡量使用、更新和 abstention，不能只以检索到的信息判断价值。
- [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/specs/otel/schemas/)：持久化稳定、最小、可解释的观测字段；不记录或推断私有推理。

## 当前状态

**No-go for serving change.** 当前应保留已验证的 ArkTS 解析与索引改进，停止围绕 qs
观察继续扩张查询输出；下一项有效工作是收集满足上述合同的独立 Development 证据或真实
活动输入。
