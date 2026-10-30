# 系统元反思：独立候选副本与检查主体

日期：2026-10-30
状态：候选/v2 合成隔离回归已通过，不表示真实产品候选通过；见[验证记录](system-meta-reflection-design.zh-CN.md#9-隔离验证记录)

## 要解决的衔接问题

当前检查 v1 把补丁摘要和调用方列出的源码关联起来，但没有证明补丁已经应用到
被检查目录。一个在旧源码上返回零的命令不能作为新提案的检查依据。本阶段增加
独立候选准备，并让 v2 检查计划明确绑定候选。原查询协议、普通记忆和评测器不改。

候选只是授权开发材料。准备完成不进入 checked/applied，不更新安装副本、不
迁移用户数据库，也不产生功能正确、因果收益或发布资格。

## 候选准备

新增 `maintain-system-candidate`，仍经 tools/agent_memory.py。必需参数为 --id、
--expected-revision、--candidate-key、--patch-file 和 --candidate-home。默认预览
仅检查已有元数据、绑定补丁和本地 Git 基线；--execute 才实际生成独立副本。
本轮仅在临时归档和合成 Git 仓库调用预览/执行，不应用到真实产品副本。

- 提案必须为当前 prepared 修订，且没有未决检查或候选准备。
- base_version 必须是本地 Git 中实际存在的完整 commit OID，不能仍填自由说明。
- patch-file 是开发根目录中的相对文件，必须列在已观察制品中，且实际字节摘要
  仍匹配；沿用 1 MiB 制品上限。
- candidate-home 是显式授权、已存在的目录，不能位于来源树或 Memory Home 内。
  运行只在其新建的私有子目录工作；不覆盖已有目录或修改来源 Git 工作树/index。

源码先从指定基线复制为独立本地 clone，不共享对象硬链接或 alternates，再在
该副本 checkout 基线、检查并应用补丁到 index 和工作树，记录结果 tree OID。
修改、新增、删除和 Git 文件模式变化由 Git patch 表达；不会运行补丁中的代码。
本入口不准备子模块内部或 Gitlink 变更的可执行内容，相关路径无法形成受支持的
字节观察时明确失败，不把空子模块目录视为源码已经完整。
使用的 Git 行为见 [clone](https://git-scm.com/docs/git-clone)、
[apply](https://git-scm.com/docs/git-apply) 官方文档。

内部 Git 命令不使用 shell；清除继承的 Git 环境覆盖，关闭系统/全局配置、hooks、
fsmonitor、外部 diff、textconv、自动维护和网络协议，保留显式本地 file 传输。
不初始化子模块或发现/执行项目工具，局部克隆缺对象/不支持时明确失败。
这不是进程沙箱，也不冻结整个系统环境。

准备时记录实际基线、候选 tree、候选 Git 配置摘要及所有补丁变更路径的观察。
变更路径最多 100 项，单项文件/链接内容最多 16 MiB，总量最多 256 MiB。
删除记录为 absent；符号链接只观察链接目标字节，不跟随链接去读取外部内容。
这些元数据形成 candidate_digest，源码和 Git 数据留在显式候选目录，不写入 SQLite。

## 存储、读取与失败

首次 --execute 才创建可选 system_change_candidates 和自己的 schema 组件。
预留状态为 preparing；Git 工作期间不持有 SQLite 写事务，阶段完成为 ready，
失败/可控中断分别记录 failed/interrupted，原副本和部分候选均保留供审查。
preparing 表示仍在准备或结果未知，不能单靠经过时间重开。

同项目 candidate-key 的相同请求终态重试只返回历史，不重新 clone、改写或
验证今天的文件；不同请求拒绝。准备时阻止提案状态变更及该提案的新检查。
相同请求由 proposal_id、prepared_state_revision、patch_file 和规范化后的
candidate_home 确定。预留写事务再次检查该键：若另一调用已完成，返回其历史，
不因父提案随后推进而拒绝，也不新建目录；仍为 preparing 时明确拒绝重复工作。
maintain-system --candidate-key 返回一条有界元数据，提案详情返回有界历史摘要。
无自动删除、提交、push 或候选目录清理；不将失败目录当成有效候选。

## 检查计划 v2

v1 原样保留，为 declared_files_only。新增 system-change-check-plan/v2，沿用
既有字段并必需 candidate_key、candidate_digest。计划文件仍在提案开发根目录，
source_files 和命令工作目录则改为该候选副本；解释由显式 v2 标识区分。

启动前核对候选属于同一项目、提案、prepared 修订和制品，状态为 ready。
每项检查前后核对实际 HEAD、index 相对候选 tree、已跟踪工作树以及 Git 配置，
并重新观察全部补丁变更路径和调用方声明的额外源码/测试文件。任一漂移或观察
失败停止后续检查。Git index/tree 比较见 [diff-index](https://git-scm.com/docs/git-diff-index)，
已跟踪工作树比较见 [diff-files](https://git-scm.com/docs/git-diff-files)。

Git 检查及字节观察均为非原子观察，不能证明两次观察之间没有改动。未跟踪/忽略
文件、子模块内部、依赖、外部输入和完整执行环境没有因此获得认证；需要时另以
已授权检查和明确范围处理。v2 不自动证明断言映射、测试覆盖或 Oracle 合理。
工作目录绑定也不证明任意命令实际使用该目录的源码：绝对旧脚本路径、导入覆盖
或外部 Runner 仍需 Agent 审查，记录保持 command_source_use_verified=false。

记录标明检查工作目录、候选 tree/digest、观察范围和额外缺口，继续保持
evidence_verified=false、promotion_eligible=false、application_performed=false。
候选准备不是产品应用，完整晋级、安装/数据应用、后续观察和代码/数据回退仍是
整体目标，不能由一个 ready 或零退出码替代。

新增合成机制用例位于 [test_system_evolution_candidates.py](../tests/test_system_evolution_candidates.py)，
覆盖独立修改/新增/删除、预览无写入、历史重试、实际 v2 目录、漂移、失败及未决
状态，并包含延迟预留与父提案推进交错的受控用例。该交错用例通过保留旧的预读
上下文固定执行顺序，不是实际多进程并发测量。对应合成回归已执行，包含临时
仓库的 Git clone/apply、Runtime 候选准备和检查；完整验证边界见上述记录。
其中一项贯通用例从合成自动名额和报告开始，关联同一提案、候选与 v2 执行记录，
再检查历史重试不新增工作、零退出不晋级和公共 query_handoff 不混入治理材料。
该模块衔接检查已通过，不覆盖真实模型调用、完整查询等价或产品应用。
