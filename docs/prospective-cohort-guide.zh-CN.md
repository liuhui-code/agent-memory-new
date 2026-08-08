# 前瞻性真实任务 Cohort 使用指南

本指南用于验证 Agent Memory 在真实、连续到达的任务中是否提供净价值。它不是新的用户
Skill，也不会让 Runtime 诊断问题。用户仍然使用固定四个 Skill；cohort 命令只负责评测治理。

## 适用场景

当你准备在一个真实 ArkTS 项目中连续使用 Agent CLI，并希望回答以下问题时使用：

- Agent 是否会自然调用 `agent-memory-query`；
- 不需要记忆时是否能保持不查询；
- 任务开始前已有的经验、业务纠正或日志映射是否被找到；
- Agent 是否检查返回锚点并改善结果；
- Token、耗时、查询错误和源码搜索是否可接受。

不要为了已有历史案例补建 cohort，也不要只登记看起来适合 Memory 的任务。

## 1. 冻结协议

复制并修改 `docs/eval/prospective-cohort-v1-calibration-protocol.json`。正式 cohort 建议使用
一个真实项目、一个任务类型和固定 presented 数量。第一版只支持 diagnosis。

协议必须在首个任务到达前确定：

- `target_presented_tasks`：到达任务总数，包含排除项；
- `evidence_origin`：真实队列使用 `prospective_real_tasks`，生成校准只能使用
  `generated_protocol_calibration`；
- `source_scope`：任务来自哪个固定项目或队列；
- `allowed_exclusion_reasons`：只能使用这些原因排除；
- 假设、总体指标、局部诊断和成本护栏；
- 固定停止且禁止 optional stopping；
- 原始任务、查询、日志和推理全部不持久化。

创建：

```bash
python tools/agent_memory.py eval-cohort-create \
  --project /path/to/project \
  --protocol /path/to/cohort-protocol.json \
  --json
```

创建后 protocol digest 固定，同一项目不能重复使用相同 `cohort_id`。

## 2. 每个任务到达时立即入组

将原始任务放在项目记忆之外的文件中。Runtime 只保存该文件的 SHA-256：

```bash
python tools/agent_memory.py eval-cohort-enroll \
  --project /path/to/project \
  --cohort-id arkts-dogfood-v1 \
  --task-id task-001 \
  --task-file /private/path/task-001.json \
  --eligibility eligible \
  --opportunity unknown \
  --json
```

`task-id` 是短的、不含任务文本的 opaque identifier。入组命令自动记录：

- 连续序号和前一项 hash；
- Git HEAD、dirty 标记和状态摘要；
- Memory 表高水位、code index generation 和 graph revision；
- 任务开始时间及 usage sample id。

同一时间只能有一个 eligible 任务处于 active。开始前如果存在未关闭的旧 usage trace，先完成
或反思旧任务，不能让两个任务共享遥测。

## 3. 任务前标记 Memory Opportunity

只有在任务开始前已经存在可引用记录时才使用 `present`：

```bash
python tools/agent_memory.py eval-cohort-enroll \
  --project /path/to/project \
  --cohort-id arkts-dogfood-v1 \
  --task-id task-002 \
  --task-file /private/path/task-002.json \
  --eligibility eligible \
  --opportunity present \
  --evidence-ref reflection:17 \
  --evidence-ref code_log:42 \
  --json
```

合法类型为 `semantic`、`reflection`、`episode` 和 `code_log`。系统验证记录属于当前项目且
可用时间不晚于任务开始。只保存 ID 和时间，不复制正文。

- `present`：至少一个任务前证据引用；
- `absent`：明确审查后不存在相关 Memory；
- `unknown`：未预先判断，不能附加引用。

不要在完成任务后回填 `present`。

## 4. 正常使用 Agent

入组后按正常方式使用 `agent-memory-query`，不要为了评测强迫 Agent 查询。Runtime 继续只提供
上下文，Agent 读取真实源码和临时日志、形成假设并验证。

原始查询可能存在于现有滚动 `last_task_trace.json`，但 cohort 完成时只提取：

- command/query 数量；
- 查询错误数量；
- 返回类型和锚点计数；
- trace SHA-256。

原始查询、Context、日志和推理不会进入 SQLite cohort 表。

## 5. 完成任务

```bash
python tools/agent_memory.py eval-cohort-complete \
  --project /path/to/project \
  --cohort-id arkts-dogfood-v1 \
  --task-id task-001 \
  --outcome pass \
  --verification test \
  --json
```

`outcome` 为 `pass`、`fail`、`partial` 或 `unknown`。已知结果必须使用 `test`、`build`、
`source_review` 或 `user_confirmation`，不能标成 `unverified`。

完成写入只能执行一次，并会关闭本任务 usage sample，使下一个 eligible 任务可以入组。
如果 trace 缺失或已被另一任务覆盖，complete 会在写入前失败，当前任务仍保持 active，不会形成
无法修复的 completed 记录。

## 6. 可选绑定 v3 单案例 A/B

对于入组时源码 clean 的任务，可以在冻结 revision 上运行现有 v3 benchmark，然后绑定结果：

```bash
python tools/agent_memory.py eval-cohort-complete \
  --project /path/to/project \
  --cohort-id arkts-dogfood-v1 \
  --task-id task-003 \
  --outcome pass \
  --verification test \
  --benchmark-result /path/to/task-003-result.json \
  --case-id task-003 \
  --json
```

绑定要求：

- `treatment_mode=selective-query-skill`；
- 结果只包含该一个 case；
- v3 measurement contract 通过；
- 入组源码 clean，具备 replay eligibility。

Cohort 只保存 quality/efficiency gate、查询次数、首次失败、锚点命中、结果分、Token、耗时和
源码搜索聚合。原始 Agent 响应不进入 cohort 表。

## 7. 排除项仍占序号

任务不符合协议时也必须登记：

```bash
python tools/agent_memory.py eval-cohort-enroll \
  --project /path/to/project \
  --cohort-id arkts-dogfood-v1 \
  --task-id task-004 \
  --task-file /private/path/task-004.json \
  --eligibility excluded \
  --opportunity unknown \
  --exclusion-reason not_diagnosis \
  --json
```

排除原因必须在协议中预注册。排除任务立即成为 terminal，不执行 complete，也不能用新任务替换
该序号。

## 8. 查看和结束

随时查看描述性报告：

```bash
python tools/agent_memory.py eval-cohort-report \
  --project /path/to/project \
  --cohort-id arkts-dogfood-v1 \
  --json
```

只有达到固定 presented 数量、所有 eligible 任务完成、usage trace 绑定且 hash chain 完整时才能
结束：

```bash
python tools/agent_memory.py eval-cohort-finalize \
  --project /path/to/project \
  --cohort-id arkts-dogfood-v1 \
  --json
```

Finalize 后 cohort 永久只读。

## 9. 如何解释结果

报告分成：

- `data_quality`：内部连续性、目标数量、trace、benchmark、opportunity 和 clean-source 覆盖；
- `segments.natural`：所有 eligible 连续任务；
- `segments.memory_opportunity`：任务前确有 Memory 的子集；
- `evidence_mode`：observational、mixed 或 paired selective query；
- outcome、激活、首次失败、锚点利用、Token、延迟和源码搜索护栏。

`external_consecutiveness=self_attested` 是硬边界：系统能证明登记后的不可替换和无内部缺口，
不能证明操作者没有隐瞒外部任务。少量 cohort 只能形成 Development 描述性证据，不证明统计
显著性、跨项目泛化或发布晋级。

如果 Context 有效但 Agent 结果没有改善，应停止扩张检索能力；只有正式 `query_handoff` 在独立
Development 任务中复现具体缺陷时，才允许修改 serving。
