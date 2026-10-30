---
type: adr
id: ADR-system-meta-reflection-lifecycle-1
status: proposed
scope: ["tools/agent_memory_runtime/system_evolution*.py", "skills/agent-memory-*/**", "install.py"]
owner: ""
approved_by: ""
approved_at: ""
approval_ref: ""
supersedes: ""
superseded_by: ""
---

# 系统元反思生命周期：执行事实、Agent 审查和实际应用分离

日期：2026-10-30。本文记录本轮已授权实施的选择；没有填造维护者的 ADR 批准。
proposed 不作为新的审批阻塞，本轮工作依据当前用户指示、源码和实际验收继续。

已有 v1 能保存评审、准备候选并执行检查，但零退出码没有覆盖判定、应用或回退语义。
本轮用户明确要求完成晋级、应用、迁移/回退、安装副本和真实宿主验证。此处扩展
既有治理流程，不改变查询/学习算法或 Runtime/Agent 的职责划分。

采用以下实现：

1. 独立的显式生命周期入口推进高级状态；普通 status writer 继续拒绝直接填写高级状态。
2. 验收计划是 prepared 制品，在执行前绑定；v3 检查观察实际生成的有界产物。
   当前 Agent 对每个断言、政策项及源码使用给出有引用的审查，Runtime 不把模型意见认证成事实。
3. checked/applied 等状态是有范围的工作流事实，不等同外部发布晋级。
   现有证据政策和 sealed/holdout 限制保留；evidence_verified/promotion_eligible 不自动变真。
4. 文件应用使用固定目标锁、前后像、逐文件原子替换与持久化检查点。
   普通开发布局和安装布局分开，安装布局仅交付安装器管理的 Runtime/四个 Skill 路径；跳过项可见。
5. SQLite 治理 v2 显式迁移后才允许高级状态；保留 v1 读取和普通查询兼容。
   升级/受支持降级保留数据和引用，不恢复旧备份来覆盖升级后的新写入。
6. 实际使用继续由 Skill 前台收尾驱动，无新增守护进程或 Agent 专用接入包装器。
   当前验收宿主为现有 Codex，其他宿主和未来 MCP 不由一次宿主通过自动获得认证。

未采用：把一份模型 pass 报告当成执行凭证；用零退出码自动发布；在查询路径自动迁移；
执行任意生成 SQL；整库旧备份覆盖后续写入；用 PID/经过时间推断未知工作已终止。

迁移采用 SQLite 推荐的“建新表、复制、删除旧表、把新表改名”路径，备份与引用检查
分别保留，参见 [SQLite ALTER TABLE](https://www.sqlite.org/lang_altertable.html) 和
[Python sqlite3 backup](https://docs.python.org/3.9/library/sqlite3.html#sqlite3.Connection.backup)。
真实宿主使用既有 CLI 与项目 .agents/skills，参见
[Codex Skills](https://learn.chatgpt.com/docs/build-skills) 和
[非交互执行](https://learn.chatgpt.com/docs/non-interactive-mode)。

后果：保留显式兼容边界和失败历史；应用不是整个目录的原子切换，使用方需在适当
停写/停止执行范围内操作。任意脱离受控进程组的工作不获得终止保证，未知事实不能填成功。
对范围外数据模型仍需新的版本化迁移实现和对应证据，不能套用治理 v1/v2 的通过结论。

实施契约和证据以[生命周期规格](../system-meta-reflection-lifecycle.zh-CN.md)、
[当前上下文](../../CONTEXT.md)及[完成证据](../system-meta-reflection-completion.zh-CN.md)为导航；
[设计第 9 节](../system-meta-reflection-design.zh-CN.md#9-隔离验证记录)保留首次验证历史。
