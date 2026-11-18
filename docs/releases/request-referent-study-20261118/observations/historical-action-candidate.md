状态所有者是 `DocumentSession`，不是 `ThumbnailLoader`。

- 源码：`/workspace/scratch/dcdb41e16594/concrete-plan-work/history-retention/source/DocumentSession.ts:1–9`
- `ready` 是该类的私有字段（第 2 行）。
- `swapDocument()` 先执行 `this.ready = false`（第 6 行），随后更新路径（第 7 行），最后调用并等待 `reader.openDocument(path)`（第 8 行）。当前代码已经满足“打开新文档之前重置 ready”的要求。
- 同文件 `DocumentReader.openDocument()`（第 11–15 行）负责读取，不持有该 ready 状态。

证据与预算：
- 已检查给定 `ThumbnailLoader.ts:1–9` excerpt，未重复读取。它只显示读取和失败日志，没有文档替换或 ready 字段；不能据此认定它拥有目标状态，也不能认定它就是先前失败的实际来源。
- `expansion_trace`：第 1 轮，为关闭“目标状态所有者与替换操作未被 primary excerpt 覆盖”的缺口，读取已有 callable alternative 指向的 `DocumentSession.ts:1–15`。JSON 未提供 `allowed_expansion_reasons` 列表。
- 源码搜索 0 次；扩展 1 轮、1 个文件；共检查 2 个源码文件（含给定 excerpt），新读 15 行。没有运行 Runtime、DB、Git 或测试，没有修改文件。
- 未知：此前失败是否实际发生、失败来自哪里、完整运行时状态演进。此次已完成状态定位，不声称诊断或验证修复成功。
