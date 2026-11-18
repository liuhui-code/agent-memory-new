未在给定源码根找到字面量 `"After an earlier load failed"` 的发出位置。

实际检查的源码证据：
- `ThumbnailLoader.ts:1–9`：直接使用 JSON 已提供的 current-worktree excerpt，未重复读取。
- `ThumbnailLoader.load`（`ThumbnailLoader.ts:2–8`）捕获 `fetch(path)` 的错误；第 6 行发出的实际字符串是 `THUMBNAIL_READ_FAILED: load failed`，不是请求的字面量。
- 保留其 `code_symbol` IDs `7, 6` 及 `emits_log → code_log_statement:1` 关系作为原始证据，不把检索优先级当作精确匹配证明。

有限扩展记录：
1. 缺口：primary excerpt 不含指定字面量。对给定源码根执行一次 `rg -n -F 'After an earlier load failed'`，无匹配。
2. 缺口：检查其他文件是否存在可拼接的片段。执行一次 `rg -n 'After|earlier|failed' --glob '!ThumbnailLoader.ts'`，无匹配。

使用预算：2 次源码搜索、2 轮扩展、0 个新增读取文件；共检查 1 个源码文件 excerpt。未重查 Runtime、DB、Git、测试或报告，未修改文件。

未知事实：无法据此确定该短语是否来自给定源码根外、运行时拼接或已不存在的版本；也没有证据证明它曾实际输出。原 JSON 的 inferred `runtime_log_diagnosis` 不改变用户这次“定位字面量”的请求。本结果仅为开发消费观察，不是原门禁或 A/B 晋级结论。
