# 前瞻性真实连续任务 Cohort 设计

## 目标

用当前四 Skill 和 `selective-query-skill` v3 评测真实使用价值，避免继续从历史提交中挑选
看起来适合 Memory 的案例。系统只建立可审计的实验控制平面，不增加 Runtime 诊断、设计
推理或新的用户 Skill。

## 为什么不是再做一个案例包

历史 Git 修复可以验证源码定位，但不能回答以下问题：

- 日常任务中 Memory 机会实际出现多少；
- Agent 是否通过真实安装机制自然发现 Query Skill；
- 项目历史经验在任务开始前是否已经存在；
- 不需要 Memory 的任务是否承担了额外成本；
- 查询结果是否被 Agent 检查并改善最终结果。

因此下一层证据必须在任务结果未知时入组，并保留任务开始前的来源和 Memory 状态。

## 业界依据

本设计采用以下成熟原则：

1. Microsoft ExP 将可信实验拆成预实验假设和指标、运行期数据质量/OEC/局部诊断/护栏、
   以及实验后归档。缺失数据和 Sample Ratio Mismatch 必须先处理，不能直接解释效果。
2. SWE-bench 使用真实 issue、冻结代码环境和可执行验证，说明真实软件任务需要同时约束
   任务来源、仓库状态和客观结果。
3. SWE-rebench 强调持续采集新鲜真实任务，降低静态基准污染和选择偏差。
4. LongMemEval 将长期记忆拆为提取、多会话、时间推理、知识更新和 abstention；因此“不查”
   与正确处理更新都必须进入评测，不能只统计召回。
5. OpenTelemetry 使用稳定 schema 和语义约定，并要求敏感遥测最小化和清洗；本设计只保存
   可观察聚合及摘要，不保存原始查询、临时日志、源码正文或 Agent 推理。

引用：

- Microsoft, Patterns of Trustworthy Experimentation, pre/during/post experiment:
  <https://www.microsoft.com/en-us/research/?p=680556>
  <https://www.microsoft.com/en-us/research/group/experimentation-platform-exp/articles/patterns-of-trustworthy-experimentation-during-experiment-stage/>
  <https://www.microsoft.com/en-us/research/articles/patterns-of-trustworthy-experimentation-post-experiment-stage/>
- Microsoft, Sample Ratio Mismatch taxonomy:
  <https://www.microsoft.com/en-us/research/publication/diagnosing-sample-ratio-mismatch-in-online-controlled-experiments-a-taxonomy-and-rules-of-thumb-for-practitioners/>
- SWE-bench: <https://arxiv.org/abs/2310.06770>
- SWE-rebench: <https://arxiv.org/abs/2505.20411>
- LongMemEval: <https://arxiv.org/abs/2410.10813>
- OpenTelemetry schemas and sensitive-data guidance:
  <https://opentelemetry.io/docs/specs/otel/schemas/>
  <https://opentelemetry.io/docs/security/>

## 系统边界

```text
真实任务到达
  -> eval-cohort-enroll（结果未知时）
       -> 固定 sequence
       -> task 内容 SHA-256
       -> Git HEAD/dirty 状态摘要
       -> Memory 高水位 manifest
       -> opportunity 预标注及已存在记录引用
       -> append-only enrollment hash chain
  -> Agent 正常使用固定四 Skill
       -> last_task_trace（现有滚动临时文件）
  -> 可选 v3 单案例 paired A/B
  -> eval-cohort-complete
       -> 只提取聚合计数和结果摘要
  -> eval-cohort-finalize
       -> 固定样本数和完整性门禁
  -> eval-cohort-report
```

SQLite 是 cohort 元数据的事实源。`last_task_trace.json` 仍是可丢弃的运行时文件；其原始查询
不会复制到 cohort 表。真实任务描述保留在用户提供的外部文件中，数据库只存内容摘要。

## 协议

`prospective-agent-cohort/v1` 必须在第一次入组前冻结：

```json
{
  "schema_version": "prospective-agent-cohort/v1",
  "cohort_id": "arkts-dogfood-v1",
  "title": "ArkTS diagnosis consecutive tasks",
  "evidence_origin": "prospective_real_tasks",
  "task_type": "diagnosis",
  "target_presented_tasks": 10,
  "enrollment": {
    "mode": "consecutive",
    "source_scope": "one-real-project",
    "allowed_exclusion_reasons": ["not_diagnosis", "duplicate_task", "environment_unavailable"]
  },
  "hypothesis": {
    "primary": "Query Skill improves verified task outcome without guardrail regression",
    "treatment_mode": "selective-query-skill"
  },
  "metrics": {
    "overall": ["verified_task_success"],
    "diagnostic": ["activation", "anchor_utilization", "first_observable_loss"],
    "guardrails": ["token_cost", "latency", "query_errors"]
  },
  "stop_rule": {
    "type": "fixed_presented_count",
    "optional_stopping": false
  },
  "data_policy": {
    "persist_raw_task": false,
    "persist_raw_query": false,
    "persist_raw_logs": false,
    "persist_reasoning": false
  }
}
```

第一版只允许 diagnosis，避免把设计任务和问题定位混为一个结果。后续任务类型通过相同抽象
扩展，但必须使用独立 cohort。

## 连续入组

每个到达任务都占一个不可复用的 `sequence_no`。排除项也计入固定 presented 数量，并必须
使用协议预先声明的原因，避免看到难例后替换。

系统能够证明：

- 已记录项无重复、无内部序号缺口；
- 达到目标后不能继续入组；
- 入组字段进入 SHA-256 hash chain，修改后审计失败；
- 同一时间最多有一个 eligible 任务处于执行中。

系统不能证明操作者是否故意没有登记某个外部任务。因此报告必须标记
`external_consecutiveness=self_attested`，不能把内部完整性表述成外部随机抽样证明。

## 时间截断与 Memory Opportunity

入组时间就是 `memory_available_at`。系统记录：

- durable memory 表的 count、max id 和最新时间高水位；
- code index generation/source revision；
- graph revision；
- manifest 的规范 SHA-256；
- Git HEAD、dirty 标记、dirty 状态摘要和变更项数量。

`opportunity=present` 必须引用任务开始前已经存在的类型化记录：

- `semantic:<id>`
- `reflection:<id>`
- `episode:<id>`
- `code_log:<id>`

系统只保存引用，不复制正文。`absent` 和 `unknown` 不允许附加引用。Dirty 源码任务可以进入
自然使用观察，但 `replay_eligible=false`，不能进入冻结源码 paired A/B 结论。

## 双重分账

每个 eligible 任务都属于 Natural Cohort；`opportunity=present` 同时进入 Memory Opportunity
segment。Headline 分别报告，绝不把机会样本的高收益冒充日常任务总体收益。

### Data quality

- hash chain、序号、目标数量和 terminal 状态完整性；
- usage trace 绑定率；
- v3 benchmark 绑定率及测量合同完整性；
- opportunity 预标注覆盖率；
- clean-source replay eligibility；
- excluded 原因分布。

### Overall outcome

- verified success / fail / partial / unknown；
- paired Agent outcome delta（仅 v3 单案例结果）；
- Natural 与 Opportunity 分账。

### Local diagnostics

- Query Skill 激活率、平均查询数和查询错误；
- anchor 返回与实际检查；
- v3 first observable loss；
- source search/read 变化。

### Guardrails

- Token 与端到端 latency overhead；
- 每案例 quality/efficiency gate；
- dirty source、缺失 trace、缺失成本归因。

少量任务只产生 Development 描述性统计，不计算伪精确显著性，也不声明泛化。

## CLI 门面

```bash
python tools/agent_memory.py eval-cohort-create \
  --project . --protocol cohort.json --json

python tools/agent_memory.py eval-cohort-enroll \
  --project . --cohort-id arkts-dogfood-v1 \
  --task-id task-001 --task-file task.json \
  --eligibility eligible --opportunity unknown --json

python tools/agent_memory.py eval-cohort-complete \
  --project . --cohort-id arkts-dogfood-v1 --task-id task-001 \
  --outcome pass --verification test \
  --benchmark-result result.json --case-id task-001 --json

python tools/agent_memory.py eval-cohort-report \
  --project . --cohort-id arkts-dogfood-v1 --json

python tools/agent_memory.py eval-cohort-finalize \
  --project . --cohort-id arkts-dogfood-v1 --json
```

排除任务使用 `--eligibility excluded --exclusion-reason <预注册原因>`，不执行 complete。

## 架构

- `prospective_cohort_contract.py`: protocol、枚举和输入验证。
- `prospective_cohort_schema.py`: 两张独立 SQLite 表和索引。
- `prospective_cohort_snapshot.py`: Git/Memory 高水位和 opportunity 引用验证。
- `prospective_cohort_metrics.py`: usage trace、v3 结果的无敏感信息投影和分账聚合。
- `prospective_cohort.py`: 门面服务、事务、hash chain、finalize/report。
- `cli_benchmark.py`: CLI 参数，不承载业务逻辑。

每个模块正文不超过 500 行。现有 Runtime serving、查询排序、图、日志和经验表均不修改。

## Fail-closed 规则

- 协议缺少固定目标、连续入组、非可选停止或数据最小化声明时拒绝创建。
- active eligible 任务未完成时拒绝入组下一个任务。
- opportunity present 缺少有效的任务前记录引用时拒绝。
- usage trace 缺失或不属于当前 task 时回滚 complete，任务保持 active。
- 任务完成只能写一次；finalized cohort 永久只读。
- v3 结果不是单案例、treatment mode 不符或测量合同失败时拒绝绑定。
- 目标数量未达到、存在 active 任务或 hash chain 失败时拒绝 finalize。
- 没有 paired A/B 时只报告 observational，不计算 uplift。

## 验收

- [x] 协议在第一次入组前冻结并持久化摘要。
- [x] eligible/excluded 都占连续 sequence，不能替换或超额。
- [x] 每次入组绑定任务摘要、Git 状态和 Memory 时间 manifest。
- [x] Opportunity 引用只能指向任务开始前存在的记录。
- [x] Cohort 表不出现原始任务、查询、日志、源码或推理。
- [x] usage trace 和 v3 单案例结果只以有界聚合进入 SQLite。
- [x] Natural/Opportunity、数据质量/OEC/诊断/护栏分账。
- [x] finalize 固定停止且 hash chain 完整。
- [x] 四 Skill、单入口、SQLite 和 500 行约束保持不变。
- [x] Development 校准不产生真实能力或 promotion 声明。
