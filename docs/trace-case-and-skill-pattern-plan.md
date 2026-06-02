# Trace Case And Skill Pattern Plan

本文定义 Agent Memory 项目中从任务轨迹到经验抽象、再到 skill candidate 的中间层设计。

目标不是增加新的用户 skill。目标是在保持四个用户 skill 不变的前提下，让：

```text
trace case
  -> reflection
  -> procedure_experience / correction_experience
  -> skill_pattern
  -> skill_candidate
```

成为一条可逐步实现的内部演化链。

---

## 1. 核心判断

当前 `procedure_experience` 字段设计只能表达：

```text
single-case procedural evidence
```

它足够支撑“经验候选”，不足够直接演化出 skill。

原因：

- skill 不是单条经验的结构化版本；
- skill 来自多次任务轨迹中的稳定模式；
- skill 需要聚合、比较、验证，而不仅是记录。

因此必须明确新增一个中间概念：

```text
trace_case
```

以及后续更高一层：

```text
skill_pattern
```

---

## 2. 三层区分

### 2.1 Trace Case

定义：

```text
一次任务的执行轨迹、观察、结果和反思压缩记录。
```

它描述：

- 任务是什么；
- Agent 做了哪些关键步骤；
- 哪些动作成功；
- 哪些动作失败；
- 最后得到了什么；
- 从这次任务中提炼出了哪些反思。

### 2.2 Experience

定义：

```text
从一个或多个 trace case 中抽象出的、可迁移的经验结构。
```

它已经脱离单次任务，开始表达：

- 前提
- 边界
- 可迁移规则
- 验证方法

### 2.3 Skill Pattern

定义：

```text
从多个 procedure_experience 中聚合出的稳定流程模式。
```

它接近 skill，但仍然是内部候选，不应直接进入正式 `skills/`。

---

## 3. Trace Case 设计

### 3.1 目标

trace case 不是 raw transcript，也不是完整 CoT 存档。

它的目标是：

```text
保留足够的执行结构，
支持后续经验抽象和 skill 模式挖掘，
同时避免存储噪音和不稳定自由文本。
```

### 3.2 参考来源

外部经验结构里最有价值的部分是：

```json
task
trajectory
outcome
reflection
metadata.related_experiences
```

但不能直接照搬 `thought` 原文。

### 3.3 为什么不长期存完整 CoT

完整 CoT 不适合作为主存储结构：

- 太长
- 不稳定
- 噪音多
- 容易把表达方式误当成策略
- 对 skill 泛化帮助不如结构化摘要大

因此 trace case 应保留：

```text
thought_summary
decision_reason
hypothesis
why_this_step
```

而不是完整原始推理文本。

### 3.4 建议结构

适配当前项目的 trace case 结构建议如下：

```json
{
  "case_id": "case_20260602_001",
  "timestamp": "2026-06-02T10:00:00Z",
  "task": {
    "description": "完整任务描述",
    "task_type": "diagnosis",
    "difficulty": "medium",
    "domain": "harmonyos",
    "problem_frame": "页面跳转后白屏"
  },
  "trajectory": [
    {
      "step": 1,
      "thought_summary": "先确认这是 route 类问题，而不是纯布局问题。",
      "action_type": "query",
      "action_target": "context",
      "action_input_summary": "页面跳转后白屏",
      "observation_summary": "命中 pages/Detail route target",
      "success": true,
      "followup_focus": "route",
      "tokens": 1240,
      "time_sec": 45
    }
  ],
  "outcome": {
    "success": true,
    "final_result": "定位到 route target 写错",
    "quality_score": 0.92
  },
  "reflection": {
    "what_worked": ["route focus", "route target query"],
    "what_failed": ["blank-screen generic search"],
    "key_insights": ["route symptom应优先查router和target page"],
    "generalizations": ["适用于导航后白屏问题"],
    "pitfalls": ["不要先从纯UI渲染方向展开"],
    "improvement_suggestions": ["加入route注册校验步骤"],
    "patterns": ["route-first diagnosis"]
  },
  "metadata": {
    "model_used": "qwen3-14b",
    "environment": "linux",
    "related_cases": ["case_20260530_002"]
  }
}
```

### 3.5 当前项目里的最小化版本

考虑当前项目还不应引入复杂新表，短期可以只把 trace case 先压缩进 reflect payload 逻辑层。

优先字段：

```text
query_rounds
trajectory_summary
useful_followup_focus
useful_followup_terms
misleading_followup_terms
inspection_targets
final_verification_path
related_cases
```

短期不必先建完整 `trajectory_steps` 表。

---

## 4. Trace Case 与两类经验的关系

### 4.1 procedure_experience

主要从 trace case 中提取：

- what_worked
- generalizations
- patterns
- useful_followup_focus
- useful_followup_terms
- final_verification_path

### 4.2 correction_experience

主要从 trace case 中提取：

- what_failed
- pitfalls
- improvement_suggestions
- incorrect/corrected understanding
- source evidence

也就是说：

```text
trace case
  -> procedure_experience
  -> correction_experience
```

不是一对一强绑定，而是后续可以被聚合。

---

## 5. Skill Pattern 设计

### 5.1 为什么需要 Skill Pattern

如果从 `procedure_experience` 直接进入 `skill_candidate`，问题是：

- 太依赖单条 case
- 复用噪声大
- 很难知道步骤是否稳定

因此需要一个中间层：

```text
skill_pattern
```

### 5.2 定义

skill pattern 是：

```text
从多个 procedure_experience 聚合出的稳定执行模式。
```

### 5.3 建议结构

```json
{
  "pattern_name": "arkts_route_blank_screen_diagnosis",
  "trigger_cluster": ["页面跳转后白屏", "router.pushUrl后空白"],
  "common_followup_focus": ["route", "log"],
  "common_query_patterns": [
    "业务页面名 + route/router terms",
    "目标page + router log"
  ],
  "common_steps": [
    "query route anchors",
    "inspect route target and page registration",
    "check related logs",
    "verify route mismatch"
  ],
  "common_stop_conditions": [
    "route mismatch confirmed",
    "route evidence absent after 2 rounds"
  ],
  "common_outputs": [
    "suspected route target",
    "next inspection file",
    "verification checklist"
  ],
  "failure_modes": [
    "误把纯布局白屏当 route 问题"
  ],
  "supporting_cases": ["case_1", "case_2", "case_3"],
  "supporting_experiences": ["exp_1", "exp_2"],
  "success_rate": 0.8,
  "misleading_rate": 0.1,
  "promotion_status": "candidate"
}
```

### 5.4 skill_pattern 的价值

它是后续 skill candidate 的直接原料：

```text
procedure_experience
  -> clustered
  -> skill_pattern
  -> skill_candidate
```

---

## 6. 仍然保持四个 Skill 不变

这是最重要的边界。

用户仍然只使用：

```text
agent-memory-learn
agent-memory-query
agent-memory-maintain
agent-memory-reflect
```

### 6.1 reflect

负责写入：

- task
- compressed trajectory
- outcome
- reflection
- experience_type
- related_cases

### 6.2 maintain

负责：

- 聚合相似 trace case
- 发现 procedure/correction experience
- 输出 skill_pattern candidates

### 6.3 query

负责：

- 查询相关 case / experience / pattern
- 不直接暴露全量轨迹，只返回压缩后的证据和 follow-up

### 6.4 learn

负责：

- 当 correction_experience 指向 learn 语义错误时，回写修正

---

## 7. 推荐的短期实现顺序

### Phase A: Trace Case Fields In Reflect

目标：

- 不建大表，先在 reflect 协议层补 trace-case 压缩字段。

建议先补：

```text
query_rounds
useful_followup_focus
useful_followup_terms
misleading_followup_terms
inspection_targets
final_verification_path
related_cases
```

### Phase B: Maintain Can Summarize Case Clusters

目标：

- maintain-review / maintain-plan 能发现“多条 procedure_experience 指向相似模式”。

输出先做成：

```text
skill_pattern_candidate
```

先不自动写 skill 文件。

### Phase C: Export Skill Candidate Draft

目标：

- 把 skill pattern 导出成 Markdown 候选，而不是直接写正式 skill。

建议目录：

```text
docs/skill-candidates/
```

或：

```text
skills/_candidates/
```

### Phase D: Review And Promote

目标：

- 人审后再进入正式 `skills/`

---

## 8. 成功标准

如果这条设计落地，应达到：

1. 单次任务的关键轨迹能被压缩记录。
2. 经验抽象不再只依赖 lesson 文本。
3. procedure_experience 由多个 case 支撑，而不是单条 reflection 直接升 skill。
4. correction_experience 能利用同样的 trace case 提供 learn/semantic repair 证据。
5. 用户仍然只用四个 skill。

---

## 9. 当前建议

最值得的下一步不是立即生成 skill，而是：

```text
先把 trace-case 压缩字段接入 reflect 协议层
```

因为没有轨迹层，后续 skill 演化只能基于事后总结，泛化质量会很弱。
