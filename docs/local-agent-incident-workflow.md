# 本地 Agent 问题定位闭环

## 目标

本地 Agent 不应只把 Agent Memory 当成搜索数据库。更有效的用法是把它作为诊断控制层，协调当前代码、代码图、代码日志图、临时运行日志、Incident、历史经验、影响范围和验证结果。

推荐闭环：

```text
用户问题
  -> 自动准备证据
  -> 建立多个候选假设
  -> 获取源码、日志和运行证据
  -> 使用反证淘汰错误方向
  -> 修改前评估影响范围
  -> 执行修改和验证
  -> 记录实际影响
  -> 沉淀有边界的经验
```

用户仍然只使用固定四个 Skill。Skill 负责选择阶段和调用命令，`tools/agent_memory.py` 仍是唯一运行时入口。

## 证据原则

Agent 应按以下顺序使用证据：

1. 当前源码、构建结果、测试结果和可复现运行结果。
2. 当前代码图、代码日志锚点和精确语义关系。
3. 已解决 Incident 和带验证来源的经验。
4. 普通历史经验和相似案例。

历史经验不能覆盖当前源码。`association` 只能产生调查方向，不能表述为根因；`supported` 表示存在结构或运行机制；`verified` 才表示存在解决或验证证据；`rejected` 是明确反证。

## 阶段一：自动准备上下文

Agent 收到故障描述后自动调用：

```bash
python tools/agent_memory.py evidence-context \
  --project . \
  --goal diagnosis \
  --query "<用户问题或症状>" \
  --json
```

依次读取：

- `goal_plan`：本轮目标、子查询和停止原因。
- `evidence.direct`：代码、日志和其他当前锚点。
- `evidence.supporting`：Incident、结构关系和支持证据。
- `evidence.advisory`：只能用于建议的历史经验。
- `evidence_chains`：共享锚点形成的有界证据链。
- `evidence_gaps`：缺少的源码学习、临时日志或验证证据。

Agent 不应把返回结果直接改写成结论。结果首先用于决定要读取哪些源码、运行哪些命令以及需要用户提供什么日志。

## 阶段二：分析临时运行日志

用户提供流水日志时，先进行有界分析，不要把完整日志直接注入 LLM：

```bash
python tools/agent_memory.py analyze-runtime-log \
  --project . \
  --query "<故障描述>" \
  --log-file /tmp/runtime.log \
  --json
```

优先使用以下结果：

- 标准事件和高信号日志切片。
- `session_candidates`。
- `runtime_episode_candidate.candidate_chain`。
- `log_signal_summary` 和 `observability_gaps`。
- `log_improvement_suggestions`。
- `reflect_payload_template`。

原始用户日志是临时定位材料，不进入长期记忆。只有确实有复用价值时，才压缩为 Incident Trace：

```bash
python tools/agent_memory.py incident-trace \
  --project . \
  --symptom "<用户可见现象>" \
  --log-file /tmp/runtime.log \
  --json
```

Incident Trace 只保留短日志证据、标准事件、代码锚点和候选因果链。

## 阶段三：假设与反证循环

Agent 至少保留两个可区分的候选假设：

```text
H1: 候选根因
支持证据: 当前哪些事实支持它
反证: 哪些事实与它冲突
缺失证据: 什么结果能够确认或否定它
下一步: 最小成本的源码检查、日志检查、命令或测试
```

下一轮调查优先使用：

- `suggested_followup_terms` 和 `followup_focus`。
- 精确文件路径、符号名、路由名、资源名和日志事件名。
- `evidence_gaps` 中明确缺少的证据。
- 能够区分多个假设的检查，而不是重复寻找支持同一假设的相似结果。

随后由 Agent 直接读取源码、使用 `rg` 检索、检查 Git 历史、执行复现命令或运行测试。记忆系统负责缩小搜索空间，当前代码和运行结果负责裁决。

满足以下任一条件时停止扩展查询：

- 一个假设获得直接机制和验证证据，其他假设被反证。
- 下一轮没有产生新证据，需要新的运行日志或用户输入。
- 已定位到最小可验证修改范围。

## 阶段四：修改前影响分析

确定候选修改文件后运行：

```bash
python tools/agent_memory.py impact-scope \
  --project . \
  --files src/a.ets \
  --files src/b.ets \
  --query "<准备修改的行为>" \
  --json
```

Agent 应检查：

- `reverse_dependents`：可能受影响的调用者和消费者。
- `outgoing_dependencies`：被修改代码依赖的下游节点。
- 相关 Incident 和经验提示。
- `verification_checklist`：首批验证目标。
- coverage gap：未学习文件不能被解释为低风险。

图遍历是有界辅助证据。它不能替代编译器、测试或运行验证。

## 阶段五：验证和实际影响反馈

Agent 完成修改后执行构建、测试和必要的复现检查，然后记录紧凑结果：

```bash
python tools/agent_memory.py impact-feedback \
  --project . \
  --outcome pass \
  --executed-tests tests/ProfileServiceTest.ets \
  --json
```

失败时使用 `--failed-tests`，不稳定测试使用 `--flaky-tests`，影响分析遗漏的目标使用 `--missed-targets`。不要持久化完整 diff 或测试日志。

这些反馈用于改善后续测试推荐，不能把一次成功自动提升为通用规则。

## 阶段六：经验沉淀

运行时会保留有界的最近任务轨迹。问题解决并完成验证后，可以执行：

```bash
python tools/agent_memory.py reflect \
  --project . \
  --from-last-task \
  --task "<问题>" \
  --lesson "<根因、修复方式和适用边界>" \
  --json
```

反思至少应包含：

- 触发条件和可观察现象。
- 真正根因和关键机制。
- 错误假设及其反证。
- 实际修复动作。
- 验证方法和证据来源。
- `applies_to` 与 `does_not_apply_to`。

业务语义纠正应写为 `correction_experience`，不能包装成通用操作流程。可复用诊断步骤才适合写为 `procedure_experience`。

## 阶段七：周期治理

定期运行：

```bash
python tools/agent_memory.py maintain-health --project . --json
python tools/agent_memory.py maintain-plan --project . --json
```

Agent 使用结果处理图中孤立符号、失效边、低信号日志、缺失业务语义、查询未命中、误导经验和过时记忆。维护动作必须经过相应的确认或治理命令，不能因为健康检查提示而自动删除数据。

## Agent 自动执行协议

可以将下面的规则放入项目 Agent 指令或四个固定 Skill 的内部协议：

```text
处理故障时：
1. 自动运行 evidence-context --goal diagnosis。
2. 有运行日志时运行 analyze-runtime-log。
3. 至少形成两个候选假设，并为主要假设主动寻找反证。
4. 使用当前源码、运行结果和测试作为最终事实。
5. 修改前运行 impact-scope。
6. 修改后执行验证并写入 impact-feedback。
7. 问题解决后从 last-task 生成有适用边界的 reflection。
8. association 证据不得表述为确定根因。
9. 证据不足时明确报告缺口，不使用历史经验补齐事实。
```

## 当前边界

- 运行时不会替 Agent 执行测试或修改源码。
- 当前因果等级是证据强度分类，不是反事实因果证明。
- 影响图采用有界遍历，未返回关系不代表不存在依赖。
- 临时日志分析依赖已有日志质量；缺少请求、会话、路由、资源、原因和结果字段时应报告观测缺口。
- 四个用户 Skill 保持固定；新增诊断能力应在内部协议和运行时命令中演进。
