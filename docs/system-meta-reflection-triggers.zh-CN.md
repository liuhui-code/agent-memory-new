# 系统元反思：任务收尾判断与评审名额

日期：2026-10-30
状态：触发/名额合成隔离回归已通过，不构成真实宿主行为或完整功能通过证据；见[验证记录](system-meta-reflection-design.zh-CN.md#9-隔离验证记录)

## 本阶段目标与边界

已有设计依赖 Agent 自己记住触发优先级和一次评审预算。本阶段增加
`reflect-system-trigger`，将声明的任务状态、具体信号和跳过规则交给确定性代码
处理；可在既有 SQLite 归档显式占用一个评审名额，再由用户当前 Agent 生成报告。
命令不调用模型、不发现真实任务边界、不认证事件、不运行检查，也不改查询返回。

四个 Skill 仅在真实逻辑任务收尾并存在具体信号时交接到 Reflect。不得把每次查询、
学习分片或聊天轮次当成一个新任务。宿主是否真正调用仍取决于加载的 Skill 和
宿主执行；没有后台进程、特定 Agent wrapper 或自动 task-end hook。

## 输入与优先级

命令接受且仅接受 --payload / --payload-file 之一。输入及 canonical JSON 至多
4,000 Unicode 字符，文件有界读取至多 32 KiB；固定格式 system-meta-trigger/v1。
以下顶层字段全部必需，未知项按规定表示，不提交原始任务、查询或工具输出。

| 字段 | 契约 |
|---|---|
| schema_version | system-meta-trigger/v1 |
| task_ref | null，或 key/origin（host/client_local）；键沿用实际任务，1–160 字符的不透明 ASCII 标识 |
| task_state / task_outcome | in_progress/completed/failed/blocked/cancelled；success/failure/partial/unknown |
| memory_use / memory_requested | used/not_used/unknown；是否明确请求过 Memory 的布尔声明 |
| manual_request | 当前是否有明确人工评审请求，不由历史反馈许可推断 |
| review_enabled / user_cancelled / budget_available | 当前复盘开关、停止要求与可用预算的布尔声明；不是实测成本 |
| activity | task/system_review/system_evolution；自动路径不递归评审自身及系统改进工作 |
| signals | 至多四项且种类不重复，格式如下 |
| version_refs / query_refs | 与评审报告同样的有界版本字段及调用引用；未知值不得补造 |

信号 kind 为 memory_error/user_correction/evidence_conflict/repeated_gap；每项必须
有非空 refs。repeated_gap 还必须有不透明 gap_key 及至少两个不同的 round_refs，
表示同一缺口在实际不同查询轮次没有新增可检查证据。其他信号不能带这两个字段。
引用均为单行、至多 240 字符，全部 query/信号/轮次引用合计至多八个不同值。
客户端关联键可以标识实际已观察事件，但不能伪称宿主提供或制造事件本身。

判断顺序为：当前用户停止/关闭/预算不足 → 明确手动请求 → 非 task 活动跳过 →
未收尾跳过 → 未观察到 Memory 使用或请求跳过 → 身份缺失跳过 → 无具体信号
跳过 → 考虑一次自动评审。普通空结果、截断、分页、预期时效保护及任务最终失败
本身不是具体信号。多个信号按上列固定顺序选一个 trigger，仍只产生一次评审。
手动请求可以覆盖未完成任务或已取消任务的后续复盘，但不能越过当前停止要求。

## 只读判断与显式占位

默认只读判断，返回 review/skip、原因、报告绑定字段、预算和已有记录线索；它不
保证客户端接下来只生成一次。客户端未保存状态时，最多只能承诺当前上下文去重。
默认路径不初始化归档、创建表或写入跳过记录。

只有本地治理记录已获当前授权时使用 --claim。它要求既有归档和实际任务关联；
不会为了评审初始化数据库。符合条件时在短写事务内为该项目/任务占用一个名额，
返回 claim_created。自动调用者只有 claim_created=true 才能开始生成；重复占位
返回 skip/already_claimed。并发占位使用唯一约束和 BEGIN IMMEDIATE。
唯一性以实际 Memory Home/项目归档和声明身份为边界；不能切换归档或轮换任务键
来重开同一任务的预算。旧版本或不遵守占位协议的调用方不获得这项去重保证。

没有既有评审时，review-key 由项目和任务身份的 SHA-256 派生；已有评审时沿用
原线程和下一连续修订。已有报告会阻止再次自动评审；显式手动请求可按原线程
补充修订。没有任务身份的手动评审仍可留在当前会话，但不能声称已持久化占位。

名额状态仅 reserved/recorded：reserved 表示已分配、是否执行模型未知，不是
正在运行的进程；recorded 表示该线程实际保存过报告，失败/跳过报告也只是记录。
硬中断不自动恢复名额，不按时间推断模型已终止或再次触发。用户明确要求手动
恢复时可以沿用该线程，但不能把恢复当成第二个独立任务。

首次 --claim 只创建可选 system_meta_review_triggers 及其独立 schema 组件；
不创建普通索引或三个评审治理表。reflect-system 保存报告时才创建原治理表，
并在同一事务校对占位身份、线程与自动 trigger，更新 report_id/review_revision。
首次自动报告记录后，显式补充使用 manual trigger；同内容旧修订重试仍直接返回
原记录，不被后来增加的占位或指针误判为新的一次自动评审。
占位前后的报告都保持不可变修订，不能改键绕过去重；没有占位的旧显式报告路径
继续可用，但不能获得占位带来的去重承诺。

## 读取、隐私和验证范围

maintain-system 摘要显示有界名额列表，--trigger-id 读取一条完整有界声明与关联。
即使尚无报告治理表也能读取名额。SQLite 只保留类型化标识、信号引用、布尔声明、
请求摘要、状态与报告指针，不保存原始任务、日志、源码、完整命令或模型推理。
字段校验不是自动脱敏、真实任务认证或事件核验。

以下是参数语法示例，--claim 仅在已有本地记录授权时使用：

```bash
python tools/agent_memory.py reflect-system-trigger --project . --payload-file "<trigger.json>" --json
python tools/agent_memory.py reflect-system-trigger --project . --payload-file "<trigger.json>" --claim --json
python tools/agent_memory.py maintain-system --project . --trigger-id <id> --json
```

受控回归位于 [test_system_evolution_triggers.py](../tests/test_system_evolution_triggers.py)，
覆盖优先级、只读/惰性表、并发占位、报告绑定、历史重试和重复缺口输入。
这些机制用例已运行通过；全部使用合成输入，不是真实任务、模型执行、活动批准或评测 Oracle。

占位、触发判断和报告绑定不产生 checked、已应用、因果收益或发布资格。
真实 Codex 普通示例已观察到 Skill 读取、context 实际错误、一次名额和建议性评审保存。
其他宿主、预算及更广环境下的并发/隔离仍须对应证据。专用晋级、受控应用、治理迁移、
回退和已复现的开发版缺陷修复另见[完成证据](system-meta-reflection-completion.zh-CN.md)，
不能由一个名额记录替代其独立执行结果。
