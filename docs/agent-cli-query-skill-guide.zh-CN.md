# Agent CLI 调用 Query Skill 中文指南

本文说明本地 Agent CLI 如何调用 `agent-memory-query`，充分利用当前记忆系统完成两类核心工作：

1. 根据用户描述的问题定位故障。
2. 基于当前代码、代码图和通用设计原则给出可执行的代码设计。

正常使用时，用户只需要描述目标、约束和可用证据。Agent 负责选择 Query Skill 协议、调用 `tools/agent_memory.py`、读取 JSON、检查源码并执行验证。用户不需要手写 `design-intent`、Delta Graph 或 Hypothesis Ledger。

## 1. 使用前提

在目标项目根目录安装本地 Skill 和运行时：

```bash
python install.py --project . --local-skills
python tools/agent_memory.py doctor --project .
```

安装后应存在：

```text
.agent-skills/agent-memory-query/
tools/agent_memory.py
.agent-memory/projects/<project_id>/memory.db
```

如果 Agent CLI 支持显式 Skill 名称，可以直接要求使用 `agent-memory-query`。如果不支持显式名称，只需在自然语言中同时说明“先查询当前代码、代码图、日志图和经验，再定位/设计”，Skill 的描述会触发路由。

首次处理项目或目标区域尚未学习时，先让 Agent 调用 `agent-memory-learn`：

```text
先学习 entry/src/main/ets/pages/ProfilePage.ets 周围两层依赖，检查解析统计，
然后使用 agent-memory-query 定位个人资料页白屏问题。
```

查询结果出现 `missing_code_anchor`、`missing_dependency_edge` 或大量未学习文件时，不应继续依赖历史经验猜测，应先补充学习范围。

## 2. Query Skill 如何路由

`agent-memory-query` 是一个薄路由层。它只加载与当前目标相关的一份协议，不会把所有记忆和规则塞入上下文。

| 用户目标 | Query Skill 协议 | 首选命令 |
|---|---|---|
| 理解文件、符号、路由、资源或当前行为 | Code Understanding | `context` |
| 定位错误、白屏、崩溃、日志或线上事故 | Incident Diagnosis | `context`，每个候选原因单独查询 |
| 评估改动影响、回归风险和测试范围 | Change Impact | `impact-scope` |
| 设计功能、重构、接口、状态流和模块边界 | Repository-Grounded Design | `design-assist` |
| 判断历史经验、纠正或冲突是否可信 | Evidence Policy | `context` / `search` |

同一个任务可能包含多个意图，但 Agent 应先选择一个主目标。例如“修复白屏并重构 ProfileService”应先定位根因，验证后再进入设计流程，不能用重构方案替代故障诊断。

## 3. 推荐的 Agent CLI 总提示词

可以把下面内容加入项目 `AGENTS.md`，或在任务开始时发送给 Agent：

```text
本项目已安装 Agent Memory。处理问题定位、代码理解、影响评估或代码设计时：

1. 优先使用 agent-memory-query，不要直接凭历史对话下结论。
2. 所有运行时调用使用 tools/agent_memory.py 和 --json。
3. 证据优先级：用户明确约束 > 当前源码/配置 > 当前代码图和代码日志 >
   运行日志/Incident > 语义纠正 > 已验证经验 > 普通经验。
4. 先读取 query_handoff、当前源码锚点和原始关系边；Runtime 不提供诊断结论。
5. 原始关系边只能作为待检查线索，不能报告为调用链或根因。
6. 设计任务先调用 design-assist；重要设计再执行 prepare/check/compare/verify。
7. 不因缺少图边就断言没有依赖；必须报告覆盖缺口。
8. 只把必要证据注入上下文，避免输出整份 JSON 或完整日志。
```

## 4. 问题定位：用户如何发起

推荐把症状、发生条件、最近变化和可用日志写清楚，但不需要预先判断原因：

```text
使用 agent-memory-query 定位这个问题：个人资料页首次进入白屏，返回后再次进入正常。
已知发生在登录成功后的首次路由，最近修改了 ProfileService 和会话恢复逻辑。
先查询当前代码、代码日志、关系路径和历史纠正；由你在本次 Agent 会话中建立多个候选假设，
不要把 Runtime 排序或最近经验直接当根因。选择最能区分候选的检查，验证后再修改。
```

有日志文件时：

```text
使用 agent-memory-query 定位个人资料页白屏。
临时日志在 /tmp/profile-runtime.log。日志只用于本次定位，不持久化原文。
请直接读取流水日志，先使用 query_handoff 中的日志关键词缩小范围。
形成多个候选原因后逐个查询相关日志代码和源码，自行推测调用链与因果链。
```

## 5. 问题定位：Agent 应执行的流程

### 5.1 获取第一轮上下文

```bash
python tools/agent_memory.py context \
  --project . \
  --query "个人资料页首次进入白屏，登录成功后 profile load failed" \
  --json
```

Agent 应按以下顺序消费结果：

1. `query_handoff.log_keywords`：用于搜索临时流水日志。
2. `query_handoff.log_anchors`：代码日志模板、logger、事件、阶段和位置。
3. `query_handoff.code_anchors`：首批当前源码入口。
4. `query_handoff.path_context`：强日志锚点对应的当前图候选路径、预期日志、边来源和缺口。

`path_context.activated=true` 时也不能直接选择第一条路径。Agent 应逐条比较
`expected_log_anchors` 与临时日志中的真实顺序、进程/会话标识、缺失事件和反证；
无法区分时保留多条路径。`structural_score` 只评价当前图结构与来源质量，不包含经验权重，
也不是根因概率。没有候选路径表示图证据不完整，不表示该调用没有发生。
4. `semantic_facts` 和纠正信息：业务含义与适用边界。
5. `reflections`、`episodes`：历史经验，只能辅助。
6. `edge_matches`：原始一跳关系，只用于导航。

不要按照数组位置直接认定第一项是根因。评分只表示检索相关性和证据质量，不等价于因果性。

### 5.2 Agent 直接分析临时流水日志

Runtime 不读取临时日志。Agent 使用 `rg`、`sed` 或其他本地工具，先按
`log_keywords` 找到关键行，再检查前后时间窗口、进程、logger、事件、错误码、
request/session/trace 标识、最后成功阶段和缺失阶段。

Agent 根据观察至少提出两个不同机制的可证伪候选原因，并记录支持证据、反证、
缺失证据和最小区分性检查。

### 5.3 逐个候选查询并检查源码

一次只查询一个候选原因：

```bash
python tools/agent_memory.py context \
  --project . \
  --query "ProfileService 请求成功但响应解析失败，定位解析函数和失败日志" \
  --json
```

Agent 根据 `code_anchors`、文件、符号和日志锚点打开源码，至少检查：

- 日志语句所在函数是否仍与学习结果一致。
- 调用者、状态读写、异步边界和错误分支。
- 当前配置、路由、资源和权限条件。
- 图中缺少但源码实际存在的动态调用或回调。
- 历史纠正是否只适用于旧版本或其他业务域。

源码与记忆冲突时，以源码为准，并把旧记忆作为待治理对象，而不是强行解释源码。

建议代码日志至少包含：

```text
timestamp process level event_name trace_id span_id parent_span_id
request_id/session_id error_code reason result route/resource
service.name service.version service.instance.id
```

不要为了“日志更丰富”在每一行增加字段。优先补充任务开始、关键分支、外部调用失败和最终结果四类日志。

### 5.4 由 Agent 推测调用链和因果链

Runtime 到此只完成上下文供给。Agent 用当前源码确认调用关系，用日志时序、
关联标识、分支机制和反证推测因果链，并在当前 CLI 会话中建立工作表：

```text
候选假设
引用的 evidence_refs / 源码位置 / 日志行
支持证据
反证
缺失证据
下一项区分性检查
```

执行原则：

1. Agent 优先执行能排除多个候选的检查。
2. 检查后重新运行窄查询，补充精确文件、符号、错误码、route 或 trace id。
3. 候选被源码或运行证据否定时标记为 rejected，不要换一种措辞继续保留。
4. 没有新增证据时停止扩展查询，明确报告证据限制。

因果等级：

| 等级 | 可以怎样表述 |
|---|---|
| `association` | “这是相关线索，需要检查” |
| `supported` | “机制、关联身份和时间顺序支持该假设，仍需干预验证” |
| `verified` | “定向干预后，前后证据验证了该根因” |
| `rejected` | “当前证据否定该候选” |

### 5.5 记录紧凑 Incident，而不是归档完整日志

需要跨任务保留定位结果时：

```bash
python tools/agent_memory.py incident-trace \
  --project . \
  --symptom "个人资料页首次进入白屏" \
  --log-file /tmp/profile-runtime.log \
  --json
```

Incident 只保存短日志摘要、事件、代码锚点、关系证据和压缩 Span Graph。确认修复后记录三类不同信息：

```bash
python tools/agent_memory.py incident-trace-status \
  --project . \
  --id 12 \
  --status resolved \
  --resolution "首次进入页面恢复正常" \
  --intervention "将会话恢复等待移动到 ProfileService 初始化边界" \
  --verification-evidence "修复前 20 次复现 8 次；修复后 50 次未复现，相关测试通过" \
  --json
```

只有 resolution 没有 intervention 和 verification evidence 时，证据最多是 supported，不能升级为 verified。

### 5.6 修改前后检查影响范围

修改前：

```bash
python tools/agent_memory.py impact-scope \
  --project . \
  --files entry/src/main/ets/service/ProfileService.ets \
  --query "修复首次加载时会话恢复竞态" \
  --json
```

修改后也可按 Git 基线检查：

```bash
python tools/agent_memory.py impact-scope --project . --base HEAD~1 --json
```

Agent 应读取 reverse dependents、outgoing dependencies、coverage gaps 和 verification checklist。图只做有界遍历；未学习文件不能被解释为低风险。

测试完成后记录紧凑反馈，不保存测试日志正文：

```bash
python tools/agent_memory.py impact-feedback \
  --project . \
  --files entry/src/main/ets/service/ProfileService.ets \
  --executed-tests ProfileServiceTest \
  --outcome pass \
  --json
```

### 5.7 问题定位的停止条件

满足以下任一条件时停止继续检索：

- 已有 verified 假设，且回归检查通过。
- 所有候选均被 rejected，需要采集新的外部证据。
- 连续查询没有新增证据，`stop_reason` 表明低新颖度或无新结果。
- 缺少运行日志、复现条件或未学习代码，继续推理只会增加猜测。

最终答复必须分开写：当前事实、候选/结论、反证、改动影响、验证结果和剩余不确定性。

## 6. 代码设计：用户如何发起

推荐提示词：

```text
使用 agent-memory-query 设计个人资料缓存。
目标：降低重复网络请求；范围限制在 ProfileService 和数据层；
不能把持久化逻辑放进页面；必须保持现有公开 API 兼容；
验收标准：缓存命中不发网络请求，过期后刷新，失败可回退。
请先基于当前代码和代码图识别责任边界，再用通用设计原则和适用条件评估模式。
先给最小可行方案；只有存在实质性权衡时才给第二方案。
```

用户最好提供四类信息：

- `目标`：系统要获得什么行为。
- `范围`：允许修改哪些模块或边界。
- `约束/排除项`：兼容性、性能、技术和组织限制。
- `验收标准`：可以怎样验证设计成立。

## 7. 代码设计：简单流程

大多数设计先调用：

```bash
python tools/agent_memory.py design-assist \
  --project . \
  --query "设计个人资料缓存，保持 ProfileService 公开 API 兼容" \
  --mode design-only \
  --scope "ProfileService 和数据层" \
  --constraint "页面不得拥有持久化逻辑" \
  --constraint "不得破坏现有调用方" \
  --acceptance "缓存命中不发网络请求" \
  --acceptance "过期后刷新且失败可回退" \
  --exclude "全局缓存框架" \
  --json
```

`--scope`、`--constraint`、`--acceptance` 和 `--exclude` 可以重复。

Agent 应按顺序读取：

1. `current_design`：当前模块、入口、责任和依赖事实。
2. `design_guidance.forces`：变化、耦合、状态、失败和兼容性压力。
3. `existing_patterns`：源码结构中已经观察到的模式信号。
4. `pattern_candidates`：带前提与禁忌条件的可选策略。
5. `principle_checks`：单一职责、依赖方向、状态所有权、接口稳定性等检查。
6. `required_decisions`：仍需用户或源码证据解决的设计决策。
7. `delta_template`：未声称成立的最小变更模板。

`existing_patterns` 表示当前结构中观察到了某种形态，不表示它一定正确。`pattern_candidates` 是条件化策略：

- `applicable`：已有足够结构和约束支持考虑。
- `needs_evidence`：缺少适用证据，不能直接采用。
- `caution`：目标约束与模式常见前提冲突。

模式名称永远不能单独成为设计理由。设计理由必须落到当前责任边界、变化方向、依赖、状态、失败模式和验证方式。

## 8. 代码设计：完整控制循环

跨模块、公共 API、状态所有权或重要运行路径变化，应使用完整流程。

### 8.1 Agent 内部整理 Intent 和 Contract

Agent 从自然语言生成 `design-intent/v1` 和可选 `design-contract/v2` 临时文件。用户只需确认未解决的业务权衡，不需要编辑 JSON。

Intent 至少表达：目标、范围、排除项、硬约束、验收标准和开放问题。Contract 用场景描述约束与质量要求，并为后续覆盖检查提供稳定 id。

### 8.2 构建候选无关的基线

```bash
python tools/agent_memory.py design-prepare \
  --project . \
  --intent /tmp/design-intent.json \
  --contract /tmp/design-contract.json \
  --json
```

Agent 必须先读 repository model 的 topology、ownership、behavior、data、failure、runtime 和 change 视图，再写候选。候选自己的路径不能反过来定义基线范围。

### 8.3 生成最小 Delta 并检查

候选用 `design-delta/v2` 表达“增加/修改哪些节点和边、保持哪些不变量、如何验证”，而不是保存源码或思维过程。

```bash
python tools/agent_memory.py design-check \
  --project . \
  --intent /tmp/design-intent.json \
  --contract /tmp/design-contract.json \
  --proposal /tmp/profile-cache.json \
  --json
```

结果解释：

- `blocked`：结构错误、未知关键锚点或违反硬约束，必须修改方案。
- `review`：假设、覆盖或证据不足，需要人工判断。
- `clean`：有界检查未发现问题，不等于设计已被证明正确。
- `change_plan.steps`：按依赖排序的实施与验证步骤。

### 8.4 只有存在真实权衡时比较方案

```bash
python tools/agent_memory.py design-compare \
  --project . \
  --intent /tmp/design-intent.json \
  --contract /tmp/design-contract.json \
  --proposal /tmp/profile-cache-local.json \
  --proposal /tmp/profile-cache-shared.json \
  --json
```

Agent 应报告决策、敏感条件和取舍，不应简单输出总分最高者。若两份方案只是命名不同，应保留一个最小方案，不制造伪选择。

### 8.5 实施期间检查进度

```bash
python tools/agent_memory.py design-progress \
  --project . \
  --proposal /tmp/profile-cache.json \
  --base HEAD \
  --json
```

Agent 只执行返回的下一批 dependency-ready steps。新增文件存在但预期符号尚未声明时仍是 `in_progress`，不能因为文件已创建就标记完成。

### 8.6 基于实际改动验证

```bash
python tools/agent_memory.py design-verify \
  --project . \
  --proposal /tmp/profile-cache.json \
  --base HEAD~1 \
  --test-report build/test-results.xml \
  --json
```

`design-verify` 是只读检查，不会替 Agent 运行测试。Agent 先运行项目已有编译和测试命令，再把 JUnit/JSON 等机器可读报告交给验证器。

验证重点：

- 实际文件和符号是否符合 Delta。
- 导出 API 是否意外变化。
- 源码关系和学习图是否一致。
- 编译器与测试报告是否支持验收场景。
- 测试证据是否绑定当前 Git 和文件摘要，避免复用过期报告。

## 9. 设计答复的推荐格式

Agent 最终设计答复应保持可执行，而不是输出运行时原始 JSON：

```text
当前结构事实
- 入口、责任边界、状态所有者、关键依赖和已有扩展点。

设计目标与约束
- 用户目标、明确排除项、兼容性要求和验收标准。

推荐方案
- 修改哪些组件、增加哪些责任、依赖方向和关键流程。

为何适用
- 当前代码证据 + 设计原则 + 模式适用条件，而不是只写模式名称。

拒绝的方案
- 仅列真实备选及拒绝原因。

影响范围与风险
- 调用方、状态、失败路径、配置、日志和测试范围。

实施顺序
- 对应 change_plan 的依赖顺序。

验证计划
- 编译、测试、运行观测和回滚条件。

假设与证据缺口
- 尚未被当前源码、图或运行证据支持的内容。
```

## 10. 如何节省 Agent Token

- 首轮使用自然语言和精确业务症状，不要把整份日志粘进对话。
- 让 Agent 调用 `--json` 后只摘取 direct evidence、关键链、缺口和下一步。
- 后续查询加入文件、符号、错误码、route、resource 或 trace id，避免重复宽查询。
- 普通设计只使用 `design-assist`；完整协议仅用于重要结构变化。
- 默认 `--scope auto`，只有全局架构或重复模式问题才用 `--scope global`。
- 不把临时日志原文、完整 repository model 或所有经验原样输出给用户。
- 达到停止条件后停止检索，进入源码检查、实验或验证。

## 11. 常见误用

### 误用一：直接采用最近经验

错误：最近的经验略微相关，因此直接沿用其结论。

正确：检查 experience 的 intent、scope、状态、反证和当前代码锚点。普通经验只作为 advisory evidence。

### 误用二：把静态图可达性当因果链

错误：A 调用 B，所以 B 一定导致事故。

正确：静态边只说明机制可能性。还需要相同运行身份、时间顺序、定向干预和前后验证。

### 误用三：一次查询后立即修改代码

错误：选择第一条高分结果直接修复。

正确：读取 Hypothesis Ledger，先执行能区分候选的检查，再修改最小范围。

### 误用四：看到设计模式名就套用

错误：检测到 Observer/Strategy 等名称后直接增加抽象。

正确：验证变化轴、所有权、调用方向、数量和测试收益；缺少这些证据时保持简单结构。

### 误用五：把图中没有边解释为没有影响

错误：impact-scope 未返回依赖，因此改动安全。

正确：先检查 coverage gaps、学习范围和动态调用；缺边表示未知。

### 误用六：把历史成功测试当当前验证

错误：旧 Incident 或旧报告曾经通过，所以当前方案 verified。

正确：验证证据必须对应当前改动和 Git 状态，必要时使用 `verification-run/v1` 绑定摘要。

## 12. 最小操作清单

问题定位：

```text
[ ] 明确症状、条件、最近变化和可用日志
[ ] context 查询用户问题，读取 query_handoff
[ ] Agent 直接读取临时日志并形成多个候选原因
[ ] 每个候选原因单独 context 查询
[ ] 检查当前源码、原始边和配置
[ ] 按候选工作表执行区分性检查，推测调用链和因果链
[ ] 修复前运行 impact-scope
[ ] 运行测试和运行观测
[ ] 记录 intervention、verification evidence 和紧凑反馈
```

代码设计：

```text
[ ] 明确目标、范围、约束、排除项和验收标准
[ ] design-assist
[ ] 核对 current_design、forces、patterns、principles 和 decisions
[ ] 先给最小候选
[ ] 重要设计执行 prepare -> check -> compare（可选）
[ ] 按 change_plan 实施并运行 progress
[ ] 运行真实测试后 design-verify
[ ] 分开报告事实、方案、风险、验证和证据缺口
```

## 13. Query Skill 的边界

`agent-memory-query` 负责读取、协调和检查证据，不负责：

- 学习新的代码范围：交给 `agent-memory-learn`。
- 合并、降权、淘汰或刷新记忆：交给 `agent-memory-maintain`。
- 把验证后的过程写成经验：交给 `agent-memory-reflect`。
- 自动执行设计或测试：由 Agent 使用项目现有工具完成。

四个 Skill 的职责保持固定。新增诊断、代码图、日志图、因果链和设计能力都通过 Query Skill 的渐进式协议和唯一运行时入口复用，不增加新的用户级 Skill。
