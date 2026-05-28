# Experience System Principles

反思是生成经验的必要条件之一，但不是充分条件。一个良好的经验系统不只是保存心得，而是让经验在下一次任务中被正确命中、正确解释、正确迁移、正确修正。

核心闭环：

```text
事件记录
-> 结构化反思
-> 抽象规则
-> 业务/代码/日志实体链接
-> 查询命中
-> 使用反馈
-> 治理修正
-> 再次沉淀
```

## 1. 经验必须来自可追溯事件

反思不能悬空。每条经验最好能回到：

- 原始问题
- 当时上下文
- 用过的查询
- 相关代码、日志、文件、命令
- 成功或失败的证据
- 最终结果

经验应包含出处、证据和可复用建议，而不是只保存一句心得。

## 2. 经验需要类型分层

成熟的 agent memory 系统通常不会把所有内容放在一个扁平 notes 表中。至少应区分：

- `episodic memory`：发生过什么，例如一次任务、一次失败、一次定位过程。
- `semantic memory`：稳定事实、项目规则、业务含义。
- `procedural memory`：下次怎么做，例如流程、检查表、修复策略。
- `working/core memory`：当前必须放进上下文的少量高价值内容。
- `archival memory`：大量长期内容，需要查询时召回。

当前项目已有 `episodes`、`semantic_facts`、`reflections`、`code_files`、`code_symbols`、`code_log_statements`、`memory_edges`。下一步重点是让 `reflections` 更接近 procedural memory，也就是让它明确记录触发条件和下次动作。

## 3. 要有检索命中机制

经验系统最容易失败的地方是：写得很多，但下一次查不到。

需要同时支持：

- 多字段检索：问题、业务词、文件、函数、日志、错误现象、修复动作。
- 查询扩展：用户自然语言问题转成技术关键词。
- 实体链接：把文件、函数、日志、业务词、历史任务连起来。
- 网络检索：不是只查一条记录，而是查相关链路。
- 加权排序：结合 recency、confidence、scope、status 和命中字段。

对当前项目来说，`memory_edges`、业务语义字段、日志语义字段和 query expansion 是核心能力。后续重点不是增加更多表，而是让每次 learn 和 reflect 都产出真实业务词、代码实体、日志模板和触发条件。

## 4. 要有复用、修正、保留闭环

Case-Based Reasoning 的经典循环可以映射为：

```text
Retrieve -> Reuse -> Revise -> Retain
检索 -> 复用 -> 修正 -> 保留
```

一次历史经验不是拿来照抄，而是：

- 检索相似案例。
- 迁移到当前问题。
- 验证是否有效。
- 如果有效，增强经验。
- 如果误导，标记 stale 或写入反例。

当前项目的 `used_reflection_ids`、`reflection_outcome`、`applied_count`、`last_outcome` 是正确方向。后续应继续加强“使用后反馈”：每次用了哪条经验、是否帮助、哪里不适用。

## 5. 要有经验治理

没有治理的记忆会腐烂。经验系统必须能处理：

- `stale`：过时。
- `merged`：重复合并。
- `archived`：低频归档。
- `rejected`：错误经验。
- `confidence`：可信度。
- `scope`：适用范围。
- `evidence`：证据。
- `reviewed_at`：是否复核。
- `miss`：查询失败记录。

记忆不是越多越好，而是要可控地留下高信号内容。`maintain`、`review`、`miss` 的方向是对的，尤其是 miss 记录，它能反向驱动学习和字段补全。

## 6. 要从单环学习走向双环学习

单环学习：

```text
这次失败了 -> 下次改一个操作
```

双环学习：

```text
这次失败了 -> 为什么我的判断框架会让我失败？
```

对应到本地 Agent：

- 单环：下次先查日志。
- 双环：为什么我总是只查 symptom，不查业务实体？
- 单环：补一个 query expansion。
- 双环：learn 阶段是否缺少业务语义字段？
- 单环：修复某个 bug。
- 双环：为什么方案设计没有验证前置假设？

经验系统要支持这种递归整理：不只是记录结果，还要持续整理判断方式。

## 7. 要有抽象化能力

体验学习可以抽象成：

```text
具体经验 -> 反思观察 -> 抽象概念 -> 主动实验
```

对应 Agent Memory：

```text
一次任务 episode
-> 反思 reflection
-> 稳定规则 semantic/procedural memory
-> 下一次 query / plan / execution 使用
```

如果只停在 reflection，没有抽象成 `future_rule`、`trigger_condition`、`repair_action`，它就还不是成熟经验，只是复盘文本。

## 8. 要有人类可审查的外部化表示

经验系统需要人类可读、可审查、可治理的外部表示。SQLite 适合作为源事实，Obsidian 适合作为人类复核镜像。

当前项目的架构是合理的：

```text
SQLite source of truth
-> generated Obsidian mirror
-> human review
-> maintain / reflect 写回 SQLite
```

这比只依赖黑盒向量库更适合本地 agent，因为用户可以看到经验如何形成、为什么命中、何时过期。

## Current Project Direction

下一阶段可以命名为 `Procedural Memory Loop`，目标是把反思升级成真正的可执行经验。

优先加强四个方向：

1. 经验入库质量：问题、业务词、文件、函数、日志、触发条件必须结构化。
2. 经验召回质量：自然语言问题能命中业务语义、代码实体、日志模板和历史反思。
3. 经验复用反馈：每次用了哪条经验，是否帮助，是否误导。
4. 经验治理压缩：重复合并、过期标记、失败 miss 反哺学习字段。

一句话总结：

```text
经验系统的价值不在于记得多，而在于下一次能把正确经验带回正确问题，并在使用后继续修正自己。
```

