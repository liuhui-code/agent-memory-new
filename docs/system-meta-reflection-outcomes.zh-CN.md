---
type: feature-spec
id: SPEC-system-meta-outcome-context-1
status: draft
scope: ["tools/agent_memory_runtime/system_evolution_outcome*.py", "skills/agent-memory-maintain/**", "tests/test_system_evolution_outcomes.py"]
owner: ""
approved_by: ""
approved_at: ""
approval_ref: ""
supersedes: ""
superseded_by: ""
---

# R1：原提案、实际应用与后续结果的只读关联

日期：2026-11-01。按用户继续指示实施 R1，批准字段留空。
本文落实[递归方案的首个切片](system-meta-reflection-recursive-evolution.zh-CN.md#11-实施顺序与完成条件)，
不扩展成轮次数据库、自动调度或真实长期效能活动。

## 行为

新增单一 Runtime 入口下的 `maintain-system-outcome`，参数为 --project、可选
--memory-home、--id、--application-key、--plan-file、可选 --observations-file 和 --json。
它读取已存在的 SQLite 治理记录及指定的有界开发制品，提供当前 Agent 可复核的证据上下文。
没有 --execute、状态修改、自动初始化、文件写入、模型调用或新表。

计划 `system-change-outcome-plan/v1` 必须是 prepared 时绑定的制品，先于候选检查和实际应用。
它关联提案/修订、round_key、hypothesis、expected_result、guardrails 及固定任务窗口。
核对时沿 actual apply → acceptance → candidate → prepared artifact 关联，不能在应用后
补写一份未绑定计划，或通过换路径/换应用/换项目冒充原预期。

后续 [R3](system-meta-reflection-handoffs.zh-CN.md)增加 plan/v2，保留全部 v1 字段并要求预绑定
host_review 许可/预算。当前 R1 读取支持两版本，仍完全只读；v1 不自动升级或继承交接许可。

后续声明 `system-change-outcome-observations/v1` 必须另存，绑定实际项目、提案、轮次、计划
SHA-256 及应用键。它保留连续到达序号、实际任务关联、纳入/排除、结果/验证引用及可用成本。
严格格式、边界和可安装使用协议见
[Maintain 参考](../skills/agent-memory-maintain/references/system-outcomes.md)。

## 事实与声明分账

SQLite 仍是报告、提案、检查和操作的事实来源。输出保留原问题/验收断言、父基线及其
caller-declared 属性、候选摘要、实际应用关联，以及应用后监测、关闭和回退记录。
真实退出码及产物错误来自既有操作记录；最多观察二十条后续记录，截断和未决操作明确标注。

当前文件前/后像仅为读取时观察，不构成原子快照。回退、漂移或目标不可读不会被改写成
已应用版本仍然生效；历史检查不因此重新执行或获得 Oracle 认证。计划材料须保留可读。

后续任务文件是调用方声明。Runtime 核对格式、绑定、连续序号、重复身份、排除原因和
有界成本，不认证真实到达时间、外部连续性、任务结果或验证人的独立性。declared_complete
只表示声明数量达到计划；缺任务为 partial，无文件为 unavailable，不能填成通过。
排除项计入 presented；未知结果和缺成本单列，不在分母中静默消失。

Agent 依据实际上下文复核原假设，区分工具事实、调用方声明与未知项；保持简短且不输出
私有推理。下一轮或新候选需要现有证据/授权条件，不能由本读取结果自动触发。
现有 `reflect-system` 可在授权后保存真实评审；R1 不给旧报告增加额外字段或绕过触发名额。
重复读取会重新观察当前输入及其摘要，不创建不可变轮次账本。需要保留本次复核时，应在
已授权的开发制品或既有严格评审记录中引用实际输入摘要；跨会话轮次持久化仍属于 R2。
后续 [R2 轮次记录](system-meta-reflection-rounds.zh-CN.md)已经实现该持久化；R1 本命令继续只读，
不会为了历史保存自动创建或写入 R2 组件。

## 声明边界

- 输出 `system-change-outcome-context/v1`，始终 advisory_only=true、requires_agent_review=true。
- records_written、proposal_state_changed、application_performed、model_invoked 均为 false。
- evidence_verified、efficacy_verified、promotion_eligible、causal_effect_established 均为 false。
- 声明成本是任务总量，未知为 null，不视为实测元反思增量成本；不自动计算净收益或因果效果。
- 当前 Cohort v1 仍只支持 diagnosis；本输入不是 cohort 入组、随机/paired 对照或效能晋级。
- v1 触发、不递归默认值和普通 query_handoff 的实现保持原有行为。

## 验收方向

独立临时归档与 Git 仓库用例覆盖：完整 application/monitor 关联、安装副本的真实失败退出、
未初始化时不建归档、计划篡改/晚绑/跨项目/跨应用拒绝、未知/排除/成本及输入边界、
漂移/代码回退可见、截断/未决记录，以及读取前后数据库字节/表结构和非空查询交接不变。
用例是 development 机制验证；具体运行结果记录在 gitlog 和专用完成证据中，不作为真实任务收益。
