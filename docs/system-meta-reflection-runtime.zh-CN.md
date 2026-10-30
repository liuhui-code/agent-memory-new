# 系统元反思：独立治理记录与提案状态

日期：2026-10-30
状态：相关合成隔离回归已通过；不是完整功能验收或发布结论，见[验证记录](system-meta-reflection-design.zh-CN.md#9-隔离验证记录)

本次按已确认的[设计规格](system-meta-reflection-design.zh-CN.md)，在既有 SQLite
治理方式中增加独立记录能力，不调整查询、排序、学习提取或普通反思存储算法。
Runtime 不调用模型评审或推断缺陷，不自行选择修复、迁移或发布。新增显式检查
计划入口只按调用方授权执行有限命令，其子命令可以有自身副作用。

## 入口与写入边界

仍使用 `tools/agent_memory.py`，保持四个 Skill。以下命令已在临时归档/合成仓库
回归中调用；真实使用前仍须绑定实际安装副本与版本。

| 命令 | 用途 | 副作用 |
|---|---|---|
| `reflect-system-trigger` | 任务收尾判断、报告绑定和可选一次名额 | 默认只读；已授权的 --claim 才创建独立名额记录，不调用模型 |
| `reflect-system` | 保存有界、建议性的系统评审和至多一项提案 | 显式写入独立治理表；仅首次保存时创建其表和版本记录 |
| `maintain-system` | 读取摘要、一个评审线程或一项提案及审计事件 | 以 SQLite 只读 URI 打开已存在归档；不初始化归档或治理表 |
| `maintain-system-status` | 带预期修订号更新允许的提案状态 | 仅修改治理状态并追加事件；prepared 额外读取指定制品的有界字节摘要 |
| `maintain-system-check` | 预览或显式执行绑定提案的有限检查计划 | 默认只读；--execute 才预留独立运行记录并启动授权命令，不推进提案状态 |
| `maintain-system-candidate` | 预览或显式准备基线加补丁的独立候选 | --execute 才在指定目录新建私有 clone，并在该副本应用补丁，不更新原副本或安装版本 |

检查计划、进程事实与断言审查的边界见[显式检查契约](system-meta-reflection-checks.zh-CN.md)。
任务边界声明、触发优先级与跨会话名额的保证范围见[触发契约](system-meta-reflection-triggers.zh-CN.md)。
候选准备及检查计划 v2 的主体绑定见[候选契约](system-meta-reflection-candidates.zh-CN.md)。
检查计划 v3 另外观察实际生成产物；显式治理 v2 迁移及 accept/apply/follow-up/
rollback/resume/resolve 的高级状态与副作用见[生命周期规格](system-meta-reflection-lifecycle.zh-CN.md)。
`maintain-system --operation-key` 可读其独立审计记录。原 status writer 的直接晋级拒绝保持不变。

所有操作都使用显式 `--project` / `--memory-home` 的既有归档定位语义。保存要求
归档已初始化并含当前 project_id；不会为了评审调用普通初始化、索引或迁移。
声明的 archive_project_id 若非 null，须与实际目标一致。默认查询和 doctor 不
创建这些治理表；doctor 的基础检查通过不等于已经核验此功能。

不存在的归档/治理区在读取时返回 available=false；部分表缺失、未知治理版本或
存储错误明确返回错误，不猜测修复。显式写入事务使用 BEGIN IMMEDIATE，创建表、
报告修订、初始提案及事件一起提交；状态更新与事件也在同一事务内。
采用独立 execute 而非中途提交的脚本执行，参考
[Python sqlite3 文档](https://docs.python.org/3.9/library/sqlite3.html)与
[SQLite 事务语义](https://www.sqlite.org/lang_transaction.html)。实际回归覆盖及其边界见上述验证记录。

## 报告输入

保存时提供 `--review-key <opaque-key>` 和且仅一个 `--payload` / `--payload-file`。
报告格式为 `system-meta-review/v1`，所有下列顶层字段都必需；未知项用规定的
null、空列表或缺口表达，不添加 raw_logs、源码、命令或 verified 等字段。

| 字段 | 当前写入契约 |
|---|---|
| report_format / advisory_only | 固定格式标识；advisory_only 必须为 true |
| task_ref | null，或仅含 key 与 origin（host/client_local）的对象；自动触发须有任务关联 |
| review_revision | 1 至 2³¹−1 的整数，首次为 1，后续连续增加；布尔值不算整数 |
| trigger / task_state | manual/memory_error/user_correction/evidence_conflict/repeated_gap；任务状态 in_progress/completed/failed/blocked/cancelled |
| task_outcome / memory_use | success/failure/partial/unknown；used/not_used/unknown |
| version_refs | 可选键 runtime_revision/runtime_digest/skill_revision/skill_digest/protocol_version/source_revision/source_digest/archive_project_id/index_generation；值可为 null，generation 为非负有界整数 |
| query_refs | 调用引用列表；引用不含多行文本，长度不超过 240 字符 |
| observations | 最多 8 项，每项仅含 summary 和 refs |
| checks | 最多 5 项，每项含 assertion、expected_ref、observed_refs、result、scope；result 为 pass/fail/unknown/not_run |
| model_opinions | 最多 5 项，每项含 dimension、assessment、evidence_refs、counter_evidence_refs |
| target_components | memory/rules/query/learn/reflect/data_model/evaluator/delivery 的不重复列表 |
| change_proposals | 0 或 1 项，格式如下 |
| missing_evidence / omitted_counts | 最多 8 条缺口；省略计数仅接受 observations/checks/model_opinions/change_proposals/evidence_refs 的非负整数 |
| additional_cost | 必须包含 tokens 和 elapsed_ms，实测数值或 null；未测量不填 0 |
| review_status | completed/partial/skipped/failed；文档模板 not_run 不接受为已执行评审 |

每项 observations.summary 最多 500 字符；assertion/scope 最多 300 字符，
opinion.assessment 最多 400 字符。整份输入以及排序键、紧凑分隔、保留 Unicode
的 canonical JSON 均不超过 4,000 字符，文件读取至多 32 KiB；全部引用合计
最多 8 个不同值。拒绝重复 JSON 键、错误类型、无效 Unicode、非有限成本和
未知字段。省略计数只说明已知省略，不宣称全部潜在证据覆盖。

自动触发只接受已完成/失败/阻塞任务；取消不自动触发，成功抽样仍未启用。
写入器核对结构与关联，不认证触发信号真的发生、引用材料真实或模型判断正确。
pass/fail 需要预期与观察引用，但这些仍是调用方主张。字段限制不等于自动脱敏；
Agent 仍负责仅提交简短事实和引用。

review-key 和 task_ref.key 使用归档内唯一命名空间的 ASCII 不透明标识（1–160
字符，可用字母数字及 `_.:-`）。会话内任务键应带会话命名空间；不要用任务正文。
这些键不证明真实任务独立性、前瞻入组或外部来源谱系。

## 提案输入与修订

change_proposals 的唯一条目必需字段为 target_component、change_kind、problem、
proposed_change、evidence_refs、acceptance_criteria、compatibility、rollback、
proposal_state。目标须在报告 target_components 中；change_kind 为
defect/requirement/structural，初始状态仅 proposed/needs_evidence。acceptance_criteria
至少 1 项、最多 5 项；problem/proposed_change/compatibility/rollback 各至多 600 字符。

可选 proven_layer、migration（null 或至多 400 字符）、alternatives（最多 3 项）
及 artifact_refs。skipped/failed 评审不创建提案。Runtime 保存建议而不判定其真实性，
不得以一条新记录冒充已复现缺陷或已批准需求。

同 review-key、同 revision、同 canonical 摘要的重试返回原记录，不重复插入。
同修订不同内容、修订跳号、线程改换任务身份，或同任务另建 review-key，均返回
冲突。首次任务关联为 null 的线程不能事后换绑为另一身份。修订是不可变快照，
不覆盖旧报告；带候选的新修订创建关联提案快照，不自动覆盖或退休已准备的旧提案。
维护者可显式将旧提案 superseded，并在 note 中关联替代制品。
candidate 内的 proposal_state 是初始不可变快照；当前治理状态以提案详情顶层的
state/state_revision 为准，不能根据报告里的旧状态覆盖维护进展。

摘要区分 review_revisions、review_threads 和 changes。线程数不等于独立真实
任务数量；多个修订/提案不成为多条独立证据。默认列表只返回有界摘要；指定
review-key 返回最新完整报告和有界修订摘要，指定 change-id 返回提案及有界事件。
提案详情还返回独立检查运行摘要；--run-key 返回一条完整、有界的执行记录，
与 review-key/change-id 互斥。读取这些历史记录不重新验证当前文件。
--trigger-id 可读取一个名额及原始类型化声明，与其他详情选择互斥。只有名额而
尚无评审表时摘要 available=true、报告计数为 0，不冒充已经执行过评审。

## 使用方式（参数示例）

仅在报告实际存在且用户已授权本地治理记录保存时调用：

```bash
python tools/agent_memory.py reflect-system --project . --review-key <namespaced-review-key> --payload-file <review.json> --json
python tools/agent_memory.py maintain-system --project . --limit 5 --json
python tools/agent_memory.py maintain-system --project . --review-key <namespaced-review-key> --json
python tools/agent_memory.py maintain-system --project . --change-id <id> --json
python tools/agent_memory.py maintain-system --project . --run-key <run-key> --json
```

可在摘要模式使用 --status 过滤提案；它不与 review-key/change-id/run-key/trigger-id 详情组合。
limit 为 1–20，默认 5；列表、修订与事件均明确标记截断。返回中的报告仍为
建议性数据，不会被加入普通 memory、FTS、经验反馈、排名或查询 payload。
counts 始终统计该项目全部治理记录，状态筛选只影响 changes 列表。

## 状态与制品准备

当前 writer 支持以下状态：

- proposed 可转 needs_evidence/prepared/rejected/superseded。
- needs_evidence 可转 proposed/prepared/rejected/superseded。
- prepared 可更新制品观察，或转 needs_evidence/rejected/superseded。
- rejected/superseded 为该提案快照的终态，新候选用新的报告修订表达。

更新须给 --expected-revision 与 --note；过期修订返回 state_conflict，不静默覆盖。
每次更新追加不可变审计事件。示例仅说明语法，不代表存在对应提案或实际应用：

```bash
python tools/agent_memory.py maintain-system-status --project . --id <id> --expected-revision <state_revision> --status needs_evidence --note <brief-reason> --json
python tools/agent_memory.py maintain-system-status --project . --id <id> --expected-revision <state_revision> --status prepared --note <brief-reason> --development-root <authorized-development-copy> --base-version <declared-base> --artifact-file candidate.patch --json
```

prepared 要求显式开发根目录、基线声明，以及 1–3 个目录内的不同普通文件；
文件为相对路径，每份有界读取最多 1 MiB。只记录相对路径、原始字节 SHA-256、
大小、时间与根目录，不保存文件内容，不运行代码。基线属于 caller_declared，
摘要观察不证明补丁可应用、仓库快照原子性或检查通过。
提案详情的 artifact_digest 绑定根目录、声明基线及按路径排序的制品身份，忽略
观察时间；该摘要可供显式检查计划引用，不认证真实基线或实际应用。

checked/applied/monitoring/closed/rolled_back 仍需完整断言审查和应用条件的入口，
当前状态 writer 返回 verification_gate_unavailable。特别是 prepared 不代表
checked；显式检查记录也不自动晋级。当前没有数据库迁移、回退、安装或发布入口。

## 存储与错误

候选使用独立 system_change_candidates 表和 system_evolution_candidates 组件，
仅首次显式准备才创建。--candidate-key 读取历史元数据，提案详情附带有界候选
列表；不在普通查询、初始化、doctor、FTS 或 Vault 中创建或消费候选。
preparing 记录阻止提案变更及新检查，不能按经过时间清除。ready 只表示准备阶段
完成，历史读取/重试不重新核验当前文件，所有效能与晋级标记仍保持未证明。

仅显式保存创建 system_meta_reviews、system_change_proposals、system_change_events，
并在既有 runtime_schema_versions 登记 system_evolution 版本；不改变基础表的
required 集合，不在普通初始化或查询中创建治理表。报告、提案与事件在既有
归档内按 project_id 隔离，没有新数据库、FTS 或后台进程。
首次显式检查执行才另建 system_change_check_runs 并登记 system_evolution_checks
组件，预览和读取不创建。running/未决运行阻止提案状态变更，不以超时推断结束。
首次显式 --claim 只建 system_meta_review_triggers，登记 system_evolution_triggers
组件，不创建评审或检查表。reserved/recorded 只表达名额分配与报告保存，不能
视为活进程或实际模型调用；正常查询、初始化、doctor 不消费该名额。

新命令完成参数解析后的已知输入/冲突/存储错误以 system-evolution-error/v1 返回，退出码 1；
JSON 包含 code 和简短 message，不回显报告正文。输入结构检查在写入前进行。
缺少参数、互斥参数和参数整数解析失败仍遵循既有 argparse 错误行为。
状态错误、制品观察失败和事务失败不会被解释成成功；本轮未实证其回滚行为。

新增受控回归用例位于 tests/test_system_evolution.py，明确为合成机制输入，不是
真实用户任务、批准或评测 Oracle。按用户要求没有执行测试、编译、Runtime、
安装、迁移、性能或效能检查；首次真实活动与系统级改进仍须满足原有变更政策。
