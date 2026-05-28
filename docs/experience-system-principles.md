# Experience System Principles

本文定义 Agent Memory 项目中的“记忆系统”和“经验系统”边界，并说明主流理论与成熟 Agent 产品实践对当前项目的设计参考。

核心定义：

```text
记忆是对事实的压缩。
经验是对事实、上下文、隐含前提、失败路径和推理过程再抽象后的结论。
```

因此，经验系统不是更大的记忆库，而是记忆系统之上的学习、抽象、迁移和验证层。

## 1. 分层定义

当前项目应清晰区分三层：

```text
Memory Layer
  facts / episodes / code wiki / logs / business semantics / edges

Reflection Layer
  task review / reasoning summary / worked paths / failed paths / assumptions

Experience Layer
  verified abstract rule / preconditions / transfer rule / verification method / reusable skill pattern
```

### Memory Layer

记忆层回答：

```text
发生过什么？
代码里有什么？
日志在哪里？
事实是什么？
实体之间如何相连？
```

典型数据：

- `semantic_facts`
- `episodes`
- `code_files`
- `code_symbols`
- `code_log_statements`
- `memory_edges`
- business summaries and terms

记忆层可以被压缩、索引、查询和治理，但它本身不等于经验。

### Reflection Layer

反思层回答：

```text
这次任务为什么成功或失败？
Agent 当时如何推理？
哪些线索有效？
哪些假设误导？
下次应避免什么？
```

典型数据：

- `task_type`
- `outcome`
- `problem`
- `reasoning_summary`
- `context_used`
- `what_worked`
- `what_failed`
- `mistake`
- `lesson`
- `future_rule`
- `trigger_condition`
- `repair_action`

反思是经验生成的必要条件之一，但不是充分条件。未经验证和抽象的 reflection 只是经验候选。

### Experience Layer

经验层回答：

```text
在什么前提下，哪种判断方式可以迁移到类似问题？
这条经验如何验证？
什么时候它不适用？
它是否值得沉淀成 skill？
```

经验必须包含：

- abstract conclusion：抽象结论。
- preconditions：适用前提。
- hidden assumptions：隐含假设。
- negative preconditions：不适用条件。
- reasoning pattern：推理模式。
- transfer rule：迁移规则。
- verification method：验证方法。
- failure modes：可能误导的情况。
- source cases：来自哪些 episode/reflection。
- reuse feedback：复用后是否帮助或误导。

## 2. 理论参考

### Kolb Experiential Learning

Kolb 的体验学习循环可以映射为：

```text
Concrete Experience
  -> Reflective Observation
  -> Abstract Conceptualization
  -> Active Experimentation
```

对应当前项目：

```text
episode / code / logs
  -> structured reflection
  -> experience rule
  -> next query / diagnosis / design / execution
```

参考意义：

- `episode` 和代码日志只是具体经历。
- `reflection` 是观察和复盘。
- `experience` 是抽象概念，必须高于单次任务。
- 经验必须在下一次任务中被主动实验和验证。

### Case-Based Reasoning

Case-Based Reasoning 的经典循环是：

```text
Retrieve -> Reuse -> Revise -> Retain
```

对应当前项目：

```text
query similar cases
  -> adapt prior solution or reasoning path
  -> verify against current source/logs
  -> retain new experience or mark old one stale
```

参考意义：

- query 不应只返回事实，也应返回相似 case。
- 相似 case 不能直接照搬，必须经过适配。
- 使用后的反馈必须写回：helped、misleading、partial。
- 经验系统要保留正例，也要保留反例和失败前提。

### Double-Loop Learning

单环学习修正动作：

```text
这次失败了 -> 下次改一个操作
```

双环学习修正判断框架：

```text
这次失败了 -> 为什么我的判断框架会让我失败？
```

对应当前项目：

```text
single-loop:
  页面白屏 -> 下次先查 route

double-loop:
  页面白屏 -> 不要只按 symptom 查；
  先识别业务实体、入口文件、路由链、日志模板，再递归查询。
```

参考意义：

- 经验系统必须记录隐含假设和失败假设。
- 经验不是操作清单，而是判断方式的改进。
- miss 记录不仅表示“查不到”，也可能表示 learn/reflect 的抽象维度缺失。

### SECI Knowledge Creation

SECI 强调隐性知识和显性知识之间的转换：

```text
tacit reasoning
  -> explicit reflection
  -> combined experience wiki
  -> internalized skill behavior
```

对应当前项目：

```text
Agent 隐性推理
  -> reflect --payload
  -> SQLite + Obsidian mirror
  -> query / plan / skill reuse
```

参考意义：

- Obsidian mirror 不只是展示层，也是人类审查经验形成过程的界面。
- SQLite 仍是 source of truth。
- 经验应可读、可审查、可治理，而不是黑盒向量命中。

## 3. 产品实践参考

### MemGPT / Letta: Memory Hierarchy

MemGPT/Letta 的核心启发是：上下文是稀缺资源，应把记忆分层管理。

对当前项目的意义：

```text
Experience Layer
  highest priority, compact, action-oriented

Reflection Layer
  retrieved when reasoning history or failure path matters

Memory Layer
  retrieved as evidence, source context, code/log anchors
```

query 返回时不应把所有内容平铺。更合理的顺序是：

```text
experience candidates
  -> similar reflections/cases
  -> semantic facts
  -> code/log/wiki evidence
  -> bounded edges
```

### Generative Agents: Observation, Planning, Reflection

Generative Agents 的启发是：reflection 的价值在于影响 planning。

对当前项目的意义：

- `agent-memory-query` 不能只服务问答，也要服务方案设计。
- 经验应该进入 diagnosis/design/execution 的前置上下文。
- 反思应记录“为什么这个计划有效或无效”，而不仅是“做了什么”。

### Zep: Temporal Knowledge Graph

Zep 的启发是：记忆需要实体、关系和时间变化。

对当前项目的意义：

```text
experience
  -> problem type
  -> business entity
  -> file / symbol / log
  -> assumption
  -> repair action
  -> verification method
```

当前 `memory_edges` 已经连接代码文件、函数和日志。下一步应让经验也进入网络，形成：

```text
reflection -> abstracts_to -> experience
experience -> applies_to -> problem/business entity
experience -> supported_by -> episode/log/file
experience -> warns_against -> anti-pattern
```

### Voyager: Skill Library

Voyager 的启发是：高阶经验最终可以沉淀为可复用 skill。

对当前项目的意义：

经验的最高形态不是一句 lesson，而是可执行的过程模板。例如：

```text
ArkTS 页面白屏定位经验
1. query 业务页面名 + route/router/page stack
2. query 相关 log template
3. 检查入口文件、router.pushUrl、页面注册
4. 检查资源和生命周期
5. 输出修改计划和验证命令
```

这与项目宗旨一致：通过 LLM skill 调用命令降低使用门槛。

## 4. 对当前项目的设计原则

### 原则一：不要把 reflection 直接当 experience

`reflection` 是经验候选。它只有在经过复用、验证、抽象后，才可以升级为经验。

建议后续在 maintain/reflect 中区分：

```text
raw reflection
validated reflection
experience candidate
accepted experience
skill candidate
```

### 原则二：经验必须带适用前提

没有前提的经验很容易污染推理。

示例：

```text
经验：
ArkTS 页面白屏优先查 route。

适用前提：
问题发生在页面跳转后，且存在 router.pushUrl / page stack / route config。

不适用：
页面未跳转，只是局部组件不渲染。

验证：
查询 route edge、入口文件、相关日志模板，并检查页面注册。
```

### 原则三：经验必须保留隐含假设

经验抽象时需要记录：

- 当时默认了什么？
- 哪些前提后来被证明正确？
- 哪些前提误导了方案？
- 下次如何更早验证这些前提？

这比简单记录“下次先查 X”更重要。

### 原则四：经验必须支持反例

成熟经验系统不只记录有效路径，还记录：

- 什么时候无效。
- 为什么误导。
- 哪些症状看起来相似但本质不同。
- 哪些查询词会把 Agent 带偏。

这要求 `reflection_outcome=misleading` 不只是治理信号，也应成为经验边界的一部分。

### 原则五：query 应先召回经验，再下钻事实

推荐 query 组织：

```text
1. 当前问题属于哪类？
2. 是否有 accepted experience 或 experience candidate？
3. 是否有相似成功/失败 case？
4. 相关事实、代码、日志、边是什么？
5. 这条经验的前提在当前问题中是否成立？
```

这样 query 结果才会服务推理，而不是只返回一堆片段。

### 原则六：经验可以升级为 skill

当同一类经验多次被验证有效，可以生成 skill 候选：

```text
multiple helped reflections
  -> accepted experience
  -> skill candidate
  -> user review
  -> local Agent skill template
```

这会把经验系统和项目的四个 skill 入口自然连接起来。

## 5. 建议的后续演进

短期不必立刻新增表。可以先在现有 `reflections` 和 governance 字段上表达经验候选：

```text
task_type
outcome
problem
reasoning_summary
context_used
what_worked
what_failed
trigger_condition
repair_action
applies_to
does_not_apply_to
confidence
last_outcome
applied_count
```

下一步再考虑新增或明确经验层字段：

```text
experience_statement
preconditions
negative_preconditions
hidden_assumptions
reasoning_pattern
transfer_rule
verification_method
failure_modes
source_cases
helped_count
misled_count
```

最终目标：

```text
事实被压缩成记忆；
记忆和隐含前提被推理成经验；
经验被验证后沉淀成可调用 skill。
```

## 6. 当前项目的一句话方向

当前项目不应止步于 Agent Memory Runtime，而应演进为：

```text
Agent Memory Runtime
  + Reflection Capture
  + Experience Abstraction
  + Skill-level Reuse
```

记忆负责提供事实基底，反思负责暴露推理过程，经验负责形成可迁移判断，skill 负责把成熟经验变成可重复执行的行为。
