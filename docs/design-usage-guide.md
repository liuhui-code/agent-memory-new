# 代码设计能力使用指南

本文说明如何使用 Agent Memory 的仓库级代码设计能力。该能力不会增加新的用户 Skill，仍通过固定四个 Skill 中的 `agent-memory-query` 使用；`tools/agent_memory.py` 下的设计命令是 Agent 调用的稳定后端，也可用于人工检查和 CI。

## 适用场景

适合以下任务：

- 新功能设计、模块拆分和服务边界调整
- ArkTS/TypeScript 状态所有权与页面逻辑重构
- 公共接口、持久化模型和配置结构变更
- 需要比较多个候选方案的技术决策
- 实现前影响分析、实现中进度判断、实现后设计验证

不必用于单行修复、纯文本修改或已经明确实现方式的机械变更。

## 用户如何调用

用户只需用自然语言提出设计任务，并明确希望先设计还是直接推进。例如：

```text
基于当前代码图，为 Profile 页面增加缓存能力。先给设计方案，不要修改代码。
```

```text
为这个需求生成两个结构上有明显差异的候选方案，比较后推荐一个。
```

```text
按选中的设计推进实现，每完成一阶段检查 design-progress，最后验证设计偏差。
```

```text
验证当前修改是否符合原设计；测试报告在 build/test-results.xml。
```

`agent-memory-query` 会按需加载设计协议。用户不需要记忆新 Skill 名称，也不必手写 JSON；正常情况下由 Agent 根据当前代码证据生成临时设计文件并调用运行时。

## 推荐的简单入口

正常使用只需要一句自然语言。Agent 在内部调用：

```bash
python tools/agent_memory.py design-assist --project . \
  --query "为 ProfileRepository 增加缓存，保持 ProfileService API 兼容" \
  --mode design-only --json
```

三种模式对应用户常见表达：

| 用户表达 | 内部模式 | 行为 |
| --- | --- | --- |
| “先设计，不改代码” | `design-only` | 返回推荐方案、必要备选、风险和验证要求 |
| “设计并实现” | `design-and-implement` | 设计检查通过后进入实现和验证闭环 |
| “比较A和B” | `compare` | 只比较存在实质结构或行为差异的候选 |

`design-assist` 自动完成自然语言意图、设计证据和候选无关基线准备，返回紧凑结果：

- `current_design`：当前revision、入口、稳定边界、扩展点和状态所有者
- `design_guidance.forces`：从目标和约束识别的设计作用力
- `existing_patterns`：由当前代码图支持的已有结构模式
- `pattern_candidates`：带前置条件、反条件和必要决策的候选模式
- `principle_checks`：最小设计、依赖方向、状态所有权、信息隐藏和可观测性检查
- `candidate_template`：不包含虚构修改或覆盖声明的Delta模板
- `interaction`：Agent下一步和真正需要用户决策的问题

模式名称不是结论。`candidate` 表示可以进入方案比较，`needs_evidence` 表示结构证据不足，`caution` 表示存在反条件。普通局部修改没有真实变化轴时，返回空模式候选是正确行为。

以下完整工作流主要用于高级检查、CI或调试。正常用户不需要手工执行。

## 完整工作流

```text
学习当前代码
  -> 检索设计证据
  -> 定义设计意图和质量合同
  -> 生成候选无关的设计工作台
  -> 编写一个或多个候选 Delta
  -> 检查和比较候选
  -> 按 Change Plan 实现
  -> 重建设计进度
  -> 验证实际修改
  -> 人工确认后记录紧凑 Outcome
```

### 1. 学习或刷新当前代码

首次使用，或项目代码已经明显更新时，先学习目标范围：

```bash
python tools/agent_memory.py learn-entry --project . \
  --entry entry/src/main/ets/pages/ProfilePage.ets --depth 2 --json
```

也可以学习一个目录：

```bash
python tools/agent_memory.py learn-path --project . \
  --path entry/src/main/ets --json
```

检查 `parse_stats`，确认目标文件、符号、代码日志和语义边已被识别。项目更新后优先刷新既有学习范围：

```bash
python tools/agent_memory.py maintain-refresh-scope --project . --json
```

### 2. 获取设计证据

```bash
python tools/agent_memory.py evidence-context --project . \
  --goal design \
  --query "为 Profile 页面增加缓存，但持久化逻辑不能进入页面" \
  --json
```

阅读顺序：

1. 当前代码和符号证据
2. `repository_model` 的 topology、ownership、behavior、data、failure、runtime、change 视图
3. `architecture_slice` 中的直接关系
4. `evidence_gaps`
5. 历史经验和校准提示

历史经验只能提示风险，不能证明当前代码仍然如此。缺少关系表示证据不足，不表示不存在依赖。

### 3. 定义设计意图

创建临时 `intent.json`：

```json
{
  "schema_version": "design-intent/v1",
  "id": "profile-cache-intent",
  "goal": "为 Profile 查询增加缓存并保持页面职责单一",
  "scope": [
    "entry/src/main/ets/pages/ProfilePage.ets",
    "entry/src/main/ets/service/ProfileService.ets"
  ],
  "exclusions": [
    "不修改登录流程",
    "不把持久化逻辑放入页面"
  ],
  "acceptance_criteria": [
    "重复查询命中缓存",
    "ProfileService 公共 API 保持兼容",
    "缓存失败可定位"
  ],
  "constraints": [
    "页面只依赖服务接口",
    "缓存状态只有一个所有者"
  ],
  "open_questions": [
    "缓存生命周期是否跟随应用进程"
  ]
}
```

字段含义：

| 字段 | 用途 |
| --- | --- |
| `goal` | 要解决的问题，而不是预设实现方式 |
| `scope` | 明确关注范围，可扩展基线但不能替代自动发现的基线 |
| `exclusions` | 明确本次不处理的内容 |
| `acceptance_criteria` | 可观察、可验证的完成标准 |
| `constraints` | 不能违反的边界和兼容要求 |
| `open_questions` | 尚未证实、需要决策的问题 |

### 4. 定义质量合同

复杂设计建议使用 `design-contract/v2`：

```json
{
  "schema_version": "design-contract/v2",
  "id": "profile-cache-contract",
  "intent_id": "profile-cache-intent",
  "goal": "为 Profile 查询增加缓存并保持页面职责单一",
  "constraints": [
    "ProfileService.load API 保持兼容",
    "ProfilePage 不拥有持久化状态"
  ],
  "quality_scenarios": [
    {
      "id": "cache-observable",
      "attribute": "observability",
      "stimulus": "缓存查询完成",
      "environment": "正常运行",
      "artifact": "Profile 查询链",
      "response": "输出一次命中或未命中结果信号",
      "measure": "每次查询恰好一个结果信号",
      "priority": "high",
      "evidence_requirements": ["delta", "repository", "verification"]
    }
  ]
}
```

质量场景应该描述“刺激、环境、对象、响应、度量”，不要只写“性能要好”或“代码可维护”。

### 5. 生成设计工作台

```bash
python tools/agent_memory.py design-prepare --project . \
  --intent intent.json --contract contract.json --json \
  > workbench.json
```

重点检查：

- `baseline_revision`：候选必须基于这个代码图版本
- `anchor_catalog`：可以引用的当前文件和符号
- `relation_vocabulary`：可表达的关系类型
- `synthesis_brief`：当前边界、所有权和风险摘要
- `authoring_gaps`：写候选前必须处理的不确定性
- `candidate_template`：不带实现主张的 `design-delta/v2` 模板

工作台不会自动替用户决定架构，也不会自动声称某个质量目标已经覆盖。

### 6. 编写候选 Delta

候选只描述计划中的结构变化，不保存源码，也不要求记录 Agent 的内部思维过程：

```json
{
  "schema_version": "design-delta/v2",
  "id": "profile-cache-service",
  "contract_id": "profile-cache-contract",
  "baseline_revision": 12,
  "goal": "为 Profile 查询增加缓存并保持页面职责单一",
  "anchors": [
    "file:entry/src/main/ets/service/ProfileService.ets"
  ],
  "add_nodes": [
    {
      "id": "new:ProfileCache",
      "kind": "service",
      "file_path": "entry/src/main/ets/service/ProfileCache.ets"
    }
  ],
  "modify_nodes": [
    "file:entry/src/main/ets/service/ProfileService.ets"
  ],
  "add_edges": [
    {
      "source": "file:entry/src/main/ets/service/ProfileService.ets",
      "relation": "uses_service",
      "target": "new:ProfileCache"
    }
  ],
  "remove_edges": [],
  "assumptions": [
    "缓存生命周期可跟随应用进程"
  ],
  "invariants": [
    "ProfileService.load 签名保持兼容",
    "ProfilePage 不直接访问缓存"
  ],
  "constraint_coverage": [
    "ProfileService.load API 保持兼容",
    "ProfilePage 不拥有持久化状态"
  ],
  "quality_coverage": ["cache-observable"],
  "coverage_evidence": [
    {
      "target_type": "scenario",
      "target_id": "cache-observable",
      "delta_refs": ["new:ProfileCache"],
      "repository_refs": [
        "file:entry/src/main/ets/service/ProfileService.ets"
      ],
      "verification_refs": [
        "profile cache tests",
        "cache result signal"
      ]
    }
  ],
  "verification": {
    "tests": ["profile cache tests"],
    "observability": ["cache result signal"]
  }
}
```

只有存在明显结构或行为权衡时才需要第二个候选。例如：进程内缓存与持久化缓存、修改现有服务与新增独立服务。仅仅改名的方案不算有效候选。

### 7. 检查候选

```bash
python tools/agent_memory.py design-check --project . \
  --intent intent.json --contract contract.json \
  --proposal candidate-a.json --json
```

状态处理：

| 状态 | 含义 | 后续动作 |
| --- | --- | --- |
| `blocked` | 存在结构错误、合同错误或硬规则冲突 | 修改候选，不应开始实现 |
| `review` | 存在假设、证据缺口或警告 | 人工确认或补证据 |
| `clean` | 当前有界检查未发现问题 | 可以比较或进入实现，但不等于设计必然正确 |

还应查看：

- `errors` 和 `warnings`
- `coverage_summary`
- `dimensions`
- `change_plan`
- `historical_risk`，仅作为历史提示

如果出现 `baseline_revision_mismatch`，说明学习图在候选编写后发生变化。重新学习或刷新范围，再从 `design-prepare` 开始，不要简单删除 revision 字段绕过检查。

### 8. 比较候选

```bash
python tools/agent_memory.py design-compare --project . \
  --intent intent.json --contract contract.json \
  --proposal candidate-a.json --proposal candidate-b.json --json
```

重点阅读：

- `recommended_candidate`
- `decision_reasons`
- `tradeoffs`
- `sensitivity_points`
- `selected_change_plan`

比较顺序先看硬错误，再看高优先级质量场景、当前证据、警告、不确定性和变更规模。历史 Outcome 只有至少五条同类人工确认结果后，才可能作为最后的平局提示。

### 9. 按 Change Plan 实现

`change_plan.steps` 是依赖图，不是强制串行清单。没有依赖的步骤可以并行推进。

实现过程中运行：

```bash
python tools/agent_memory.py design-progress --project . \
  --intent intent.json --contract contract.json \
  --proposal selected.json --base HEAD --json
```

步骤状态：

| 状态 | 含义 |
| --- | --- |
| `completed` | 已有 Git、符号、语义或测试证据证明完成 |
| `in_progress` | 新文件存在，但预期 ArkTS/TypeScript 声明还不完整 |
| `ready` | 依赖已完成，可以开始 |
| `pending` | 仍等待前置步骤 |
| `blocked` | 设计门禁、循环依赖、失败测试或过期证据阻断 |

只执行 `next_steps` 中的步骤。`--completed-step` 仅用于需要人工确认的消费者审查或可观测性步骤，不能手工覆盖实现步骤和测试失败。

### 10. 提供测试和编译证据

运行时不会替用户执行测试，但可以读取已有报告：

- JUnit XML
- pytest JSON report
- Jest JSON
- `test-report/v1`
- `compiler-report/v1`

编译报告示例：

```json
{
  "schema_version": "compiler-report/v1",
  "command": "hvigor assembleHap",
  "verifies": ["ArkTS compiles"],
  "diagnostics": []
}
```

高可信验证可使用 `verification-run/v1` 将报告绑定到 Git revision 和文件摘要：

```json
{
  "schema_version": "verification-run/v1",
  "base_revision": "<base commit sha>",
  "head_revision": "<current HEAD sha>",
  "started_at": "2026-07-14T10:00:00Z",
  "completed_at": "2026-07-14T10:01:30Z",
  "source_digests": {
    "entry/src/main/ets/service/ProfileService.ets": "<sha256>"
  },
  "report_digests": {
    "build/test-results.xml": "<sha256>"
  }
}
```

报告路径和摘要路径都相对于项目根目录。绑定内容与当前代码不一致时，证据状态为 `stale`，不能满足验证义务。没有清单的旧报告仍可使用，但会明确标记为 `unbound`。

### 11. 最终验证

```bash
python tools/agent_memory.py design-verify --project . \
  --intent intent.json --contract contract.json \
  --proposal selected.json --base HEAD~1 \
  --test-report build/test-results.xml \
  --test-report build/compiler-report.json \
  --verification-run verification-run.json \
  --json > verification.json
```

结果处理：

| 状态 | 含义 |
| --- | --- |
| `aligned` | 当前有界证据未发现计划与实现偏差 |
| `replan` | 存在缺失变更、计划外变更、API/图偏差、失败测试、过期证据或场景未验证 |

必须阅读 `verification.replan_triggers`，不能只看文件召回率。常见触发器包括：

- `planned_changes_missing`
- `unplanned_files_changed`
- `architecture_gate_failed`
- `planned_symbols_missing`
- `unplanned_exported_api_change`
- `source_graph_delta_mismatch`
- `stale_test_evidence`
- `quality_scenario_not_verified`

### 12. 人工确认后记录 Outcome

只有在人工或上层 Agent 审阅验证报告后，才记录紧凑结果：

```bash
python tools/agent_memory.py design-outcome --project . \
  --verification verification.json --outcome success --json
```

可选结果：

- `success`：设计和实现达到目标
- `partial`：部分达到，需要后续改进
- `failure`：设计或实施未达到目标

Outcome 只保存紧凑指标和校准特征，不保存源码、Diff、测试日志、候选内容或内部推理。同类结果少于五条时不会影响后续候选比较；达到阈值后也只能作为当前证据完全相同时的风险提示。

## 可选项目规则

需要版本控制的硬性架构约束可以放入 `design-rules/v1`：

```json
{
  "schema_version": "design-rules/v1",
  "rules": [
    {
      "id": "service-must-not-import-page",
      "kind": "forbid_edge",
      "severity": "error",
      "source_layer": "service",
      "target_layer": "ui",
      "rationale": "服务层不能依赖页面层"
    }
  ]
}
```

规则必须由项目明确维护。历史经验、日志诊断和 Outcome 都不能自动升级为硬规则。

## 推荐的 Agent 行为

1. 先获取当前代码证据，再提出方案。
2. 小变更只给一个最小候选；存在真实权衡时再给多个候选。
3. 所有未证实内容进入 `assumptions`，不得写成当前事实。
4. 不因图中缺少关系就假定没有依赖。
5. 不用历史经验覆盖当前 exact/static 代码证据。
6. 不跳过 `blocked`，不手工伪造完成状态。
7. 实现时只推进依赖满足的 `next_steps`。
8. 最终以 `design-verify` 的 replan triggers 和测试/编译证据验收。

## 最小使用路径

简单设计任务至少执行：

```text
evidence-context --goal design
  -> design-prepare
  -> design-check
  -> 实现
  -> design-progress
  -> design-verify
```

有多个候选时增加 `design-compare`；需要长期校准时，在人工复核后增加 `design-outcome`。

## 常见问题

### 是否会自动修改代码？

设计运行时本身只读，不会生成或应用 Diff。Agent 可以在用户授权的正常编码流程中根据 Change Plan 修改代码。

### 是否必须使用 ArkAnalyzer？

不是。内置静态 ArkTS/TypeScript 适配器可以完成基础设计检查。可选 ArkAnalyzer Provider 提供更精确的调用、继承、接口和状态证据；不可用时会明确回退到静态分析。

### 是否必须提供两个候选？

不是。没有真实权衡时只写一个最小候选，避免为了比较而制造无意义方案。

### `clean` 或 `aligned` 是否证明设计正确？

不能。它们只表示当前有界证据未发现问题。外部系统约束、未学习代码、运行时行为和需求理解仍需要人工确认。

### 项目代码更新后怎么办？

刷新学习范围并重新运行 `design-prepare`。不要复用旧的 `baseline_revision` 或通过删除版本字段绕过漂移检查。
