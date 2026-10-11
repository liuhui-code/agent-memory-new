# 规范性上下文：ADR 与 Feature Spec 契约及最小接入

状态：已按用户授权编写最小 Runtime 接入；未执行验证，文档批准仍须依据真实来源
日期：2026-10-11

实施前核对基线：`9f7bed27ff4a754b503d5e457584908ba9eea6c0` 的代码与已跟踪文档。用户于 2026-10-11 明确要求“跳过验证步骤，根据上述文档，从理论上完成优化项目”；本次据此编写最小接入代码，未执行测试、性能门禁、真实活动就绪审计或效能评测。

## 目的与边界

本文件区分当前任务意图、已批准架构决策、已批准需求和历史经验，并记录规范性文档最小接入的理论设计与本次实现。它不是具体项目的已批准 ADR、Feature Spec 或功能验收记录，不证明接入后 Agent 效能会提升。

Agent Memory 的职责仍是向本地 Agent CLI 提供有来源、时效和缺口标注的项目上下文。Agent 阅读当前源码、用户材料和临时流水日志，负责问题定位、设计推理及验证。对外维持固定四个 Skill、`tools/agent_memory.py` 单一入口、SQLite 事实来源和 Obsidian 生成镜像；不引入平行数据库或自动决策器。

本契约沿用 [`agent.md`](../agent.md)、[MVP 实施计划](mvp-implementation-plan.md)、[`Design Context Provider`](superpowers/specs/2026-07-16-design-context-provider.md) 和[上下文供给边界](context-provider-boundary.md)。既有设计文档已把“接入被接受或被取代的 ADR”列为长期阶段，本文细化其可信度、适用条件与验证门槛，并按本次用户授权实现最小接入。常规[评测与变更政策](evaluation-and-change-policy.md)的证据要求仍保留，本次跳过验证不代表门禁已满足。

## 实施前核对结果

| 主题 | 基线内可确认的项目事实 | 对接入建议的判断 |
|---|---|---|
| 存储与检索 | SQLite 是事实来源；已有 [FTS5 索引](../tools/agent_memory_runtime/storage_search_schema.py)、代码/日志关系与经验治理实现 | Embedding 存储或独立 Graph 数据库不能当作现状 |
| 设计上下文 | [`design-context/v1`](../tools/agent_memory_runtime/design_context.py) 已提供源码锚点、当前任务约束、语义纠正、设计知识、历史警告与证据缺口 | 不需要另建“先查总账，再查 ADR，再查 Memory”的固定入口 |
| 经验治理 | 冲突、覆盖、时效与评估已有机制 | `memory_save`/`memory_update` 不是本项目公开 Runtime API，不能据此重建治理 |
| 规范性文档 | 现有设计规范与政策可直接读；当前 `project_context` 返回任务约束、语义纠正和记忆证据，尚无经批准文档的独立接入与权威状态校验契约 | 自动检索属于待验证的能力缺口，不等于现有 serving 已发生缺陷 |
| 效能证据 | 既有[真实前瞻活动审计](real-campaign-readiness-audit.zh-CN.md) 记录 no-go，审计 revision 与本次核对基线不同 | 历史就绪结论不能充当本次审计或规范性文档接入的收益证据 |

旧[机器可读审计](eval/real-campaign-readiness-audit-2026-08-08.json) 绑定日期 `2026-08-08` 与 revision `0a13dc1921c40869dbcd5a8b4deec7c2f36462ad`；中文审计文档后续记录 paired 合同已在 Development 层补齐。这两种记录有不同的时间与证明范围，不能合并为一次新的审计。恢复真实活动仍须按现有门禁审查 Campaign Source Manifest；本文没有关闭任务来源等外部缺口的证据。

原研究报告正文及案例、指标的出处未纳入本次可核验材料。原草稿转述的 Issue `#1038`、`coding-memory/scale-test`、Top-1 40% 对 10% 等条目均保持“未核验”，不能成为本项目事实、验收基线或门禁；缺少来源也不足以断言它们是虚构。本文不采纳“先造 10 个 ADR 和 5 个 Feature 条目”的固定数量回填建议，应只记录有可追溯来源的真实决策和需求。

## 概念与权威边界

| 信息类型 | 回答的问题 | 来源与生命周期 | Agent 用法 |
|---|---|---|---|
| 当前任务意图 | 这次用户要什么、不能做什么、怎样验收 | 当前对话；默认临时，不自动入库 | 直接约束本次工作；冲突时先向用户澄清 |
| 当前源码与运行观察 | 现在实际怎样工作 | 源码、测试、构建输出、用户临时日志；带 revision/时间 | 核实现与复现；观察不自动证明设计意图 |
| ADR | 为什么选这个架构、替代方案和后果是什么 | Git 中经审查的决策文档；保留批准证据与显式取代关系 | 仅 `accepted`、批准可追溯且适用当前范围时作为项目约束；`proposed` 不具约束力 |
| Feature Spec | 预期能力、范围、不变量、验收场景是什么 | Git 中经需求方/维护者批准的稳定规格；版本化 | 用来检查设计与实现偏差；不能替代当前源码事实 |
| 业务语义与纠正 | 项目术语和业务含义怎样解释 | 现有 Memory 来源、scope 与验证机制 | 已确认与待核纠正使用不同权威等级；均须核对当前源码和适用范围 |
| 历史经验 | 过去什么有效、失败或需警惕 | 现有 Memory 治理与来源机制 | 提醒核查；不凭相似度覆盖当前用户约束、当前源码或已批准规格 |
| Feature Ledger | 哪些规格存在、状态如何 | 可由规格/Issue 生成的可选索引 | 仅导航；不复制验收条件形成第二事实来源 |

本文沿用现有 [`authority_order`](../tools/agent_memory_runtime/design_context.py) 与[设计使用指南](design-usage-guide.md#41-authority_order)：

```text
当前任务明确约束
  > 当前源码、测试和编译结果
  > 已确认项目决策或业务纠正
  > 当前派生代码图
  > 尚待源码确认的语义纠正
  > 已验证项目经验
  > 通用设计知识
  > 未验证历史观察
```

本次实现不调整这个顺序。新增 `normative_context` 提供独立标注的文档引用，批准字段仅是原文声明，须由 Agent 核查后才能作为适用项目约束。Agent 读到已批准 Feature Spec 与当前代码矛盾时，应分别注明“预期契约”和“实际行为”：源码用于核实实际行为，规格用于提出待验证的偏差。不能用规格否认当前事实，也不能仅凭实现现状认定规格已经失效。Agent 继续核查负责人、批准版本、当前 revision 和测试，区分实现偏差与规格过期；Runtime 不自动裁决。

已被取代、撤销或拒绝的 ADR/规格可用于解释历史，不能作为当前硬约束。文件名、Git 提交、状态标签或本次文档修订都不自动证明批准；批准来源无法核验的文档只作为待核材料。

JTBD 可以帮助需求方表述用户在什么情境下要达成什么结果，但不是记忆表结构、因果证据或检索评分。MoSCoW 只服务于具体计划窗口的优先级讨论，不应改变查询相关性和权威性。不要把 Sprint 任务进度混入稳定 Feature Spec；必要时保留到现有任务管理系统。

## 建议的轻量文档契约

真实变更试用阶段优先使用 Git Markdown，不为了凑数预创建空目录或大量示例。本次最小接入增加独立的 SQLite 派生表，但没有生成实际 ADR、Feature Spec 或批准记录。

- **ADR 触发**：出现跨模块边界、持久化契约、兼容性、安全或显著质量属性取舍时，由维护者提出；普通实现细节不建 ADR。至少包含背景、决策、替代方案及取舍、后果、证据、适用范围、负责人和状态。缺失的决策依据保持未知，不回填猜测。
- **Feature Spec 触发**：用户需要长期稳定的行为、不变量或验收场景时提出草案，由需求方确认后才批准；一次性任务意图不升级为规格。至少包含适用范围、行为/非目标、可验证验收、负责人、状态、相关 ADR 与已有源码/测试引用。尚未实现的内容可注明缺口。
- **批准与验收**：现行文档需记录批准人、日期和可追溯的评审或明确确认记录。批准说明决策或需求被接受，不说明功能已实现或验收通过；验收结果须另有源码 revision、验证方法和结果依据。
- **状态与修订**：至少区分草案、现行、取代和撤销/拒绝，并写清文档体系已有状态的含义；ADR 可沿用 `proposed`、`accepted`、`superseded`、`deprecated`。状态变更需审查，取代文档需链接新旧双方及适用范围。Git 路径、revision 与内容摘要用于溯源；批准后改变实质约束需重新审查，不能自动继承旧批准。
- **避免双写**：规范原文及其批准依据以受审查的 Git 文档为准；SQLite 仍是 Runtime 记忆和机器可读记录的事实来源。本次派生记录保存有界源文快照及其来源、批准声明与版本信息，随学习刷新，不独立编辑规范或反向批准 Git 文档。具体字段见下文最小实现；其适用性尚未经阶段 3 的验证。Obsidian 仍只是生成镜像，不承担批准流程。

这些文档要求继续区分批准声明与实际验收。本次最小派生 schema 见下文；“将 ADR 全文作为普通经验写入 Memory”和“从代码自动生成已批准特性”会混淆证据与权威，不采用。

## Agent 使用流程

1. 从用户当前问题建立临时任务意图：期望结果、可观察现象、约束、排除项、验证方法和未知项。缺失信息保持未知，不自动持久化。
2. 按任务类型有选择地使用现有 `context` 或 `design-context`。精确的局部问题可先读源码；设计问题用设计上下文，日志问题由 Agent 自己阅读临时日志并查询相关锚点。
3. 仅当查询涉及稳定产品契约或架构取舍时，读取已有上下文输出中的 `normative_context`，并打开引用的原始 Git 文档，核对批准依据、适用范围与取代关系。未索引的文档可直接读或通过现有 Learn Skill 学习。记录所读版本及当前源码 revision；未提交修改还需记录内容摘要，并单独核查修改内容是否已获批准。
4. 由 Agent 输出候选、反证、权衡、实施及验证。Runtime 检查文档字节新鲜度、Git 路径状态和元数据完整性，不认证批准人、审查质量或规格符合性，也不选择方案或诊断根因；旧设计命令的适用边界遵循[现有 Query Skill 协议](../skills/agent-memory-query/references/code-design.md)。
5. 若任务实际改变了批准规格或架构决策，由相应负责人通过代码评审更新文档；经验仍按现有反思和维护流程治理，不与规范性文档自动双向同步。

## 分阶段验证与接入门槛

下表保留常规证据推进路径。本次用户明确要求跳过验证、按理论实施，是当前任务的实施授权；它不把缺失的前置证据补成事实，也不改变后续评测分类、holdout 消费纪律或收益声明规则。

| 阶段 | 交付与检查 | 进入下一阶段的条件 |
|---|---|---|
| 0. 文档 | 本文件厘清类型、边界和来源；不改 serving | 维护者认可文档契约与审查责任；本次修订不自动完成批准 |
| 1. 真实变更试用 | 未来自然到达的任务中，仅在触发条件成立时记录真实 ADR 或 Feature Spec；批准依据与验收结果分别记录 | 有可审查的维护记录与 Agent 使用记录，没有重复事实来源；不足则停止 |
| 2. 上下文缺口验证 | 从真实试用形成假设，再在独立 Development fixture 中复现现有供给契约遗漏的关键约束；保存 `context` 的实际 `query_handoff` 或 `design-context/v1` 正式输出，并核查源码与批准版本 | 按评测政策定位具体失败层；仅缺少尚未承诺的自动文档检索只算能力缺口 |
| 3. 最小派生接入评审 | 优先复用现有入口、Provider/Adapter 和证据模型；仅在至少两类独立缺陷指向同一缺失契约时，评审是否需要 Git 文档适配及派生索引 | 按政策通过回归、完整能力、性能与 500 行门禁，验证来源/批准/范围/过期/取代行为；外部验证与结论等级合规 |
| 4. 效能评估 | 先冻结合规任务与测量协议，再在同任务、源码 revision、模型、预算和停止规则下比较上下文使用的质量与总成本 | 通过实际对照才能作限定范围的收益声明；少量 Development 结果不支持泛化或 promotion |

阶段 2 只允许形成并验证假设，不凭 shadow 输出修改 serving。尚未提供 ADR 自动检索本身不是 serving 缺陷；必须说明受影响的既有供给职责、应返回的适用约束与实际公共输出，再按政策复现和定位。无法识别失败层时记录缺口并停止；两个相似案例不等于两类独立缺陷。Development fixture 可验证已知预期的受控机制，但不能冒充真实任务或收益证据。

常规阶段 3 的索引与返回契约应由证据倒推；本次则在用户明确授权下选择了下述最小理论契约，尚未证明其完整性、正确性或成本。阶段 4 若采用真实前瞻活动，仍须先满足现有 Campaign Source Manifest 与就绪门禁，不能把外部精选仓库或生成用例重新命名为真实效能证据。对照成本须包含 Memory 查询与上下文处理，不能只比较模型执行成本。

当前交付包含文档契约与阶段 3 的最小实现代码；阶段 1、2、4 的维护记录、独立缺陷证据与效能对照均未补齐。没有真实决策或稳定需求时，仍不为了填充索引而生成条目。

下一阶段的具体交付见[验收矩阵与真实试用材料清单](normative-context-acceptance-plan.zh-CN.md)：
先固定实际实现版本与受控预期，再验收来源、权威、学习事务、边界和分发，随后
用齐备的真实材料记录任务闭环。当前仅完成验收设计，全部场景均为 `not_run`；
未指定的批准文档、批准依据和自然到达任务保留缺口，不启动真实效能活动。

建议记录的评价维度是：遗漏已批准约束的比例、错误引用过期文档的次数、源码/规格矛盾是否被显式指出、最终验收是否覆盖规格、Agent 读取与 Token/延迟成本、文档维护成本。无客观判定依据的任务标记为 `unknown`；不承诺预设百分比收益。任何 retrieval、ranking 或 evaluation 改动仍须遵守[项目评测与变更政策](evaluation-and-change-policy.md)。

## 未采纳的捷径

- 不把未核验的报告假设、Issue、benchmark、示例 API 或指标当作现状，也不把缺少来源直接写成伪造结论。
- 不强制每个任务查询 Ledger、ADR、Memory 三套内容；按意图渐进披露。
- 不新增 Skill、Agent 包装器、设计决策 Agent、自动因果判断或平行存储。
- 不用批量回填 ADR、固定 30/60/90 天日程或制造案例来替代可追溯的真实决策与任务。
- 不让规范性文档压过当前用户明确要求；文档与源码不一致时提示冲突并核查，不静默覆盖。

## 本次理论实现（未执行验证）

接入复用现有 `learn-entry`、`learn-path`、`wiki-index` 和 `maintain-refresh-scope`。只在用户已选择的学习范围内识别显式标记的 Markdown，不自动扫描另一套 ADR 目录，不增加用户 Skill 或 CLI 命令。普通 Markdown 继续作为既有 wiki 上下文。

规范性提取通过[同一文件句柄](../tools/agent_memory_runtime/normative_documents.py)
先读取至多 4 KiB 前缀识别标记，再有界读取剩余正文；未标记的普通 Markdown 不
读取其余正文。标记、元数据、正文与文档摘要来自同一组读取字节，不在识别后重新
打开文件。整份文档最多读取 64 KiB 加一字节用于发现超限；这仍不是文件系统快照，
不能认证读取期间没有外部修改。

安装器沿用完整 Runtime 与 Skill 目录复制，新模块及 [Learn 格式参考](../skills/agent-memory-learn/references/normative-documents.md)会随安装分发。强制安装时，同一来源/目标目录不会被删除后重拷贝。本次只修改代码和说明，没有执行安装或初始化现有 Memory 数据库。

### 文档格式

首版使用平铺 frontmatter：每个键一行，值为普通标量、引号字符串，或 `scope` 的单行 JSON 数组；不支持通用 YAML 嵌套或多行值。文档上限 64 KiB，frontmatter 上限 4 KiB、48 行。下面只是格式示意，空白批准字段不得作为真实批准证据：

字节上限按原始 UTF-8 字节计量，允许文件起始带一个 UTF-8 BOM。整文最多
65,536 字节；frontmatter 从文件第一个字节计至闭合 `---` 行结束，包含 BOM、
首尾分隔符和实际 LF/CRLF 换行字节，最多 4,096 字节；闭合行没有换行时计至
其末字节，但没有后续正文仍属于无效文档。不能先去掉 BOM 或将 CRLF 转成 LF
再判断字节上限。

结构换行支持 LF 与 CRLF。开启分隔符是源文件第 1 行；闭合分隔符须位于其后
48 行内，即源文件行号不超过 49，闭合行、空行和注释都计入这 48 行。裸 CR 或
Unicode 段落分隔符不作为额外的结构行。`type` 保留字按 `adr` / `feature-spec`
字面拼写，可用单/双引号包裹，不对该保留字使用 JSON 转义。识别前缀在 4 KiB
边界截断的末行不用于确立标记；符合完整头部上限的类型行须已包含在前缀内。

派生正文统一 CRLF 为 LF，以物理行定位摘录；来源摘要仍计算原始整文字节。
这些定义是本次理论契约收敛，具体边界预期见[验收计划的 N16](normative-context-acceptance-plan.zh-CN.md#n16-格式口径与独立预期未执行)，尚未执行验证。

```markdown
---
type: feature-spec
id: SPEC-your-feature
status: draft
scope: ["src/your-feature/**"]
owner: ""
approved_by: ""
approved_at: ""
approval_ref: ""
supersedes: ""
superseded_by: ""
---
# 特性名称

## 行为与范围
填写真实需求和非目标。

## 验收场景
填写初始情境、触发事件与可观察结果，未知项保持未知。
```

ADR 使用 `type: adr`，状态为 `proposed`、`accepted`、`superseded`、`deprecated` 或 `rejected`；Feature Spec 使用 `draft`、`approved`、`superseded`、`withdrawn` 或 `rejected`。SQLite 将它们规范化为 `draft`、`approved`、`superseded`、`withdrawn`、`rejected`，未知状态不按批准处理。批准声明需有负责人、批准人、`YYYY-MM-DD` 日期及审查引用；字段齐全仍不证明批准有效。首版每份文档的 `supersedes` / `superseded_by` 各引用一个稳定文档 ID，实际取代关系由 Agent 核查。

### 派生存储与查询

- [`normative_documents`](../tools/agent_memory_runtime/normative_schema.py) 独立保存文档类型、状态、scope、批准声明、取代引用、源文快照、摘要、观察到的 Git HEAD 和学习 generation；FTS5 只索引派生词项。它们不写入普通经验或语义事实。
- 文档记录与代码学习在[同一 SQLite 事务](../tools/agent_memory_runtime/code_wiki_indexing.py)中更新。部分学习只更新命中文档；显式 `--replace` 重建同一 source root 的文档索引；已删除、取消标记或元数据无效的文档退出派生表。Git 历史仍负责保留原始决策。
- [`maintain-refresh-scope`](../tools/agent_memory_runtime/code_wiki_refresh.py) 保留记录中的深度 `0`，不把单文件文档学习扩大为两层链接学习。原 source root 仍存在时，已删除的入口文件或所选路径形成空 Scope，退休相应缓存；source root 本身缺失时仍报告来源缺口，不自动清空该来源的记录。
- [`context`](../tools/agent_memory_runtime/query_results.py) 返回 `query_handoff.normative_context`；[`design-context`](../tools/agent_memory_runtime/design_context.py) 返回 `project_context.normative_context`。候选读取最多 12 份，完整输出最多 6 份，compact 最多 2 份；只检查这些候选的源文与 Git 路径状态，不执行仓库全量查询扫描。
- [`normative-context/v1`](../tools/agent_memory_runtime/normative_context.py) 返回声明状态、范围、批准引用、新鲜度、Git 状态、取代声明与有界摘录。`expected_contract_candidate` 只是可供 Agent 审查的候选；所有记录均需核查批准，Runtime 不把标签升级为已确认硬约束。重复 ID、范围未确认、文档变化、未跟踪或未提交内容会明确标注。
- `scope_basis: document_source_root` 表明 scope 属于文档原 source root；`source.matches_query_project` 只比较该根目录与查询项目根目录，不判定任务是否适用。即使外部文档声明项目全局范围，也返回 `source_root_requires_agent_confirmation`，由 Agent 核查其与当前任务的关系，不用归档项目的锚点代为确认或将其自动列为当前契约候选。
- 被取代、撤销或拒绝的文档标为 `historical_reference_only`，草案标为 `draft_hypothesis_only`；源文变化或缺失时不返回旧摘录。观察到的 Git HEAD 与源文摘要是溯源信息，不构成对批准版本的 seal 或批准证明。
- `source.digest` 是学习时保存的原始字节摘要，`source.observed_digest` 是本次有界读取所得摘要；无法完整读取时后者为 `null`。新鲜度与观察摘要来自同一次读取，不因返回摘要再读一遍。文档变化时仍保留两者供 Agent 对照，索引元数据不因此更新，旧摘录继续省略。compact 保留这两个来源字段；缓存记录不认证之后的文件状态。
- compact 与已有上下文共享预算，优先删减新增文档摘录与引用。`examined_document_count` 是本轮已检查候选数量，`omitted_document_count` 累计这些候选在完整输出、compact 和预算删减中未展示的数量；`candidate_limit_exceeded` 表明检索还存在未检查的候选，不把已检查数量冒充全部匹配数量。`omitted_evidence_gap_count` 同样累计未展示的已知缺口。
- 完整缺口包含缓存记录 ID、文档 ID、source root 与路径；compact 保留记录 ID、文档 ID 和原因，以区分不同来源的同名文档。未知状态有明确缺口标记。摘录提供实际显示文本的起止行，字符压缩后重新计算末行；`truncated` 包括正文片段、引用与缺口的截断，需要完整契约时展开查询或直接打开源文，不能据片段验收。
- `runtime/last_context.json` 只保留规范性摘录的行号与截断元数据，不额外复制摘录正文；当前命令的公开输出仍可携带有界摘录。该运行缓存不认证来源在之后仍然新鲜，原文及有界 SQLite 文档快照沿用既有契约。
- `maintain-rebuild-derived --target search` 从 SQLite 修复规范性 FTS，不刷新 Git 内容；`vault-export` 从 SQLite 生成 `Normative Context/index.md` 和最多 500 份文档镜像，不反向修改或批准规范。镜像提供原始 Git 文件链接，索引显示来源新鲜度；来源变化、缺失或无法检查时，在旧快照前明确提示它不是当前来源证据。

摘要相同仅说明本次读到的字节与已索引摘要相同，不认证批准或任务适用性。Git
路径状态与正文摘要分别观察，学习 generation 绑定 SQLite 批次；这些字段不构成
同一时刻的全仓库文件系统快照。Agent 仍须记录实际阅读版本和所依据的批准材料。

### 取代声明的缓存查询

[`replacement_lookup`](../tools/agent_memory_runtime/normative_relationships.py) 只查询
同一项目、同一 source root 的缓存元数据。每个正向目标最多显示 2 个缓存引用，
声明 `approved` 且声称取代当前文档的反向引用最多显示 3 个；各查询多取一行以
标注预览截断。compact 保留正向目标 ID、查询状态和截断标记，反向引用保留简短
来源标识。不同 source root 的同名 ID 不合并，也不跨根目录挑选取代者。

正向查询状态为 `not_indexed`、`ambiguous` 或 `unique`，仅描述当前缓存：未索引
不证明 Git 中不存在目标，唯一命中也不证明学习范围外没有同名文档。类型差异、
对方缺少或使用不同的回指、直接两文档同向循环声明，以及新文档未声明批准都会
形成待核提示；这些是元数据观察，不裁定取代关系无效，也不做完整循环检测。

该查询不额外读取目标正文或检查目标 Git 状态，输出明确保留
`target_sources_checked: false`、`source_checked: false` 与
`approval_verified: false`。目标如果也在本轮候选中，其单独引用可有独立的来源
观察；不能把主文档的新鲜度套用到这些缓存链接。`examined_document_count` 仍只
计算至多 12 份查询候选，不把链接元数据当作已检查的文档。

Agent 根据原 source root 打开新旧双方的真实 Git 文档，核对批准、适用范围和
当前版本；未索引的已知目标可直接读或通过既有 Learn Skill 学习其明确范围。
Runtime 不根据反向声明自动更新旧文档状态，不认证批准，也不选出胜出的契约。
草案及历史材料继续遵循原有使用限制。

### 学习结果与读取缺口

`parse_stats.normative_index` 增加本轮 `source_root`、新增/变化/未变化计数、
实际退出索引的原因计数、元数据待核数量及下一步提示。变化按相同缓存路径的
原始字节摘要判断，不把新路径当成新的业务需求，也不把刷新当成批准或验收。
内容未变化的成功读取仍更新观察到的 revision 和学习 generation。
`indexed_sample` 同时返回 `source_digest`、`observed_revision` 和
`index_generation`，描述本轮写入的文档来源；其中 revision 是学习时的仓库观察，
不是之后查询时的 HEAD，也不自动绑定批准版本。

`indexed_sample`、`retirement_sample`、`metadata_issues`、`read_issues` 各最多
返回 20 条，并分别保留总量与截断信息。`next_action` 提示先审阅真实来源/元数据
问题，否则查询本轮真实文档 ID、查看退出摘要或记录本轮没有规范性变化；它不
执行批准、状态修改或猜测字段。已索引规范性文档不再自动进入该 source root 的
业务语义补全模板，混合学习仍可为代码返回既有 `semantic_followup`。

规范性同步区分确定的失效与读取失败：成功批次中，Scope 已确认的删除、取消
标记或格式无效会移除相应派生记录。显式 `--replace` 先移除同一 source root 内
未选中的文档，再刷新已选项；临时选择表只存在于本次 SQLite 连接，不成为第二份
长期事实来源。更新与删除仍在调用方学习事务内完成。

选定 Markdown 在规范性提取阶段出现读取错误，包括选取后文件消失时，
[`write_wiki_index`](../tools/agent_memory_runtime/code_wiki_indexing.py) 在提交前中止
当前批次。该批次的代码、规范性行及 FTS 变更回滚，旧记录和 generation 不因这次
失败更新；调用方也不会为失败批次登记或推进学习 Scope 检查点。稳定缺失由后续
Scope 刷新确认并退休，不能把中途读取失败当作一次成功刷新。

已有 `--json` 选项的命令通过[统一 Runtime 入口](../tools/agent_memory_runtime/runtime_entry.py)
返回 `normative-learning-error/v1`，退出码为 `1`。报告包含来源、已知的 Scope ID、
`failed_batch` 回滚/检查点状态、`attempted_normative_index` 与重试提示；其中的索引
及退休数量描述回滚前的尝试，不是已提交变更。读取问题仍以最多 20 条预览和总量
区分，文本模式只在标准错误中显示最多 5 条读取问题。修复真实来源后重试原范围，
不为重试自动扩大学习范围或追加 `--replace`。

回滚保证仅限失败的学习批次。多 Scope 维护中更早完成的 Scope 可能已经提交，
初始化及更早代码读取、后续 Scope 登记等步骤也有各自边界；本次不把局部错误处理
视为整个 CLI 调用的全流程原子性、统一错误协议或容错证明。

初始化发现规范性 FTS 表需要新建时，从既有 SQLite 文档行填充新派生表；正常
已有表不因此每次重建。此恢复不读取 Git、不改文档状态，也不证明索引完整性。

### 日常维护概况

现有 [`maintain-health`](../tools/agent_memory_runtime/governance_health.py) 增加
`counts.normative_documents` 和 `normative_index`，后者使用
[`normative-index-health/v1`](../tools/agent_memory_runtime/normative_health.py)：

- `document_count`、`declared_status_counts` 和 `duplicate_identity_count` 统计 SQLite
  当前缓存。状态计数来自文档声明的规范化结果，不是实际批准数或验收通过数。
- `source_sample` 仅读取最近索引的最多 20 份文档，返回读取数量、新鲜度计数、
  未检查数量与截断标记；不做全量仓库扫描，也不在健康概况中检查 Git 状态。
- `review_sample` 最多列出 5 份有来源或元数据缺口、未知状态、重复 ID 或取代声明
  待核的文档，并单独标注样本截断。取代声明复用上述有界缓存查询，其链接目标
  不因出现在报告中就增加已读取的来源样本；取代声明待核不等于已证明文档有误。
- 待核项保留缓存记录 ID、`source_digest` 和本次样本读取的 `observed_digest`；
  无法完整读取时观察摘要为 `null`。Vault 镜像同样区分已索引摘要与导出时观察摘要，
  后者无法取得时标为 `unavailable`。这些观察不更新 SQLite 文档快照或批准声明。
- 维护建议只要求 Agent 核对原文、批准和既有学习 Scope，再按授权刷新。概况不
  自动修改状态、不批准规范、不认证整体新鲜度，也不产生质量门禁或收益结论。

上述代码为本次授权的理论实现。未执行安装烟测、回归、编译、性能门禁、来源有效性实验或 Agent 效能评测；不能据此宣称功能已验证、成本降低、就绪门禁通过或可晋级。

## 参考来源

- 项目约束：[`agent.md`](../agent.md)、[MVP 实施计划](mvp-implementation-plan.md)、[Design Context Provider](superpowers/specs/2026-07-16-design-context-provider.md)、[Agent 上下文供给边界](context-provider-boundary.md)、[评测与变更政策](evaluation-and-change-policy.md)。
- 实现与使用协议：[`design-context/v1` 实现](../tools/agent_memory_runtime/design_context.py)、[FTS5 schema](../tools/agent_memory_runtime/storage_search_schema.py)、[设计使用指南](design-usage-guide.md)、[Query Skill 设计协议](../skills/agent-memory-query/references/code-design.md)。
- 历史活动证据：[真实前瞻活动就绪审计及后续补充](real-campaign-readiness-audit.zh-CN.md)、[2026-08-08 机器可读审计](eval/real-campaign-readiness-audit-2026-08-08.json)。它们不代表本次重新审计。
- Michael Nygard, [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)：轻量 ADR 的背景、决定和后果。
- GitHub, [Spec Kit Agentic SDD](https://github.com/github/spec-kit/blob/main/docs/reference/agentic-sdd.md)：规格、计划、任务及一致性分析的分工。
- OpenSpec, [Glossary](https://openspec.dev/docs/glossary)：区分主规格与变更提案中的 delta spec；只参考这种分工，不直接复制工具链。
- Cucumber, [Gherkin Reference](https://cucumber.io/docs/gherkin/reference/)：用初始情境、触发事件和可观察结果表达验收场景；执行验证还需要对应实现与断言。

这些来源支持文档化与可验证性原则，不直接证明本项目接入 Runtime 后会获得性能或质量收益。
