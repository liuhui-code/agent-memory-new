---
type: feature-spec
id: SPEC-system-meta-host-handoff-1
status: draft
scope: ["tools/agent_memory_runtime/system_evolution*.py", "skills/agent-memory-maintain/**", "skills/agent-memory-reflect/**", "tests/test_system_evolution_handoffs*.py"]
owner: ""
approved_by: ""
approved_at: ""
approval_ref: ""
supersedes: ""
superseded_by: ""
---

# R3：有界窗口复核的宿主交接

日期：2026-11-01。承接 [R1](system-meta-reflection-outcomes.zh-CN.md)、
[R2](system-meta-reflection-rounds.zh-CN.md)及[递归方案](system-meta-reflection-recursive-evolution.zh-CN.md)。
用户继续实施指示不被补填为规范批准。本切片实现窗口复核交接，不改变普通查询或增加后台模型。

## 事先许可与边界

outcome plan/v2 在原 v1 字段之外要求 host_review：enabled、authorization_ref、
max_review_attempts=1、automatic_retries=0、max_report_chars（1–4000）。它和观察窗口一起
在候选检查/应用之前绑定；v1 计划仍可人工复核，但不具有 R3 自动交接许可。
authorization_ref 是当前 Agent 核对已有用户授权的引用，不是 Runtime 认证的权限凭证。

窗口终点沿用预声明 target_presented，所有到达/排除项均计数；不是墙上时间到期。
宿主已知有活动轮次时，可在实际任务收尾或明确批次维护边界调用交接。系统评审/改进活动
继续自动跳过，不能靠重命名任务绕过。没有正常任务自动抽样、定时器、守护进程或第五个 Skill。

## 一个交接入口

maintain-system-round-handoff 使用严格有界 JSON，action 为 inspect、claim、complete、fail。
默认预览；只有 --execute 写入。inspect 不依赖原制品仍在，缺归档不初始化。
claim 需要真实 host/client_local 任务引用、终态、活动、当前开关/预算声明及可得版本引用。
取消、关闭复核、预算不足、非终态、递归活动、未许可计划、不完整窗口或无可核对声明结果时跳过。

claim 核对 R2 修订、计划/应用身份、新观察任务内容、剩余 assessment 预算及未决操作。
一次事务在模型生成前分配名额，冻结实际 R1 上下文及 assessment 绑定。同项目归档中
每轮一次、每宿主任务一次；也检查既有 v1 名额/报告，v1 自动触发检查 R3 名额。
预览只报告 ready；只有本次成功创建名额返回 should_review=true。重复请求/响应丢失不再
授予生成许可；已领名额不能因时间过去而回收或重试。名额不是模型已运行或进程已结束的证明。

complete 提交当前 Agent 的 R2 assessment；冻结字段必须逐项匹配，当前上下文/修订必须
仍等于名额中的快照。R2 assessment 和交接完成事件在同一事务追加，失败整体回滚。
相同完成请求重试返回历史，不重新读取已经移走的原文件；不同内容拒绝覆盖。
fail 追加有界原因/引用/声明成本，保留名额消费；不清理未决实际操作或重开自动机会。
人工恢复与新授权仍走既有 R2/生命周期协议，不重写失败历史。

## 持久化、预算与真实性

可选组件 system_evolution_handoffs/system-handoffs-v1 用一张不可变交接事件表保存 claim/finish。
要求治理 v2 和 R2 已安装，使用原显式备份迁移入口；普通初始化/查询/交接不隐式安装。
每轮最多两条事件，request/receipt 为 32/128 KiB；更新/删除被拒绝，未知组件拒绝读写。
代码回退不覆盖后续 Memory 或交接数据。摘要/SQL 保护不认证数据库所有者及外部连续性。

Runtime 真正约束的是名额次数、重试次数和提交报告字符数。模型/工具的实际 Token、耗时
仍由宿主控制与声明，不冒充硬计量；未知成本保持 null。运行在用户当前模型，不引入另一个
评审模型，也不由 Runtime 调模型。交接只生成并保存评估，不自动决定 adopt、创建下一候选、
执行 apply/rollback 或授予晋级，不建立因果收益。证据、效能与宿主调用保证标记仍为 false。

R4/R5 正常任务漏检审计、真实活动及长期收益仍需独立来源和合同。本切片的隔离机制测试
不能证明业务效能、完整 RE01–RE14 场景或任意宿主都能触发。

严格请求格式及宿主步骤见可安装的 [Maintain 参考](../skills/agent-memory-maintain/references/system-handoffs.md)，
实际验证及其范围见[完成记录](system-meta-reflection-handoffs-completion.zh-CN.md)。
