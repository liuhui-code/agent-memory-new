# Context 评测归因审计使用指南

`eval-context-attribution-audit` 是评测控制面命令。它读取已经保存的 Context 结果、对应案例包和可选的 Agent A/B 结果，生成一个不可覆盖的 JSON 审计矩阵。

它不会查询项目、重建索引、运行 Agent、写 SQLite、读取源码或推理根因。四个用户 Skill 不变。

## 何时使用

当 Development Context gate 或 Agent A/B 失败时，先使用本命令拆开失败层，再决定是否值得建立一个新的独立 Development fixture。

不要将它用于：

- 已消费 sealed holdout 的重跑或调参；
- 直接修改 candidate 排序、localizer 预算或 compact 截断；
- 证明 Agent 已经利用了 Context；
- 根据项目名、文件名或 Oracle 形成局部修补。

## 命令

每个 `--context-result` 必须按同一顺序对应一个 `--case-pack`。目标文件必须不存在，防止覆盖审计结论。

```bash
python tools/agent_memory.py eval-context-attribution-audit \
  --project . \
  --context-result docs/eval/moonlight-context-utility-development-result.json \
  --case-pack docs/eval/moonlight-context-utility-development-cases.json \
  --context-result docs/eval/nga-context-utility-development-result.json \
  --case-pack docs/eval/nga-context-utility-development-cases.json \
  --context-result docs/eval/legado-context-utility-development-result.json \
  --case-pack docs/eval/legado-context-utility-development-cases.json \
  --agent-result docs/eval/context-utility-agent-ab-result.json \
  --target docs/eval/context-attribution-development-audit-YYYY-MM-DD.json \
  --json
```

## 输出解释

- `input_artifacts`：输入文件名和 SHA-256。先核对摘要，再引用结论。
- `cases`：每例的来源仓库、revision、Oracle 审查状态、实际 Context 状态、观察层和失败检查项。
- Oracle 的 source diff 或 symptom 审查不完整时，`observed_layer` 固定为
  `oracle_evidence_insufficient`，不会被统计为检索失败或边界候选。
- `observed_layer`：候选、localizer、compact、摘录、非门禁信号或未知。它描述观察点，不声称根因。
- `agent_utilization`：如果 Agent 结果没有当前 Context 结果的 digest 绑定，则为 `unresolved_unbound`。即使 `memory_context_present=true`，也不能把 Agent 成败归因到该 Context 结果。
- `boundary_hypotheses`：相同观察层跨两个来源仓库出现时，只标记为 `independent_reproduction_candidate`。
- `policy`：永远显式说明此审计不授权 serving 或架构修改。

## 审计后的决策

1. 同一层跨独立来源重复：为该层建立新的项目无关 Development fixture。
2. 不同层混合：分别验证，不合并成“整体 ranking 问题”。
3. Case gate 通过但 funnel 有失败：视为非门禁或 Oracle 投影信号，先检查评测契约，不改服务。
4. Agent 结果未绑定：记录为未知；下一轮实验应在运行时显式记录 Context-result/payload digest。
5. 无法独立复现公共 `query_handoff`：停止实现，保留证据缺口。

完整设计、理论来源和当前六案例结论见 `docs/superpowers/plans/2026-08-08-context-attribution-audit.md`。
