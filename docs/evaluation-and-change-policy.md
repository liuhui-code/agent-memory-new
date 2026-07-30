# 评测与能力改动强制政策

## 目的

本政策约束查询、代码图、日志图、因果路径、语义提取、源码摘录和能力评测的后续改动。
目标是防止案例驱动的单点修补、指标调优、架构漂移，以及把结构完整的测试误认为真实有效的
外部验证。

这是仓库级强制规则。`AGENTS.md` 引用本文件，后续实现、测试、计划和结果解释均不得绕过。

## 系统边界

- Runtime 只负责检索、排序、关联、压缩和返回可核验上下文。
- 本地 Agent CLI 负责形成假设、诊断根因、判断真实调用路径、设计方案和验证结论。
- 代码图、日志图、经验和因果路径都是证据，不是 Runtime 生成的诊断结论。
- 临时用户流水日志由 Agent 读取和推理，不因评测需要扩张为 Runtime 诊断接口。

## 证据纪律

禁止制造或推测以下内容后再把它们写成真实案例事实：

- 未在 issue、复现记录、测试、源码或真实运行材料中出现的日志文本；
- 未被来源材料支持的用户症状；
- 仅因代码位置相邻而推定的因果关系；
- 把声明位置、文件范围或修复 diff 自动当成真实执行路径；
- 为满足案例数量、类型覆盖或门禁格式而补造的 Oracle。

无法获得直接证据时，案例只能标为探索性观察。未知项必须保留为未知，不能由评测作者补全。

## 评测等级

### 探索性观察

用于形成假设，可以来源于静态审计、不完整历史或 shadow 输出。不得用于：

- 宣称系统提升或退化；
- 修改生产排序、阈值或架构；
- 发布晋级；
- 对外称为 holdout、外部门禁或泛化验证。

### Development

用于稳定复现一个已知机制。必须独立、最小、可审查，并能在实际服务输出中观察到缺陷。
Development 可以驱动实现，但不能证明外部泛化。

### Calibration

用于冻结阈值和覆盖分层。它验证度量与决策边界，不替代案例真实性审查。

### Holdout

只有同时满足以下条件才能称为 holdout 或 external gate：

1. `governance.evaluation` 已分类并通过强制校验；
2. split 为 `holdout`、change policy 为 `sealed`、source isolation 为 `external_holdout`；
3. 每个案例具有真实来源谱系和明确的独立性依据；
4. 症状、日志、修复和 Oracle 均有可追溯依据；
5. 已在运行前冻结，且未参与实现、查询措辞、权重、阈值或 Oracle 调整；
6. 只执行预先声明的次数，消费后不得修改、调参或重跑。

`legacy_unclassified` 或 `enforced: false` 的案例无论文件名、suite、review status 或 seal 如何，
都不是合格 holdout。

### 谱系分类

- `development` 和 `calibration` 可以通过 `governance.evaluation.lineage_defaults` 继承同一批
  已审查 fixture 的 `source_family` 与 `independence_basis`，运行结果必须标为
  `lineage_mode: pack_defaults`。
- `holdout` 禁止继承包级谱系；每条案例必须显式声明来源族和独立性依据，避免用一个宽泛声明
  掩盖案例级污染、缺证或来源重叠。
- 只能分类仍参与活动门禁且来源可验证的案例包。已执行、已消费或历史密封的未分类产物保持
  `legacy_unclassified`，不得事后补标签获得晋级资格。
- 文件名包含 `calibration`、`holdout` 或 `sealed` 不构成分类依据；必须由治理元数据和验证器
  共同决定。

## Seal 与 Calibration 的边界

- Seal 证明内容在冻结后未变化，并不证明症状真实、Oracle 正确或修复具有因果性。
- Calibration 证明类型与分层覆盖，并不证明单个案例有效。
- `source_diff_reviewed: true` 是审查声明，不是审查质量本身。
- 三者不得相互替代，也不得被合并解释为“案例已被证明真实”。

### 执行前封印门禁

- `eval-context-capability` 和 `eval-agent-benchmark` 必须在选择案例、访问目标源码、调用
  Runner 或使用 Oracle 评分前拒绝未分类或未通过必需 seal 验证的 holdout。
- `eval-seal-cases` 是唯一允许读取未封印 holdout 的评测入口；它只负责源码 revision、声明
  变更文件和规范摘要审计，不执行 Context 或 Agent。
- 未封印草案可以继续接受人工源码审查和元数据修正，但不得通过 `--limit`、`--case-id` 或
  其他局部执行参数绕过门禁。
- 一旦任何 Context 或 Agent 评测实际执行案例并使用 Oracle 评分，该案例即视为已消费；不得
  事后补 seal 获得 holdout 资格。

## 能力通过与晋级资格

- `system_context_gate=pass` 只说明当前案例的上下文供给满足 Oracle。
- `promotion_eligible=true` 还必须满足治理已强制分类、split 为 `holdout`，且 seal 已验证并为必需。
- Development 和 calibration 结果即使全部通过，也不能直接进入 Agent A/B 晋级链。
- 未分类能力集通过后，`next_gate` 必须是 `classify_evaluation_pack`，不能是
  `paired_external_agent_ab`。
- `--fail-on-fail` 检查系统能力和必需的 calibration 门禁，不因 development 缺少外部晋级资格
  而失败。
- `promotion_policy.reasons` 必须解释未晋级原因；禁止用 `status=pass` 掩盖治理缺口。

## 改动决策规则

### 修改服务行为

必须同时满足：

1. 独立 development fixture 可以稳定复现；
2. 缺陷出现在实际 `query_handoff` 或其他正式公共输出，而非仅存在于 shadow/audit 数据；
3. 能定位到候选生成、召回、融合、选择、压缩或源码读取中的具体失败层；
4. 修复使用通用机制，不包含项目名、文件名、案例措辞或 Oracle 特例；
5. 既有完整门禁、性能门禁和文件行数门禁无新增回归。

### 修改评测器

只有在评测器错误判断一个预期结果已知的受控案例时才允许修改。不得因为真实项目分数低而
放宽 Oracle、指标、阈值或失败条件。

### 修改架构

只有至少两类相互独立的缺陷都指向同一个缺失契约时，才允许增加或调整架构抽象。单个案例、
单个指标或单个项目不能证明架构缺口。优先复用现有 Port、Adapter、Provider 和证据模型。

## Shadow 与指标解释

- `mode: shadow`、`serving_candidates_changed: false` 和 informational 指标只用于诊断观察。
- Shadow 阶段首先丢失证据，不等于正式服务链也首先在该阶段失败。
- 聚合分数下降必须先分解到具体案例、阶段和最终 Agent 可见上下文。
- 系统 Context 门禁只评价上下文供给，不评价 Agent 是否能诊断。
- Agent A/B 才评价 Agent 是否利用上下文改善任务结果，两者不得混写。

## 强制工作流

每次能力改动按以下顺序执行：

1. 写清用户可见失败和当前证据，不先写解决方案。
2. 标记证据等级，区分事实、推断、shadow 观察和未知项。
3. 在独立 development fixture 中复现实际公共输出缺陷。
4. 使用审计信息定位首次可证明的服务失败层。
5. 检查现有抽象是否已经表达该能力。
6. 实现最小的通用机制修复。
7. 运行聚焦回归、完整能力门禁、性能门禁和 500 行门禁。
8. 使用未参与调优的新来源做一次性外部验证；没有合格来源时停止在 development 结论。
9. 分别记录已证明、未证明和下一步证据缺口。

## 停止规则

出现以下任一情况必须停止实现并记录证据缺口：

- 不能证明问题影响正式服务输出；
- 不能区分评测器错误与系统错误；
- 只能通过项目、文件、关键词或 Oracle 特例提高分数；
- 来源不足以证明日志、症状或因果关系；
- 修复需要依据已消费 holdout 调整权重、查询或阈值；
- 新抽象只解释一个案例，尚无第二类独立缺陷；
- 失败层仍未知，只能继续增加遥测或功能进行猜测。

停止不是失败。此时正确产物是明确的未知项、可复现条件和下一次需要收集的证据。

## Link My Harmony 追溯说明

`docs/eval/link-my-harmony-log-owner-unseen-holdout-*` 已冻结并执行，不修改历史文件，也不重跑。
但其治理结果为 `legacy_unclassified` 且 `enforced: false`，部分运行日志和因果关系缺少直接来源
支持。因此该结果永久降级为探索性观察：可以保留用于提出假设，不能作为外部晋级门禁、查询
退化证明或架构改动依据。

其中发现的 128 callable 全局截断、4,000 行机制扫描边界和属性流缺口都只是待验证假设。
必须分别进入独立 development fixture，并在正式 `query_handoff` 中复现后才能驱动实现。

## 提交前检查

- [ ] 没有制造日志、症状、因果关系或 Oracle。
- [ ] 案例等级和治理状态与文档表述一致。
- [ ] 服务改动由独立 fixture 和正式输出复现支持。
- [ ] Shadow 结果未被当成发布证据。
- [ ] 没有使用已消费 holdout 调参。
- [ ] 架构改动有至少两类独立缺陷支持。
- [ ] 结论区分系统 Context 能力与 Agent 推理能力。
- [ ] 已满足停止规则或记录未解决证据缺口。
