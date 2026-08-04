# Agent A/B 测量链校准报告

## 结论

本轮完成 3 个案例、每例 3 轮、共 9 个 pair 和 18 次独立 Agent 调用。交叉顺序审计
通过：Baseline-first 5 次，Memory-first 4 次；所有 observation 使用同一个 Codex
`gpt-5.5`、low reasoning、prompt protocol digest 和隔离只读 Runner。

本轮**没有证明诊断质量 uplift，也没有隔离出 Context 自身的效率贡献**。三个案例的 Baseline 与 Memory 平均 outcome 都是
0.9111，根因准确率都为 0.7778。与此同时，Memory 将平均 Token 从 119,477 降至
64,656（-45.88%），平均耗时从 42.73 秒降至 30.38 秒（-28.91%），源码搜索减少
75.00%，源码读取减少 50.82%。但旧 Runner 只给 Memory 注入调查协议和硬预算，并在 Memory
查询完成后才开始计时，因此这些数字只能称为“Context + 调查协议”的组合信号，不能归因于
Context，也不能用于晋级或修改 serving path。

## 二维矩阵

| 案例 | Context gate | Outcome uplift | 效率 | 治理解读 |
|---|---:|---:|---|---|
| `mutation-e94b869b178b` | pass | 0.0 | Token -10.60%，Agent 耗时 -27.11% | 质量已到 1.0 ceiling；只校准旧协议，不代表真实事故或 Context 效率 |
| `youtube-media-page-array-merge` | fail | 0.0 | Token +11.61%，耗时 -10.09%，搜索/读取下降 | 候选阶段召回目标，但紧凑投影丢失；Agent 三轮 `+0.4/-0.4/0`，供给缺陷与效用混合，不能晋级 |
| `dimina-harmony-tabbar-height` | fail | 0.0 | Token -70.61%，Agent 耗时 -41.21%，搜索 4.67→0 | exact owner 未召回；近邻 Context 或 Memory 独有调查协议可能减少探索，当前实验不能区分 |

预注册的 outcome 矩阵把两个真实案例都归入 `Context fail + uplift zero`。Youtube 只支持继续
调查紧凑检索供给。Dimina 只能形成“近邻 Context 可能降低探索”的假设，不能证明 exact-owner
门禁产生效率假阴性，因为 Agent 两组没有使用相同调查协议。后续必须使用 v2 唯一变量合同，
并把定位 outcome、机制证据与端到端 efficiency 分开预注册。

## 治理决定

1. 保留 `alternating_case_trial_parity/v1`、完整 pair 审计和 prompt digest；固定顺序偏差已消除。
2. 保留确定性评分器。本轮离线重评分直接复用 18 条 response，没有再次调用 Agent，结果一致。
3. 不修改 Runtime serving 排序、Context 阈值或 Oracle。Youtube 只有一个紧凑投影缺陷类；
   Dimina 只有一个近邻效率案例，均未达到两个独立缺陷类的架构变更条件。
4. 已停止按旧协议扩充案例。下一轮先使用 `agent-benchmark-treatment/v2`：两组共享提示与预算、
   计入 Memory 查询成本、使用机制范围 Oracle、每案例偶数轮，再收集独立 Development 证据。
5. Mutation 结果只用于协议校准，不得计入真实事故准确率。

## 证据

- 案例与 Context：[Youtube 案例](agent-ab-calibration-mutation-cases.json)、
  [Youtube Context](agent-ab-calibration-youtube-context-result.json)、
  [Dimina 案例](agent-ab-calibration-dimina-cases.json)、
  [Dimina Context](agent-ab-calibration-dimina-context-result.json)
- Agent 结果：[Youtube 完整结果](agent-ab-calibration-youtube-result.json)、
  [Youtube responses](agent-ab-calibration-youtube-responses.json)、
  [Dimina 完整结果](agent-ab-calibration-dimina-result.json)、
  [Dimina responses](agent-ab-calibration-dimina-responses.json)
- 机器可读汇总：[campaign summary](agent-ab-measurement-calibration-summary.json)

原始源码正文、工具输出和私有推理均未持久化；结果只保留结构化答案、文件名与聚合遥测。
本报告是对已消费响应的解释修正，没有修改案例、Oracle、response 或重新调用 Agent。
