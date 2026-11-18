目标是 `ThumbnailLoader.load(path: string): Promise<void>`，位于 `source/ThumbnailLoader.ts:2–8`。它在第 4 行 `await fetch(path)`；若抛错，在第 5–6 行捕获并输出 `THUMBNAIL_READ_FAILED: load failed`。错误被捕获，没有重新抛出。

给定 excerpt 中的 `source/DocumentSession.ts:5–9` 是早先的 `swapDocument`，不是所找的 load 方法。它将 `ready` 设为 false 并等待 `reader.openDocument(path)`；这些代码未建立该失败与缩略图 load 的关联。因此只能确认 load 自身 fetch 失败时记录错误，不能确认“先前 swapDocument 失败必然使 load 报错”。

观察记录：
- 查询：保留给定 JSON 原查询；未重查 Runtime、DB、Git、测试或报告。
- 来源：给定 JSON `project_id=88836fa8d065fc26`，freshness=current、generation=1；具体源码 revision 未给出。
- 已检查：JSON excerpt `DocumentSession.ts:1–15`（record_type=`code_symbol`，record_ids=`[3]`）；补读 `ThumbnailLoader.ts:1–9`（callable alternative，未提供 record ID）。
- expansion_trace：第 1 轮，补读 1 文件，闭合“请求中的 load 实现尚未检查”缺口。
- 源码搜索 0 次，扩展 1/2 轮，涉及源码 2/7 文件，无重复 excerpt。
- 停止：目标方法与错误输出已直接检查；跨方法失败传播未知。仅开发消费观察，不代表原门禁或 A/B 晋级。
