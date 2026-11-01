# R2 持久轮次完成记录

日期：2026-11-01。基于 4d5e068 及工作区中的 R1/递归方案更新。
契约见[R2 轮次](system-meta-reflection-rounds.zh-CN.md)；完整目标见
[递归方案](system-meta-reflection-recursive-evolution.zh-CN.md)。

## 实际交付

- 原 SQLite 的可选 system-rounds-v1 组件，一张不可变事件表；使用既有入口显式备份安装。
- 类型化 open/assessment/decision，修订/CAS、幂等、父子顺序、冻结记录次数预算和未决工作检查。
- 保存 R1 计划/输入摘要/上下文、Agent 评估和原决策，原文件移走后仍可跨会话读取历史。
- 新上下文可在非 stop 已决轮次内追加评估；原 decision/decision_revision 不被替换，轮次不重开。
- 记录建议不部署代码或推进提案，不认证任务/成本、外部连续性、因果收益或外部晋级。

## 独立隔离用例

[test_system_evolution_rounds.py](../tests/test_system_evolution_rounds.py) 使用临时 Git、归档和实际
应用/监测/回退。任务结果、Agent 意见及未知操作行明确为受控开发材料，不是真实效能样本。

| 检查 | 实际核对 |
|---|---|
| 显式安装 | 预览不创建表/备份；写入拒绝未安装；有效备份不含新增表，重复安装复用 |
| DDL 中断 | 建表/触发器后实际抛错，事务回滚，备份和原库完整且无组件残留 |
| 历史和幂等 | 原文件删除后读旧快照、重复键复用历史；改内容冲突，旧未知/负结果保留 |
| 不可变及查询隔离 | SQL 更新/删除被拒绝；非空 query_handoff 前后相同 |
| 并发修订 | 两个实际并发评估仅一个追加成功，另一个修订冲突 |
| 父子与预算 | 第二个实际候选/验收/应用关联子轮，预算不能改；耗尽拒绝；父轮晚到评估不改变子轮顺序 |
| 决策及晚到反证 | 不完整输入拒绝 adopt；新反证追加但不改原决策；stop 阻止续轮与续写 |
| 未决状态 | 未知子进程元数据阻止评估；记录 stop 不清理实际 running 记录 |
| 版本和旧读写 | 未知组件/缺保护拒绝且不修复；安装副本执行；实际 4d5e068 Runtime 读写后新记录仍在，交接一致 |

先行七项通过，耗时 80.160 秒；补充父子、停止/版本和旧查询后，三项定向通过，耗时
45.162 秒；完善晚到评估后，同三项通过，耗时 37.124 秒。它们覆盖九个不同当前用例，
不冒称一次九项整组运行。

最终相关批次保存在[R2 机器记录](evidence/system-meta-reflection/regression-r2-rounds.json)，
与 [R1](evidence/system-meta-reflection/regression-r1-outcomes.json) 和
[生命周期](evidence/system-meta-reflection/regression-final.json) 历史记录分开。
计数、运行环境、临时根清理和开始/结束源码清单以实际进程生成记录为准。

本次最终批次发现 72 项，71 项通过，0 失败/错误，1 项真实宿主用例按显式 opt-in 规则跳过。
测试执行 423.085 秒，含记录/清理 423.361 秒；Python 3.9.6、SQLite 3.51.0。
九项 R2 用例均在该批次通过。临时根已清理，开始/结束的 329 个 Runtime/Skill/测试文件
摘要一致，收尾重算也与机器清单一致；清单摘要为
a20ff5679e9245e47e2ed4ff557bd912b4eee6071b72fc2c6e7d1f2cc14f94c5。
这些是受控开发机制证据，运行时长不是产品性能指标，skip 不计作 R2 真实宿主验证。

收尾检查：24 份专用文档的 141 个本地链接有效；38 个 Python 文件指纹齐备，均不超过
500 行（最多 480 行）。规范声明保持 draft/proposed、批准字段为空；既有解析器将
proposed 规范化为 draft，未改变该语义。git diff --check 通过。

## 范围

当前只冻结已支持的 R1 计划/应用身份，不自动探测完整模型/Runner 环境身份。
次数预算不是实际模型调用或 Token 成本上限；超预算仍须报告新信息/缺口，不把未记录反证记为无变化。
SQL 保护及摘要不是外部认证，数据库所有者可以绕过正常 API；history_authenticated 保持 false。
本次 R2 验收不覆盖 R3 宿主交接、R4/R5 真实活动或长期收益；RE01–RE14 整场景未全跑。
现有业务 Memory、密封资产及原有未跟踪 memory.md 未被读取或改动；没有真实项目部署或模型调用。
本记录形成于 R2 切片收尾时，当时 R1/R2 及递归方案尚未提交；后续主分支交付见 Git 历史。

后续 [R3 交接](system-meta-reflection-handoffs-completion.zh-CN.md)扩展当前源码快照和显式可选组件，
其名额与完成证据单独记录，不回写本次 R2 的计数或摘要。
