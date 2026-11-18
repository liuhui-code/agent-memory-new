目标是 `DocumentSession.swapDocument(path)`，不是名称恰好为 `load` 的缩略图方法。

实际源码：`/workspace/scratch/dcdb41e16594/concrete-plan-work/history-retention/source/DocumentSession.ts:5–9`。该方法先在第 6 行执行 `this.ready = false`，第 7 行替换 `documentPath`，再于第 8 行调用 `reader.openDocument(path)`。因此，每次进入替换方法都会先重置 ready，包括上一次读取失败后的再次调用。底层读取是同文件 `DocumentReader.openDocument`，第 12–14 行执行 `await fetch(path)`。

证据与开发观察：
- 已消费 JSON 中 `ThumbnailLoader.ts:1–9` 的完整 excerpt，没有重复读取。其 `load` 只 fetch 并捕获、记录错误，不涉及 document 或 ready。
- 展开第 1 轮，仅补读 `DocumentSession.ts:1–15`，关闭“哪一方法实现替换文档与 ready 重置”的缺口。
- 新增源码搜索 0 次；新增源码读取 1 次；涉及源码文件共 2 个（含给定 excerpt）；未进行第二轮展开。
- JSON 将请求推断为 `runtime_log_diagnosis`，且把 `ThumbnailLoader.load` 列为 primary；当前源码则支持 alternative `DocumentSession.swapDocument` 为请求所指操作。检索排序不是业务归属证明。
- 未知：未验证实际失败曾发生、调用方是否调用该方法，或运行时行为是否通过测试。此结论仅为源码定位，不是故障修复验证。
- 无文件修改、无 Runtime/DB/Git/测试查询。这是开发消费观察，不是原门禁或 A/B 晋级结论。
