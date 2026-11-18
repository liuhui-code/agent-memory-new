状态所有者是 `DocumentSession`，不是首位检索结果 `ThumbnailLoader`。

实际源码：`/workspace/scratch/dcdb41e16594/concrete-plan-work/history-retention/source/DocumentSession.ts`
- 第 1–4 行：`DocumentSession` 持有私有 `ready` 和 `documentPath`。
- 第 5–9 行：替换入口 `swapDocument()` 先执行 `this.ready = false`（第 6 行），再更新路径（第 7 行），最后调用 `reader.openDocument(path)`（第 8 行）。请求中的重置顺序已存在。
- 第 11–15 行：`DocumentReader.openDocument()` 仅调用 `fetch(path)`，不是此 `ready` 状态的所有者。

给定 excerpt `ThumbnailLoader.ts:1–9` 只展示缩略图加载失败日志，没有文档替换或 `ready` 状态；它不能证明所请求的所有权。已检查该 excerpt，未重复读取。

消费记录：
- 原 JSON 保持不变；使用其 alternative `DocumentSession.swapDocument` 精确定位。
- `expansion_trace` 第 1 轮：补齐“primary 未展示所请求状态及替换入口”的缺口，读取 `DocumentSession.ts:1–15`，新增 1 文件。
- 源码搜索 0 次；扩展 1/2 轮；涉及源码文件 2/7 个（含给定 excerpt）；新增源码读取 1 次。
- 未重查 Runtime、DB、Git、测试、报告或其他实验 protocol；未修改文件。

未知事实：未验证真实的早先加载失败、运行时复现及其他状态写入；不能宣称故障已修复。此为源码定位完成的开发消费观察，不是原门禁或 A/B 晋级结论。
