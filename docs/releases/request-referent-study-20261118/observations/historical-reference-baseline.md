文档加载操作的实现是 `DocumentSession.ts:12–14` 的 `DocumentReader.openDocument(path)`，实际执行 `await fetch(path)`。

替换文档的入口是同文件 `DocumentSession.swapDocument(path)`（5–9 行）：先将 `ready` 置为 `false`（6 行），再更新路径并调用 `openDocument`（7–8 行）。因此，当前实现已经在新加载开始前重置 ready；若加载抛错，本次调用中也没有将它改回 true 的代码。

检索首选的 `ThumbnailLoader.load`（payload excerpt，`ThumbnailLoader.ts:1–9`）只包含缩略图请求和失败日志，没有文档替换或 ready 状态，不能据此认定它是用户所指的失败操作。

**实际证据与预算**
- 使用 payload：原始 query、primary code anchor/excerpt（record `code_symbol:7`）、callable alternative `DocumentSession.swapDocument`、source exploration limits、evidence gaps。
- 扩展记录：第 1 轮为补足“文档替换和 ready 重置实现”缺口，读取 `DocumentSession.ts:1–15`；工具请求窗口为 1–120，文件实际共 15 行。没有重读已提供 excerpt。
- 源码覆盖 2/7 文件（含 payload excerpt）；新增读取 1 次、15 行；搜索 0/3；扩展轮次 1/2；未重查 Runtime，未修改文件。
- 未知：没有实际失败日志或运行验证，无法确认历史上失败的具体调用。上述结论定位当前实现，不声称已复现或修复故障。
