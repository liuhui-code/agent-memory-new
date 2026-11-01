---
type: adr
id: ADR-system-meta-recursive-evolution-2
status: proposed
scope: ["tools/agent_memory_runtime/system_evolution*.py", "tools/agent_memory_runtime/prospective_cohort*.py", "skills/agent-memory-*/**"]
owner: ""
approved_by: ""
approved_at: ""
approval_ref: ""
supersedes: ""
superseded_by: ""
---

# 以跨版本反馈支持有界递归演进

日期：2026-10-30。本文是拟议选择；当前用户授权调研和方案完善，未补造 ADR 批准。
它补充[既有生命周期 ADR](0001-system-meta-reflection-lifecycle.zh-CN.md)，不取代其已实现语义。

问题：现有闭环已支持实际候选、应用和回退，但 closed 只表示声明的后续检查满足。
长期真实结果尚未关联回原假设及其产生方法；单任务内反复自评也没有新增独立反馈。
用户要求进一步研究如何改善规则、查询、学习、反思乃至数据结构，并递归改进改进机制。

拟采用：

1. 保留任务级一次自动评审和系统改进活动自动跳过；跨版本复核由新的真实结果、冻结窗口
   和既有授权驱动。用户明确请求的批次评审沿用真实关联，不轮换任务 ID 绕过去重。
2. 按 PDSA 写明预期与实际结果，借鉴 MAPE-K 分开观测、分析、计划和执行。Runtime 负责
   类型化证据与显式执行，当前 Agent 负责诊断和设计，SQLite 继续作为产品记录真源。
3. 保留稳定基线，小范围串行考察一个候选；同轮评价规则冻结。评测器和采样规则改进各自
   形成候选和新版本，不能由降低标准追认本轮通过。
4. 效果分为机制验收、自然观察和受控比较。缺少可信分母、对照或样本时保留 unknown /
   inconclusive；真实活动先具备来源和固定停止，不从既有开发回归推断长期效能。
5. 先用现有提案、操作引用和有界制品实现结果回灌，再按实际合同需求决定最小 SQLite
   扩展与宿主编排。不预设新数据库、调度服务、第五个 Skill 或框架依赖。
6. 可修改系统规则与结构；新模型迁移、query_handoff 兼容、授权和已消费外部材料纪律
   持续适用。代码回退不覆盖应用后的普通 Memory 写入。

替代方案：同回合自动反思直到满意、仅累积经验文字、直接复制开放式进化搜索、先建完整
调度架构。它们分别缺少独立反馈、系统改动制品、当前项目适配证据或最小合同需求，因此
不作为本阶段默认实现。

后果：允许持续提出并检验改进，包括对元反思本身的改进；不承诺单调增长或数学收敛。
需要版本/样本隔离、效果分账和停止规则；真实任务输入缺失时可完成开发契约，不能宣称
效能活动已经启动。下一阶段能力没有因本 ADR 被创建而自动上线。

研究原文、实际实践、完整契约、切片和 RE01–RE14 预期见
[跨版本递归演进方案](../system-meta-reflection-recursive-evolution.zh-CN.md)。
当前实现及通过证据见[CONTEXT](../../CONTEXT.md)和
[生命周期完成证据](../system-meta-reflection-completion.zh-CN.md)。

2026-11-01 实施注：当前用户继续指示下，R1 已以
[只读效果上下文](../system-meta-reflection-outcomes.zh-CN.md)复用现有提案/操作和有界制品。
该实现不创建轮次数据库或自动编排，也不把当前用户的实施授权补填为 ADR 批准。

后续 R2 已以[最小持久化契约](../system-meta-reflection-rounds.zh-CN.md)在同一 SQLite 增加
一张不可变事件表。安装走显式备份迁移；记录保留修订、父子关系、次数预算和晚到评估，
不覆盖原决策、不执行部署。它没有新增独立数据库或自动循环，批准字段仍留空。

R3 随后采用[宿主窗口交接](../system-meta-reflection-handoffs.zh-CN.md)：v2 结果计划事先绑定
复核许可/一次尝试/字符预算，独立可选交接组件保存不可变名额及完成事件。当前宿主在实际
任务/批次边界评估，Runtime 不调用模型。名额共享当前 v1 去重，完成与 R2 assessment
原子追加；保留输入漂移、失败及不重试边界。此交接不提供正常任务自动抽样或长期效能结论。

R4 按用户明确选择仅完成[就绪准备](../system-meta-reflection-campaign-readiness.zh-CN.md)。
只读门禁分账内部能力、外部资料、活动合同和证据；原有协议校验移到 Cohort 初始化之前。
它不放宽 diagnosis v1，不读取业务归档或开始真实任务；R4/R5 实际来源和效能仍未就绪。

既有选择的组合另见[两轮开发演练](../system-meta-reflection-development-journey.zh-CN.md)：
不新增运行时能力，以安装版测试核对父子轮次、晚到反馈、停止及代码/Memory 恢复。
这不构成 ADR 批准、真实活动启动或长期收益证据。
