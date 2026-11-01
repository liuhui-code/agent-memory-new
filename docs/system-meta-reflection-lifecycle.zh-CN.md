---
type: feature-spec
id: SPEC-system-meta-reflection-lifecycle-1
status: draft
scope: ["tools/agent_memory_runtime/system_evolution*.py", "skills/agent-memory-maintain/**", "tests/test_system_evolution*.py"]
owner: ""
approved_by: ""
approved_at: ""
approval_ref: ""
supersedes: ""
superseded_by: ""
---

# 系统元反思：晋级、应用、迁移与回退

本轮按用户指示实现，规范批准字段留空。源码仍使用单一 Runtime 和四个 Skill，
SQLite 为事实来源，不改变原查询协议。客户端完整格式见可安装的
[system-lifecycle.md](../skills/agent-memory-maintain/references/system-lifecycle.md)。

## 晋级契约

`maintain-system-accept` 默认预览。只有显式 --execute，且下列条件同时满足，才将
当前 prepared 修订推进为 checked：

- 治理 schema 已显式升级为 v2；没有未决检查、候选或生命周期操作。
- 验收计划属于 prepared 制品，摘要在检查前后相同；覆盖全部提案断言。
- 完成的 v3 执行记录绑定同一项目、prepared 修订、制品和候选，所有声明检查退出零。
- 每个验收项关联实际观察过且当前未改变的产物，不能只提交 pass 字符串。
- 当前 Agent 已逐项记录政策、断言与实际源码使用的审查；该审查不因落库而得到身份或语义认证。

所有提案要求 functionality、negative_cases、compatibility、cost、rollback。
defect 增加 independent_reproduction/public_output_reproduction；structural 增加两个
不同的独立缺陷类证据；evaluator 增加 known_expected；query/learn/reflect/evaluator
增加 existing_gates/performance/file_size；data_model 增加读写矩阵、数据保留、
迁移中断重试和升级后写入检查。不同引用不自动证明不同缺陷类，Agent 仍须核查来源。

checked 不是发布资格，所有全局 evidence_verified/promotion_eligible 仍为 false。
需要外部发布/泛化资格的改动继续遵守既有政策，不能由本入口认证。

## 实际应用与后续观察

`maintain-system-apply` 将被验收候选的前后像应用到显式目标；默认预览。source
保留源码相对路径，installed 将 skills 路径映射到 .agents/skills，并仅应用安装器
管理的 tools 和四个 Skill；非安装文件列在 skipped_delivery_paths。

执行时检查目标前像，使用目标级 POSIX 文件锁，保留原始字节和权限；新增、修改、
删除及符号链接内容由有界后像表达。文件逐个原子替换，SQLite 检查点分段持久化。
全部后像核对后才进入 applied；全目录切换、运行进程热更新和未知脱离进程组不在保证范围。
目标保留 .agent-memory-system.lock 协调文件；操作可能存活时不能删除该锁文件。
回退恢复声明文件的前像，检查产物和已创建的空父目录可以保留，不宣称整个目录回到逐字节快照。

`maintain-system-resume` 根据持久化日志和实际文件前/后像恢复未决应用；--execute
必须取得真实目标锁。不能凭经过时间抢占。发现第三种文件内容保留冲突，不覆盖用户修改。
`maintain-system-rollback` 使用该次实际应用的日志恢复代码前像，不恢复旧 Memory 数据库。
有效预览退出 0。非文件操作可用 maintain-system-resolve 显式中止；完成中止退出 0，
原操作仍记录 failed，不代表检查成功。有未知活跃检查时拒绝中止，不凭模型判断清除。

`maintain-system-follow-up` 按事先绑定计划在实际应用目录检查，成功后进入 monitoring；
closed 还需该当前应用/修订的成功监测、未变的代码/输入和产物。失败退出及产物缺失
分别保留，不能关闭。关闭仅满足声明的后续检查范围，不代表长期效能或因果收益。
checked 可显式退回 needs_evidence，重新准备时需重新绑定检查。

后续结果与原假设、父版本的只读关联由
[R1 效果上下文](system-meta-reflection-outcomes.zh-CN.md)实现；它不扩展 closed 的语义。
R2 保存持久轮次，R3 提供[有界宿主窗口交接](system-meta-reflection-handoffs.zh-CN.md)；它们
均不扩展 closed 的效能含义。完整目标见[递归演进草案](system-meta-reflection-recursive-evolution.zh-CN.md)，
正常任务独立审计、自动候选/部署和长期效能仍需后续实现与实际材料。

## 数据兼容和恢复

`maintain-system-migrate` 支持治理 system-evolution-v1/v2，默认预览。执行前要求新
备份文件，持有写锁后用独立连接备份已提交状态，再重建约束、核对行数、外键和完整性，
最后原子提交版本及迁移审计。失败回滚事务，保留备份供检查。

| Runtime / 数据 | 普通记忆读写 | 治理读写 |
|---|---|---|
| Git 基线 2ade686f… / 含治理 v2 的归档 | 已用实际旧代码验证读写及查询交接一致 | 该基线没有本轮治理入口 |
| 当前 Runtime / 治理 v1 | 支持，普通命令不自动升级 | 原有限状态支持；高级生命周期需显式迁移 |
| 当前 Runtime / 治理 v2 | 支持 | 原有限状态及专用生命周期入口 |

受支持降级重建治理约束，保留升级后新增普通数据；存在高级生命周期状态时拒绝
降级，不丢弃状态来伪装兼容。保留相容 Runtime 或前向修复；旧备份不能覆盖升级后写入。
不提供任意 LLM SQL 的自动执行。其他数据模型变化需要自己的版本、映射和受控迁移实现。

## 验收和授权边界

已完成的实际执行证据、失败及未覆盖项集中在验证记录中。当前工作包括真实
Codex 对普通示例查询的 Skill 发现、实际错误和一次收尾评审；它不是生产任务效能实验。
保留先前宿主失败记录，不把未证实原因填成事实。

真实安装必须绑定用户已指定/已授权的项目及 Memory Home，不替用户选择另一业务项目。
任何安装授权均不包含上游发布或读取/调优已消费密封评测包。
