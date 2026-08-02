# 跨语言 Source / Artifact Adapter 设计

## 已证明的问题

两个独立 development 来源在正式 Context 输出中首先丢失候选：

- `k2-fsa/sherpa-onnx#3759`：ArkTS 入口命中，但 C++ N-API、C API 与 HarmonyOS 构建脚本未进入候选。
- `TermonyHQ/Termony#142`：真实日志为 `EXEC FAILED: errno=13 (Permission denied)`；冻结修复前源码后，
  5 个 Oracle 文件最终命中 0 个，候选池只覆盖 2/5，C++ 启动链和 HNP Makefile 均缺失。

两者来源族、故障机制和仓库均独立，且缺陷出现在正式 `query_handoff` 的 `candidate_file` 阶段。

## 业界依据

- [SCIP](https://github.com/scip-code/scip) 使用语言无关协议承接语言专属 indexer，证明统一消费模型
  不应绑定单一解析器；其生态包含 C/C++、TypeScript、Dart 和包文件 indexer。
- [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) 提供可增量、容错的多语言语法树；本阶段保留
  静态 fallback，长期由精确 Provider 替换，而不是把正则扩散进查询层。
- [LSP 3.17](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/)
  将语言能力隔离在稳定协议后；本项目沿用已有 Semantic Adapter Port。
- [Bazel Query](https://bazel.build/query/language) 将 target、action、artifact 及关系视为图，而非普通
  文本；因此 Makefile/CMake/HNP 配置作为 Artifact Graph 输入，不混为业务源码。

## 架构

1. `SourceAdapter`：按精确文件名和后缀分类，输出 language、artifact role 和 adapter id。
2. `SemanticAdapter`：C/C++ 与 Build Artifact 输出现有 `SemanticBatch`，静态结果保留 span、
   evidence class 和 Provider telemetry；未来 SCIP/Tree-sitter Provider 不改存储和查询协议。
3. `SourceBoundaryEdgeAdapter`：解析 ArkTS `.so` import、CMake target/source 与 HNP package target，
   输出 `imports`、`builds`、`configured_by` 关系。关系只表达静态结构，不声称真实执行。
4. `query_handoff`：继续使用统一 FTS、图邻居和源码摘录；Agent CLI 根据真实日志筛选可能路径。

## 边界与性能

- 第一阶段支持 C/C++ 常见后缀、Shell、Make、CMake 及主流构建清单，不引入新数据库。
- 每个静态摘要、字符串证据、target 和跨边界关系均有数量上限；不索引二进制或生成目录。
- 增量刷新复用现有 scope invalidation；构建边界变化时只重建相关结构边。
- 不加入项目名、案例文件名或 Oracle 关键词特例，不改变四 Skill 和 Runtime/Agent 职责。

## 验证顺序

1. [x] 独立 fixture 验证分类、C++ span、构建 target 与跨边界边。
2. [x] 重跑 Termony development case；未修改其任务或 Oracle。
3. [x] 重跑 sherpa development case；未根据结果调整案例。
4. [x] 跑完整回归、10 万实体 CI 和百万实体性能门禁、500 行门禁。
5. [ ] 新来源一次性外部验证前，所有结果仍是 development，不宣称泛化或 Agent 诊断提升。

## 已完成实现

- `SourceAdapter` 统一识别 C/C++、Make、CMake、Shell 与现有语言；查询层不包含后缀分支。
- C/C++ 与 Build Artifact 通过现有 `SemanticBatch` 写入定义、源码区间、静态调用和 Provider telemetry。
- C/C++ fallback 支持常见跨行函数签名和平衡函数体范围；条件编译下的同名定义使用不同 symbol key。
- Build Artifact 为 Make/CMake target、Shell function 和变量写入源码位置。
- ArkTS `.so` import、CMake source 与 HNP package/Make target 形成有界 `imports`、`configured_by` 边；增量学习不重复插入。
- 查询使用现有 FTS5、图邻居、源码摘录和 1,500 Token 紧凑协议；Runtime 仍不做诊断。

## Development 观察

- Termony 原样复测仍为 0/1。候选文件召回为 0.60、分层文件召回为 0.40，最终锚点召回为 0，平均 Context 为 1,496 Token。其 Oracle 要求同时返回 5 个文件，而紧凑协议最多返回 4 个代码锚点，因此该包不能作为当前 compact pass/fail 契约；案例保持不变，未据此继续调权。
- Sherpa 三阶段原样复测仍为 0/3，但多行 C/C++ 定义修复使候选文件召回从 0.25 提升到 0.50，并产生直接 symbol identity 证据。最终锚点仍为 0.25，说明 native caller/build artifact 的候选组合仍不足。
- Sherpa 2,872 文件重建由约 25.3 秒增至约 30.2 秒。该成本可用于 development 验证，但尚未形成跨仓库索引 SLO 结论。
- 两套案例均为 `legacy_unclassified`、unsealed development 观察，`promotion_eligible=false`。它们证明索引覆盖有改善，不证明 Agent 诊断效果或跨项目泛化。

## 停止条件与后续

本阶段不再对这两个已观察包调整权重或 Oracle。下一项 serving 改动必须先在独立 fixture 复现明确损失层；下一次推广判断需要新的、预先分类并冻结的外部案例。长期精度升级走 Tree-sitter/编译器/LSP/SCIP Provider，不继续扩张核心查询器中的语言正则。
