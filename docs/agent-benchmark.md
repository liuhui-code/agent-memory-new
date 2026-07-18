# Agent 自采集与 A/B 自验证基准

本文说明如何从真实 Git 历史和真实 ArkTS/TypeScript 代码生成可重复案例，并比较同一个外部 Agent CLI 在“不使用上下文层”和“使用 `agent-memory-query` 证据上下文”两种模式下的表现。

该能力仍使用固定四个 Skill。案例采集、评测和质量治理属于 `agent-memory-maintain`；Agent 实际解决问题时，Memory 组通过 `agent-memory-query` 获取证据。`tools/agent_memory.py` 仍是唯一运行时入口。

## 核心边界

- Git 历史采集只生成 `draft`，不能未经审查进入 Holdout。
- ArkTS Mutation 描述可逆编辑，不修改当前源码。
- 每次 Runner 执行都使用临时工作区。
- Memory 组在冻结 revision 上重建隔离的临时记忆，不能读取当前 HEAD 的记忆。
- Oracle、修复 commit 和 Mutation 原始位置不进入 Agent 请求。
- Runner 不能返回 thoughts、reasoning 或 chain-of-thought 字段。
- 根因、设计判断、受影响文件和验证结论都由外部 Agent Runner 产生；Runtime 不参与作答。
- 评分由文件、根因类别、禁入方向、因果等级、验证状态、耗时和 Token 确定，不使用 LLM Judge。
- 最新结果只写入 runtime 快照和有界历史，不写入 SQLite 项目知识。

## 零、先测系统上下文能力

昂贵 Agent A/B 前先运行 `eval-context-capability`。它在冻结 revision 上重建隔离索引，
直接检查系统是否召回 Oracle 文件、避开禁止文件、提供要求的当前源码摘录并保持在
1,500 Token 预算内，不调用任何模型。日志、经验和因果路径只有在案例显式提供
`oracle.context_requirements` 时才进入门禁；否则标为 `informational`。

详细命令、字段与 Gramony 五案例 development 结果见
[`docs/system-capability-evaluation.md`](system-capability-evaluation.md)。系统门禁失败时先修
上下文供给；通过后再运行本文件后续的 Agent A/B，验证 Agent 是否真正利用这些证据。

仓库内置的 `docs/eval/system-capability-cases.json` 应作为第一层快速门禁。它用十二个最小
ArkTS 案例分别检查日志、经验、候选因果路径、跨组件召回、两跳组件属性流、查询条件化组件谱系、UI 行为所有者、日志密集源码配额和无证据
abstention，允许受控的已审查反思
fixture，但不调用模型。每个场景包含原始、英文改写和中文/噪声改写三种查询，共执行
36 次隔离检索；
`query_robustness` 要求同一 Oracle 在所有变体下稳定通过。该门禁通过后，再用 Gramony
冻结源码验证真实项目代码定位，最后才运行外部 Agent A/B。系统能力通过只说明 context
供给满足 Oracle，不代表 Agent 已得到正确根因。

真实项目验证分为可迭代 development 案例和禁止调参的 sealed holdout。当前
`docs/eval/gramony-context-holdout-cases.json` 首次运行 0/3，通过失败本身是有效结果；
不得修改该集合的措辞或 Oracle 来提高分数。

完成后续 development 改进后，另一组独立的
`docs/eval/gramony-context-generalization-holdout-cases.json` 首次有效运行 1/3。它确认
数据库持久化上下文可以泛化，同时暴露跨组件属性反向追踪和锚点精度缺口。该结果同样只
作为冻结观察，不允许回调案例或权重；详见 `docs/system-capability-evaluation.md`。

## 一、从 Git 历史采集案例

```bash
python tools/agent_memory.py eval-harvest-history \
  --project . \
  --source /path/to/arkts-project \
  --target /tmp/arkts-history-cases.json \
  --scan-limit 200 \
  --limit 20 \
  --since 2025-01-01 \
  --json
```

采集器读取非 merge commit，优先保留：

- 同时修改实现和测试的提交。
- 提交主题包含 fix、bug、crash、blank、refactor、修复、白屏或重构等信号的提交。
- 修改 ArkTS、TypeScript、JavaScript、JSON5、Python、Dart 或 Swift 实现的提交。

案例包含修复前 revision、修复后 revision、变更文件、测试文件和隐藏 Oracle。初始任务描述只指向受影响区域，避免把提交主题中的答案直接暴露给 Agent。

所有历史案例初始为 `review_status: draft`。审查时必须：

1. 用真实用户症状替换宽泛任务描述。
2. 从实现文件中移除格式化、文档和无关修改。
3. 确认真正根因类别。
4. 补充禁止方向和验证测试。
5. 确认修复前 revision 可以构建或至少可以静态检查。
6. 再改为 `validated`；独立保留且不参与调优的案例才能改为 `holdout`。

## 二、生成 ArkTS 可控故障

```bash
python tools/agent_memory.py eval-mutate-arkts \
  --project . \
  --source /path/to/arkts-project \
  --target /tmp/arkts-mutation-cases.json \
  --limit 20 \
  --json
```

第一版 Mutation Operator：

| Operator | 故障类型 | 修改 |
|---|---|---|
| `remove_await` | async | 移除一个异步等待点 |
| `corrupt_route_target` | route | 将一个路由目标改成不存在的目标 |
| `corrupt_resource_key` | resource | 将一个 `$r(...)` 资源键改成不存在的键 |

只生成某类案例：

```bash
python tools/agent_memory.py eval-mutate-arkts \
  --project . \
  --source /path/to/arkts-project \
  --target /tmp/route-cases.json \
  --operator corrupt_route_target \
  --limit 10 \
  --json
```

生成器记录源文件摘要、精确 occurrence、替换文本和已知 Oracle，但不修改源文件。Benchmark 执行时才在临时工作区应用 Mutation，并在应用前检查摘要，避免项目更新后把故障注入错误位置。

Mutation 案例的 Oracle 是“构造已知”，不等价于真实线上事故。报告必须按 provenance 分组，不能把 Mutation 准确率描述为真实事故准确率。

## 三、Agent Runner 协议

`eval-agent-benchmark` 不绑定 Codex、Claude Code 或其他 Agent CLI。调用者提供一个可执行 Runner；运行时通过 stdin 发送单个 JSON 请求，Runner 通过 stdout 返回单个 JSON 结果。

```text
Agent Memory Runtime
  -> 冻结 revision 到临时工作区
  -> 应用可选 Mutation
  -> baseline: 只提供工作区
  -> memory: 在该工作区重建隔离记忆并提供上下文 query_command
  -> Runner 调用目标 Agent CLI
  -> Runner 返回结构化结果
  -> 使用隐藏 Oracle 对外部 Agent 结果做确定性评分
```

Runner 请求：

```json
{
  "schema_version": "agent-benchmark-request/v1",
  "case_id": "mutation-123",
  "variant": "memory",
  "trial_index": 1,
  "workspace": "/tmp/agent-memory-benchmark-xxx/workspace",
  "case": {
    "id": "mutation-123",
    "task_type": "diagnosis",
    "task": {"description": "Navigation reaches a missing target."},
    "source": {"before_revision": "abc123"}
  },
  "memory_access": {
    "runtime": "/path/to/tools/agent_memory.py",
    "project": "/tmp/.../workspace",
    "memory_home": "/tmp/.../memory-home",
    "query_command": ["python", "...", "context", "..."]
  },
  "instructions": [],
  "response_schema": {}
}
```

Baseline 请求不包含 `memory_access`。Memory 请求中的临时数据库只从冻结工作区构建，不包含修复后代码。

Runner 响应：

```json
{
  "schema_version": "agent-benchmark-response/v1",
  "case_id": "mutation-123",
  "variant": "memory",
  "trial_index": 1,
  "root_cause_category": "route",
  "predicted_files": ["entry/src/main/ets/pages/Profile.ets"],
  "supporting_files": ["entry/src/main/ets/pages/Index.ets"],
  "investigated_files": [
    "entry/src/main/ets/pages/Profile.ets",
    "entry/src/main/ets/pages/Index.ets"
  ],
  "causal_level": "supported",
  "verification_status": "pass",
  "query_rounds": 2,
  "source_search_count": 2,
  "expansion_trace": [
    {"reason": "missing_caller", "files": ["entry/src/main/ets/pages/Index.ets"]}
  ],
  "stop_reason": "supported_cause_found",
  "evidence_basis": "direct_source_mechanism",
  "mechanism_evidence_files": ["entry/src/main/ets/pages/Profile.ets"],
  "source_file_count": 2,
  "memory_anchor_hit_count": 1,
  "primary_anchor_hit_count": 1,
  "non_anchor_file_count": 1,
  "token_estimate": 1800,
  "model_input_tokens": 1600,
  "model_cached_input_tokens": 400,
  "model_uncached_input_tokens": 1200,
  "model_output_tokens": 200,
  "model_reasoning_tokens": 80,
  "command_count": 3,
  "command_output_bytes": 6400,
  "source_read_count": 2,
  "source_read_output_bytes": 5200,
  "tool_error_count": 0,
  "source_search_miss_count": 1,
  "source_search_error_count": 0,
  "source_read_error_count": 0,
  "other_tool_error_count": 0,
  "cost_metrics_reported": true,
  "elapsed_ms": 22000,
  "summary": "The route target is invalid."
}
```

响应只能包含简短结果，不允许私有推理字段。Runner 应负责把目标 Agent CLI 的输出转换成上述稳定协议。
`predicted_files` 只包含根因或修复归属文件；`supporting_files` 保留用于确认调用链、
边界和反证的辅助文件。两组文件都必须出现在 `investigated_files`，且不能重复。

## 四、直接运行 A/B Benchmark

```bash
python tools/agent_memory.py eval-agent-benchmark \
  --project . \
  --cases /tmp/arkts-mutation-cases.json \
  --source /path/to/arkts-project \
  --runner /path/to/agent-benchmark-runner \
  --runner-timeout 300 \
  --limit 20 \
  --output-responses /tmp/arkts-responses.json \
  --json
```

默认行为：

- 每个案例分别运行 baseline 和 memory。
- 两组使用独立临时工作区，避免修改互相污染。
- Runner 的 cwd 固定为临时工作区，并清除继承的 `AGENT_MEMORY_HOME`。
- Memory 组自动执行临时 `init` 和 `wiki-index`。
- 工作区和临时记忆在单次 Runner 返回后删除。
- 结果写入 `runtime/last_agent_benchmark.json`。
- 有界历史追加到 `runtime/agent_benchmark_history.jsonl`，只保留最近 100 次。

如果 Runner 自己负责构建隔离记忆，可显式添加 `--skip-memory-prepare`。此选项不能用于正式 Holdout，除非 Runner 协议能证明记忆只来自冻结 revision。

### 可信本地 Ollama Runner

仓库提供 `examples/ollama-agent-benchmark-runner.py`，用于在本机 Ollama 中验证完整
`source_excerpts` 是否减少源码搜索和重复读取。它不是 Runtime 的第五个 Skill，也不改变
`tools/agent_memory.py` 唯一运行时入口；它只实现通用 Benchmark Runner 协议。

Runner 强制 `http` loopback 地址，只接受 `localhost`、`127.0.0.0/8` 或 `::1`，启动前
检查 `/api/version` 和 `/api/tags`，并拒绝未安装的模型。Agent 只能调用两个受限工具：
工作区内的字面量 `search_source` 和行窗口 `read_source`。路径逃逸、外部文件符号链接、
超过 2 MB 的单文件、超过 180 行的窗口以及现有搜索/读取/文件预算都会被拒绝。Runner
直接统计工具调用、输出字节、错误、实际读取文件和 Ollama Token，不信任模型自报计数。
工具阶段关闭模型思考模式并限制为 256 个生成 Token；最终结构化响应限制为 512 个，
避免较慢 CPU 上的无界生成占满单次 Runner 超时。
模型返回的 `predicted_files` 和 `supporting_files` 仍用于答案评分，但不会增加 Runner
遥测的 `source_file_count`；该计数只来自实际 `read_source` 和已传给本地模型的当前源码
摘录，避免模型虚构文件被误记为已检查证据。

先在本机自行安装并启动 Ollama、下载一个支持 tool calling 的固定模型，然后执行：

```bash
chmod +x examples/ollama-agent-benchmark-runner.py
export AGENT_BENCHMARK_OLLAMA_HOST="http://127.0.0.1:11434"
export AGENT_BENCHMARK_OLLAMA_MODEL="<installed-model:tag>"

python tools/agent_memory.py eval-agent-benchmark \
  --project . \
  --cases docs/eval/gramony-history-cases.json \
  --source /path/to/frozen/gramony \
  --runner examples/ollama-agent-benchmark-runner.py \
  --allow-drafts \
  --case-id gramony-login-duplicate-submit \
  --trials 1 \
  --json
```

先用一个案例一轮确认协议，再扩大到三个案例三轮。结果应报告
`runner=ollama_local`、`source_boundary=local_process` 和
`source_excerpt_delivery=full`。完整摘录只进入本地模型请求；Benchmark 响应、运行快照和
历史仍只保存聚合遥测与文件名，不保存工具输出或源码正文。模型名、模型摘要/版本、Ollama
版本和硬件条件应随正式 A/B 记录，不能把模拟服务测试当成模型质量结论。
模型还必须先通过最小原生工具探针；只会输出任务复述、无法在生成上限内形成
`tool_calls`、或把无源码结论标为直接机制的模型不能进入多案例测试。小模型通过协议探针
不代表具备 ArkTS 诊断质量，单案例质量或效率门禁失败时必须停止扩大调用矩阵。

## 五、复用已记录响应

为了调试评分器或在 CI 中重复计算，不必再次调用 Agent：

```bash
python tools/agent_memory.py eval-agent-benchmark \
  --project . \
  --cases /tmp/arkts-cases.json \
  --responses /tmp/arkts-responses.json \
  --json
```

响应包格式：

```json
{
  "schema_version": "agent-benchmark-responses/v1",
  "observations": []
}
```

CI 可加 `--fail-on-fail`，当 Memory 组相对 Baseline 回归时返回退出码 1；加
`--fail-on-efficiency-fail` 可在质量通过但效率门禁失败时返回退出码 1。

## 六、重复试验与检索纪律

单次 Agent 执行会受模型采样和工具选择影响。需要评估稳定性时使用：

```bash
python tools/agent_memory.py eval-agent-benchmark \
  --project . \
  --cases /tmp/arkts-cases.json \
  --source /path/to/arkts-project \
  --runner examples/codex-agent-benchmark-runner.py \
  --trials 3 \
  --json
```

`--trials` 范围为 1 到 10。Runtime 对每个案例按 trial 成对执行 Baseline 和
Memory，不复用会话，也不挑选最好结果。每条响应携带 `trial_index`；多轮结果增加：

- `trial_results`：每轮配对分数和 Delta。
- `trial_non_regression_rate`：Memory 不低于同轮 Baseline 的比例。
- `memory_root_cause_consistency`：Memory 根因类别众数占比。
- `memory_predicted_files_consistency`：Memory 文件集合众数占比。
- `average_source_file_count`：Agent 实际检查文件数量。
- `average_memory_anchor_hit_rate`：检查文件与 Memory code anchors 的交集比例。
- `average_primary_anchor_hit_count`：实际检查的主锚点数量。
- `average_non_anchor_file_count`：主/扩展锚点之外的文件数量。
- `average_source_search_count`：源码搜索次数；内置 Codex Runner 优先从 JSONL
  `command_execution` 遥测统计 `rg/grep/find/fd`，并通过
  `source_search_count_source` 标明 `runner_telemetry` 或兼容性的
  `agent_reported` 回退。
- `average_supporting_file_count`：用于佐证但不声明为根因所有者的文件数量。
- `average_expansion_rounds` 和 `reported_stop_reasons`：缺口驱动扩展与停止行为。
- `average_model_input_tokens`、`average_model_cached_input_tokens`、
  `average_model_uncached_input_tokens`、`average_model_output_tokens` 和
  `average_model_reasoning_tokens`：模型成本归因。
- `average_command_count`、`average_command_output_bytes`、
  `average_source_read_count`、`average_source_read_output_bytes` 和
  `average_tool_error_count`：工具成本归因。`average_source_search_miss_count`
  单独记录 `rg/grep` 退出码 1 的无匹配搜索，不把它误判为工具故障。
  `average_source_search_error_count`、`average_source_read_error_count` 和
  `average_other_tool_error_count` 按命令家族拆分其余非零退出。分类表示失败命令的
  家族，不推断失败原因。只保留计数和字节数，不保存命令输出正文。

三轮及以上才标记 `stability_evaluated=true`。质量门禁要求至少三分之二的 trial
不回归，且 Memory 根因类别一致率至少三分之二。单轮仍可作为开发检查，但不能作为
稳定性结论。

内置 Codex Runner 使用 `anchor_first_deterministic_expansion_v8` 检索纪律，并将 Memory
探索组织为 `TRIAGE -> GAP -> VERIFY -> STOP` 状态机。Agent 先检查最高排名的
`role=primary` 锚点，不默认打开所有锚点；只有声明一个合法 evidence-gap reason 才能
检查 `role=expansion` 或非锚点文件。每个文件先读取一个最多 180 行的窗口；仅当 Agent
明确指出尚未解决的证据缺口时，允许同一文件追加一个窗口。一轮最多新增两个文件，
总计最多两轮、七个文件和三次源码搜索。Runner 将本次具体数字直接写入 Memory 提示。
Agent 在每条命令前维护 `searches_used`：复合命令、管道中的每个搜索程序都分别计数；
已知 anchor 路径直接读取。每个实际打开的源码文件写入 `investigated_files`；
`expansion_trace` 只记录缺口原因和最多两个代表文件。Runner 使用
`investigated_files - primary anchors` 确定性派生 `expansion_file_count` 和满足每轮两文件
约束的最小 `expansion_rounds`，不再依赖 Agent 完整复述文件轨迹。只有已检查文件展示
具体机制，且 `mechanism_evidence_files` 至少包含
一个 causal `predicted_files` 所有者时，才能报告 `supported_cause_found`；该列表也可
包含直接支撑机制的 supporting boundary。可能归属或预期行为只能标记为
`inference_only`。预算耗尽时报告不确定性而不是继续扩展。
一旦 causal/repair-owner 文件已经展示足以解释症状的具体机制，并完成必要的约束或
边界确认，Agent 必须停止后续搜索和读取。源码读取放大率由
`average_source_read_count / average_source_file_count` 计算，用于判断重复读取是否下降。
`source_file_count`、锚点命中和非锚点文件数由 Runner 计算，不由模型自报。新 Runner
上报完整探索指标时，任一预算、原因码、证据基础或停止原因违规都会使
`source_exploration_within_budget` 门禁失败；旧响应保持兼容，但不能声明满足该门禁。
v4 至 v8 的内置 Codex Runner 样本都必须提供 `runner_telemetry` 搜索计数；完整
`turn.completed` 遥测且没有命令事件时，Runner 记录实测零搜索，而不是回退到模型自报。
模型自报计数只兼容缺少完整结束遥测的更早响应。v6 的一次读取质量门禁仅用于原始
v6 协议回放；v7 将重复读取转为效率信号，避免把合理的第二证据窗口误判成诊断失败。
v8 的确定性扩展记账只应用于带 `runner_investigated_files` 来源标记的新样本；历史
v4-v7 仍按各自原协议回放。
根因类别优先表达故障领域与因果机制：并行请求、竞态和异步副作用归 `async`；媒体
加载、解码、播放或本地媒体资源访问归 `media`，即使底层机制是 API 误用；只有主要
问题本身是外部或平台 API 契约时才归 `api`。

质量和效率使用独立门禁：

- `quality_gate` 保持原有非回归、稳定性、上下文和探索契约，不因成本变化重写。
- `efficiency_gate` 要求所有 observation 上报成本归因，Memory 的平均 Token 开销不
  超过 Baseline 10%，平均耗时开销不超过 15%，源码搜索次数不回归，平均源码读取
  放大率不超过 2.0 且不高于 Baseline。相同 Token、耗时、搜索和读取规则还必须在
  每个案例独立通过，不能用一个案例的节省抵消另一个案例的回归。
- `promotion_gate` 只有在质量和效率同时通过时才通过。`status` 继续作为
  `quality_gate` 的兼容别名。

内置 Codex Runner 从 JSONL `usage` 和完成的 `command_execution` 事件提取上述指标。
缓存 Token 是输入 Token 的子集，不重复计入 `token_estimate`。Runner 仅写入聚合数值，
不把命令正文、命令输出、源码内容或私有推理写入响应工件。

## 七、评分模型

单次外部 Agent 结果分 `agent_outcome_score`：

```text
40% 根因类别命中
35% 预期文件召回
15% 预测文件精度
10% 因果等级校准
-25% 命中禁止方向
```

同时独立报告：外部 Agent 根因准确率、文件召回与精度、禁止方向命中率、因果校准准确率、验证通过率、平均查询轮数、平均 Token、平均耗时，以及 Context 相对 Baseline 的 `context_uplift`。这些指标评价上下文供给效果，不表示 Runtime 具有诊断能力。

支持上下文成本上报的 Runner 还应返回 `memory_context_bytes` 和
`memory_context_token_estimate`。Memory 样本超过 1,500 token 时质量门禁失败。
内置 Codex Runner 会自动上报；旧 Runner 未上报时保持兼容，但不能据此宣称满足预算。

Development Suite 至少需要一个完整 A/B Pair。Holdout Suite 至少需要 10 个案例，并满足：

- 所有 A/B Pair 完整且不重复。
- Context 组外部 Agent 结果分不低于 Baseline。
- Context 组外部 Agent 根因准确率不低于 Baseline。
- Context 组禁止方向命中率不高于 Baseline。
- 每个案例的 Context 结果分都不得低于其 Baseline，不能用其他案例的提升抵消。

质量门禁只要求非回归；是否达到可发布提升目标，应由项目额外设置更严格阈值。

## 八、案例治理与防泄漏

案例生命周期：

```text
draft -> validated -> holdout
  \-> rejected
```

- `draft` 只用于开发，执行时需要 `--allow-drafts`。
- `validated` 已确认任务、Oracle、revision 和验证路径。
- `holdout` 不参与权重、协议或 Mutation Operator 调优。
- Holdout 失败后先修实现；不能为了通过而静默修改 Oracle。
- 修复 commit、after revision、Oracle 和 Mutation 原始位置不会进入 Runner public case。
- Runner 不应读取冻结 revision 之后的 Git 历史。
- 用户原始日志不写入案例包；只保留经审查的结构化症状和事件。

## 九、维护集成

`maintain-health --json` 返回 `context_capability` 和 `agent_benchmark`。前者报告不调用模型的
系统上下文门禁、锚点/源码摘录召回和失败案例；后者报告外部 Agent 质量、效率、结果
Delta、Token、源码读取放大率和逐案例失败。应先修复系统上下文门禁，再判断 Agent A/B
中的推理、工具规划或模型能力问题。

## 十、当前限制

- 运行时不内置具体 Agent CLI Runner，因为不同 Agent 的调用、权限和 Token 统计方式不同。
- Git 历史任务描述仍需要审查；提交主题不是可靠的用户问题。
- Mutation 第一版只有三类确定性 Operator。
- 当前不自动执行项目测试；Runner 可以执行测试并报告 `verification_status`。
- 质量评分不判断自然语言答案风格，也不使用 LLM 对答案打分。
- 设计案例可以使用同一协议，但高质量设计 Oracle 仍需要人工评审。

## 十一、真实项目试点

仓库已加入 Gramony 的 source-reviewed development 草案和筛选记录：

- `docs/eval/gramony-history-cases.json`
- `docs/eval/gramony-pilot-results.json`
- `docs/gramony-benchmark-pilot.md`
- `examples/codex-agent-benchmark-runner.py`
- `examples/ollama-agent-benchmark-runner.py`

这些案例来自真实 ArkTS 修复历史，但仍保持 `draft`。源代码差异审查不能替代
HarmonyOS 运行环境中的症状复现和验证，因此不得直接作为 Holdout 或发布结论。

内置 Codex Runner 会先在 Runner 进程中执行隔离 Memory 查询，再把结果作为上下文
交给只读 Agent。每次执行使用临时 `HOME/CODEX_HOME`，不继承用户 Skills、
Plugins、规则和历史。诊断样本固定使用 `context --compact`；设计样本使用
`design-context --compact`。如果 compact 结果含 `source_excerpts`，内置 Codex Runner
会在构造外部提示前删除正文，只保留符号、行号、来源和截断元数据，并报告
`source_excerpt_delivery=external_metadata_only`。因此这类运行不能用于证明源码摘录
降低了读取次数。内置 Ollama Runner 可以在强制 loopback 边界内消费完整 compact
结果，并声明 `source_boundary=local_process` 和 `source_excerpt_delivery=full`。
需要精确复现时，可重复传入 `--case-id` 选择固定案例。

## 十二、组合关系泛化观测

第三组 Gramony sealed holdout 在通用 ArkTS 组件属性流完成后冻结，专门检查系统能否从
用户 UI 症状提供叶子组件、父级组合文件和可用源码窗口。首次且唯一一次运行 0/3 通过，
但所有案例仍满足 1,500 Token 预算。聚合结果为：锚点召回 0.5、精度 0.2778、MRR
0.6667、源码区间召回 0.1667。

该结果表明 development fixture 上正确的静态边并不足以证明真实项目泛化。外部 Agent
仍可能收到名称相近的组件而缺少真正控制布局或状态的父级文件；即使目标文件已返回，
源码窗口也可能停在非行为区间。详细不可变结果见
`docs/eval/gramony-context-composition-holdout-result.json`。该案例集不得用于排序调参或重复
验收，后续改进必须使用独立 development 数据，并以新的未见案例判断是否提升。
