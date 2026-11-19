# Agent Memory 当前上下文

本文件记录当前实现事实和未完成事项，不替代当前用户指示、源码、测试或批准证据。

- 运行入口仍为 tools/agent_memory.py；四个 Skill 是前台协议。SQLite 为事实来源，Vault 为派生镜像。
- 人工维护增加 review-ui 本地前台工作台：六类记忆分页 / 搜索 / 详情，事实、反思、经历的批量审查 / 归档 / 恢复及备份后永久删除。源码索引只读，不迁移元反思组件、不改变 Query 协议；使用说明见 docs/memory-review-workbench.zh-CN.md。
- 系统元反思使用宿主当前模型。触发、名额、报告、候选、检查和生命周期记录与普通检索隔离；不接入额外评审模型或后台服务。
- 元反思的验证基线及旧版兼容读写基线为 2ade686f12373c214d7b9c3809f0e8821d770944，兼容回归固定使用该提交，不随 HEAD 移动。实际交付提交以 Git 历史为准；原有未跟踪的 memory.md 不是本任务产物。
- 治理 v1 的显式状态命令仍不能直接设置 checked/applied 等状态。新生命周期入口要求显式治理 v2 迁移、绑定候选的 v3 检查产物和当前 Agent 的逐项审查。
- checked 表示声明范围内的执行条件与 Agent 审查齐备；不认证审查者、Oracle 或外部泛化，promotion_eligible/evidence_verified 仍为 false。
- 实际应用支持 POSIX 文件锁、逐文件原子替换、持久化前后像及检查点。source/installed 布局分别应用源码路径或 tools 与 .agents/skills 安装路径；不改写 Memory 数据文件。
- 代码回退与数据降级分开。治理 v1/v2 迁移备份归档、保留引用和后续写入；存在高级状态时拒绝降级，保留兼容 Runtime 或走前向修复。
- 本轮交付为当前仓库实现及已授权的隔离安装/真实宿主验收。另一个真实业务项目未指定；额外部署是可选后续，不是本轮代码任务的前置条件。
- 原生命周期实现已由 4d5e068 提交并推送。后续递归方案仍为规范草案，R1/R2/R3 开发切片已实现；正常任务自动采样、自动候选/部署和长期效能仍未完成。v1 的信号、手动语义和递归默认跳过保留，当前自动名额与 R3 共享任务去重。
- 2026-11-01 新增 R1 maintain-system-outcome：只读关联预绑定计划、实际应用及后续操作/任务声明，不建表、不推进状态；任务结果/成本仍为未认证声明，长期效能标记保持 false。源码和规范见 docs/system-meta-reflection-outcomes.zh-CN.md。
- R1 最终相关回归发现 63 项，62 项通过，0 失败/错误；真实宿主按设计跳过。新记录为 regression-r1-outcomes.json，旧生命周期快照保留；R1 安装副本已实际执行，未声称真实宿主自动选择或长期收益通过。
- R1/R2/R3 实现、R4 开发准备、两轮演练及递归方案随本次主分支交付统一纳入 Git；4d5e068 是此前生命周期基线，实际交付提交及远端状态以 Git 历史/远端 main 核对为准。没有改动真实业务 Memory 或部署到未指定项目。
- R2 新增 system-rounds-v1 可选组件和一张不可变事件表，使用原迁移入口显式备份安装。轮次读写支持修订/CAS、幂等、父子关系、冻结记录次数预算、晚到评估及原决策保留；预算不是实测模型 Token 限制。
- R2 最终相关回归发现 72 项，71 项通过，0 失败/错误，1 项真实宿主 opt-in 跳过；九项新增轮次用例均通过。regression-r2-rounds.json 单独记录 329 个源码文件的稳定快照及临时根清理，旧 R1/生命周期记录保留原范围；未把 skip 记作新的宿主或长期效能验收。
- R3 新增 maintain-system-round-handoff 和显式备份安装的 system-handoffs-v1。v2 结果计划事先绑定许可/一次尝试/零重试/字符上限；窗口齐备时先领名额，再由当前宿主评估，完成与 R2 assessment 原子保存。漂移或中断保留名额，Runtime 不调用模型或部署；源码和契约见 docs/system-meta-reflection-handoffs.zh-CN.md。
- R3 的 Codex CLI 0.165.0 安装副本宿主验收已通过（111.541 秒）：一个 claim/recorded finish 和一条 inconclusive 评估，未知结果/成本保留，重领不再生成。real-host-r3-handoff.attempt-2.json 记录实际结果，attempt-1 保留权限失败；整回合 usage 不是增量元反思成本或长期效能。
- R3 最终相关回归发现 84 项，82 项通过，0 失败/错误，2 项宿主 opt-in 跳过；11 项 R3 用例全部通过。regression-r3-handoffs.json 单独记录当时 335 个文件的稳定快照及临时根清理；R3 收尾时的 Runtime/Skill 摘要与该宿主安装副本一致，后续改动另行记录。
- 按用户选择，R4 仅完成开发准备、暂不启动真实活动。maintain-system-campaign-readiness 只读检查 internal/external/campaign/evidence，六组资料未提供时保留 no_go；旧 diagnosis 合同不获得通用活动资格。开发探针使用临时未初始化 Memory Home，没有读取业务归档或采集真实任务。
- 两个独立 CLI 条件复现了 eval-cohort-create 在拒绝缺来源/不支持协议前已建库的问题；现已把原校验移到初始化前。就绪检查本身不打开 SQLite，原有有效诊断/校准流程仍按原合同执行；见 docs/system-meta-reflection-campaign-readiness.zh-CN.md。
- R4 准备的 43 项相关影响面回归全部通过，无失败/错误/跳过，八项新就绪用例均通过；regression-r4-readiness.json 保存 342 文件稳定清单及临时根清理。readiness-r4-development.json 明确为开发探针，六组外部缺项、无真实项目/归档绑定，实际任务采集为零；未运行模型或冒称整个 R3 重验。
- 随后完成一次安装版 R1–R4 两轮集成演练（1 项测试、9 阶段，47.748 秒）：父轮建议/实际回退、子轮关联/去重、晚到反证、停止/预算、历史与两条后写 Memory 保留、查询隔离及 R4 no_go 均通过。相对 R4 的 342 文件全部未变，仅新增该集成测试；当前运行时/Skill 未变，未调用模型或启动真实活动。见 docs/system-meta-reflection-development-journey.zh-CN.md。

当前证据：

- 2026-11-19 按用户授权交付 main：此前本地整合提交 3c6a07a 与本轮成熟案例/设计质量元反思一并进入交付范围。已核对远端 main 是本地祖先；当前 Skill 为四个、31 个资源，沿用已记录的 14/21 项隔离资源与协议检查，标准校验器缺 PyYAML 的限制保留。历史 verification 的 HEAD/committed/pushed 字段描述捕获时点，实际提交和远端状态以 Git 为准。提交准备只补充 CONTEXT/gitlog 说明，不改 Runtime、案例卡或已固定证据，不包含原有 memory.md；不启动真实活动。
- 2026-11-19 增加 Agent 侧“设计质量反思与元反思”参考，接入 Reflect、Query 设计收尾及 Maintain/R3 指定范围的交接。普通设计反思检查边界/抽象/总复杂度/演进/取舍，系统元反思再定位输入指导、案例/查询、学习、反思规则或数据表达层。沿用既有字段、四类触发和候选治理；开发本功能不等于手动评审授权，意见不变成分数或 verified 标记，普通反馈不自动递归。隔离回放 21 项资源/协议断言通过：四个 Skill 的 31 资源一致、五个意见与一个 needs_evidence 候选保存/幂等、自动跳过及 full/compact 查询隔离保持；手动触发为明确标记的合成输入。前三轮脚本的 read 命令/--json/输出格式错误与日志保留；标准校验器缺 PyYAML，元数据不变。Runtime 311 源文件、六张案例及历史 30 资源检查记录/旧 P2 基线原样保留。见 docs/evidence/design-quality-meta-reflection-20261119/verification.json；无真实宿主/长期收益结论，未提交/推送。
- 2026-11-19 按用户要求预置六张有原始来源的外部设计案例卡及问题特征索引，接入 Query Skill 按需参考：Shopify 模块化单体、VS Code 宿主、SQLite WAL、Stripe API v1 幂等、Google SRE 资源准入、Cloudflare 2019 WAF 复盘。原文于 11-18 核对；事实、迁移判断、前提与反例分开，Stripe v1/v2 语义不混用。临时安装的四个 Skill 共 30 个资源一致，案例分支 10 处引用可达，311 个 Runtime 源文件未变；标准校验器缺 PyYAML，frontmatter 与提交版相同。记录在 docs/evidence/mature-design-cases-20261119/verification.json，不声称设计收益或独立宿主采用通过。未写业务 Memory；新 Skill 与旧 P2 的 23 资源基线分开，历史证据原样保留；尚未提交/推送。
- 2026-11-18 交付转入本地整合提交：G1–G5 组合包的 610 个文件已再次与工作区核对一致，逻辑分组用于审阅，采用一个整合提交。打包后仅 CONTEXT / gitlog 增加本次提交说明；Runtime、Skill 和冻结证据保持原样。各阶段的“未提交”、HEAD 与 committed 字段描述其历史时点，实际提交标识以 Git 历史为准；此步骤不推送，也不启动真实活动。
- 2026-11-18 对尚未提交的 Rust 接入与显式文件投影做限定范围作者审阅，未发现已证实需修复的新缺陷，未因此扩展实现。G1–G5 当前组合包的范围与实际重放记录见 [本地收尾](docs/evidence/local-delivery-20261118/review.md)；旧 P0/P1/P2 证据不改写，原 81/14 项不重复运行。Runtime/Skill 未改，真实活动、提交、推送均未启动。准备阶段以此收口，下一步需要真实产品任务或明确交付动作。
- 2026-11-18 完成 P2 对照准备：固定 Git 320e951 的 20 个 Skill 资源作为 A，P0 的 23 个作为 B/C，三组均使用当前 Runtime。实际安装/公开 CLI 合成演练中，每组 310 个安装 Runtime 文件一致，源码投影/通用目录/共有学习记录一致，C 额外合成反思正常返回，13 个资料隔离断言通过。首次预期误把 learn-path 生成的共有 episode 排除，失败、原计划和脚本保留；只修正开发检查预期。B−A 衡量整个指导包，C−B 只衡量额外 Runtime 历史；无模型/真实任务/独立评审、无效能结论。真实来源、执行/预算合同和独立评审未齐，no_go；工作表不接入 diagnosis cohort。Runtime/Skill 未改、原 81/14 项未重跑、未提交/推送。见 [P2 合同与证据](docs/design-comparison-preparation.zh-CN.md)。
- 2026-11-18 完成 P0/P1：G1–G3 基线固定为内容摘要 8005d6b78ea741aec330ce7c29aba0a8a500e637d672473119e61d22e9eb2895，组合补丁/新文件包在临时目录重放后 538 文件匹配，未提交。P1 是 Agent 编写的受控报告预览案例：依据真实 ThreadingHTTPServer 入口选用短临界区和不可变快照，14 项检查通过；增加 JSON 只改 renderer/测试，103 行 Coordinator 摘要不变。历史 M1 参考仅部分迁移，反馈在临时 Memory 保存为普通反思；首个缺 lesson 的写入被拒绝并保留。Runtime 311 / Skill 23 文件仍匹配基线，81 项原检查未重复运行，无真实界面接入、独立设计效能或 M2。见 [基线索引](docs/development-baseline-20261117.zh-CN.md)和 [P1 案例](docs/design-preview-development-case.zh-CN.md)。
- 2026-11-17 已完成 Rust source-only 声明接入：沿用现有 CLI/语义适配/SQLite，保留范围和原始字节摘要，修正泛型、编码、同一行条件重复身份问题；不推断宏/cfg/类型/调用。实际项目还暴露了设计视图裁剪丢失显式文件的问题，已先在独立 ArkTS 公共输出复现，再修投影保留规则。最终 46 项相关 + 35 项基础回归通过，共 81 个不同用例；临时安装通过，ArkLog 只读学习 32 文件/487 声明，202 个原始文件未变。full/compact 保留 Controller，方法范围由聚焦 context 提供；历史失败保留，无 M2/真实效能结论。见 [Rust 交付与证据](docs/rust-source-context.zh-CN.md)。
- 2026-11-17 完成现有 Query / Reflect Skill 的设计指导交付：输入预填、按需设计参考、适配/失配示例、定性取舍与可选决策模板、有条件反馈。15 项定向回归通过；临时安装的四个 Skill 共 23 个资源及五条实际 CLI 学习/设计/反馈命令通过，原 309 个 Runtime 源码/资源摘要不变。标准 Skill 校验缺 PyYAML，替代元数据检查与验证脚本三次错误假设均保留；没有独立设计效能结论、M2 或真实活动。见 [开发交付](docs/design-guidance-development.zh-CN.md)。
- 2026-11-16 按用户提供的 M1 任务对 ArkLog 9aa4c503c271ab22375ec5e40e645f536b441c11 完成只读映射和临时副本原生实验，保留当前串行 Controller / Runtime / stream_id。新增四项实际契约探针和四类故意错误对照，修正了旧 A→B 测试无法区分 device-only 的盲区；最终 pnpm test 与 cargo workspace 各 193 项通过，构建 / check 通过。历史端口权限失败与一次现有时延断言失败保留，未改变阈值或业务代码。见 [M1 报告](docs/arklog-m1-design-experiment.zh-CN.md)。
- M1 的 Memory 接入结果为 completed_with_context_gap：当前 `.rs` 未注册，实际学习与显式锚点查询均返回 0 个 Rust 源码锚点，不能称完整 Memory 辅助 Rust 设计已通过。LiveOnly 真机未验证，M2 未启动；ArkLog 原始 202 文件和工作区保持不变，本轮无推送 / 部署 / 真机操作。
- 人工工作台最终隔离回归 59 项全部通过（原有基础 35 + 新增 24），99.560 秒（含记录 / 清理 99.844 秒），0 失败 / 错误 / 跳过；源码与静态资源的前后清单一致。最终报告 docs/evidence/memory-review-development.final.json；原 58 项结果保留。收尾独立复现并修复了备份继承 WAL 头及遗留临时旁文件的问题，新增只读独立打开回归。首次沙箱禁止端口绑定的 5 项初始化错误及授权后通过记录同样保留。
- 2,366 条生成记录的真实浏览器流程通过 22 项检查，最终界面再通过 6 项 HTML 注入防护 / 双窗口冲突 / 窄屏检查，备份修复后追加 5 项界面删除检查（合计 33 项）；预期冲突返回一次 409，未见页面脚本异常。10 万条生成记录的单次开发测量：分页约 138–159 ms、中文搜索约 96 ms、待审查页约 25 ms，不证明真实任务或百万级 SLO。见 docs/evidence/memory-review-browser-development.json 与 docs/evidence/memory-review-scale-development.json；业务归档及原有 memory.md 未读写。工作台、基础检查和受控证据作为本次 main 交付内容，实际提交与远端状态以 Git 历史及远端核对为准。
- 41d9a30 之后执行 35 项基础检查，全部通过，0 失败/错误/跳过，耗时 70.670 秒（含记录/清理 70.904 秒）。入口为 python3 -m tests.run_basic_checks；报告 docs/evidence/basic-checks-41d9a30.json 记录 331 文件稳定清单及临时根清理，未调用模型或开启真实活动。该次仅新增测试入口/报告及说明，当时运行时代码未变。
- 原有 37 项隔离验证已通过；最终批次发现 56 项，55 项普通隔离回归通过，真实宿主按设计跳过并另行实际运行通过。代码清单与开始/结束摘要一致记录在 regression-final.json。
- 退出码 7 且无产物的监测用例复现了收集顺序缺陷，修复后定向通过。
- 安装副本完整生命周期、安装布局实际更新/回退、Git 基线普通读写兼容的定向用例通过。
- 真实 Codex CLI 0.165.0 已在普通示例查询中读取项目本地安装 Skill、观察实际 I/O 失败、分配一次名额并保存建议性评审；最终证据见 docs/evidence/system-meta-reflection/real-host-smoke.final.json。
- 文件模式位 0744 被扩宽的开发版缺陷已复现并修复。最终回归快照包含修复，现有模式位及代码回退验证通过。
- 活跃写者持锁拒绝恢复、实际硬退出 77 后跳过已写文件的恢复，以及实际 DDL 重建后的迁移事务回滚均通过。
- 恢复/中止有效预览错误退出 1 已复现并修复；中止保留原操作 failed，未知子进程仍拒绝清除。预览、重试和 checked 失效路径均已回归。
- 初次宿主启动的沙箱权限拒绝，以及带验收语境的首次宿主无评审结果均保留；不推断后者的未证实原因。

交付边界：

1. 运行代码、必要验证及规范/ADR/完成矩阵已落实；本轮不宣称生产效能或外部发布资格。
2. 如用户另行指定真实部署项目及 Memory Home，再执行该目标已授权的安装/迁移；不自动选择其他业务项目或发布上游。

下一阶段方案：

- 采用任务级反馈与跨版本窗口复核两个节奏。R1/R2/R3 已关联原假设、应用与后续结果，保存轮次并提供一次宿主窗口交接；接下来需要正常任务独立审计与真实来源/效能合同。
- 主要补齐正常任务漏检审计、评价规则冻结、版本/样本隔离、质量/成本/完整性分账及停止/回退；当前 Cohort v1 只支持 diagnosis，不能直接宣称覆盖通用开发任务。
- [完整递归演进方案](docs/system-meta-reflection-recursive-evolution.zh-CN.md)的 R1/R2/R3 已落实，R4 就绪准备已提供；R4 真实活动/R5 未启动，RE01–RE14 整场景仍未执行。各切片局部机制单独记录；[新 ADR](docs/adr/0002-bounded-recursive-evolution.zh-CN.md)仍为 proposed、批准字段留空。

相关规范：[设计](docs/system-meta-reflection-design.zh-CN.md)、[生命周期](docs/system-meta-reflection-lifecycle.zh-CN.md)、
[ADR](docs/adr/0001-system-meta-reflection-lifecycle.zh-CN.md)、[完成证据](docs/system-meta-reflection-completion.zh-CN.md)、
[变更政策](docs/evaluation-and-change-policy.md)。
