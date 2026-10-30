# Agent Memory 当前上下文

本文件记录当前实现事实和未完成事项，不替代当前用户指示、源码、测试或批准证据。

- 运行入口仍为 tools/agent_memory.py；四个 Skill 是前台协议。SQLite 为事实来源，Vault 为派生镜像。
- 系统元反思使用宿主当前模型。触发、名额、报告、候选、检查和生命周期记录与普通检索隔离；不接入额外评审模型或后台服务。
- 元反思的验证基线及旧版兼容读写基线为 2ade686f12373c214d7b9c3809f0e8821d770944，兼容回归固定使用该提交，不随 HEAD 移动。实际交付提交以 Git 历史为准；原有未跟踪的 memory.md 不是本任务产物。
- 治理 v1 的显式状态命令仍不能直接设置 checked/applied 等状态。新生命周期入口要求显式治理 v2 迁移、绑定候选的 v3 检查产物和当前 Agent 的逐项审查。
- checked 表示声明范围内的执行条件与 Agent 审查齐备；不认证审查者、Oracle 或外部泛化，promotion_eligible/evidence_verified 仍为 false。
- 实际应用支持 POSIX 文件锁、逐文件原子替换、持久化前后像及检查点。source/installed 布局分别应用源码路径或 tools 与 .agents/skills 安装路径；不改写 Memory 数据文件。
- 代码回退与数据降级分开。治理 v1/v2 迁移备份归档、保留引用和后续写入；存在高级状态时拒绝降级，保留兼容 Runtime 或走前向修复。
- 本轮交付为当前仓库实现及已授权的隔离安装/真实宿主验收。另一个真实业务项目未指定；额外部署是可选后续，不是本轮代码任务的前置条件。

当前证据：

- 原有 37 项隔离验证已通过；最终批次发现 56 项，55 项普通隔离回归通过，真实宿主按设计跳过并另行实际运行通过。代码清单与开始/结束摘要一致记录在 regression-final.json。
- 退出码 7 且无产物的监测用例复现了收集顺序缺陷，修复后定向通过。
- 安装副本完整生命周期、安装布局实际更新/回退、Git 基线普通读写兼容的定向用例通过。
- 真实 Codex CLI 0.165.0 已在普通示例查询中读取项目本地安装 Skill、观察实际 I/O 失败、分配一次名额并保存建议性评审；最终证据见 docs/evidence/system-meta-reflection/real-host-smoke.final.json。
- 文件模式位 0744 被扩宽的开发版缺陷已复现并修复。最终回归快照包含修复，现有模式位及代码回退验证通过。
- 活跃写者持锁拒绝恢复、实际硬退出 77 后跳过已写文件的恢复，以及实际 DDL 重建后的迁移事务回滚均通过。
- 恢复/中止有效预览错误退出 1 已复现并修复；中止保留原操作 failed，未知子进程仍拒绝清除。预览、重试和 checked 失效路径均已回归。
- 初次宿主启动的沙箱权限拒绝，以及带验收语境的首次宿主无评审结果均保留；不推断后者的未证实原因。

交付边界：

1. 运行代码、必要验证及规范/ADR/完成矩阵已落实；本轮不宣称生产效能或外部发布资格。
2. 如用户另行指定真实部署项目及 Memory Home，再执行该目标已授权的安装/迁移；不自动选择其他业务项目或发布上游。

相关规范：[设计](docs/system-meta-reflection-design.zh-CN.md)、[生命周期](docs/system-meta-reflection-lifecycle.zh-CN.md)、
[ADR](docs/adr/0001-system-meta-reflection-lifecycle.zh-CN.md)、[完成证据](docs/system-meta-reflection-completion.zh-CN.md)、
[变更政策](docs/evaluation-and-change-policy.md)。
