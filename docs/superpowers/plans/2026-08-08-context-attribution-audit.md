# Context 评测归因审计闭环

> 状态：已完成（仅评测控制面；未改变 Runtime serving）

## 目标

将保存的 Development Context 和 Agent A/B 结果整理为可核验的逐例归因矩阵。该矩阵必须区分：

- Oracle 或评测证据是否不完整；
- 候选召回、localizer、紧凑投影和源码摘录的可观察损失层；
- Agent 是否真正利用 Context，或只是存在未绑定的 A/B 观察；
- 可跨独立来源复现的既有边界候选；
- 未知项。

它不重跑已消费产物，不读取或持久化任务正文、源码正文、临时日志或 Agent 推理，也不改变检索、
排序、图、经验、Skill 或 SQLite 数据。

## 设计依据

- [TREC evaluation guidance](https://trec.nist.gov/howto.html)：先冻结测试对象和判定，再解释错误，避免以案例结果反调系统。
- [BEIR](https://arxiv.org/abs/2104.08663)：检索结果应按来源和任务分解，不能以单一聚合分数替代失效分析。
- [SWE-bench](https://arxiv.org/abs/2310.06770)：评测输入、任务和验证边界应可追溯，避免将不一致的 Agent 输出归因给系统组件。
- `docs/evaluation-and-change-policy.md`：首次损失只是观察；必须在独立 Development fixture 和实际公共输出复现后，才能变更 serving；不同层的失败不能拼成同一修复合同。

## 已执行计划

- [x] 审计现有 `context --compact` 结果、evidence funnel、案例谱系和 Agent A/B 聚合。
- [x] 确认已有 evidence funnel 已记录候选、localizer、callable、range、primary 和 compact 阶段，避免再造一套 Runtime 追踪。
- [x] 新增只读 `eval-context-attribution-audit` 门面，保持 `tools/agent_memory.py` 为唯一入口。
- [x] 要求 Context 结果和案例包一一对应，拒绝无来源、重复案例或缺少 revision 的输入。
- [x] 对每个保存输入写入 SHA-256；输出目标不可覆盖，形成稳定审计工件。
- [x] 将 Agent A/B 标为 `unresolved_unbound`，除非它显式绑定相同的 Context 结果摘要；禁止从 “Context 存在” 推断 “Agent 因此改善”。
- [x] 生成六案例 Development 审计工件并加入单元测试。

## 归因规则

| 条件 | 结果 | 可作出的结论 |
| --- | --- | --- |
| 来源 diff 或症状审查缺失 | `oracle_evidence_insufficient` | 先补评测证据；不得把该案例算为任何检索层失败。 |
| `candidate_file=false` | `candidate_recall` | 实际服务观察中，期望文件未进入候选集合。不是某个权重是根因。 |
| candidate 通过但 `localizer_file=false` | `localizer_projection` | 候选进入检索，但局部化集合丢失期望文件。 |
| localizer 通过但 compact primary/anchor 失败 | `compact_projection` | 紧凑投影发生损失。 |
| 锚点存在、源码摘录失败 | `source_excerpt_projection` | 摘录选择或预算层需要独立复现。 |
| Context gate 已通过但 `evidence_primary=false` | `non_gating_evidence_observation` | 该 funnel 信号不是门禁失败，不能作为修复目标。 |
| Agent 结果没有 Context-result digest 绑定 | `unresolved_unbound` | 不可归因 Agent 利用或退化。 |

跨来源重复只会产生 `independent_reproduction_candidate=true`。它仍不是 repair authorization；只有同一既有边界在项目无关 fixture 和正式 `query_handoff` 中复现，才允许设计最小机制修复。

## 首次审计结论

工件：`docs/eval/context-attribution-development-audit-2026-08-08.json`。

- 3/6 为 `candidate_recall`，覆盖 Moonlight 与 NGA 两个仓库。
- 2/6 为 `localizer_projection`，覆盖 Moonlight 与 Legado 两个仓库。
- 1/6 Context gate 通过，但仅有非门禁 `evidence_primary` 信号。
- 所有六个 A/B Memory 臂都报告了 Context，但没有与三份 Context 结果建立 digest 绑定，Agent 利用保持未决。
- 因而没有 serving 或架构修改授权；更不应按项目名、文件名、关键词或 Oracle 做局部补丁。

## 后续阶段

1. 为 `candidate_recall` 建立一个项目无关 Development fixture，先复现实际 `query_handoff` 缺失，再检查现有 candidate fusion 边界。
2. 为 `localizer_projection` 建立另一独立 fixture，证明候选存在而 serving localizer 丢失目标；不得复用同一项目或 Oracle 词汇。
3. 每个 fixture 分别跑 focused 回归、完整 Context gate、性能和 500 行检查。
4. 只有两个独立缺陷类别指向同一个现有边界时，写出最小修复合同；否则记录分歧并停止，不扩张架构。
5. 使用未参与开发的新来源进行一次性验证；没有合格来源时结论停留在 Development。
