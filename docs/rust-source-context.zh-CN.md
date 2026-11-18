# Rust 源码上下文：受限声明适配

日期：2026-11-17。受限开发交付；不授予设计效能或外部晋级资格。

## 问题与范围

M1 的 ArkLog 实验和独立 Rust 开发夹具均需要文件与声明导航。既有源码注册不包含 `.rs`，
普通学习和显式 `design-context` 锚点不能凭空补出文件。本轮复用语言注册、语义适配器、
SQLite 和原 CLI，不改变检索评分、模式选择或 Agent/Runtime 职责。

## 设计取舍

仅增加后缀可以解决识别，但不足以说明方法位置和适用限制；完整编译语义引入了当前目标
不需要的环境与依赖成本。采用现有语义适配契约下的受限 Rust 声明提取，质量优先级是
不伪造证据、可核对源码位置、保持其他语言兼容，再考虑声明覆盖范围。

支持目标：文件、普通函数、简单类型、内联模块、trait 中的函数和 impl 中的关联函数/方法。
保留原始字节内容摘要、声明范围、整理过空白的源码头、静态证据标记与所属源码作用域。
同名成员按作用域区分；条件定义的重复项按行号和出现次序保持物理身份区别，
同一行的重复定义也不合并。不挑选某个声明作为生效的编译结果。

明确限制：没有宏展开、条件编译求值、类型推导、跨文件模块解析、调用/派发或生命周期证明。
跳过宏 token tree 与函数体内的嵌套声明；复杂/不完整语法或提取预算不足时仍保留文件级证据，
可能仅有部分声明。字符预算为 1,000,000，单文件至多 2,000 个声明，头部至多 512 token，
作用域递归至多 32 层。无效 UTF-8 不通过忽略坏字节生成另一条声明。
语义适配只声明 definitions，学习 gaps 与文件摘要提示 source-only 限制。

IR 的 `method` 表示有源码所属作用域的 callable，也包含 Rust 关联函数；
`owner_kind=source_scope` 不证明运行时状态所有权、接收者类型或派发关系。

参考原始语法：[函数](https://doc.rust-lang.org/reference/items/functions.html)、
[impl](https://doc.rust-lang.org/reference/items/implementations.html)、
[tokens](https://doc.rust-lang.org/reference/tokens.html)、
[条件编译](https://doc.rust-lang.org/reference/conditional-compilation.html)。
这些资料定义语法，不证明本实现覆盖完整 Rust。

## 验收与停止边界

- 先在独立夹具的实际学习/设计查询观察缺口，再修改生产能力。
- 验证普通声明、跨行头、所属作用域和范围；不从注释、字符串、宏体或不完整文件生成声明。
- 验证不同 owner、条件重复声明的标识不会在设计锚点中冲突。
- 验证原 `context` 的内容摘要新鲜度门禁和重复学习保持正确；不将 `design-context` 既有
  时间戳快照标记称为新的内容摘要认证。Agent 仍须打开当前源码确认设计锚点。
- 完成源码/语义/设计/安装相关回归、500 行门禁及隔离安装副本检查。
- 实际范围或身份无法可靠判断时，记录缺口而不制造调用关系或编译结果。

不启动 M2 或真实活动；不修改已有密封评测或 ArkLog 原始工作区。Rust 支持只是源码供给
能力，不能作为更有设计品味或 Memory 增量收益的证明。

## 实际开发反馈

原 Runtime 的 309 个文件已按初始内容摘要重建到隔离副本，确认独立夹具实际学习为 0、
设计查询锚点为空。首轮夹具错误读取了 JSON 顶层字段，不能作为有效红灯；当时已开始实现。
纠正的复现在逐文件验证过的改动前副本完成，证据保留实际先后顺序，不改写成先红后绿。

受控反例还暴露并修正了泛型中 `->` 截断 impl 所属作用域、CRLF 归一化破坏原始摘要、
无效 UTF-8 被忽略后生成伪声明，以及同一行条件重复导致 key 冲突。初始错误和后续回归均保留。

实际 ArkLog 宽查询首次未在前 24 个设计节点中展示目标方法，compact 的前 3 个节点还可能
遗漏显式文件。独立 ArkTS 夹具复现了显式文件丢失，Rust 夹具保留为正向对照。
现只调整投影：已学习的显式 entry file 排在其他节点前，再按原预算裁剪；没有新评分或候选生成。
目标方法的全部覆盖仍不保证，应通过聚焦 `context` 获取声明范围并阅读当前源码。

## 使用

在已安装此 Runtime 的 Rust 项目中，限定源码目录学习：

```bash
python3 tools/agent_memory.py learn-path --project . --path src --json
python3 tools/agent_memory.py design-context --project . --query "需要设计的行为" --anchor src/lib.rs --compact --json
python3 tools/agent_memory.py context --project . --query "SomeType::method" --compact --json
```

不要把构建输出等同当前手写源码；本适配器不执行 Cargo 或求值编译配置。
可重学以更新内容摘要；`context` 会阻止已变更的旧源码锚点。
`design-context` 既有快照使用时间戳作导航提示，并非新增的摘要认证。

## 证据

本轮的受控负例、回归、临时安装和只读源码检查位于
[开发证据目录](evidence/rust-source-development-20261117/)。最终结果写入 `delivery.json`。
旧 M1 和上轮 Skill 交付仍保留各自时间点的能力范围；本轮不改写历史证据。

最终 [delivery.json](evidence/rust-source-development-20261117/delivery.json) 为
`passed_bounded_development`，范围如下：

| 验证 | 实际结果 |
|---|---|
| 源码/语义/设计/新鲜度回归 | 46 项通过，0 失败/错误/跳过，进程 59.596 秒；包括 13 项 Rust 检查和显式锚点保留检查 |
| 基础回归 | 35 项通过，0 失败/错误/跳过，记录耗时 71.067 秒；两组共 81 个不同用例，不将中间重复执行累加 |
| 临时安装副本 | 学习 Rust 夹具、设计/普通上下文返回、改动后旧锚点阻断均通过；安装 Runtime 与最终源码一致 |
| ArkLog 只读范围 | TUI 27 文件 / 417 声明，Core 5 文件 / 70 声明；capabilities 均只有 definitions，无 adapter_errors |
| 实际设计查询 | full 24、compact 3 个锚点；首项均保留显式 Controller 文件；不保证展示全部目标方法 |
| 实际聚焦查询 | 返回 `pump_log_batches_limited` 的 365–383 行及 `reconcile_stream` 的 190–224 行，当前内容摘要门禁为 current |
| 原始源码与边界 | ArkLog 202 个原始文件及工作区状态不变；Python 500 行门禁与 diff 检查通过 |

新源码仅在旧语言注册/语义适配/静态提取路径接入两个模块，另对已复现的设计投影裁剪作局部修正。
无新命令、依赖、数据库迁移或评分服务。第一次宽视图要求目标方法全覆盖的检查仍保存为失败；
后续没有将该要求包装为已通过，而是明确了文件导航与聚焦方法证据的不同范围。
