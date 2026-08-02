# 真实任务 Context 价值闭环计划

## 目标

验证 Agent Memory 在新的真实 ArkTS 故障中，能否向本地 Agent CLI 提供紧凑、可核验且有增量价值的上下文。Runtime 只检索、关联和压缩证据；Agent 负责读取临时日志、形成候选原因、推断调用链和验证结论。

## 已证明的缺口

- Termony 的五文件 Oracle 超过 compact 的四代码锚点上限，不能作为单轮通过契约。
- Sherpa 的 ArkTS 入口能够召回，但 native caller、C API 和构建证据仍在候选或组合阶段丢失。
- 两套资产均为已观察的 `legacy_unclassified` development 数据，不能继续调优或证明推广。
- 现有 `query_variants` 只能改变措辞并共享 Oracle，不能表达“首轮定向”和“单候选聚焦”应返回不同证据。

## 方法依据

- TREC Session Track 将检索评价放在多轮搜索会话中，而不是要求首轮一次返回全部证据：<https://trec.nist.gov/data/session.html>。
- BEIR 与 TREC 的分层检索实践要求区分候选生成、排序和最终选择，缺失候选不能由末级调权补回：<https://arxiv.org/abs/2104.08663>、<https://trec.nist.gov/howto.html>。
- RAGAS 将检索供给与生成结果分开评价；本项目对应 Context gate 与 Agent A/B 两层：<https://arxiv.org/abs/2309.15217>。
- 所有执行服从 `docs/evaluation-and-change-policy.md`，不得制造日志、修改已消费 holdout，或从 shadow 观察直接改变 serving。

## 长期协议

一个真实任务保留一个基础 Oracle，供最终 Agent A/B 评价。Context gate 可在 `query_variants` 中声明：

- `investigation_stage: orientation`：首轮只要求日志关键词、入口或主要组件等定向证据；
- `investigation_stage: focused`：Agent 已抽取一个候选原因后，只要求该候选对应的实现、边界或配置证据；
- `oracle_override`：只覆盖本轮的 `expected_files`、`forbidden_files` 和 `context_requirements`，不改变来源、revision、根因类别或最终 Agent Oracle。

分阶段结果必须分别报告，并且所有声明阶段均通过后，场景 Context gate 才能通过。未声明 stage 的既有 wording variants 保持原语义和兼容性。

## 新外部来源

只使用此前未出现在仓库评测资产中的公开源码族：

1. `asasugar/HPRichText#36`：HTML parser 对缺失子节点直接 `push` 导致崩溃；修复提交 `8ad85b85b542a69a5d3d5099bc249805cb11a00f`。
2. `751496032/DSBridge-HarmonyOS#5/#7`：未定义 native 方法或非法方法名通过 `throw` 使应用退出；修复提交 `f83458f9b074271b785ab01903d34a763e38cd66`。
3. `Chenlvin/Melotopia-HMOS`：横屏播放器歌词不更新；修复提交 `eb4ff38f7f7615f820da80c9d59c9587c0803afb`。

每个来源独立冻结 before/after revision、changed files、公开症状、源码范围和来源谱系。原始用户日志不写入记忆。

## 执行阶段

1. [x] 用受控测试证明共享 Oracle 会误判分阶段查询，并实现通用评测协议。
2. [x] 冻结三个来源的案例包，执行 seal 前源码 diff 和文件审查。
3. [x] 执行 model-free Context gate 并记录首个证据损失层；Melotopia 因后台会话被误启第二次，按治理规则失效并保留审计记录。
4. [x] Context gate 失败后停止 serving 修改；两个有效来源指向不同首损层，不满足架构变更所需的共同缺失契约。
5. [x] HPRichText 与 DSBridge 均未通过 Context gate，Agent A/B 按协议跳过；未请求或使用外部模型披露。
6. [x] 运行评测链路完整回归、CI 规模性能、四 Skill、JSON、diff 和 500 行门禁。

## 验收

- 分阶段 Oracle 不改变既有 case pack 和 Agent A/B 基础 Oracle。
- 报告可区分 orientation 与 focused 的通过率和缺失证据。
- 新案例来源真实、revision 不可变、谱系明确、seal 可验证。
- 不包含仓库名、文件名、issue 文本或 Oracle 特例的 serving 代码。
- Runtime/Agent 边界、四个 Skill、1500 Token、SQLite source of truth 和 500 行限制保持不变。

## 执行结论

- HPRichText：`orientation` 失败、`focused` 通过，平均 1,186.5 Token。候选文件和文件定位完整，首个可证明损失位于最终 compact 证据组合。
- DSBridge：两个阶段均失败，平均 1,467.5 Token。候选文件与文件定位存在，但 class-field arrow 实现未进入 callable/range 证据，首损位于 callable 定位。
- Melotopia：sealed pack 被重复执行，整个来源按 `duplicate_holdout_execution` 失效，指标不得解释、调参或用于晋级。
- 两个有效来源未证明同一个架构缺口，因此本阶段只交付分阶段评测契约和审计闭环，不修改 serving。
- 详细结果见 `docs/eval/staged-context-value-closure-report.md`。

## 验证

- 分阶段协议、case seal、revision 治理、工作区隔离、证据漏斗、源码区间、历史持久化和 runner 共 98/98 通过；最小聚焦门禁为 36/36。
- 仓库 167 个非运行时 JSON 全部可解析，Python 在 `/tmp` 字节码缓存下编译通过，`git diff --check` 通过。
- Skill 目录仍严格为 `learn`、`query`、`reflect`、`maintain` 四个；`tools/` 和 `tests/` 没有超过 500 行的 Python 文件。
- CI 规模门禁第二次独立运行通过：100,000 searchable entities、300,000 edges，所有查询计划通过；500 方法增量 P95 为 4,977.561 ms。第一次运行在 Scope 外变更和 500 方法文件上分别超阈值 2.9% 与 6.5%，记录为临界性能抖动，不据此修改架构。
- 全仓串行套件进入既有高成本 `test_agent_memory_part_12` 后因吞吐过低人工中止；中止前未观察到失败。最近完整基线保持 829 项执行记录，本次不将中止运行表述为完整通过。
