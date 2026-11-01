# R3 宿主窗口交接完成记录

日期：2026-11-01；基于 4d5e068 和工作区中的 R1/R2 更新。
契约见[R3](system-meta-reflection-handoffs.zh-CN.md)，目标见[递归方案](system-meta-reflection-recursive-evolution.zh-CN.md)。

## 实际交付

- outcome-plan/v2 在候选检查/应用前绑定许可引用、一次尝试、零自动重试和字符预算。
- maintain-system-round-handoff 的严格 inspect/claim/complete/fail；默认预览，显式写入。
- 显式备份安装的 system-handoffs-v1，一张不可变 claim/finish 表；普通读取不建表。
- 窗口/新观察/预算/终态守卫；v1/R3 当前自动路径共享任务去重；重复或丢失响应不再授予生成。
- 冻结上下文与 R2 assessment 字段，评估与完成事件同事务保存；输入漂移拒绝，失败名额保留。
- Maintain/Reflect 安装版路由当前宿主，Runtime 不调用模型、重开决策或部署下一候选。

## 受控机制验证

[隔离用例](../tests/test_system_evolution_handoffs.py)使用真实临时 Git、SQLite、安装副本和既有
候选/验收/应用。任务、模型意见和未知操作元数据明确为受控开发材料。

| 范围 | 观察 |
|---|---|
| 安装 | 缺归档不初始化，未安装不自动建表；预览不备份，显式迁移备份及幂等 |
| 原子性 | 实际 DDL 后中断完整回滚；R2 assessment 插入后故障，评估和 finish 一起回滚 |
| 名额 | 实际并发只授予一次；v1/R3 两个先后方向均去重；预算/停止/递归/非终态不生成 |
| 输入 | 部分窗口、无已知结果、旧/禁用计划、相同观察不领取；漂移/错误绑定/修订冲突拒绝完成 |
| 预算 | 不能容纳最小报告时不领取；超字符报告拒绝；assessment 次数用尽不领取 |
| 保留 | 失败不回收名额、不清理未知实际操作；SQL 不可更新/删除；原文件删除后读历史及幂等保存 |
| 兼容 | 安装副本实际运行，非空 query_handoff 不变；实际 4d5e068 普通读写保留 R3 事件 |

首批 10 项通过，耗时 159.707 秒。补充最小报告预算、缺保护和真实旧版读写后，
四项定向通过，耗时 75.083 秒；这些运行覆盖 11 个不同当前用例，不冒称一次 11 项运行。
最终相关批次单独保存为[R3 机器记录](evidence/system-meta-reflection/regression-r3-handoffs.json)，
不覆盖 [R2](evidence/system-meta-reflection/regression-r2-rounds.json) 或此前快照。

最终批次发现 84 项，82 项通过，0 失败/错误，2 项真实宿主用例按 opt-in 规则跳过。
11 项当前 R3 用例均在该批次通过；R3 真实宿主另行实际执行，见下一节，不从 skip 推断通过。
执行 588.376 秒，含记录/清理 588.641 秒，Python 3.9.6、SQLite 3.51.0；临时根已清理。
开始/结束及收尾重算的 335 个 Runtime/Skill/测试文件摘要一致，清单摘要为
30e748ef9d10283cddc09db28256348d1625499523e7eee5d8f0d1271581ba7b。
这些运行时长是验证成本，不是产品性能指标。

收尾检查：27 份专用文档的 165 个本地链接有效；43 个 Python 文件指纹齐备，均在
500 行内（最多 480 行）。五份更新规范通过既有解析器的大小/头部/状态检查，draft/proposed
声明及空批准字段保持；git diff --check 通过。R3 收尾时的 Runtime/Skill bundle 与宿主安装快照相同。

## 真实宿主验收

[宿主用例](../tests/test_system_evolution_handoffs_host.py)单独 opt-in 执行，使用安装版 Skill、
实际归档和当前配置的 Codex 模型；只是受控窗口交接，不是真实任务效能样本。
首试退出 1，permission 且无事件/调用/usage；[失败记录](evidence/system-meta-reflection/real-host-r3-handoff.attempt-1.json)保留。
第二次在已授权的外层权限下运行 Codex 自身 workspace-write 沙箱，通过，耗时 111.541 秒；
[实际记录](evidence/system-meta-reflection/real-host-r3-handoff.attempt-2.json)显示本地 Maintain Skill
及交接参考已读取，实际存在一个 claim、recorded finish 和一条 inconclusive assessment，
声明 tokens/elapsed_ms 均为 null。未新增决策或改变原 monitoring 提案，完成后重领返回不生成。
源码与安装 Runtime/Skill bundle 摘要一致：
70190d2eca83c6a3b165523346519dcacb48ee280b2c74452b5ed697f33807d6。
不把普通批次 skip 当作真实宿主通过。

宿主观测的整回合 usage：input_tokens=564042，其中 cached_input_tokens=464768；
output_tokens=5026，reasoning_output_tokens=1857。按宿主原字段保留，不推断计费金额、
增量反思成本、性能退化原因或成本收益。runtime_invocations 是 started/completed 工具事件
片段，含尚无退出码的项，不直接作为工具调用总数。

本机 Codex CLI 0.165.0 的帮助及
[官方非交互文档](https://learn.chatgpt.com/docs/non-interactive-mode)、
[CLI 参考](https://learn.chatgpt.com/docs/cli/reference)用于核对运行参数。
Context7 resolve-library-id 请求发生传输错误，因此采用本机帮助和已打开的官方页面。
没有读取认证文件或替换模型。精确模型身份不可得，记为未知；全回合 usage 不当作元反思增量成本。

## 限制

许可引用、任务真实性/外部连续性、声明成本和数据库所有者均未被认证。实际约束是名额和
提交字符数，不是宿主 Token/工具硬计量。v1 自动信号语义和成功抽样默认值保留；旧 Runtime
普通读写兼容，不支持旧/新自动触发并行共享 R3 预算。R4/R5、完整 RE01–RE14、自动新候选/
部署和长期收益仍为后续工作。

Skill 自带 quick_validate.py 在当前 Python 缺 PyYAML，未能执行；没有为此引入项目依赖。
已单独核对两份 Skill 的 frontmatter 与 HEAD 相同、名称/描述边界及未完成占位；实际安装与
引用可发现性另有回归/宿主验证，不把这些检查冒称为原验证器通过。
现有业务 Memory、已消费密封资产和原有未跟踪 memory.md 没有被读取或改动。
本记录形成于 R3 切片收尾时，当时 R1/R2/R3 及方案尚未提交；后续主分支交付见 Git 历史。

随后 [R4 开发准备](system-meta-reflection-campaign-readiness-completion.zh-CN.md)新增只读审计并
修正 Cohort 初始化顺序，形成新的源码快照；不回写本次 R3 记录，也不把该宿主结果当成 R4 验收。
