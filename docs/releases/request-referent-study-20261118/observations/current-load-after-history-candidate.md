按“替换文档并重置 ready”的行为描述，对应 `DocumentSession.swapDocument(path)`，并非字面命名为 `load`：
- `source/DocumentSession.ts:5–9`：第 6 行先设置 `this.ready = false`，第 7 行替换路径，第 8 行调用 `reader.openDocument(path)`。
- 同文件 `12–14` 行：实际读取入口 `DocumentReader.openDocument`，内部调用 `fetch(path)`。

如果“load method”要求字面名称，则给定摘录中的 `ThumbnailLoader.load` 位于 `source/ThumbnailLoader.ts:2–8`；它捕获读取错误并打印 `THUMBNAIL_READ_FAILED: load failed`，未涉及文档替换或 ready。不能将这两个方法视为已证实的同一调用链。

探索记录：
- 原始 primary 摘录 `ThumbnailLoader.ts:1–9` 已检查，未重复读取。
- 扩展第 1 轮：为核实“替换文档／ready 重置”缺口，读取候选 `DocumentSession.ts:1–15`。
- 源码搜索 1 次，排除上述已读文件后搜索 `load|ready|document|openDocument`，无匹配。
- 共涉及源码文件 2 个，扩展 1 轮；未修改文件，未查询 Runtime、DB、Git、测试或其他实验材料。

未知：没有实际失败日志、执行顺序或测试证据，不能确认此前失败属于哪个读取方法，也不能宣称运行时问题已修复。以上为开发消费观察，不是原门禁或 A/B 晋级结论。
