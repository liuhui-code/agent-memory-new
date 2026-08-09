# 真实前瞻 Agent 活动就绪审计

## 结论

截至 revision `0a13dc1921c40869dbcd5a8b4deec7c2f36462ad`，结论是 **no-go**：
前瞻 cohort 控制面和 Codex v3 Runner 已经可用，但仓库没有真实连续 ArkTS 任务源，也没有
足以启动真实效能活动的来源、验证和 revision 绑定证据。

该结论只限制 `prospective_real_agent_efficacy_campaign`。它不表示 Runtime 功能失败，也不授权
修改查询、排序、代码图、日志图、经验或 serving 行为。

机器可读结论见
`docs/eval/real-campaign-readiness-audit-2026-08-08.json`。

## 审计问题

本次审计只回答：当前是否已经具备条件，用未来自然到达的真实任务可信地评价
`agent-memory-query` 的采用、质量和成本。

它不评价历史 holdout 分数，也不把以下材料重新分类：

- 生成式 ArkTS fixture；
- 历史 Git 修复；
- 已消费 sealed case；
- 旧的 preloaded-context A/B；
- 没有任务前时间边界的回放结果。

## 方法依据

1. Microsoft ExP 要求实验前冻结可证伪假设、成功指标、数据质量指标和护栏，并根据预期受影响
   比例考虑样本量；活动中不能用提前观察替代预定停止条件。
2. SWE-rebench V2 要求真实软件任务具有可重放环境、可靠测试和实例级混杂标记。
3. SWE-Bench-CL 按时间顺序组织任务，区分连续学习、迁移和遗忘，而不是把无序历史案例视为
   自然任务流。
4. OpenTelemetry 的敏感数据原则要求只采集服务于观察目的的数据，并优先使用聚合或匿名数据。

引用：

- Microsoft, Patterns of Trustworthy Experimentation:
  <https://www.microsoft.com/en-us/research/?p=680556>
- Microsoft, During-Experiment Stage:
  <https://www.microsoft.com/en-us/research/group/experimentation-platform-exp/articles/patterns-of-trustworthy-experimentation-during-experiment-stage/>
- SWE-rebench V2: <https://arxiv.org/abs/2602.23866>
- SWE-Bench-CL: <https://arxiv.org/abs/2507.00014>
- OpenTelemetry sensitive-data guidance:
  <https://opentelemetry.io/docs/security/handling-sensitive-data/>

## 已就绪能力

| 能力 | 状态 | 可证明内容 |
|---|---|---|
| Cohort 控制面 | Pass/Development | 固定数量、连续序号、排除项、时间快照、hash chain、自然观察与有界 replay package 可工作 |
| 数据最小化 | Pass | Cohort SQLite 不保存原始任务、查询、日志、源码或推理 |
| Codex Runner | Pass | Runner 可记录搜索、读取、Token、耗时、Memory 查询和锚点路径 |
| v3 测量合同 | Pass/Calibration only | 生成 L0/L1/L2 能验证协议，不证明真实 Agent 能力 |
| 四 Skill 与 Runtime 边界 | Pass | 无需增加 Skill 或 Agent-specific wrapper |

## 阻塞条件

### 1. 没有真实活动项目

仓库中的 `.ets` 文件位于 `tests/fixtures` 或 `docs/eval/fixtures`。当前可见 Memory Home 配置
只指向本仓库、临时目录和评测 fixture，没有用户指定的持续维护 ArkTS 项目。

**关闭证据：** 用户指定一个正在维护、允许本地学习和评测的 ArkTS 项目路径及负责人。

### 2. 没有连续任务来源

当前不存在未来任务队列、到达边界、队列负责人或“不遗漏任务”声明。内部 hash chain 只能证明
已登记数据没有替换，不能证明操作者登记了全部外部任务。

**关闭证据：** 在首项任务到达前指定任务来源、负责人、开始时间、固定停止规则和预注册排除项。

### 3. 没有客观验证计划

历史案例拥有各自 Oracle，不代表未来自然任务有可执行验证。`source_review` 只能形成审查证据，
不能自动等价为 fail-to-pass 测试。

**关闭证据：** 为任务来源定义允许的 test、build、真实复现或独立用户确认规则；无法验证的结果
必须保留 `unknown`。

### 4. 原始任务只有摘要，没有外部保管规则

Cohort 只保存原始任务 SHA-256，这是正确的数据最小化，但 digest 无法独立证明任务真实性。
没有原始任务保管人、保留期限和审计访问规则时，后续无法复核。

**关闭证据：** 指定 SQLite 之外的本地保管位置、负责人、保留期限和最小审计访问权限。

### 5. Paired 合同已在 Development 层补齐，真实来源仍缺失

`paired_replay` 现在会按冻结的首个 eligible 规则创建字节上限、只读的 task-start Memory
snapshot。回放要求同一 task digest、Git revision/tree、Memory、Query Skill、Runner 和环境摘要；
task/source/Memory 错绑 fixture 均由 `eval-cohort-complete` fail closed。旧 v3 结果不能补绑。

这只关闭评测合同的 Development 缺口，不能证明真实活动的任务来源、连续性或效能。

### 6. 真实活动的指标和声明尚未冻结

生成校准协议不能替代 source-specific 假设。当前也不知道 Memory Opportunity 的自然发生率，
不能拍脑袋选择 20 项并宣称具有统计功效。

**关闭证据：** 先冻结 feasibility 活动的目的和固定数量；它只能估计数据完整性、采用和机会率。
后续效能活动必须使用新的协议，根据独立先验确定样本理由，禁止沿用同一批任务调参与验收。

## 声明矩阵

| 问题 | 证据来源 | 允许声明 | 禁止声明 |
|---|---|---|---|
| 自然采用和可靠性 | Prospective usage trace | 激活、错误、机会率、验证结果关联 | Memory 导致成功或降低 Agent 总成本 |
| 边际质量和成本 | 同 revision 的 v3 paired 结果 | 冻结协议内的结果、搜索、读取、Token 和耗时差异 | 自然采用、跨项目泛化或 promotion |
| 任务真实性 | 外部原始任务和客观验证 | 任务、任务前状态和结果可审计 | digest、seal 或生成 Oracle 自动证明真实 |

源码读取只能证明 Agent 检查过文件，不能证明该证据在隐藏推理中造成最终结论。项目不应为追踪
隐藏推理而保存 CoT 或增加特定 Agent wrapper。

## 启动门禁

只有以下条件全部满足后，才能创建 `evidence_origin=prospective_real_tasks` 的协议：

- [ ] 用户指定活动 ArkTS 项目和任务来源负责人；
- [ ] 到达边界、固定停止和排除原因在首项任务前冻结；
- [ ] 项目已通过 Learn/maintain health，任务前 Memory Home 明确；
- [ ] 原始任务由 SQLite 外部保管，隐私和留存责任明确；
- [ ] 每项任务允许的客观验证方法已定义；
- [ ] dirty 任务只进入 Natural 观察，不绑定 A/B；
- [x] paired v3 结果能够证明 task-start input identities 一致（Development fixture）；
- [ ] feasibility、observational 和 paired 声明边界写入协议；
- [ ] 样本理由和停止规则不依赖活动中间结果；
- [ ] 用户明确允许将冻结源码上下文发送给所选 Agent Runner。

## 当前允许的下一步

唯一允许的下一步是获取并审查 Campaign Source Manifest，至少包括：

- 本地项目路径和项目负责人；
- 任务队列来源和连续性负责人；
- 活动开始边界；
- 任务前 Memory Home；
- 客观验证策略；
- 原始任务保管和保留策略；
- clean revision 与 paired 候选策略；
- Runner、模型、trial 和数据发送授权。

在该 Manifest 缺失前，不创建真实 cohort、不选择任务、不执行 Agent A/B，也不修改 serving。

可从 `docs/eval/campaign-source-manifest.template.json` 创建本地草案。模板是待人工填写的
治理输入，不是活动证据；`status` 保持 `draft_template_only`、占位符未被替换或授权为 false 时，
不得据此创建 cohort。
