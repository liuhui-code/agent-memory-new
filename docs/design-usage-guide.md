# Agent CLI 代码设计能力使用指南

## 1. 能力定位

Agent Memory 不负责替用户生成或选择代码设计。它是本地 Agent CLI 的设计
上下文供给层：

```text
用户提出需求
  -> Agent 调用 design-context
  -> 系统返回代码事实、约束、设计知识和证据缺口
  -> Agent 检查当前源码
  -> Agent 分析质量属性、原则、候选与权衡
  -> Agent 输出设计方案
  -> 用户确认后再实施和验证
```

职责边界：

- **Agent Memory Runtime**：检索、关联、裁剪和标注上下文。
- **Agent CLI**：理解需求、设计候选、分析取舍、选择方案、制定计划。
- **用户**：确认业务目标、硬约束和关键权衡。

系统不会：

- 根据关键词自动推荐某个设计模式；
- 自动生成或排名候选方案；
- 自动选择最终设计；
- 自动生成实施步骤并将其当成结论；
- 用历史经验覆盖当前源码或用户约束；
- 保存用户需求、临时方案或 Agent 的推理过程。

## 2. 用户如何使用

用户不需要记忆后台命令，也不需要编写 JSON。仍然通过固定的
`agent-memory-query` Skill，用自然语言提出设计任务。

推荐描述以下内容：

- **目标**：需要增加或改变什么行为。
- **范围**：主要涉及哪些功能、模块或入口。
- **硬约束**：兼容性、性能、安全、平台和组织限制。
- **排除项**：本次明确不处理什么。
- **验收标准**：如何判断设计与实现达到目标。
- **工作方式**：只输出设计，还是确认后继续实现。

例如：

```text
结合当前代码，为 ProfileRepository 增加缓存。
保持 ProfileService 的公开 API 兼容，页面不能持有持久化状态。
缓存失效和加载失败必须可观测。
先给出设计方案，不修改代码。
```

```text
重新设计登录态刷新流程。
重点考虑并发请求、超时恢复和旧版本调用方兼容。
请先检查当前状态所有者和所有消费者，再比较必要的候选方案。
```

对于简单局部修改，可以直接说明：

```text
先检查当前实现。这是局部调整，不要为了未来可能的变化增加新抽象。
```

## 3. Agent 的默认流程

### 3.1 第一轮：方向查询

Agent 使用用户原始需求调用：

```bash
python tools/agent_memory.py design-context \
  --project . \
  --query "为 ProfileRepository 增加缓存并保持 ProfileService API 兼容" \
  --constraint "页面不得持有持久化状态" \
  --constraint "加载失败必须可观测" \
  --compact \
  --json
```

第一轮的目标不是获取设计答案，而是确定：

- 应从哪些源码位置开始检查；
- 当前代码图显示了哪些责任和依赖；
- 是否存在相关项目约束或业务语义纠正；
- 可能需要讨论哪些质量属性；
- 哪些设计原则或模式资料值得参考；
- 当前证据还缺什么。

### 3.2 检查当前源码

Agent 优先查看：

```text
current_repository.source_anchors
current_repository.entry_points
current_repository.boundaries
current_repository.state_owners
current_repository.affected_consumers
current_repository.relations
```

这些内容来自学习后的代码图，作用是导航，不是源码真相。

Agent 必须打开当前文件确认：

- 实际责任是否与图中一致；
- 接口、调用者和状态所有者是否仍然有效；
- 图中缺失的关系是否只是尚未学习；
- 当前分支是否已经发生变化；
- 用户描述是否与真实代码行为一致。

图中不存在一条边，不能证明依赖不存在。

### 3.3 第二轮：Agent 聚焦查询

Agent 检查第一轮结果后，明确真正需要关注的质量属性和源码范围：

```bash
python tools/agent_memory.py design-context \
  --project . \
  --query "为 ProfileRepository 增加缓存并保持 ProfileService API 兼容" \
  --concern performance \
  --concern compatibility \
  --concern reliability \
  --anchor "data/ProfileRepository.ets" \
  --anchor "service/ProfileService.ets" \
  --constraint "页面不得持有持久化状态" \
  --compact \
  --json
```

参数含义：

| 参数 | 用途 |
| --- | --- |
| `--query` | 保留完整用户目标，第二轮也不应替换成孤立关键词 |
| `--concern` | Agent 确认需要分析的质量属性，可重复 |
| `--anchor` | Agent 确认需要聚焦的文件，可重复 |
| `--constraint` | 当前任务硬约束，可重复 |
| `--compact` | 使用不超过约 1500 Token 的紧凑上下文 |
| `--max-items` | 调整证据召回上限，通常无需修改 |

`--concern` 由 Agent 在检查第一轮上下文和源码后决定。Runtime 返回的
`routing_hints` 只是词法检索提示，Agent 可以确认、拒绝或补充。

## 4. 如何阅读返回结果

### 4.1 `authority_order`

当信息冲突时，按以下原则处理：

```text
当前任务明确约束
  > 当前源码、测试和编译结果
  > 已确认项目决策或业务纠正
  > 当前学习代码图
  > 尚待源码确认的语义纠正
  > 已验证项目经验
  > 通用设计知识
  > 未验证历史观察
```

检索分数高不等于权威性高。

### 4.2 `current_repository`

提供当前学习范围中的结构上下文：

- `snapshot`：图版本、新鲜度、截断与缺口。
- `entry_points`：与需求或显式 anchor 相关的入口。
- `boundaries`：当前模块或层边界摘要。
- `state_owners`：已识别的状态所有者。
- `extension_points`：当前结构中的可能扩展点。
- `affected_consumers`：相关调用者或消费者。
- `source_anchors`：建议打开检查的源码锚点。
- `relations`：有界代码关系。
- `test_anchors`：可能相关的测试位置。
- `observability_anchors`：相关代码日志位置。

这些字段只说明“系统当前学到了什么”。

### 4.3 `project_context`

包括三类信息：

- `task_constraints`：当前任务硬约束，优先级最高。
- `semantic_corrections`：业务语义补充或纠正，只作为 guardrail。
- `memory_evidence`：相关历史经验和语义事实，只作为提示或风险警告。

未验证纠正会标记：

```text
authority = project_semantic_correction
verification_state = requires_current_source_confirmation
```

Agent 必须确认纠正的 scope 和当前源码，不能直接把它当成设计结论。

### 4.4 `quality_context`

`routing_hints` 帮助 Agent 发现可能相关的关注维度，例如：

- `performance`
- `compatibility`
- `reliability`
- `security`
- `maintainability`
- `modifiability`
- `testability`
- `flexibility`

`scenario_questions` 使用质量属性场景方法，把抽象要求转为可分析问题。例如：

```text
性能：什么负载下，需要达到怎样可观测的延迟或吞吐响应？
兼容：哪些调用方、公开接口或持久化格式必须保持不变？
可靠：发生超时或部分失败时，系统应如何恢复并被观测？
可修改：未来哪一种变化是可信的，哪些模块应保持不受影响？
```

Agent 应将重要问题进一步转为设计约束、风险或验收标准。

### 4.5 `design_knowledge`

这是版本化的通用设计知识，而不是项目学习出的模式。

每条知识可能包含：

- `applicability`：什么情况下可能适用；
- `preconditions`：采用前必须成立的条件；
- `contraindications`：不应采用的情况；
- `tradeoffs`：收益对应的成本；
- `question` 或 `questions`：Agent 需要回答的问题；
- `evidence_needed`：需要哪些源码或运行证据；
- `source_ref` 或 `provenance`：理论和资料来源。

正确使用方式：

```text
当前确实存在两个独立变化的行为，并且调用方需要稳定契约，
因此 Strategy 的适用前提成立。
```

错误使用方式：

```text
系统返回了 Strategy，所以应该使用 Strategy。
```

### 4.6 `evidence_gaps`

缺口必须转换为以下三种动作之一：

1. 打开当前源码补充证据；
2. 向用户确认业务约束；
3. 在方案中明确标记为假设，并给出验证方法。

不能把证据缺失解释成“没有风险”。

## 5. Agent 如何形成设计方案

拿到上下文后，Agent 应独立完成以下推理：

1. 重述目标、范围、约束和排除项。
2. 还原当前责任边界、状态所有权和关键行为流。
3. 明确架构关键质量属性和可观测场景。
4. 识别当前设计真正存在的问题，而不是先寻找模式。
5. 先生成最小可行方案。
6. 只有存在实质结构或质量取舍时，才增加备选方案。
7. 对每个方案分析收益、代价、风险和适用前提。
8. 选择方案，并说明为什么它更符合当前代码与约束。
9. 给出影响范围、迁移顺序和验证计划。

设计原则应作为检验问题使用：

- 是否复用了现有责任边界？
- 新抽象解决了真实变化、耦合、所有权或测试问题吗？
- 状态是否有清晰且唯一的所有者？
- 依赖方向是否把业务策略留在正确的层？
- 是否检查了所有公开接口消费者？
- 每个新增分支是否有测试或可观测验证路径？
- 是否把未知信息明确标成假设？

## 6. 推荐的设计答复格式

Agent 最终面向用户的结果不应直接复制 Runtime JSON，建议使用：

```text
当前结构
- 入口、责任边界、状态所有者、消费者和关键依赖。

目标与约束
- 用户目标、硬约束、排除项和验收标准。

关键质量场景
- 需要满足的性能、可靠性、兼容性或可修改性场景。

推荐方案
- 修改哪些责任和接口。
- 状态、数据和失败如何流动。
- 为什么符合当前结构和适用原则。

备选方案
- 仅列出存在实质取舍的方案。
- 说明没有选择的原因。

影响范围
- 相关文件、符号、调用者、数据和测试。

风险与假设
- 当前证据缺口、迁移风险和需要确认的问题。

实施计划
- 由 Agent 根据依赖关系制定的分阶段步骤。

验证计划
- 编译、测试、运行观测、兼容性和回滚检查。
```

设计理由必须引用当前源码、任务约束或明确的设计知识适用条件。

## 7. 设计后如何验证

用户确认方案并完成实现后，Agent 应：

1. 检查实际改动文件和预期影响范围。
2. 运行项目已有编译、静态检查和测试。
3. 检查公开 API 和持久化格式是否意外变化。
4. 检查新增状态、分支和失败路径是否可测试或可观测。
5. 比较实际实现与设计目标，而不是只比较文件列表。
6. 对偏差重新判断：合理演化、遗漏还是错误实现。

可使用现有能力辅助客观检查：

```bash
python tools/agent_memory.py impact-scope \
  --project . \
  --base HEAD~1 \
  --query "<设计目标>" \
  --json
```

旧 `design-verify` 可以用于核对源码、API、代码图、编译和结构化测试证据，
但它不是设计质量裁判，也不会替 Agent 运行测试。

## 8. 旧设计命令说明

以下命令为兼容已有自动化而保留：

```text
design-assist
design-prepare
design-check
design-compare
design-progress
design-verify
design-outcome
```

默认设计流程不再使用其中的 Runtime 设计推理能力。

- 不使用 `design-assist` 的模式候选作为推荐。
- 不使用 `design-compare` 的结果替 Agent 作决策。
- 不使用 Runtime 生成的 `change_plan` 替 Agent 制定实施计划。
- 不把 `clean`、评分或历史校准解释成设计正确。
- `design-verify` 只保留客观证据检查价值。

未来这些命令会进一步拆分为事实校验和旧决策逻辑；正常用户无需依赖它们。

## 9. 常见错误

### 一轮宽泛查询后直接设计

第一轮用于定向。跨模块、状态、公共接口或重要运行路径设计，应检查源码并使用
明确的 concern 和 anchor 执行第二轮查询。

### 把代码图当作完整调用图

代码图是学习后的有界结构。缺失关系必须通过源码确认。

### 让历史经验决定当前架构

经验只能提示风险、约束或失败模式，不能建立当前结构事实。

### 先选模式再寻找理由

应先明确问题、变化轴和质量场景，再判断某个模式的适用前提是否成立。

### 为未来可能性过度抽象

没有可信变化、边界、所有权或质量压力时，优先局部修改和现有责任边界。

### 忽略业务语义纠正的范围

纠正经验可能只适用于特定模块、版本或场景。必须核对 scope 和当前源码。

### 将验证器结果当成架构结论

静态检查只能发现已编码规则覆盖的问题，不能替代质量属性权衡和业务判断。

## 10. 最小检查清单

```text
[ ] 用户目标、范围、硬约束、排除项和验收标准明确
[ ] 执行 design-context 第一轮方向查询
[ ] 打开并检查当前源码锚点
[ ] 确认真正相关的质量属性
[ ] 必要时使用 concern 和 anchor 执行第二轮聚焦查询
[ ] 区分当前源码、代码图、项目纠正、经验和通用知识
[ ] 最小方案先行，只保留有实质取舍的备选
[ ] 说明原则适用条件，而不是只列模式名称
[ ] 标记证据缺口、假设、风险和验证方法
[ ] 用户确认后再实施
[ ] 运行真实编译、测试和运行观测
[ ] 检查实际实现与设计目标的偏差
```

## 11. 延伸文档

- 长期架构与业界依据：
  [`Design Context Provider`](superpowers/specs/2026-07-16-design-context-provider.md)
- Agent CLI 查询与问题定位完整指南：
  [`Agent CLI Query Skill 中文指南`](agent-cli-query-skill-guide.zh-CN.md)
- Runtime 与 Agent 职责边界：
  [`Agent 上下文供给边界`](context-provider-boundary.md)
- 代码图和存储协议：
  [`Schema Reference`](../references/schema.md)
