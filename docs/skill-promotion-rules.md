# Skill Promotion Rules

本文定义 Agent Memory 项目中，如何把：

```text
docs/skill-candidates/<name>.md
-> skills/_candidates/<name>/SKILL.md
-> skills/<name>/SKILL.md
```

这条链路中的最后一步收紧成明确、可审计、以人工确认为中心的流程。

约束前提：

```text
1. 用户仍然只使用四个正式 skill。
2. SQLite 仍然是 source of truth。
3. 自动聚合、draft、package 可以由 runtime 生成。
4. 正式 promotion 到 skills/<name>/ 必须是人工确认步骤。
```

---

## 1. 为什么正式 Promotion 不能自动化

前面的阶段已经证明：

- 单条 reflection 不等于 skill
- 多条 procedure_experience 聚合后才能形成 skill pattern
- skill pattern 可以导出 draft 和 candidate package

但这还不足以自动进入正式 `skills/`，原因是：

1. pattern 可能只是局部稳定，不具备跨任务稳定性
2. query anchors 可能仍有噪音
3. common_steps 目前仍带有启发式成分
4. expected_outputs 可能还不够清晰
5. failure_modes 可能覆盖不足

因此：

```text
formal skill promotion
!= draft export
!= candidate package
```

正式 promotion 必须是单独的人工确认动作。

---

## 2. 三个层级

### 2.1 Draft

位置：

```text
docs/skill-candidates/<name>.md
```

用途：

- 面向 review 的 Markdown 草稿
- 可自由修改和讨论
- 可以不完整

特点：

- 允许存在不稳定表述
- 不要求格式完全像正式 skill
- 主要承担“整理经验簇”的作用

### 2.2 Candidate Package

位置：

```text
skills/_candidates/<name>/SKILL.md
```

用途：

- 表示该草稿已通过一轮 review
- 已经开始具备 skill 结构
- 但尚未成为正式 skill

特点：

- 结构应接近正式 skill
- 允许存在“待补验证”的部分
- 不能直接当成稳定能力宣传

### 2.3 Formal Skill

位置：

```text
skills/<name>/SKILL.md
```

用途：

- 正式进入项目可维护 skill 集
- 被视为稳定、可复用、可持续演进的协议

特点：

- 必须通过人工确认
- 必须有清晰输入、输出、触发条件、边界条件
- 必须经过至少一轮回归验证

---

## 3. Promotion 前提条件

一个 candidate package 想进入正式 `skills/`，至少应满足：

### 3.1 支撑案例数量

至少满足：

```text
2+ supporting reflections
```

更稳的目标是：

```text
3+ supporting reflections
```

原因：

- 两条只够证明“有重复”
- 三条以上才更接近“稳定模式”

### 3.2 触发条件稳定

必须能回答：

- 什么时候触发这个 skill
- 什么情况下不该触发

至少要在 candidate 中明确：

```text
trigger cluster
common followup focus
applies_to
does_not_apply_to
```

### 3.3 步骤可执行

`common_steps` 不能只是抽象建议，必须能转成明确操作顺序。

至少要求：

```text
1. 起始查询动作
2. 中间 inspection 动作
3. 验证动作
4. 停止条件
```

如果 reviewer 读完以后仍然不知道“第二步具体怎么做”，就不能 promotion。

### 3.4 输出稳定

必须能说明 skill 执行后要产出什么。

例如：

```text
- next query terms
- inspection target shortlist
- verification checklist
- diagnosis summary
- change-design evidence summary
```

如果 expected_outputs 不稳定，说明仍处于经验层，不应 promotion。

### 3.5 失败模式明确

正式 skill 必须说明它会在什么情况下误导。

至少要能列出：

```text
failure_modes
negative_preconditions
anti_patterns
```

没有这部分，skill 很容易在错误场景下被复用。

### 3.6 已经过人工审查

必须满足：

```text
docs/skill-candidates/<name>.md 已审
skills/_candidates/<name>/SKILL.md 已审
```

至少一轮 review 应明确：

- 哪些词要保留
- 哪些词是噪音
- 哪些步骤太宽泛
- 哪些边界必须写清楚

---

## 4. 人工确认清单

正式 promotion 前，reviewer 应逐项确认：

### 4.1 命名

- skill 名称是否稳定
- 是否准确反映触发场景
- 是否不会和现有正式 skill 混淆

### 4.2 触发条件

- 是否有稳定症状或触发信号
- 是否清楚说明适用范围
- 是否清楚说明不适用范围

### 4.3 执行流程

- 是否能按顺序执行
- 是否包含起始步骤、递归步骤、验证步骤
- 是否存在明显跳步

### 4.4 输出协议

- skill 执行后，是否能稳定产出固定类型结果
- 输出是否能被本地 Agent CLI 继续消费

### 4.5 误用风险

- failure_modes 是否足够明确
- 是否存在容易被泛化到错误领域的风险

### 4.6 文档质量

- 是否已经从经验摘录改写成真正的 skill 文案
- 是否去掉了过多 case-specific 噪音

---

## 5. 正式 Promotion 的建议流程

建议流程：

```text
1. maintain-plan 发现 review_skill_pattern_candidate
2. maintain-skill-draft 写入 docs/skill-candidates/<name>.md
3. reviewer 编辑和收敛 draft
4. maintain-skill-package 写入 skills/_candidates/<name>/SKILL.md
5. reviewer 再次确认 candidate package
6. 人工复制/迁移到 skills/<name>/SKILL.md
7. 回归验证
8. 更新 gitlog 和相关文档
```

注意：

```text
第 6 步不建议在当前阶段由 runtime 自动完成
```

原因：

- 正式 `skills/` 是稳定接口面
- promotion 失败的代价高
- 现在仍处于经验系统快速演进期

---

## 6. 当前阶段不建议自动化的内容

当前不建议 runtime 自动做：

### 6.1 自动写正式 skill

不建议：

```text
maintain-skill-promote -> skills/<name>/SKILL.md
```

至少在当前阶段不做。

### 6.2 自动替换现有正式 skill

如果已有同名正式 skill，更不应自动覆盖。

### 6.3 自动安装 candidate skill

candidate package 只是候选，不应被当成正式用户能力安装。

---

## 7. 何时可以考虑增加正式 Promotion 命令

只有在下面条件都满足时，才考虑增加比如：

```text
maintain-skill-promote
```

条件：

1. candidate package 结构已稳定
2. reviewer checklist 已明确
3. 至少一批 candidate 已成功手工 promotion
4. 正式 skill 模板结构稳定
5. 覆盖同名冲突、回滚、审计信息的设计已明确

在此之前：

```text
formal promotion stays manual
```

---

## 8. 成功标准

如果这套 promotion 规则正确落地，应达到：

1. draft、candidate、formal skill 三层边界清楚
2. runtime 可以帮助生成和整理，但不会越过人工确认
3. 正式 `skills/` 不会被低质量经验污染
4. 用户仍然只使用四个正式 skill
5. 经验系统可以继续演化，但正式能力面保持稳定

---

## 9. 当前建议

当前最合理的策略是：

```text
先把 draft 和 candidate package 路径跑顺，
formal promotion 继续保持人工执行。
```

等手工 promotion 有几轮稳定样本后，再考虑是否增加正式 promotion 命令。
