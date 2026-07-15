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
  "root_cause_category": "route",
  "predicted_files": ["entry/src/main/ets/pages/Profile.ets"],
  "investigated_files": ["entry/src/main/ets/pages/Profile.ets"],
  "causal_level": "supported",
  "verification_status": "pass",
  "query_rounds": 2,
  "token_estimate": 1800,
  "elapsed_ms": 22000,
  "summary": "The route target is invalid."
}
```

响应只能包含简短结果，不允许私有推理字段。Runner 应负责把目标 Agent CLI 的输出转换成上述稳定协议。

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

CI 可加 `--fail-on-fail`，当 Memory 组相对 Baseline 回归时返回退出码 1。

## 六、评分模型

单次外部 Agent 结果分 `agent_outcome_score`：

```text
40% 根因类别命中
35% 预期文件召回
15% 预测文件精度
10% 因果等级校准
-25% 命中禁止方向
```

同时独立报告：外部 Agent 根因准确率、文件召回与精度、禁止方向命中率、因果校准准确率、验证通过率、平均查询轮数、平均 Token、平均耗时，以及 Context 相对 Baseline 的 `context_uplift`。这些指标评价上下文供给效果，不表示 Runtime 具有诊断能力。

Development Suite 至少需要一个完整 A/B Pair。Holdout Suite 至少需要 10 个案例，并满足：

- 所有 A/B Pair 完整且不重复。
- Context 组外部 Agent 结果分不低于 Baseline。
- Context 组外部 Agent 根因准确率不低于 Baseline。
- Context 组禁止方向命中率不高于 Baseline。

质量门禁只要求非回归；是否达到可发布提升目标，应由项目额外设置更严格阈值。

## 七、案例治理与防泄漏

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

## 八、维护集成

`maintain-health --json` 返回 `agent_benchmark`，包括最近门禁、案例数、外部 Agent 结果 Delta、外部 Agent 根因准确率 Delta 和 Token 节省。最近门禁失败时，维护建议会要求先检查上下文供给造成的 Agent A/B 回归，再继续修改检索、代码图、日志图、关系路径或设计协议。

## 九、当前限制

- 运行时不内置具体 Agent CLI Runner，因为不同 Agent 的调用、权限和 Token 统计方式不同。
- Git 历史任务描述仍需要审查；提交主题不是可靠的用户问题。
- Mutation 第一版只有三类确定性 Operator。
- 当前不自动执行项目测试；Runner 可以执行测试并报告 `verification_status`。
- 质量评分不判断自然语言答案风格，也不使用 LLM 对答案打分。
- 设计案例可以使用同一协议，但高质量设计 Oracle 仍需要人工评审。
