# 开发基线与提交审阅索引

日期：2026-11-17。P0 已固定当前三段开发交付；没有修改仓库 Git index、创建提交或推送。

基于 Git HEAD `320e95137a890403cbd6496858a8a1c7de79c6ec`，内容快照摘要为
`8005d6b78ea741aec330ce7c29aba0a8a500e637d672473119e61d22e9eb2895`。
它标识开发文件，不认证案例质量或外部晋级。

## 可重放审阅包

- [manifest.json](evidence/development-baseline-20261117/manifest.json)：311 个 Runtime 文件、23 个 Skill 文件、变更路径和逐文件摘要。
- [tracked-changes.patch](evidence/development-baseline-20261117/tracked-changes.patch)：16 个已跟踪文件的完整工作区补丁。
- [untracked-files.tar.gz](evidence/development-baseline-20261117/untracked-files.tar.gz)：明确属于三段交付的 199 个新文件，不含用户的 `memory.md`。

已在自有临时 Git 目录重放补丁与归档，538 个文件的摘要全部匹配。基线依赖文件由当前
已验证 Runtime / Skill 快照提供，改动前文件取自上述 HEAD。未重跑已通过的 81 项验证。
该包不包含之后新增的 P0 索引和 P1 案例；后续工作引用此固定基线，不改写历史产物。

## 建议的提交分组

| 顺序 | 独立目的 | 主要文件与证据 |
|---|---|---|
| G1 | ArkLog M1 历史实验 | M1 报告、五组证据、`tests/run_arklog_m1.py` 与原生探针 |
| G2 | Agent 主导的设计指导 | Query / Reflect Skill、三个参考材料、设计指导开发报告与证据 |
| G3 | Rust 源码与显式文件保留 | 两个 Rust 模块、语言注册/提取/投影修改、三组相关测试、Rust 合同与证据 |

README、CONTEXT、gitlog、使用指南和 provider 规范含多个阶段内容，需要按段拆分；
manifest 的 `logical_groups` 已列出归属。当前提供的是组合补丁及逻辑提交方案，
不是声称三个已分别构建和验证的提交。拆分时应依次验证文档引用和依赖，不能将用户文件混入。

## 当前有效的验证范围

| 证据 | 能说明什么 | 不能说明什么 |
|---|---|---|
| [M1 报告](arklog-m1-design-experiment.zh-CN.md) | 当时真实源码、原生对照和测试盲区 | 当时 Memory Rust 能力通过；新任务收益 |
| [设计指导交付](design-guidance-development.zh-CN.md) | Skill 材料、安装与接口检查 | 独立宿主遵循协议或设计质量提升 |
| [Rust 最终结果](evidence/rust-source-development-20261117/delivery.json) | 46 项相关 + 35 项基础用例、临时安装和只读源码验证 | 宏/类型/调用解析、完整方法投影、真实效能 |

旧快照中的源码/文档摘要只描述其时间点，不能要求它与后来扩展后的工作区相同。
最新 Runtime 摘要与 Rust 最终验证一致，Skill 摘要与指导交付一致。所有失败记录保持原样。

## P1 入口

后续 [报告预览设计案例](design-preview-development-case.zh-CN.md) 使用本基线的隔离副本。
它是编写的新开发任务，包含实际代码和控制反例，不是外部任务、独立评审或隐藏评测。
P1 不修改生产 Runtime，也不把报告预览接入真实工作台。

2026-11-18 补充：P1 已完成受控实现、14 项检查和格式变化演练，见上述案例。
建议后续将本基线索引/审阅包、P1 报告与证据、`tests/fixtures/design_preview/`、
`tests/test_design_preview_case.py` 作为 G4 单独审阅。README、CONTEXT、gitlog 和使用指南中
本阶段的新索引段归 G4；它们不属于已冻结的 G1–G3 补丁。尚未执行任何分组提交。

## P2 入口

[设计对照准备](design-comparison-preparation.zh-CN.md)固定 A 的原始 Skill 和 B/C 的 P0 指导包，
三组共用本 Runtime。合成接口演练核对共享设置记录与额外历史的差异；不运行模型或真实任务。
工作表、原始 Skill 包、演练/自审/就绪记录及此阶段索引段建议归 G5，独立于 G4 和原始审阅包。
当前真实设计活动仍为 no_go；未把 P2 材料改写进已冻结的 G1–G3 证据。

## 当前组合交付入口

2026-11-18 的 [G1–G5 本地收尾](evidence/local-delivery-20261118/review.md)提供后续阶段在内的
组合补丁、新文件包和逐文件清单，恢复范围是本开发切片及必要依赖。它保留本页开头的旧 P0 包，
不是五个已经独立验证的提交，也不替代真实活动。重放状态见该目录的 `manifest.json`。
