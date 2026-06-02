# Experience Layer Typing Plan

本文定义 Agent Memory 项目中经验层的分型设计、治理方向，以及经验如何在不增加用户可见 skill 数量的前提下逐步演化为 skill candidate。

约束前提：

```text
用户接口仍然固定为 4 个 skill：
  - agent-memory-learn
  - agent-memory-query
  - agent-memory-maintain
  - agent-memory-reflect
```

本设计不引入第五个 skill，不引入 daemon，不引入 vector database，也不改变 SQLite 作为 source of truth 的原则。

---

## 1. 目标

当前经验层主要依附在结构化 reflection 上，已经能表达：

- hidden assumptions
- negative preconditions
- verification method
- reuse feedback
- source cases
- skill candidate

但这仍然偏单一。后续要解决两个不同目标：

1. 一类经验应当逐步演化成可复用的 skill candidate。
2. 另一类经验应当用于纠正 learn 写入的业务语义和记忆理解偏差。

因此，经验层必须分型，而不是继续把所有经验都塞进一个统一“候选经验”桶里。

---

## 2. 经验层分型

### 2.1 Skill 型经验

定义：

```text
可以重复触发、重复执行、重复验证的问题处理流程压缩。
```

作用：

```text
procedure_experience
  -> accepted experience
  -> skill_candidate
  -> future executable skill
```

这类经验回答的问题是：

- 什么情况下触发？
- 第一步查什么？
- 下一步怎么递归 query？
- 什么情况下停止？
- 最后应输出什么？
- 哪些情况会误导？

建议名称：

```text
procedure_experience
```

示例：

- ArkTS 页面跳转后白屏定位流程
- 资源加载失败定位流程
- query miss 修复流程
- memory-aware change design 流程

### 2.2 纠正型经验

定义：

```text
对已有学习结果、业务语义理解、代码语义提取结果的纠偏规则。
```

作用：

```text
correction_experience
  -> learn governance
  -> semantic repair
  -> better memory quality
```

这类经验回答的问题是：

- 之前学进去的内容哪里错了？
- 为什么错了？
- 应如何修正？
- 以后 learn 阶段要避免什么理解偏差？

建议名称：

```text
correction_experience
```

示例：

- 把页面文件误理解成 service 文件
- 把 log 的业务意义写偏
- 把 permission / ability / route 混淆
- 把字段业务对象理解错

---

## 3. 为什么必须分型

如果不分型，会出现两个问题：

### 3.1 Skill 演化路径被污染

如果 skill candidate 池里混入大量“纠错经验”，则这些记录没有稳定触发条件、没有执行步骤，也没有输出协议，无法自然演化为 skill。

### 3.2 Learn 治理路径被稀释

如果 correction 类经验埋在 procedure lesson 里，maintain 无法明确知道：

- 是该补 learn-business？
- 还是该 review 经验候选？
- 还是该修正已有语义？

因此经验层必须从设计上拆出：

```text
可执行经验
vs
记忆纠偏经验
```

---

## 4. Skill 型经验设计

### 4.1 目标

Skill 型经验不是长 lesson 文本，而是“未来 skill 的结构化压缩”。

### 4.2 必要字段

建议后续在现有 reflection / experience-candidate 结构之上，补出以下逻辑字段：

```text
experience_type = procedure_experience
trigger_signals
entry_query_patterns
preferred_followup_focus
recommended_steps
stop_conditions
verification_checklist
expected_outputs
failure_modes
reuse_evidence
promotion_status
```

字段含义：

- `trigger_signals`
  - 触发这条经验的稳定症状、日志、页面行为、业务对象。

- `entry_query_patterns`
  - 第一次 query 应优先使用的模式，不是完整 query 文本，而是稳定模式。

- `preferred_followup_focus`
  - 递归 query 时优先使用哪类 focus：
    - route
    - resource
    - log
    - config
    - generic

- `recommended_steps`
  - 经验压缩后的执行步骤。

- `stop_conditions`
  - 什么情况下停止递归查询或停止诊断。

- `verification_checklist`
  - 必须检查的 source/log/test/repro 条目。

- `expected_outputs`
  - 这条经验最终应产出的结果。

- `failure_modes`
  - 哪些场景会让这条经验误导。

- `reuse_evidence`
  - 它被哪些任务成功或部分成功复用过。

- `promotion_status`
  - 当前是否只是候选、已接受、还是已进入 skill candidate。

### 4.3 Skill 演化条件

一条 procedure_experience 只有在满足以下条件时，才值得升级为 skill candidate：

```text
1. 有稳定触发条件
2. 有重复可执行步骤
3. 有前置条件和不适用条件
4. 有验证方法
5. 多次 reuse_feedback 为 helped 或 partial
6. expected_outputs 足够稳定
```

### 4.4 典型输出形态

未来 skill candidate 最终应能导出成：

```text
输入:
  problem frame / source clue / current query state

步骤:
  query -> inspect -> refine -> stop

输出:
  next query
  inspection targets
  diagnosis summary
  verification checklist
  reflect payload hint
```

---

## 5. 纠正型经验设计

### 5.1 目标

纠正型经验不是为了直接执行，而是为了让 learn 更准确、memory 更干净。

### 5.2 必要字段

建议后续逻辑上表达这些字段：

```text
experience_type = correction_experience
target_memory_type
target_anchor
incorrect_understanding
corrected_understanding
correction_reason
source_evidence
applies_to_learning_stage
prevention_rule
governance_action
```

字段含义：

- `target_memory_type`
  - 被纠正的对象类型，例如：
    - code_file
    - code_symbol
    - code_log_statement
    - reflection

- `target_anchor`
  - 对应对象的稳定锚点，例如：
    - `pages/Profile.ets`
    - `pages/Profile.ets::loadProfile`
    - `pages/Profile.ets::load profile failed`

- `incorrect_understanding`
  - 之前错误的业务理解。

- `corrected_understanding`
  - 更准确的业务理解。

- `correction_reason`
  - 为什么之前的理解错了。

- `source_evidence`
  - 当前代码、日志、资源、配置或任务证据。

- `applies_to_learning_stage`
  - 这条纠偏经验作用在哪个阶段：
    - learn-entry
    - learn-business
    - maintain semantic repair

- `prevention_rule`
  - 以后再遇到类似结构时的 learn 防错规则。

- `governance_action`
  - 下一步治理动作：
    - rewrite_memory
    - add_business_terms
    - review_semantic_conflict
    - ignore

### 5.3 目标不是 Skill 化

这类经验默认不进入 skill candidate 主路径。它们的主要用途是：

```text
纠错
-> 修正 learn-business 语义
-> 减少 query 漂移
-> 提升 memory 质量
```

只有少数通用纠偏流程，才可能被进一步抽象为维护类 skill candidate。

---

## 6. 保持四个 Skill 不变

这是整个设计必须严格保持的边界。

用户仍然只使用：

```text
agent-memory-learn
agent-memory-query
agent-memory-maintain
agent-memory-reflect
```

后续所有经验分型和 skill 演化，都只能通过这四个 skill 背后的 runtime 协作完成。

### 6.1 learn

负责：

- 学习结构
- 学习业务语义
- 接收 correction 类经验对 learn 的反哺

### 6.2 query

负责：

- 使用 procedure_experience 作为更高优先级的 investigation frame
- 使用 followup_focus 和 suggested_followup_terms 做递归查询

### 6.3 maintain

负责：

- review_query_miss
- add_business_terms
- review_semantic_conflict
- promote_experience_candidate
- 后续区分 procedure / correction 两类经验的治理动作

### 6.4 reflect

负责：

- 记录任务结果
- 记录 query 行为
- 记录 reuse_feedback
- 产生 procedure_experience 或 correction_experience 候选

---

## 7. 对当前表结构的落地方向

### 7.1 短期原则

短期不要立刻新增大量 experience 表。先在现有 reflection 结构和 governance 流程里表达分型。

### 7.2 短期表达方式

优先在 reflection / experience candidate 逻辑层区分：

```text
experience_type = procedure_experience | correction_experience
```

现阶段可以通过：

- reflect payload 结构
- maintain-plan action 分类
- vault review 页面

来先完成分型，而不是马上引入完整独立 experience schema。

### 7.3 中期方向

当分型稳定后，再考虑独立表，例如：

```text
experiences
experience_sources
experience_reuse_feedback
skill_candidates
```

但这一步不是当前第一优先级。

---

## 8. 对 reflect 的升级方向

为了让经验能真正演化，reflect 后续应记录的不只是 lesson，还应记录“经验类型”和“query 行为证据”。

建议 reflect 后续补充：

```text
experience_type
query_rounds
useful_followup_focus
useful_followup_terms
misleading_followup_terms
final_verification_path
```

意义：

- procedure_experience 可以据此沉淀成 skill-ready 流程。
- correction_experience 可以据此沉淀成 learn/maintain 的纠偏规则。

---

## 9. 对 maintain 的升级方向

maintain 后续不应只 review “经验候选”，而应按类型治理：

### 9.1 procedure_experience

建议动作：

```text
review_procedure_experience
accept_procedure_experience
promote_skill_candidate
mark_stale
```

### 9.2 correction_experience

建议动作：

```text
review_correction_experience
rewrite_memory
apply_learning_rule
ignore
```

对当前 runtime 的直接要求应是：

- `review_correction_experience` 不只返回类型标签
- 应直接返回 `correction_targets`
- 应返回 `learning_rule_draft`
- 应返回面向受影响 records 的 `learn_business_payload_template`
- 应返回修复用 `workflow_steps`

这样 maintain 才不会把所有经验候选都当成同一种东西。

---

## 10. Skill Candidate 演化路线

后续 skill 候选的正确生命周期应是：

```text
procedure_experience
  -> accepted procedure_experience
  -> skill_candidate
  -> generated skill template
  -> reviewed real skill
```

注意：

- 不是所有 experience 都能进 skill candidate。
- correction_experience 默认不走这条主线。
- skill candidate 先导出模板，而不是自动写进正式 `skills/`。

建议中间态：

```text
docs/skill-candidates/
```

或：

```text
skills/_candidates/
```

先做人审查，再决定是否进入正式 skill。

---

## 11. 分阶段计划

### Phase A: Experience Typing

目标：

- 在 reflect 和 maintain 逻辑层区分两类经验。
- 不新增第五个 skill。

任务：

1. 为 reflection / experience candidate 增加 `experience_type`。
2. 更新 reflect payload 说明。
3. 更新 maintain-plan 的经验治理动作分类。
4. 更新 vault 页面，把 procedure / correction 分开展示。

### Phase B: Procedure Experience Becomes Skill-Ready

目标：

- 让 procedure_experience 能表达 skill-ready 结构。

任务：

1. 增加 `trigger_signals`、`recommended_steps`、`expected_outputs` 等字段逻辑。
2. 记录 query round / followup_focus / useful terms。
3. 用 reuse feedback 判断是否进入 skill candidate。

### Phase C: Correction Experience Feeds Learn Governance

目标：

- 让 correction_experience 真正反哺 learn。

任务：

1. 记录 target anchor 和 corrected understanding。
2. 接 maintain-plan 的 `rewrite_memory` / `add_business_terms`。
3. 形成 learn-business 的纠偏规则。

### Phase D: Skill Candidate Output

目标：

- 导出 skill candidate 模板，但仍保持用户只用四个正式 skill。

任务：

1. 生成 skill candidate 文档模板。
2. 审查后决定是否进入正式 `skills/`。

---

## 12. 成功标准

这一设计落地后，应达到：

1. 用户界面仍然只有四个 skill。
2. 经验候选在治理时能明确区分：
   - 可执行经验
   - 纠偏经验
3. procedure_experience 能自然演化成 skill candidate。
4. correction_experience 能自然反哺 learn 和 semantic repair。
5. query / maintain / reflect 对经验的使用路径更清晰，不再把所有经验混在一个通道里。

---

## 13. 当前建议

如果继续执行，下一步最值得做的是：

```text
第一步：
  在设计层和 reflect/maintain 协议层引入 experience_type

第二步：
  为 procedure_experience 补 skill-ready 字段

第三步：
  为 correction_experience 补 learn-governance 字段
```

先把经验层分型做对，再谈自动 skill 演化，会更稳。
