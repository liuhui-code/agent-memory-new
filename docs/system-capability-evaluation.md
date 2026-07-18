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
  "min_source_span_recall": 1.0,
  "require_abstention": false,
  "required_evidence_gaps": []
}
```

未声明 Oracle 的能力只报告 `informational`，不会因为“有一些结果”就伪装成通过。
因此代码定位、日志图、经验检索、因果上下文和源码证据可以分开判断。源码摘录正文只在
临时查询进程中使用；能力观察与持久化报告只保存路径、命中、计数、耗时和 Token。

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

## 内置十案例能力集

`docs/eval/system-capability-cases.json` 配合
`docs/eval/fixtures/system-capability/` 提供最小、可审查、与外部项目无关的 ArkTS 能力集：

- 2 个日志案例：正确日志发射点、显式排除的弱相关日志及当前源码摘录。
- 2 个经验案例：可复用 procedure 进入主 lane，纠正经验只进入 guard lane。
- 2 个因果案例：从精确日志发射点返回有界调用候选、关系和禁止分支检查。
- 1 个跨组件案例：验证直接组件与一跳依赖组件都进入 Top-K 和源码区间。
- 1 个日志密集案例：验证日志命中不会挤掉发射点与服务源码摘录。
- 1 个组件属性流案例：验证叶子组件可沿属性绑定反向找到两层计算与透传组件。
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
`informational`；对应能力由上面的内置十案例集单独门禁，不能用代码定位结果替代。

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
