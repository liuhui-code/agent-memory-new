# 系统上下文能力评测

## 目标

该评测只回答一个问题：在不调用 Agent/LLM 的情况下，系统能否根据用户问题提供正确、
紧凑、可验证的上下文。它不评价模型是否会规划工具、理解源码或给出正确根因。

```text
真实案例 + 冻结 revision + 隐藏 Oracle
                  |
                  v
       隔离 wiki/code/log 索引
                  |
                  v
          context --compact
                  |
                  v
  确定性系统能力评分（不调用 Agent）
                  |
          pass -> Agent A/B
          fail -> 修复上下文供给
```

`eval-context-capability` 属于现有 `agent-memory-maintain` 治理范围，不增加第五个
用户 Skill；`tools/agent_memory.py` 仍是唯一运行时入口。

## 能力边界

默认门禁使用案例已有的隐藏 Oracle：

- `expected_files`：必须出现在 `query_handoff.code_anchors`。
- `forbidden_files`：不得进入代码锚点。
- 紧凑响应必须使用 `agent-context-compact/v1`。
- `output_budget.estimated_tokens` 必须处于 1,500 Token 预算内。

可在 `oracle.context_requirements` 中显式增加：

```json
{
  "required_log_keywords": ["session invalid"],
  "required_log_files": ["src/ProfileService.ets"],
  "forbidden_log_keywords": ["generic network timeout"],
  "forbidden_log_files": ["src/NetworkClient.ets"],
  "required_experience_types": ["correction_experience"],
  "required_main_experience_phrases": ["bounded session retry"],
  "forbidden_main_experience_phrases": ["retry every failure"],
  "required_guard_experience_phrases": ["401 means invalid session"],
  "required_path_files": ["src/Session.ets"],
  "required_path_relations": ["calls"],
  "forbidden_path_files": ["src/Cache.ets"],
  "min_relation_hints": 1,
  "min_path_candidates": 1,
  "require_source_excerpt": true,
  "require_expected_anchors": true,
  "required_top_k": 3,
  "min_anchor_precision": 0.5,
  "required_source_spans": [
    {"file_path": "src/Session.ets", "start_line": 40, "end_line": 70}
  ],
  "hierarchical_callable_spans": [
    {"file_path": "src/Session.ets", "symbol": "restoreSession"}
  ],
  "hierarchical_owner_spans": [
    {"file_path": "src/ProfilePage.ets", "symbol": "refreshSession"}
  ],
  "hierarchical_range_spans": [
    {"file_path": "src/Session.ets", "symbol": "restoreSession"}
  ],
  "min_source_span_recall": 1.0,
  "require_abstention": false,
  "required_evidence_gaps": []
}
```

未声明 Oracle 的能力只报告 `informational`，不会因为“有一些结果”就伪装成通过。
因此代码定位、日志图、经验检索、因果上下文和源码证据可以分开判断。源码摘录正文只在
临时查询进程中使用；能力观察与持久化报告只保存路径、命中、计数、耗时和 Token。

`hierarchical_callable_spans`、`hierarchical_owner_spans` 与
`hierarchical_range_spans` 只用于分层定位影子评估，不加入 `system_context_gate`。它们分别
标注目标 callable、从该 callable 反向一跳可达的真实 caller/owner、以及可供 Agent 检查的
源码范围。旧的 `required_source_spans` 和 `required_owner_spans` 仍作为未迁移案例的观察
回退；新案例应使用专用字段，避免影子标注改变紧凑源码摘录门禁。尚未人工标注的维度会显示
为 `null`，不能解读为 0 分或通过。

若案例只校准完整审计的层级定位，而不要求紧凑 Context 直接返回目标文件，应保留
`expected_files` 作为影子文件指标，并显式设置 `require_expected_anchors: false`。这样紧凑
预算和 schema 仍受门禁约束，但 callable、owner、range 的 Oracle 不会被无关的紧凑锚点失败
掩盖。需要同时验证服务检索和分层定位的案例则保持默认值 `true`。

## 运行

```bash
python tools/agent_memory.py eval-context-capability \
  --project . \
  --cases docs/eval/gramony-history-cases.json \
  --source /tmp/gramony \
  --allow-drafts \
  --case-id gramony-split-view-chat-navigation \
  --case-id gramony-login-duplicate-submit \
  --case-id gramony-webm-local-file-access \
  --fail-on-fail \
  --json
```

每个案例在自己的冻结工作区和临时 Memory Home 中重建索引。命令写入：

- `runtime/last_context_capability.json`
- `runtime/context_capability_history.jsonl`，最多保留 100 条
- `maintain-health --json` 的 `context_capability`

`system_context_gate=pass` 只允许进入下一层 Agent A/B，不等于最终诊断能力通过。
Agent A/B 仍需独立检查根因、文件、因果校准、稳定性、Token、耗时和工具成本。

紧凑检索先保留直接命中，再交错最多一个达到阈值的图邻居，并用轻量 MMR 延后同质代码
候选；显式枚举的多个路径目标不参与合并。最终最多返回四个文件锚点。源码摘录会在前三个
主锚点之间公平分配字符预算，并在同一文件内按查询词密度和 ArkTS 行为信号选择有界
窗口；报告只保留窗口路径、行号和选择原因。`required_top_k`、`min_anchor_precision` 和
`required_source_spans` 分别约束排序、噪声比例和真正送给 Agent 的源码位置。
`require_abstention` 用于无证据负例：代码、日志、经验和路径必须全部为空，并报告要求的
`evidence_gaps`，不能用弱相关结果填满上下文。

## 内置十五案例能力集

`docs/eval/system-capability-cases.json` 配合
`docs/eval/fixtures/system-capability/` 提供最小、可审查、与外部项目无关的 ArkTS 能力集：

- 2 个日志案例：正确日志发射点、显式排除的弱相关日志及当前源码摘录。
- 2 个经验案例：可复用 procedure 进入主 lane，纠正经验只进入 guard lane。
- 2 个因果案例：从精确日志发射点返回有界调用候选、关系和禁止分支检查。
- 1 个跨组件案例：验证直接组件与一跳依赖组件都进入 Top-K 和源码区间。
- 1 个日志密集案例：验证日志命中不会挤掉发射点与服务源码摘录。
- 1 个组件属性流案例：验证叶子组件可沿属性绑定反向找到两层计算与透传组件。
- 3 个领域实体干扰案例：分别验证渲染所有者、路由所有者，以及查询所有者与消费页面。
- 1 个无证据案例：三种措辞都必须稳定 abstain，并显式报告代码和日志证据缺口。

直接运行：

```bash
python tools/agent_memory.py eval-context-capability \
  --project . \
  --cases docs/eval/system-capability-cases.json \
  --source docs/eval/fixtures/system-capability \
  --fail-on-fail \
  --json
```

案例可以声明 `context_setup.reflections`，但只允许最多 8 条、合计不超过 32 KB 的已审查
合成反思。Fixture 通过公开 `reflect` 运行时命令写入每个案例独立的临时 Memory Home；
不允许 SQL、任意命令或生产记忆复制。Oracle 只供评分器读取，不进入 `context` 查询。

每个场景还可以声明 1 至 5 个 `query_variants`。运行时在场景选择和 `--limit` 之后展开
变体；每个变体使用独立工作区和临时记忆，但共享场景 Oracle。报告中的
`capability_profile.query_robustness` 按场景聚合稳定性，任一变体失败仍会使总门禁失败。

```json
"query_variants": [
  {"id": "original", "description": "original task wording"},
  {"id": "en-paraphrase", "description": "equivalent English wording"},
  {"id": "zh-noise", "description": "中文表述，并包含需要排除的噪声"}
]
```

2026-07-18 首轮固定措辞基线为 6/6 通过。加入每场景三种表述后，第一次稳定性运行仅
15/18 通过，暴露出语义查询被 `refresh` 误判为维护、中文附加措辞稀释纠正经验触发条件
覆盖率两个缺陷。修复后 6 个场景、18 个变体全部通过，查询变体通过率为 1.0；代码锚点
和源码摘录召回均为 1.0，平均上下文为 998.6667 Token。

增加无证据场景和最终输出缺口重算后，当前门禁为 7 个场景、21 个变体全部通过；
abstention 为 3/3，平均上下文为 992.9524 Token，代码锚点 MRR 为 1.0。所有观察仍为
model-free，未持久化源码正文。

加入跨组件与日志密集场景后，当前门禁为 9 个场景、27 个变体全部通过。代码锚点召回、
主锚点召回、MRR、源码区间召回和变体通过率均为 1.0，abstention 为 3/3，平均上下文为
1,014.8519 Token。查询只在检索阶段拆分 CamelCase/下划线标识符并做保守英文词形归一，
不会改变经验治理的基础分词语义。

加入独立的 Timeline 组件属性流 development 场景后，第一次运行通过 29/30，唯一失败是
中文显式组件名让源码焦点停在 import 区域。补充通用 ArkTS 属性绑定、`@Prop` 和条件渲染
行为信号后，当前门禁为 10 个场景、30 个变体全部通过。代码锚点召回、主锚点召回、MRR、
源码区间召回和查询变体通过率均为 1.0；abstention 为 3/3，平均上下文为 1,033.4 Token。
学习阶段记录不含值的 `passes_property` 边，紧凑查询仅反向遍历组件关系两跳并最多提升
两个上游文件；它不生成数据流或因果结论。两组 Gramony sealed holdout 均未重跑。

在第三组 sealed holdout 完成且保持不可变后，后续实现只使用新的 Commerce 合成
development 数据。新增组件谱系和 UI 行为所有者两个场景后，完整门禁为 12 个场景、
36 个变体全部通过。代码锚点召回、主锚点召回、MRR、源码区间召回和变体通过率均为
1.0；abstention 为 3/3，平均上下文为 1,006.0278 Token。

学习阶段现在把最多 12 个 ArkTS 链式操作名写入文件摘要，并排除已知 ArkUI Builder
调用的伪函数符号，同时保留项目自定义的大写方法。查询阶段只用原始问题词及明确 UI 同义词确认精确操作所有者；短 ASCII
词按边界匹配，源码可定位性也只能增强已有文本命中，不能凭空创建相关性。组件结果存在
一致静态分支时，紧凑层保留分支成员而不回填同名前缀噪声；源码窗口优先组件绑定和 UI
modifier 行。三组 Gramony sealed holdout 均未重跑，也未用于本轮阈值或排序调优。

加入三个独立的 Commerce 实体干扰场景后，开发门禁第一次为 37/45。修复只针对开发复现：
增加有界 ArkTS 成员行为操作、显式多类型身份聚焦、页面/服务查询对数据实体的角色抑制，
以及文件级强命中的查询聚焦源码窗口。最终 15 个场景、45 个变体全部通过；代码锚点召回、
主锚点召回和 MRR 均为 1.0，平均精度为 0.7731，源码区间召回为 1.0，平均上下文为
956.4889 Token。原有 36 个变体和 3 个 abstention 变体均保持通过。

## 案例密封与失败归因

Holdout 在首次执行前必须经源码 diff 审查并密封：

```bash
python tools/agent_memory.py eval-seal-cases \
  --project . \
  --cases /tmp/reviewed-holdout.json \
  --target docs/eval/project-holdout-cases.json \
  --source /path/to/frozen-project \
  --json
```

密封摘要覆盖除 `seal` 本身以外的完整 JSON。加载时会拒绝摘要不匹配、revision 不存在、
修复提交不一致、声明文件不在真实 diff 中、缺少源码审查或 Oracle 未列入隐藏字段的案例。
失败报告把每个检查映射到 `candidate_generation`、`ranking_precision`、
`passage_selection`、`graph_structure`、`experience_governance`、
`abstention_calibration` 或 `context_compactness`，并给出允许修复层、禁止捷径和下一次验证。
密封案例失败后不得原地调整任务措辞、阈值或 Oracle。

## Gramony 结果

首轮三案例测试在 split-view 导航上失败：完整检索已在 log-emitter 中找到
`ChatList.ets`，但紧凑层为抑制弱日志噪声把它删除，通用 `chat` 符号占满主锚点。

修复后只允许一个达到阈值且具有明确函数/符号身份命中的 log-emitter 进入主锚点；
普通弱日志仍被抑制。随后增加 Sticker 扩展名与新聊天标题两个开发案例，补齐 ArkTS
`NavPathStack.pushPath/replacePath` 命名路由、文件/符号节点归一、内部边候选召回与有界
图邻居重排。五案例复测结果：

| 指标 | 结果 |
|---|---:|
| 系统上下文门禁 | pass |
| 代码锚点召回 | 1.0 |
| 主锚点召回 | 1.0 |
| 代码锚点 MRR | 0.7 |
| 源码摘录召回 | 1.0 |
| 人工源码区间召回 | 1.0 |
| 平均上下文 | 1,175.4 Token |
| 平均索引准备 | 1,343.8 ms |
| 平均查询 | 408.4 ms |

Gramony 案例集没有日志关键字、经验或因果路径的人工 Oracle，所以这三项保持
`informational`；对应能力由上面的内置十五案例集单独门禁，不能用代码定位结果替代。

## Gramony Holdout

`docs/eval/gramony-context-holdout-cases.json` 隔离了三个此前未进入案例库的真实修复，并在
首次执行前冻结问题描述、变更前 revision、Top-K、精度、源码区间和禁止文件。该集合不
参与排序或摘录策略调优，失败结果也不能通过放宽 Oracle 消除。

首次运行 0/3 通过：文件召回为 0.8333、MRR 为 0.8333，但源码区间召回仅 0.5。推送
注销案例命中了目标文件和正确源码区间，但额外噪声使精度未达门禁；媒体状态案例因日志
证据占用预算未输出源码摘录；文字可读性案例漏掉了 `ReplyToPreview.ets`。这些结果说明
开发集通过不等于泛化完成，下一轮应使用新的训练/开发案例改善跨组件召回和证据配额，
再用另一组未见案例验收，而不是回调本 holdout。
本轮只扩展 development 案例与合成门禁，没有重跑或使用该 sealed holdout 调参。

## 第二组 Gramony 泛化 Holdout

完成九案例合成门禁和五案例 development 优化后，从未进入上述集合的三个历史修复中
重新审查并冻结了 `docs/eval/gramony-context-generalization-holdout-cases.json`。它覆盖搜索
栏与列表布局、连续消息用户名的跨组件属性传递、格式化实体的数据库重载。首次运行前的
案例文件 SHA-256 为
`72e1588b9cb41850068e2e4d1831013e0dea600bfd9b7776160e41790c6766f1`。

该集合只执行一次有效系统能力评测，结果为 1/3 通过：

| 指标 | 结果 |
|---|---:|
| 系统上下文门禁 | fail |
| 代码锚点召回 | 0.7778 |
| 主锚点召回 | 0.7778 |
| 代码锚点精度 | 0.3889 |
| MRR | 1.0 |
| 源码摘录召回 | 0.7778 |
| 人工源码区间召回 | 0.6667 |
| 平均上下文 | 1,192.6667 Token |

数据库格式化实体案例通过，说明持久化语义和 DAO 调用上下文可以在未见案例中联合召回。
搜索栏案例把目标文件排到第一名并命中正确源码区间，但四个锚点中只有一个 Oracle 文件，
未通过精度门禁。连续消息案例只命中 `MessageBubble.ets`，漏掉上游 `ChatDetail.ets` 与
`ChatDetailItem.ets`，暴露出代码图尚不能稳定反向恢复 UI 属性计算与透传链。

精简结果保存在 `docs/eval/gramony-context-generalization-holdout-result.json`。该失败不用于
修改本集合、调整阈值或继续调当前排序；后续应在新的合成/development 案例中发展反向
组件属性流和查询条件下的锚点精度，再使用另一组未见案例验收。

## 第三组 Gramony 组合关系 Holdout

加入通用 `passes_property` 组件边并使十场景 development 门禁通过后，又从未被前两组
案例使用的历史修复中冻结三个组合与 UI 行为案例。案例文件
`docs/eval/gramony-context-composition-holdout-cases.json` 的运行前及运行后 SHA-256 均为
`c2fe3ca4d161ff1e70b8b2549758ee87d4096f2ed56e7bd131548e768482fb69`。

该集合只执行一次有效评测，结果为 0/3 通过：

| 指标 | 结果 |
|---|---:|
| 系统上下文门禁 | fail |
| 代码锚点召回 | 0.5 |
| 主锚点召回 | 0.5 |
| 代码锚点精度 | 0.2778 |
| MRR | 0.6667 |
| 源码摘录召回 | 0.5 |
| 人工源码区间召回 | 0.1667 |
| 平均上下文 | 1,101 Token |

聊天底部安全区案例找到了叶子组件，但没有沿组合关系带回页面容器，并被名称相近的媒体
子组件占用预算。列表分隔线案例没有找到 `ChatList.ets`，说明自然语言 UI 行为仍可能被
通用聊天实体和页面符号稀释。首页搜索间距案例召回了两个目标文件，但精度只有 0.5，且
父组件摘录没有落在人工确认的组合区间。三例均满足 1,500 Token 紧凑预算。

精简结果保存在 `docs/eval/gramony-context-composition-holdout-result.json`。本结果只证明当前
泛化边界，不用于修改检索实现、案例阈值或 Oracle。下一轮开发应在独立案例上验证查询
条件化组件谱系、具体 UI 行为锚点和源码窗口对齐，再另建未见集合验收。

## 2026-07-18 三仓发布决策

当前密封库存共 15 个真实 ArkTS 案例：Jingmo 13 个，Gramony 2 个。首组 Jingmo 十案例
首次运行 1/10；在独立开发集修复并达到 45/45 后，第二组不重叠 Jingmo 三案例首次运行
0/3。之后将候选召回拆成有界 FTS5 通道，增加查询焦点覆盖精排与符号范围优先的源码
窗口；开发门禁继续保持 45/45，锚点召回 1.0、MRR 0.9722、源码区间召回 1.0，平均
上下文 957.8 Token。

两个保留的 Gramony 案例随后只执行一次，结果为 0/2：锚点召回和 MRR 均为 0.75，
精度为 0.25，源码区间召回为 0.0，平均上下文 1,287.5 Token。富文本案例已将目标文件
排在首位，但仍带入三个噪声文件；聊天列表案例漏掉 `ChatDataSource.ets`。主失败类仍为
`ranking_precision`，并伴随 `candidate_generation` 与 `passage_selection`。该集合已从
`reserved_unseen` 转为 `immutable_observation`，不得重跑或用于调参。

不可变摘要见 `docs/eval/jingmo-context-holdout-result.json`、
`docs/eval/jingmo-post-repair-holdout-result.json`、
`docs/eval/gramony-unseen-sealed-holdout-result.json` 和
`docs/eval/real-project-capability-release-decision.json`。`maintain-health.context_capability`
同时返回 `cross_project_history`，按真实源码项目汇总最新案例观察、密封覆盖、通过/失败数、
加权召回和上下文 Token；未密封历史只能证明覆盖，不能作为晋级证据。

随后从第三个独立 ArkTS 项目 Bookkeep 审查并密封三个真实修复：主页列表无法滚动、月份
切换后收支不刷新、录入页分类区遮挡输入区。密封摘要为
`93cc937b9a639677e318b716746f36575c247de318ea23226c727b2009c67bc5`，三个案例只执行
一次，结果为 0/3。所有案例均返回空代码锚点，召回、MRR 和源码区间召回均为 0，平均
上下文仅 388 Token。统计报告同时产生排序和 passage 失败，但根故障是候选生成：抽象
英文症状与项目中的中文业务词、ArkTS modifier 和通用页面名之间没有足够词汇交集。

开发门禁在本次外部执行前保持 45/45，锚点召回 1.0、MRR 0.9676、源码区间召回 1.0，
平均上下文 943.5111 Token。密封库存现为三个项目、18 个案例；真实项目泛化与 Agent
效率门禁仍未同时通过，发布决策继续为 `deny_promotion`。Bookkeep 结果保存在
`docs/eval/bookkeep-unseen-sealed-holdout-result.json`，不得重跑或用于项目名/文件名特例
调优。下一轮必须在独立开发夹具中复现“抽象症状到结构化 ArkTS 行为”的词汇鸿沟，再用
新的密封项目验收。

## 2026-07-19 第四项目结构召回观察

Bookkeep 失败只在独立 development 夹具中复现。实现新增语言无关的行为概念与
`sqlite_fts5_fielded/v2` 结构 FTS 通道，把滚动、响应式聚合刷新和视觉遮挡症状映射到
已索引的 ArkTS 行为 marker；该通道只作用于 `code_files`，受候选预算限制，不使用项目
名或历史 Oracle 别名。结构 marker 覆盖也参与源码焦点选择。紧凑投影在 Token 紧张时
优先保留两条候选路径和公共 emitter 证据，再舍弃一个非 emitter 的重复源码摘录。

新增三个独立场景及九个措辞变体后，开发门禁为 18 个场景、54 个变体全部通过。锚点
召回 1.0、MRR 0.9741、源码区间召回 1.0，平均上下文 893.5556 Token，平均查询
327.3704 ms。随后审查并密封第四个真实 ArkTS 项目
Home-Assistant-HarmonyOS-Next 的四个修复，摘要为
`36d8a013c2368e0c302cf767ee3c446dcf28a30440ebcc01b87f8e12df926307`。

该集合只执行一次，结果为 0/4。右侧间距案例的目标 `SystemTile.ets` 召回、MRR 和源码
区间召回均为 1.0，但三个锚点中只有一个 Oracle 文件，未过精度门禁。其余三例未召回
期望的 service、store 或 repository owner，暴露出启动 fallback 后升级、回调内异常
隔离、动作后权威状态刷新等生命周期语义尚未进入通用索引证据。聚合锚点召回和 MRR 为
0.25，精度 0.0833，源码区间召回 0.25，平均上下文 1,141.25 Token。

结果保存在 `docs/eval/homeassistant-unseen-sealed-holdout-result.json`。密封库存现为四个项目、
22 个案例，发布继续为 `deny_promotion`。本集合不得重跑；后续只能在独立夹具中复现
生命周期 transition、callback containment、refresh owner 与布局邻居精度，再使用新的
密封案例包观察泛化。

## 2026-07-19 第五项目机制召回观察

Home Assistant 暴露的四类失败只在独立 development 夹具中复现。ArkTS 摘要新增保守的
既有机制 marker：fallback/repository、callback/deserialization、action/lifecycle/state
write 与 async boundary。它们只描述当前源码中可检查的机制，不推断缺失修复；结构候选
使用最小 marker 覆盖保留互补 owner。高熵精确标识符无直接或图支持证据时会 abstain，
避免普通主题词替代未知标识符。`eval-context-capability` 无显式 `--limit` 时现在默认执行
完整案例集。

新增四个场景及十二个措辞变体后，开发门禁达到 22 个场景、66 个变体全部通过。锚点和
主锚点召回均为 1.0，MRR 为 0.9883，人工源码区间召回为 1.0，平均上下文 854.0152
Token，平均查询 383.6212 ms。随后从第五个独立 ArkTS 项目 Aigis 审查并密封四个真实
修复，摘要为
`474f5fe5bf038a214c2efdb6a30235d0eaac86ac5c1da9b20c66d0baa0a6e057`。

该集合只执行一次，结果为 1/4。TOTP URI 默认参数案例通过。滑动编辑状态传递与必填项
校验案例均召回目标 owner，但邻居过多；前者的源码窗口还偏离人工事件区间。OTP 生成后
使用计数持久化案例完全漏掉 `EntryAbility.ets`。聚合锚点召回 0.75、精度 0.25、MRR
0.625、源码区间召回 0.5，平均上下文 1,194.25 Token。结果说明机制 marker 改善了
跨项目候选召回，但尚不能稳定连接用户动作、状态交接与持久化边界，排序精度也未过门禁。

结果保存在 `docs/eval/aigis-unseen-sealed-holdout-result.json`。密封库存现为五个项目、
26 个案例，发布继续为 `deny_promotion`。Aigis 集合不得重跑或用于调参；下一轮必须在
独立夹具中复现 event-to-state handoff、validation-stop、persistence boundary 与邻居精度，
再使用新的密封包观察泛化。

## 2026-07-19 第六项目状态与持久化观察

Aigis 暴露的事件状态交接、校验停止和持久化边界只在独立 development 夹具中复现。
ArkTS 摘要新增保守的事件 handler、呈现调用、校验提前停止、显式存储写入，以及计数与
时间戳成对提交 marker。语言无关查询概念把症状映射到这些可检查机制；直接结构证据即使
同时带图来源也保持直接候选身份，图邻居仍受有界选择约束。

新增四个场景及十二个措辞变体后，开发门禁达到 26 个场景、78 个变体全部通过。锚点和
主锚点召回均为 1.0，MRR 为 0.9928，人工源码区间召回为 1.0，平均上下文 822.3077
Token，平均查询 320.6154 ms。随后从第六个独立 ArkTS 项目 harmonyos-games 审查并密封
四个真实修复，摘要为
`a7d9cca37f217a6d833d9054962bc6ba639c0075c32948de4f467b98e113a872`。

该集合只执行一次，结果为 1/4。偏好设置 context owner 精确通过。最佳分数生命周期和
颜色块邻接修改案例都把正确 owner 排在第一并覆盖人工源码区间，但各自返回三个无关
锚点，未过精度门禁。滑动后分数与终局状态不更新案例只返回 `About.ets`，完全漏掉
`NumberGameComp.ets`，其源码窗口失败源于候选未召回，而非窗口大小不足。聚合锚点召回
0.75、精度 0.375、MRR 0.75、源码区间召回 0.75，平均上下文 1,112 Token。

结果保存在 `docs/eval/harmonyos-games-unseen-sealed-holdout-result.json`。密封库存现为六个
项目、30 个案例，发布继续为 `deny_promotion`。该集合不得重跑或用于调参；下一轮只可
在独立夹具中复现抽象 gesture-to-state 召回和多余邻居精度，再使用新的密封包观察泛化。
该项目规模较小，只提供跨项目机制泛化证据，不代表大仓库性能结论。

## 2026-07-19 第七项目方法级上下文观察

harmonyos-games 暴露的抽象手势召回和邻居精度只在独立 development 夹具中复现。
ArkTS 摘要新增手势 callback 边界和索引集合写入 marker，并将 `restore` 纳入生命周期同步。
查询概念分别覆盖手势状态变化、邻接集合修改和生命周期持久化；最小结构覆盖优先保留同时
持有完整机制的 owner，不提高全局分数阈值。

新增三个场景及九个措辞变体后，开发门禁达到 29 个场景、87 个变体全部通过。锚点和
主锚点召回均为 1.0，MRR 为 0.9936，人工源码区间召回为 1.0，平均上下文 801.7011
Token，平均查询 312.931 ms。随后从第七个独立 ArkTS 项目 JustPDF 的 229 个提交中审查
并密封四个单 owner 修复，摘要为
`2cf6ddf75bd455d0c4851ee3df56cc53781534b72f949518e104f67f8e0a6c17`。

该集合只执行一次，结果为 1/4。空启动值消费案例通过。批注拖动仲裁召回 `PDFView.ets`
但位于第二名，携带三个批注邻居且窗口未覆盖 `handleViewAction`。快速翻页异步陈旧结果案例
完全漏掉 `PDFView.ets`。保存对话框案例把 `PDFAnnotationController.ets` 排在第一并满足
精度，但窗口没有落到 `pickSaveUri`。聚合锚点召回 0.75、精度 0.3125、MRR 0.625、
源码区间召回 0.25，平均上下文 1,150.5 Token。

结果保存在 `docs/eval/justpdf-unseen-sealed-holdout-result.json`。密封库存现为七个项目、
34 个案例，发布继续为 `deny_promotion`。该集合不得重跑或用于调参；下一轮只能在独立
夹具中复现异步导航 owner 召回、交互仲裁排序和方法级源码窗口对齐，再使用新的密封包
观察泛化。

## 2026-07-19 第八项目组合机制与方法范围观察

JustPDF 暴露的异步 owner 缺失、交互仲裁噪声和方法窗口偏移只在独立 development 夹具中
复现。查询概念新增异步状态顺序与触摸状态仲裁，但复用已有可检查 marker；组合结构证据
优先于通用操作名，显式文件或符号身份仍保持更高优先级。英文触发器改为词边界与有限
词形匹配，避免 `interaction` 误触发 `action`。源码摘录复用 ECMA callable 范围，机制
支持的方法先于词面窗口，并将同一源码文件的重复扫描合并为一次。

新增两个场景及六个措辞变体后，开发门禁达到 31 个场景、93 个变体全部通过。锚点和
主锚点召回均为 1.0，MRR 为 0.994，人工源码区间召回为 1.0，平均上下文 789.9462
Token，平均查询 435.5699 ms。随后从第八个独立 ArkTS 项目 FinVideo 的 134 个提交中
审查并密封四个单 owner 修复，摘要为
`8df142f386f2ba8f9ecbb0c9c0674fda541a9e6b7e952bef1794764d0fd7bd3b`。

该集合只执行一次，结果为 0/4。空触摸事件案例唯一召回 `PlayerPage.ets`，但窗口未落到
嵌套 ArkUI 回调。窗口清理案例把 `EntryAbility.ets` 排在第一且源码跨度通过，但保留两个
生命周期页面。文件夹媒体库案例漏掉 `MediaListVewModel.ets`。演员作品列表案例把
`PersonPage.ets` 排在第一，但携带通用列表、ViewModel 和测试噪声，且未命中 Builder
窗口。聚合锚点召回 0.75、精度 0.3958、MRR 0.75、源码区间召回 0.25，平均上下文
948.5 Token。

结果保存在 `docs/eval/finvideo-unseen-sealed-holdout-result.json`。密封库存现为八个项目、
38 个案例，发布继续为 `deny_promotion`。该集合不得重跑或用于调参；下一轮只能在独立
夹具中复现嵌套 DSL 回调窗口、条件数据加载召回、生命周期精度和 Builder 范围选择，
再使用新的密封包观察泛化。

## 2026-07-19 第九项目 ArkTS DSL 范围观察

FinVideo 暴露的四类失败只在独立 development 夹具中复现。ArkTS 行为摘要新增可检查的
索引触摸访问、条件分支数据源、生命周期清理、横纵轴和异步顺序保护 marker；查询概念只
组合这些源码证据，不推断缺失修复。源码范围适配器在标准 ECMA callable 之外识别链式
ArkUI 箭头回调，使嵌套事件处理和 Builder 方法可独立参与窗口选择。组件标识符被保守拆词，
但通用 Page/Screen 名不扩张；显式路径保护只接受用户原始标识符，负向和行为查询不启用。

新增四个场景及十二个措辞变体后，开发门禁达到 35 个场景、105 个变体全部通过。锚点和
主锚点召回均为 1.0，MRR 为 0.9896，源码区间召回为 1.0，平均上下文 764.5714 Token，
平均查询 520.0 ms。随后从第九个独立 ArkTS 项目 Wechat_HarmonyOS 审查并密封四个真实
修复，摘要为
`299c1db9c1932c0c0186cf3f7b60c993af3b57e6703bc571205b5cae3ac98672`。

该集合只执行一次，结果为 1/4。状态栏 owner 案例通过。音频采集生命周期案例把目标管理器
排在第一，但保留页面与测试噪声且未命中人工方法区间；键盘顶起工具栏案例只返回功能栏，
漏掉可复用 `Toolbar.ets`；搜索页键盘/返回键冲突召回目标页但位于第三名，并保留无关 owner
且窗口偏离事件处理方法。聚合锚点召回 0.75、精度 0.25、MRR 0.5833、源码区间召回
0.25，平均上下文 1,138.5 Token。

结果保存在 `docs/eval/wechat-unseen-sealed-holdout-result.json`。密封库存现为九个项目、
42 个案例，发布继续为 `deny_promotion`。该集合不得重跑或用于调参；下一轮只能在独立
夹具中复现可复用组件候选召回、音频异步生命周期 passage 精度和键盘/返回事件 owner
精度，再使用新的密封包观察泛化。

## 2026-07-19 第十项目角色与边界泛化观察

Wechat_HarmonyOS 暴露的三类失败只在独立 development 夹具中复现。ArkTS 行为摘要新增
严格命名的可复用 Toolbar 角色、媒体资源 acquire/release 配对以及键盘/返回边界 marker；
`ActionBar` 等业务动作组件不会被当作 Toolbar。结构 FTS lane 在宽查询饱和时仍保留独立
预算；两个强用户身份路径可以裁掉纯扩展尾部，但组件属性流存在时继续保留父子谱系。

新增三个场景及九个措辞变体后，开发门禁达到 38 个场景、114 个变体全部通过。锚点和
主锚点召回均为 1.0，MRR 为 0.9905，源码区间召回为 1.0，平均上下文 746.8684 Token，
平均查询 556.5351 ms。随后从第十个独立 ArkTS 项目 Siyuan Harmony 审查四个单文件真实
修复并生成密封摘要
`19a16ba06d8b322cc5f66098b1c27a375506560e58d1fa6ca606d31e89763900`。

该集合只执行一次，结果为 0/4。桌面键盘焦点和多记录分享 owner 被召回，但保留禁止
邻居且方法窗口偏离；升级解压案例只返回包配置，漏掉归档写入 owner；状态栏颜色解析
owner 被召回但排序过低且混入页面噪声。四个案例均未命中人工源码区间。聚合锚点召回
0.75、精度 0.2708、MRR 0.4583、源码区间召回 0.0，平均上下文 1,074.25 Token。

结果保存在 `docs/eval/siyuan-unseen-sealed-holdout-result.json`。密封库存现为十个项目、
46 个案例，发布继续为 `deny_promotion`。该集合不得重跑或用于调参；下一轮只能在新的
独立夹具中复现归档 I/O 候选召回、集合聚合精度、焦点与颜色 owner 精度和方法级窗口，
再使用新的密封项目观察泛化。

## 2026-07-19 第十一项目 I/O 与转换边界观察

Siyuan 暴露的归档候选缺失、聚合与焦点/颜色 owner 精度、方法窗口偏移只在新的独立
development 夹具中复现。ArkTS 摘要新增归档写入/解压边界、局部集合 fold、键盘可见性与
焦点状态、颜色转换 parser marker。源码摘录将查询支持的 callable 范围与已有范围合并，
而不是在存在旧范围时跳过机制方法。可复用间距概念同时移除 `shared/widgets/components`
通用词，只保留 `margin/padding` 源码证据，消除跨概念干扰。

新增四个场景及十二个措辞变体后，开发门禁达到 42 个场景、126 个变体全部通过。锚点和
主锚点召回均为 1.0，MRR 为 0.9915，源码区间召回为 1.0，平均上下文 726.373 Token，
平均查询 994.9683 ms。随后从第十一个独立项目 Termony 的 635 个提交中审查四个真实修复，
并生成密封摘要
`a7c9b512637b6fb43ffd900abf100b376537404d8639152663e5fa8b3710e761`。

该集合只执行一次，结果为 1/4。触摸坐标单位转换案例完整通过；空输出滚动案例召回正确
页面但未命中 read-loop 方法；剪贴板纯文本提取和启动权限串行化只返回 `module.json5`，
未召回 ArkTS owner。聚合锚点召回、精度和 MRR 均为 0.5，源码区间召回 0.25，平均上下文
721.25 Token。

结果保存在 `docs/eval/termony-unseen-sealed-holdout-result.json`。密封库存现为十一个项目、
50 个案例，发布继续为 `deny_promotion`。该集合不得重跑或用于调参；下一轮只能在新的独立
夹具中复现剪贴板记录提取、权限请求串行化、空结果循环窗口和元数据/实现区分，再使用新的
密封项目观察泛化。

## 2026-07-19 第十二项目行为所有者泛化观察

Termony 暴露的四类失败只在独立 development 夹具中复现。ArkTS 行为摘要新增剪贴板
内容读取、权限请求与结果保护、进程输出读取循环和运行时能力探测 marker；行为概念展开
会先剔除明确排除的负向子句。结构行为查询在没有路径重建时不再让通用身份日志 emitter
占用紧凑代码锚点；精确日志查询和已有路径查询保持原行为。ArkTS callable 范围解析也会
确认当前调用括号仍未闭合，避免把后续箭头表达式误并入前一个权限调用。

新增四个场景及十二个措辞变体后，开发门禁达到 46 个场景、138 个变体全部通过。锚点和
主锚点召回均为 1.0，MRR 为 0.9922，源码区间召回为 1.0，平均上下文 714.0 Token，
平均查询 1,195.2826 ms。随后从第十二个独立 ArkTS 项目 ClearChat 的 70 个提交中审查
四个真实修复，并生成密封摘要
`970f82133fc794cd0c542ccfb7f8f239830feb517f3df2871aa4be4b9645047c`。

该集合只执行一次，结果为 0/4。缓存淘汰 owner 和源码区间完整命中，但搜索相邻模块污染
精度；流式检查点 owner 排名第二且两个持久化方法窗口均未命中；初始化超时和 WebView
危险协议 owner 未进入候选。聚合锚点召回 0.5、精度 0.1875、MRR 0.375、源码区间召回
0.25，平均上下文 1,225.25 Token，平均查询 3,588.5 ms。

结果保存在 `docs/eval/clearchat-unseen-sealed-holdout-result.json`。密封库存现为十二个项目、
54 个案例，发布继续为 `deny_promotion`。该集合不得重跑或用于调参；下一轮只能在新的独立
夹具中复现大文件方法窗口、异步生命周期 owner、WebView DSL 安全 owner 和宽邻居精度，
再使用新的密封项目观察泛化。

## 2026-07-19 第十三项目并发与状态所有者观察

ClearChat 暴露的大文件持久化窗口、异步超时、WebView 安全策略和宽邻居精度只在独立
development 夹具中复现。ArkTS 摘要新增 Promise 写尾串行化、最终写屏障、超时竞争、
取消守卫、WebView 文件访问与危险协议拦截、容量淘汰扫描 marker。视觉“覆盖”概念要求
UI 图层或控件语境，避免把数据覆盖误识别成视觉重叠。

新增四个场景及十二个措辞变体后，开发门禁达到 50 个场景、150 个变体全部通过。代码
定位锚点和主锚点召回均为 1.0，MRR 为 0.9929，源码区间召回为 1.0，平均上下文
711.4133 Token，平均查询 1,466.8867 ms。随后从第十三个独立 ArkTS 项目 ccplayer 的
292 个提交中审查四个真实修复，并生成密封摘要
`1366b6a17fbeee8d2b38865b34252a6cec7f57d71991dc8e49f87fa3f7b7f7a5`。

该集合只执行一次，结果为 1/4。首帧、尺寸回调与 surface 可见性协调案例通过，并覆盖
一个人工区间；AVSession 重复释放 owner 仅作为第四个扩展锚点出现且没有源码摘录；首次
失败后的媒体源替换和 Prepared 状态控制资格 owner 均未召回。聚合锚点召回 0.5、主锚点
召回 0.25、精度和 MRR 均为 0.3125、源码区间召回 0.125，平均上下文 1,136.5 Token。

结果保存在 `docs/eval/ccplayer-unseen-sealed-holdout-result.json`。密封库存现为十三个项目、
58 个案例，发布继续为 `deny_promotion`。该集合不得重跑或用于调参；下一轮只能在新的独立
夹具中复现幂等资源清理、媒体源替换生命周期状态、Prepared 命令资格和实现相对示例页面
的排序，再使用新的密封项目观察泛化。

## 2026-07-20 第十四项目方法证据精度观察

ccplayer 暴露的四类失败只在新的独立 development 夹具中复现。方法证据查询只使用用户
原始查询中的有界术语，并要求至少三个方法体直接证据一致；强精确身份、概念组合、属性流
或结构行为竞争者可阻止方法候选过早独占焦点。明确要求排除 example、sample、demo 的
结果角色会在最终代码选择前过滤，不影响普通文件。

新增四个场景及十二个措辞变体后，开发门禁达到 54 个场景、162 个变体全部通过。平均
上下文 719.6111 Token，平均记忆准备 1,185.284 ms，平均查询 441.5247 ms。随后从此前
未参与调参的 Wake-HarmonyOS 项目审查四个真实修复，并生成密封摘要
`0ca1a2810280a686a77587c8e98c884c373ffbf6c4e85e17aa9aa08a43612873`。

该集合只执行一次，结果为 1/4。导入完成后的跨页面返回刷新链通过；直接命令 owner 已召回
且源码范围通过，但基础设施和展示邻居导致精度失败；编辑页视觉状态 owner 排名靠后且方法
窗口偏离；网络失败消息的网络层和页面层 owner 均未召回。聚合锚点与主锚点召回均为 0.75，
精度 0.2708、MRR 0.5833、源码区间召回 0.375，平均上下文 1,260.25 Token。

结果保存在 `docs/eval/wake-unseen-sealed-holdout-result.json`。密封库存现为十四个项目、
62 个案例，发布继续为 `deny_promotion`，Agent A/B 因 Context 门禁失败而不执行。该集合
不得重跑或用于调参；下一轮只能在新的独立夹具中复现命令 owner 精度、视觉状态方法窗口和
跨层错误契约召回，再使用新的密封项目观察泛化。

## 2026-07-20 第十五项目契约所有者观察

Wake-HarmonyOS 暴露的命令绑定、对比页面视觉状态和跨层错误契约问题只在新的独立
development 夹具中复现。ArkTS 摘要新增对象回调命令绑定、箭头旋转与状态切换、catch
返回边界和 UI 错误展示边界 marker。查询层分离对比子句与结果排除子句；`instead of`
保留为故障语义。高权重路径身份只使用用户直接词，语义扩展仍用于有界图谱谱系。

新增三个场景和九个措辞变体后，开发门禁达到 57 个场景、171 个变体全部通过。锚点召回
1.0、精度 0.9604、MRR 0.9938、源码区间召回 1.0，平均上下文 720.2281 Token，平均查询
454.8889 ms。CI 性能门禁同时通过：10 万实体候选命中 p95 为 11.346 ms，500 方法文件
增量刷新 p95 为 562.315 ms。

随后从此前未参与调参的 RayTV 审查四个真实修复，并生成密封摘要
`589240f57caefbf641a803e859a51635dd4dd0080f854bd412aa055c0d198a3f`。该集合只执行一次，
结果为 0/4。四个预期文件均被召回，但生成 `.preview` 源、Android Python 实现及同域
repository/service 邻居压低 Top-K 精度，四个方法区间均未命中。聚合锚点召回 1.0、主
锚点召回 0.75、精度 0.2708、MRR 0.4791、源码区间召回 0.0，平均上下文 1,304.25 Token。

结果保存在 `docs/eval/raytv-unseen-sealed-holdout-result.json`。密封库存现为十五个项目、
66 个案例，发布继续为 `deny_promotion`，Agent A/B 因 Context 门禁失败而不执行。该集合
不得重跑或用于调参；下一轮只能在独立夹具中复现生成物角色过滤、多语言实现偏好和大文件
方法窗口，再使用新的密封项目观察泛化。

## 2026-07-20 RayTV 后独立复现

只在与 RayTV 无关的合成夹具中新增四个场景、十二个措辞变体，分别验证正式源码优先于
预览生成物、查询显式指定语言时选择对应实现、完整 UI 机制所有者优先于同域薄包装层，
以及 500 行 ArkTS 文件尾部的方法窗口。生成物路径由统一策略分类：学习期跳过明确的
`.preview`、`.hvigor`、cache 和 generated 目录；查询期对旧索引保留兼容过滤，仅在
没有正式候选时回退生成物。语言过滤只在正向查询明确命名一种语言且存在匹配候选时启用。

同域精度没有按 page/service/repository 文件名硬编码，而是新增受保护异步动作概念：
查询要求重复提交保护、pending 状态或 finally 复位时，候选必须同时具备条件分支、状态
写入和异步边界。负向子句协议补充 `omit/omitting`。大文件仍返回已有 callable 范围内
最多 40 行，不扩大任意文件前缀。

完整开发门禁达到 61 个场景、183 个变体全部通过。锚点召回 1.0、Oracle 精度 0.9478、
MRR 0.9943、源码区间召回 1.0，平均上下文 722.2951 Token，平均查询 472.3005 ms。
CI 规模门禁通过：10 万实体、30 万边下候选命中 p95 为 10.02 ms，500 方法文件增量刷新
p95 为 578.846 ms。RayTV 未重跑，发布仍为 `deny_promotion`；下一步必须使用新的独立
密封项目验证泛化，通过后才可进行 Agent A/B。

## 2026-07-20 第十六项目控制器与平台边界观察

从此前未参与开发或调参的 MPL-2.0 ArkTS 项目 FlameChase 审查三个真实修复：自定义弹窗
关闭控制器、奖励偏好恢复键和 ArkUI-X 深色模式平台门禁。三个完整前置 revision 均先独立
归档，再以摘要 `51784c6b80b0b0baf68e85136cec638f4351a0ea8f8325319165b9007dbe965c`
密封；该集合只执行一次。

结果为 0/3。奖励恢复和平台门禁都召回预期文件，但前者排名第二且源码窗口偏离，并保留了
展示页；后者命中精确源码区间，但三个邻居把精度降至 0.25。弹窗案例完全漏掉实际页面，
只返回任务模型和薄 PromptAction helper，属于候选生成缺口。聚合锚点召回 0.6667、精度
0.25、MRR 0.3333、源码区间召回 0.3333，平均上下文 1,109.3333 Token，平均查询
641.6667 ms。

结果保存在 `docs/eval/flamechase-unseen-sealed-holdout-result.json`。密封库存现为十六个项目、
69 个案例，发布继续为 `deny_promotion`，Context 失败后未执行 Agent A/B。该集合不得重跑
或用于调参；后续只能在独立夹具中复现 helper 间接调用下的控制器 owner、持久化键契约
窗口和平台能力 owner 精度，再使用新的密封项目观察泛化。

## 2026-07-20 FlameChase 后独立复现

三个失败类只在与 FlameChase 无关的合成业务中复现，首次基线为 2/9。实现没有加入项目名、
路径、任务措辞、Oracle 或案例阈值：ArkTS 摘要新增可检查的 UI 回调绑定、持久化读取键契约
和平台敏感 UI 契约；查询只在用户明确要求实际 caller/owner 时，对 Controller、Helper、
Adapter、Bridge、Service、Repository 角色执行最多一跳反向调用扩展，并最多保留两个具有
真实 UI 回调绑定的 caller。持久化和平台场景按完整契约覆盖选择 owner，避免通用方法名或
同域展示页先占满上下文。

三个新增场景、九个措辞变体达到 9/9；七个相关旧场景、二十一个变体保持 21/21。完整开发
门禁为 64 个场景、192 个变体全部通过，锚点召回 1.0、Oracle 精度 0.9504、MRR 0.9945、
源码摘录召回 0.9844、源码区间召回 1.0，平均上下文 721.5365 Token，平均记忆准备
1,418.1198 ms，平均查询 494.6406 ms。

CI 规模门禁同时通过：10 万可搜索实体、8 万符号、30 万图边下候选命中和缺失查询 p95
分别为 10.632 ms 和 19.334 ms，单文件增量刷新 p95 为 223.003 ms，500 方法文件为
621.899 ms，图双向查询均命中复合索引。全量 646 个测试在受限沙箱内只有两个本机端口
绑定错误；对应测试文件在允许绑定 `127.0.0.1` 后 3/3 通过。

FlameChase、RayTV、Wake 及其他已消费密封集合均未重跑或修改。发布仍为
`deny_promotion`；下一步只能对本轮抽象修复进行代码审查，并在新的独立项目上先审查、
再密封、只执行一次，之后才决定是否进入 Agent A/B。

## 2026-07-20 第十七项目外部泛化观察

从此前未参与开发或调参的 MIT 许可 ArkTS 项目 LinysBrowser_NEXT 中审查三个真实修复，
分别覆盖网站定位权限弹窗取消、非 2-in-1 平台底部避让和超大 WebState 恢复保护。每个
案例均使用完整修复前 revision，Git 审计确认 1、2、1 个预期变更文件。案例以摘要
`7b337f701b4545df9abec518af691936dee2264510cc799e6342791b41826ea3`
密封后只执行一次。

结果为 0/3。定位权限文件被召回但排在第 4，前三名是通用弹窗承载、另一权限弹窗和弹窗
管理器，属于候选存在但 subtype/owner 精度不足。平台避让只返回标题栏组件，未召回包含
`deviceInfo.deviceType` 与底部高度表达式的页面 owner。WebState 恢复则返回快捷键、书签、
扩展和历史索引模块，完全漏掉读取保存状态并调用 WebView 恢复的 tabs owner。

聚合锚点召回 0.3333、主锚点召回 0、Oracle 精度 0.0833、MRR 0.0833、源码摘录与源码
区间召回均为 0，平均上下文 1,134 Token，平均记忆准备 6,232 ms，平均查询 1,000 ms。
结果保存在 `docs/eval/linysbrowser-unseen-sealed-holdout-result.json`。密封库存现为十七个
项目、72 个案例，发布继续为 `deny_promotion`，未执行 Agent A/B。

该集合已消费，不得重跑、修改或用于调参。下一阶段只能在新的独立夹具中抽象复现三类
能力缺口：同类弹窗中的具体权限 owner 精度、被通用 UI 词遮蔽的平台布局 owner，以及
带资源上限的保存状态读取保护。修复必须只依赖结构语义，再由另一个新密封项目验证。

## 2026-07-20 多阶段检索第一阶段

LinysBrowser 观察后没有继续添加针对性 marker、项目词或排名阈值，而是先建立长期检索
架构。新增可替换的 `RankFusionPort`，以加权 Reciprocal Rank Fusion 融合现有 SQLite
FTS5 有界候选通道。各通道的 BM25 原始分数仍保持局部可比，跨通道只融合名次；现有
owner scorer 继续作为独立下游重排层。完整查询审计新增每个候选的融合分数、最佳名次、
支持通道及逐通道贡献，紧凑 Context 不增加这些诊断字段。

项目中立的融合契约、兼容和审计测试通过。完整开发门禁保持 64 个场景、192 个变体全部
通过：锚点召回 1.0、MRR 0.9945、源码区间召回 1.0，平均紧凑上下文 721.5365 Token，
平均记忆准备 1,431.5521 ms，平均查询 502.276 ms。CI 规模门禁在 10 万实体、8 万符号、
30 万图边下通过，候选命中/缺失查询 p95 为 10.226/17.61 ms，500 方法文件增量刷新 p95
为 592.658 ms。

全量发现运行 650 个测试，受限沙箱只有两个预期的本机端口绑定错误；对应完整模块在允许
绑定 `127.0.0.1` 后 3/3 通过。Python 500 行门禁与编译检查通过。所有已消费密封集合均
未重跑或修改，发布继续为 `deny_promotion`。本阶段只证明融合边界和开发兼容性，不证明
外部泛化问题已经解决；下一阶段是字段化 passage 召回，并将候选 Recall@20 与 owner 重排、
源码窗口选择分别度量。

## 2026-07-20 多阶段检索第二阶段

本阶段增加可重建的 `code_passages`，将文件、符号和 callable 分开，并将路径/符号身份、
业务与结构语义、最多 36 个方法体证据词、最多 24 个字符串键分别索引。六个 SQLite
FTS5 通道只在各自字段内使用 BM25，再通过嵌套加权 RRF 融合名次；passage 继承源码
digest 与原子 generation，不保存源码正文，也不是新的事实来源。

首次把扩展候选直接交给现有 owner 重排时，已知开发集回归 5/192。这不是继续调一个阈值
的问题，而是候选分布改变后重排器尚未校准。因此采用影子发布：完整 Context 运行并审计
字段候选，紧凑 Context 仍使用第一阶段正式候选，Agent 输出与 Token 预算不受影响。

最终完整开发门禁保持 64/64 场景、192/192 变体通过：锚点召回 1.0、Oracle 精度
0.9504、MRR 0.9945、源码区间召回 1.0、平均紧凑上下文 721.5365 Token。字段候选文件
Recall@20 为 0.8925，说明架构可观测但质量尚不足以晋级。CI 规模门禁在 10 万实体、8 万
符号、30 万边下通过；候选命中/缺失 p95 为 30.514/55.063 ms，500 方法增量刷新 p95 为
2,127.179 ms。全量发现 656 个测试，仅有受限沙箱下两个预期本机端口错误，对应模块在
允许端口绑定后 3/3 通过。

所有已消费密封集合均未重跑或修改，发布仍为 `deny_promotion`。下一阶段先在无项目词的
独立夹具上补语言语义适配和字段候选召回，再单独校准 owner 重排；两层及新的外部门禁
共同通过前，不将 passage 候选切换为正式服务路径。

## 2026-07-21 多阶段检索第三阶段

本阶段没有增加项目关键词或继续调 owner 阈值，而是补齐语言适配器 IR。`semantic-index/v1`
新增可选且有界的 `SemanticMechanism`：operation、guard、resource bound、callback binding、
platform predicate、persistence read/write。每条证据必须绑定本地 symbol，行号必须落在该
symbol 范围内；只保存规范化词、类别、行号、置信度与短 detail，不保存源码正文。

ArkTS 与 TypeScript 静态适配器升级到 `1.1`，仍通过统一 registry 接入。SQLite 新增
`code_symbols.mechanism_evidence`，可重建 passage 新增独立 `mechanism_terms` 字段和
`semantic_mechanism_fts` 影子通道。搜索 schema 升级为 `fts-v4`；旧 passage schema 会被
丢弃并由源码行重建，不迁移或修改事实、经验和用户业务语义。

完整开发门禁保持 64/64 场景、192/192 变体通过：锚点召回 1.0、Oracle 精度 0.9504、
MRR 0.9945、源码区间召回 1.0、平均紧凑上下文 721.5365 Token，平均准备/查询为
2,086.1771/631.1094 ms。影子候选文件 Recall@20 从 0.8925 提升到 0.8980，提升有限，
因此仍不晋级正式服务路径。

CI 规模门禁在 10 万实体、8 万符号、30 万边下通过：候选命中/缺失 p95 为
10.956/20.271 ms，单文件和 500 方法增量刷新 p95 为 227.843/812.501 ms。query 测试
62/62、Context 测试 40/40、语义与 passage 聚焦测试 33/33。全量发现运行 660 个测试，
仅有受限沙箱下两个预期端口错误，对应模块在允许回环端口后 3/3 通过。

所有已消费密封集合均未重跑或修改，发布继续为 `deny_promotion`。下一阶段是分层的
file -> callable -> source range 定位及 owner 重排校准；只有候选召回、最终精度、回归、
规模和一个新外部密封项目同时通过后，才允许 passage 影子通道晋级。

## 2026-07-21 多阶段检索第四阶段初始影子实现

本阶段先建立可测的 file -> callable -> source range 边界，而没有把字段候选接入正式
Context。`sqlite_hierarchical_localizer/v1` 只接收已经过意图门控的代码候选：最多选八个
文件并限制同目录候选，随后只读取这些文件的 callable；对于最强 callable，最多补充一跳
静态调用/await/回调/组件或属性流的 caller owner。不会递归遍历图，也不会返回根因。

方法排序使用既有融合候选、符号和业务词、方法体/字符串键、以及 `SemanticMechanism`。
命中 guard、resource bound、callback、platform 或 persistence 机制时，输出范围会收紧为
仍在 callable 内的少量表达式行。完整 `context --json` 在
`query_audit.hierarchical_localization` 中暴露这些输入、限制和 provenance；紧凑 Context
及正式候选/owner 路径没有变化。

项目中立契约覆盖目录多样性、资源上限表达式窗口和一跳 caller owner。已消费密封集合未重跑
或修改，发布仍为 `deny_promotion`。下一子阶段必须先加入独立 callable/owner/range 指标，
再运行完整回归、规模门禁和一个新的密封项目；不得以本阶段契约结果调整外部项目阈值。

## 2026-07-21 分层定位影子评测

`eval-context-capability` 现在对每个冻结案例执行两次同一问题查询：紧凑 `context --compact`
仍是唯一门禁输入；额外的完整 `context --json` 只读取
`query_audit.hierarchical_localization`，用于记录文件、callable、一跳 owner 与源码范围的独立
指标。两条查询共享同一冻结工作区和临时 SQLite Memory，不改变用户查询、正式候选路径或
紧凑 Token 预算。

评测报告的 `capability_profile.hierarchical_localization` 固定为 `informational`，分别给出
`file_recall`、`callable_recall`、`owner_recall`、`owner_precision`、`range_recall` 与
`average_audit_elapsed_ms`。这避免用文件命中替代方法、调用者或具体表达式质量；也避免在尚无
人工 owner/range Oracle 时把缺失标注当成系统退化。

在最小开发日志场景的三种表述上，紧凑门禁为 3/3 通过，影子文件召回为 1.0，完整审计平均
耗时为 3,125.6667 ms。该案例没有 callable、owner 或范围 Oracle，后三项保持 `null`。结果
仅证明评测管线和非干扰边界可用，不构成晋级证据；后续必须新增独立标注的开发案例，跑完整
回归与规模门禁，再以一个新密封项目验证泛化。

随后加入 Snapshot 开发场景，三种表述分别覆盖 payload 资源上限、`restoreSnapshot` callable、
`refreshSnapshot` 一跳 caller 和 callable 范围。首次评测暴露了一个阶段语义问题：图边已经
入库，但 owner 既是直接 callable 时，在最终 callable 去重中丢失了 `graph_depth: 1` 标记。
修复不扩大图深或候选数，而是保留独立、上限为 16 的 `graph_owner_candidates` 审计阶段；owner
指标直接读取该阶段。固定的六个 graph seeds 也按直接候选、精确符号、机制证据、原始排名的
优先级选取，避免宽泛 guard 机制抢占全部预算。

修复后该场景 3/3 通过，影子 file/callable/owner/range recall 与 owner precision 均为 1.0；
平均紧凑 Context 为 1,012.6667 Token，完整审计平均为 633.6667 ms。结果仍仅是合成开发
证据，不触发晋级或外部泛化结论。

## 2026-07-23 第四阶段完整开发与规模验证

完整未密封开发集现有 65 个场景、195 个变体，全部通过紧凑 Context 门禁：代码锚点召回和
主锚点召回均为 1.0，字段候选文件 Recall@20 为 0.9104，锚点精度为 0.9404、MRR 为 0.9919，
源码区间召回为 1.0，平均紧凑 Context 为 726.0154 Token。新增 Snapshot 场景未导致既有
192 个变体回归。

完整审计的分层指标保持 `informational`，并在报告中分别给出每一项的有效 Oracle 案例数，
避免将无标注案例或少量样本平均成虚假的质量结论。当前 file/callable/range recall 分别为
0.9496、0.9349、0.9320；owner recall/precision 均为 1.0，但只有 Snapshot 的 3 个变体
提供 owner Oracle。因此此结果只说明专用评测链路正确、且没有开发回归，不足以晋级服务路径。

CI 规模门禁也通过：10 万可搜索实体、8 万符号、1.5 万日志、30 万图边，候选命中/缺失
查询 p95 为 9.572/17.816 ms；单文件和 500 方法增量刷新 p95 为 280.338/829.282 ms。查询
计划继续命中 qualified symbol、file symbol 与双向 edge 的复合索引。未运行或修改任何已消费
密封集，发布继续为 `deny_promotion`。

## 2026-07-23 第四阶段多关系 owner 校准

一跳 owner 不再假定所有关系都是 `code_symbol -> code_symbol`。本阶段将 owner 获取拆成有界
适配器：直接调用、await 和回调注册从 symbol 边读取；`passes_property` 与
`renders_component` 这类 `code_file -> component` 边则只投影回源文件中唯一优先的 `build`
callable。两条路径都最多使用六个 seed 和十六个 owner，不递归展开，也不进入紧凑服务输出。

新增两个已审阅开发场景并分别使用三种表述：`CallbackAuditPage` 校准
`registers_callback`，`TimelineRow -> EventBubble` 校准属性流 owner 投影。回调场景声明
`require_expected_anchors: false`，因为它只测完整审计；组件流场景保留紧凑锚点、区间和精度
门禁，确保投影没有替代服务检索。

两场景共 6 个变体全部通过。影子 callable/owner/range recall 和 owner precision 均为 1.0，
完整审计平均 603.1667 ms；组件流的紧凑门禁也保持 3/3 通过。该覆盖仍是合成开发证据，不能
据此提升服务路径；下一步仍需完整开发回归、规模复核与新的外部密封项目。

同一适配器已纳入 `eval-scale` CI 基线。在 10 万可搜索实体、8 万符号、30 万边下，直接
symbol owner 与文件属性流投影一起执行的 `hierarchical_one_hop_owners` p95 为 8.481 ms，
低于 150 ms 的影子审计 SLO。`passes_property` 的目标边查询命中
`idx_memory_edges_project_valid_target_relation`；源文件 callable 查询复用既有 file-symbol
索引。该 SLO 仅约束完整审计，紧凑 Context 路径仍不调用此适配器。

下一阶段不是继续调优当前开发集，而是补齐多类 reviewed callable/owner/range Oracle，并在
完整门禁和 CI 规模持续通过后，审查、冻结并只运行一次新的外部项目。外部项目的 Oracle
不得反向改变上述检索、图或排序策略。

## 2026-07-23 第十八项目外部泛化观察

选择此前未用于开发或调参的 `zcg741/chengyu-game` 原生 ArkTS 项目，从完整 Git 历史审查并
冻结三个单文件真实修复：rawfile UTF-8 解码、收藏详情弹窗的残留状态写入、以及 ArkUI router
API 迁移。修复前后 revision 与每个预期变更文件均在密封前验证；密封摘要为
`c3e155b7dfec600181b00fa063df560ba92a2e63f871911f3d3c859013bd4728`。

该集合仅执行一次，结果为 0/3。聚合锚点/主锚点召回为 0.6667，Oracle 精度为 0.1667，MRR 为
0.2778，源码摘录和区间召回均为 0.6667，平均紧凑 Context 为 1,001.3333 Token。UTF-8 案例
在候选生成阶段漏掉数据服务；弹窗和 router owner 均召回了精确范围，但分别保留同域页面或
无关 entry/service 邻居，导致精度门禁失败。

结果固定在 `docs/eval/chengyu-game-unseen-sealed-holdout-result.json`。不运行 Agent A/B，
不重跑或修改该集合，也不以项目词、文件名或任务措辞调参。后续只能在独立开发夹具中复现资源
解码候选召回与同域 owner 精度，再使用另一未消费密封项目观察泛化。
