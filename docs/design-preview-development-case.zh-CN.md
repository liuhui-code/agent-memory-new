# P1：记忆审查报告预览的隔离设计案例

日期：2026-11-17 开始，2026-11-18 收尾。Agent 编写的新开发要求，使用
[固定基线](development-baseline-20261117.zh-CN.md)；不声称用户已提出这项生产功能。
目标是实际走完输入、参考适配、候选、实现、反例和变化演练，并形成可复用的有条件案例。

## 输入简报

| 项目 | 内容与依据 |
|---|---|
| 新开发目标 | 为一个审查视图建立后台报告预览的请求/结果归属；实现仅在夹具中 |
| 已观察宿主事实 | `review_server.py` 使用 ThreadingHTTPServer，没有现成单线程事件所有者 |
| 已观察数据边界 | SQLite 是真相源；审查一次最多选择 100 条记录；预览只能持有派生快照 |
| 正确性要求 | 接受后输入不随调用方修改；旧请求、取消请求、重复回执和其他实例的回执不能提交 |
| 失败要求 | 当前失败可见；旧失败不覆盖新状态；无效输入不撤销已有有效任务 |
| 并发要求 | 检查完成身份和改变预览状态必须是同一受控提交；耗时渲染不在临界区内 |
| 顺序定义 | 本夹具的“最新”按 Coordinator 接纳顺序，不推断 HTTP 到达/用户点击顺序 |
| 资源边界 | 默认最多 100 个快照条目；是当前选择范围的开发上限，不是全库报告 SLO |
| 非目标 | 真实 HTTP/界面接入、业务 Memory 写入、硬停止线程、跨进程身份、后台服务或全库导出 |
| 变化演练 | 初版纯文本；后续增加 JSON 渲染，核对状态所有者无需修改 |
| 尚未知 | 实际视图与实例绑定、权限、客户端乱序协议、真实负载和生产渲染成本 |

宿主来源：[review_server.py](../tools/agent_memory_runtime/review_server.py#L12)、
[review_library.py](../tools/agent_memory_runtime/review_library.py#L24)、
[人工工作台合同](memory-review-workbench.zh-CN.md)。新行为和顺序语义是本开发任务的明确约定，
不是对已有工作台缺陷或产品需求的推断。

## 验收先于实现

固定任务输入与摘要记录在 `docs/evidence/design-preview-development-20261117/task.json`。
正常预览、输入修改、过期完成、取消、重复/错误实例回执、失败恢复、无效/过量输入和受控
跨线程顺序应有可观察结果。负向原型只作为已知错误对照；不能将其称作真实事故或独立候选收益。

完成取消仅意味着不再接受其结果，不证明渲染线程已退出。拥有源码作用域或逻辑状态
不等于单线程；当前宿主事实要求显式说明跨线程提交边界。

## 参考检索与适配审查

使用固定基线的临时安装副本，学习错误原型，再通过原 `design-context` 进行定向和聚焦查询。
一条 M1 历史摘要被手工放入临时 Memory，因此这里不能测量检索泛化或 Memory 独立贡献。
原始响应见 [context-replay.json](evidence/design-preview-development-20261117/context-replay.json)，
逐项适配见 [reference-review.json](evidence/design-preview-development-20261117/reference-review.json)。

| 实际参考 | 可借鉴部分 | 失配条件与本次处理 |
|---|---|---|
| 初轮 information_hiding / smallest_viable_design | 隔离渲染变化，比较必要复杂度 | 是通用指导，不供应宿主并发事实 |
| 聚焦查询返回 Strategy，理由为 flexibility / testability | 两种渲染共享输入输出契约，由调用方选择 | 采用普通函数边界；不增加策略类、注册表或自动选型。目录引用是通用 ATAM 资料，不当成模式定义权威 |
| M1 历史 reflection:1，以 unverified_historical_observation 返回 | 完成身份应在状态提交边界核对 | Rust 串行提交机制不能直接用于本宿主；正常 Stop 尾数据规则不适用于取消预览 |
| Agent 直接阅读 EIP Correlation Identifier | 将回执与发起请求关联 | 当前使用进程内句柄；没有消息总线、跨进程传输或身份认证保证 |
| 当前宿主源码与 Python Lock 文档 | 在线程可能并发时保护检查与发布 | 不依赖 GIL 隐式安全，不承诺调度公平或所有交错均已验证 |

原始参考：[EIP Correlation Identifier](https://www.enterpriseintegrationpatterns.com/patterns/messaging/CorrelationIdentifier.html)、
[Python 锁](https://docs.python.org/3.9/library/threading.html#lock-objects)。
前者只迁移请求关联思想；后者用于实现提交临界区，不要求引入完整框架。

## 候选与决定

| 方案 | 成立条件、代价与结论 |
|---|---|
| 回调直接覆盖共享结果 | 故意错误的控制原型；实测旧 A 覆盖新 B，且输入列表修改改变“快照”，不满足合同 |
| 单线程 owner 加任务队列 | 若有合适 owner loop 可以成立；当前 handler 不提供该提交入口，需要新增队列、存活和关闭职责，本案例不采用 |
| 每视图逻辑 owner，加短临界区和不可变输入 | 匹配线程式入口；承认小锁竞争与进程内句柄限制，作为本夹具实现 |

选定的 [preview.py](../tests/fixtures/design_preview/preview.py) 不读取 SQLite、不启动线程，
只提供接纳、完成、取消、失败和不可变状态读取。实际渲染由
[纯函数](../tests/fixtures/design_preview/renderers.py)在外部完成；身份检查与状态发布在同一把锁内，
临界区不调用外部回调。逻辑 owner 不等于独占线程。

Job 对象本身是进程内活动句柄，sequence 仅用于诊断。另一个实例即使序号相同也不能提交；
复制出的同值对象也不被接受。这不是权限凭证，也不能直接用于序列化 worker。
调用方须在 `request` 期间独占输入；接纳后保留的是已提供数据的快照，不是数据库事务快照。
此决定也不证明真实产品应将预览状态放在服务端，真实视图/实例绑定与界面方案仍未设计。

## 实现、反例和变化演练

初版 12 项合同检查通过。故意错误原型的两个违反结果保存在
[unsafe-control.json](evidence/design-preview-development-20261117/unsafe-control.json)，
它是已知错误控制，不是真实生产事故或独立设计候选比较。

冻结初版 Coordinator 摘要后增加 JSON：仅修改 renderer 和测试文件，Coordinator 仍为
103 行且摘要未变。最终 [14 项检查](evidence/design-preview-development-20261117/final-contract-checks.json)
覆盖快照、过期/取消/重复/错误实例回执、失败恢复、资源边界、两个受控线程交错、
中文与跨记忆类型同 ID，以及预定格式变化。不是 12 + 14 个独立用例。

```bash
python3 -m unittest -v tests.test_design_preview_case
```

这是可执行的开发案例，不是生产功能；没有 HTTP 接口、真实界面、全库报告或后台服务。
预先声明的 JSON 变化验证了这次边界局部性，不能证明任意未来变化都保持局部。

## 条件化反馈与证据边界

反馈经既有 Reflect 和 experience-usage 在自有临时 Memory 回放，结果见
[feedback-replay.json](evidence/design-preview-development-20261117/feedback-replay.json)。
首个 payload 缺少必需 lesson，Runtime 正确拒绝，输入和错误已保留；补齐后另存实际结果。
记录仍是经验候选，未自动晋级、修改 Skill 或触发元反思。

本次指导实际落实为：先核对宿主模型，拒绝原封不动迁移串行机制；将输入复制与状态提交分开；
对 Strategy 只采用有用的函数边界；保存取消、身份和进程边界的失配条件。
这是当前 Agent 的可审阅执行记录，没有未使用指导的对照，不能归因为指导或 Memory 带来的提升。

原始输入保存在 [task-brief.md](evidence/design-preview-development-20261117/task-brief.md)，
其摘要对应 task.json 的 input_brief_sha256；本文后来增加了决定和结果，不能拿后加内容冒充初始输入。
生产 Runtime / Skill 均保持 P0 摘要；既有 81 项检查不重复执行。

最终 [delivery.json](evidence/design-preview-development-20261117/delivery.json) 的范围为
`passed_controlled_case`：14 个不同用例、固定输入、基线/审阅包完整性、源码摘要和反馈读写均通过。
其中 Runtime 311 文件、Skill 23 文件及临时重放目录的 538 文件仍与 P0 相符。
这不是 95 项重新运行的产品回归，也没有把本次自编任务升级为外部效能证据。

真实接入前仍须决定视图/实例与权限绑定、点击顺序与接纳顺序的关系、数据库读取一致性、
跨进程任务身份和负载预算。本案例不阻塞于这些非目标，也不声称解决了它们。
