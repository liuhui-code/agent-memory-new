# 旗舰 ArkTS 日志问题定位纵向价值验证

## 目标与边界

本阶段验证 Agent Memory 是否能在真实 ArkTS 事故中向本地 Agent CLI 提供有增量价值的
代码、日志与经验上下文。Runtime 只负责证据供给，Agent 负责诊断和设计；不增加第五个
Skill，不持久化用户流水日志，不使用 LLM Judge，也不把 development 结果描述为外部门禁。

案例来自 `k2-fsa/sherpa-onnx` 的公开 HarmonyOS 事故
[#3759](https://github.com/k2-fsa/sherpa-onnx/issues/3759)，冻结源码为 tag `v1.13.3`
对应的 `330609dab49be6ee8b30702918ca7abbbad1286a`。历史经验只来自更早的 iOS 事故
[#3639](https://github.com/k2-fsa/sherpa-onnx/issues/3639)。源码许可证为 Apache-2.0。

## 方法依据

- 采用消融实验，将 source-only、结构上下文、Agent 经验和理想经验分层比较，避免将
  检索与推理收益混成一个总分。该思路与 RAGAS 的检索/生成分解评测一致：
  <https://arxiv.org/abs/2309.15217>。
- 采用时间截断，历史经验必须早于目标事故；长期记忆任务的时间敏感性参考 LongMemEval：
  <https://arxiv.org/abs/2410.10813>。
- 候选生成和排序分层归因参考 TREC 与 BEIR；缺失候选不能靠末级加权补回：
  <https://trec.nist.gov/howto.html>、<https://arxiv.org/abs/2104.08663>。
- 所有改动与停止条件服从 `docs/evaluation-and-change-policy.md`。

## 四层实验

现有 Runner 保持 baseline/memory 二元协议。四个概念层映射为三个独立成对案例：

1. `source-only`：每个案例的 baseline，只允许 Agent 读取冻结源码。
2. `structural_context`：memory 组仅有代码图、日志图和当前源码摘录，不注入经验。
3. `agent_memory`：在相同 Context 上注入由早期公开事故形成的 Agent 反思。
4. `ideal_memory`：在相同 Context 上注入人工审查的紧凑理想经验。

三个案例必须共享任务、源码 revision、Oracle 和历史截止时间。`context_setup` 不暴露给
Runner；Runtime 在隔离数据库中应用后，只返回反思数量与规范化 SHA-256 审计。摘要只证明
输入一致，不证明经验正确。理想经验因在目标案例审查后整理，必须标为
`development_posthoc_or_unverified`，不能宣称为独立上界。

## 执行顺序

1. 冻结来源、任务、Oracle、历史截止时间和三层经验输入。
2. 在不可变 revision 上重建一次共享索引，为每层创建隔离数据库快照。
3. 先运行无需模型的 `eval-context-capability`。
4. 只有 Context 门禁通过且治理允许晋级时，才执行三个案例各自的 baseline/memory Agent
   配对；随后计算结构收益、Agent 经验增量和理想经验上界差距。
5. 在首个可证明损失层停止，不使用下游 Agent 结果掩盖上游缺失。

## 工作区安全契约

真实仓库包含内部相对符号链接及两个指向开发者机器的绝对符号链接。原评测器会在不可变
归档上直接失败，而 working-tree 路径会保留可逃逸链接。这是可用性和隔离性两类独立缺陷，
共同指向评测工作区缺少统一净化契约。

实现规则：保留工作区内符号链接；剔除外部符号链接，并在有界的
`.agent-benchmark-sanitization.json` 中记录相对路径和数量；路径穿越及外部硬链接继续拒绝。
报告不记录宿主机目标路径。

## 2026-08-02 Development 结果

工作区净化后，三个 Context 案例均执行完成，但门禁为 `0/3`：

- 预期四个文件只召回 ArkTS `NonStreamingTts.ets`，anchor recall 为 `0.25`。
- C++ N-API 边界、C API 构造函数和 HarmonyOS Runtime 构建脚本均未进入候选集。
- 首个损失层稳定为 `candidate_file`，不是排序、压缩或经验选择。
- Oracle anchor precision 与首命中 MRR 均为 `1.0`，说明已召回的 ArkTS 入口准确。
- 平均 Context 为 `1,133` tokens，低于 `1,500` 预算；经验层各有一条经验被实际注入。
- Agent 未调用，用户流水日志未写入记忆。

## 结论与停止条件

当前已证明系统能紧凑、准确地交付 ArkTS 入口及历史经验，但尚不能为真实的
ArkTS -> C++ -> C API -> 构建配置事故提供完整上下文。此结论是 development 观察，不能证明
整体问题定位能力退化，也不能据此扩展生产语言索引范围。

下一次实现前必须再取得一个独立项目或独立事故，分别复现“语言边界源码缺失”和“构建配置
证据缺失”对正式 `query_handoff` 的影响。两类缺陷都成立后，才能设计语言无关的 Source
Adapter/Artifact Adapter 契约，并用新来源做一次性外部验证。此前停止在证据缺口，不运行
昂贵 Agent A/B。
