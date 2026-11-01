---
type: feature-spec
id: SPEC-system-meta-persistent-rounds-1
status: draft
scope: ["tools/agent_memory_runtime/system_evolution_rounds*.py", "tools/agent_memory_runtime/system_evolution_migrations.py", "tests/test_system_evolution_rounds.py"]
owner: ""
approved_by: ""
approved_at: ""
approval_ref: ""
supersedes: ""
superseded_by: ""
---

# R2：跨会话轮次、评估与决策的持久化

日期：2026-11-01。按用户继续指示实施；批准字段留空。
承接 [R1 只读结果关联](system-meta-reflection-outcomes.zh-CN.md)及
[递归演进方案](system-meta-reflection-recursive-evolution.zh-CN.md)。R2 不改变查询、排名或自动触发。

## 数据与显式迁移

在原 SQLite 中新增一张追加表 system_evolution_round_events，独立组件
system_evolution_rounds / system-rounds-v1。复用 maintain-system-migrate 的备份、写者排除、
事务和完整性检查，要求原治理已为 v2，--target-version system-rounds-v1 才安装。
默认预览；普通初始化、读取及 round-record 不创建组件。

表保存 project/study/round、revision、kind、幂等 record_key、严格请求和快照的 JSON/摘要、
实际记录时间。每项目/轮次/修订及每项目/幂等键唯一；UPDATE/DELETE 触发器拒绝覆盖/删除。
请求最多 32 KiB，快照最多 128 KiB，检查摘要能识别普通存储损坏，不提供外部身份认证或 seal。
未知版本、组件缺项或缺少保护触发器拒绝读写，不自动修复或降级丢弃记录。

迁移失败整体回滚并保留新备份。旧 Runtime 的普通读写需保持未知组件不变；没有删除组件的
降级入口。代码回退与数据恢复分开，不能用迁移前整库覆盖升级后的普通写入或轮次事件。

## 记录合同

新增 maintain-system-round-record，--payload-file 有类型有界 JSON，默认预览，--execute
才提交。严格格式见可安装的 [Maintain 参考](../skills/agent-memory-maintain/references/system-rounds.md)。

open 绑定 R1 事先声明的计划、原提案/实际应用、父轮次和冻结的记录次数预算。
assessment 保存实际读取的 R1 上下文、观察输入摘要、Agent finding/简短理由/引用和声明成本。
decision 引用最新 assessment；stop 可以在尚无 assessment 时冻结轮次。
Runtime 保存和校验记录，诊断与决策意见仍由当前 Agent 负责。

BEGIN IMMEDIATE 串行化写入，expected_revision 实施乐观并发控制；重试内容相同返回旧记录，
冲突拒绝。所有事件追加，保留旧的失败、未知及随后修订的声明，不把模型支持意见变成事实。
不保存原始任务/查询/日志、源码、完整命令或私有推理。R1 的任务/成本声明仍未被认证。

## 预算、父子关系和未决工作

每研究最多 1–10 个记录轮次，每轮最多 1–20 次评估记录，第一轮起冻结预算。
子轮必须沿本研究最新已决且非 stop 的父轮串行推进，并绑定新的计划或候选。
父子顺序按固定 round_index，晚到的父轮评估不会把谱系错误倒序。
约束边界是实际项目/Memory Home/study；禁止换键绕过，同源重试不增加独立效能证据。
这些是已记录工作的计数上限，不是模型实际 Token、额外调用或工具时间的自动计量/限制。

不允许未决检查、候选、running/interrupted 应用期间开始或评估轮次。
stop/inconclusive 可记录，但不清理实际操作、不回收未知子进程、不更改提案状态。
R2 约束轮次记录流程，不接管既有 apply/rollback 的实际执行或宿主的后续编排。

## 后续反馈与不可变决策

未决轮次可以追加评估；非 stop 的已决轮次也可在剩余预算内保存新的可观察上下文，
但仍为 decided，原 decision/decision_revision 保留。相同上下文的新措辞不是晚到证据。
stop 禁止续写。需要新决策时使用有新绑定的授权子轮，不能追认、覆盖或重开原决策。

adopt_candidate 只是建议，额外要求：Agent finding 为 supported、观察输入未漂移、
声明窗口完整且有纳入项、其结果全为 pass、任务成本齐备、实际应用像匹配，并无失败监测、
未决工作或历史截断。上述完备性检查不认证声明真实性，不计算因果收益或外部晋级。
rollback 记录也不执行代码回退，仍须现有授权生命周期入口。

## 跨会话读取

maintain-system-round 可列出项目轮次、按 key 查看最新快照与有界修订摘要，或按 revision
读取旧完整快照。缺归档/组件时不初始化；读取不依赖原计划或观察文件仍在。
最新事件可能是晚到评估，状态读 receipt.state；原决策需按 decision_revision 复核当时材料，
不能把最新上下文当成旧决策已重新验证。最多返回 20 条历史摘要，截断明确。

始终 advisory_only=true、history_authenticated=false，evidence_verified、efficacy_verified、
promotion_eligible、application_performed、proposal_state_changed、model_invoked 均为 false。
R2 本身不编排模型。后续 [R3](system-meta-reflection-handoffs.zh-CN.md)已提供有界窗口交接，
R4/R5 真实队列和独立效能活动仍为后续范围。

本切片的实际执行范围、隔离用例和机器记录见[完成记录](system-meta-reflection-rounds-completion.zh-CN.md)。
