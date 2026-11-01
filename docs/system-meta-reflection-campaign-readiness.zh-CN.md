---
type: feature-spec
id: SPEC-system-meta-campaign-readiness-1
status: draft
scope: ["tools/agent_memory_runtime/system_evolution_campaign_readiness.py", "tools/agent_memory_runtime/prospective_cohort.py", "tests/test_system_evolution_campaign_readiness.py"]
owner: ""
approved_by: ""
approved_at: ""
approval_ref: ""
supersedes: ""
superseded_by: ""
---

# R4 准备切片：真实活动的只读就绪门禁

日期：2026-11-01。承接[递归方案](system-meta-reflection-recursive-evolution.zh-CN.md)的 R4。
当前未收到真实活动项目/任务来源等外部资料；实施本准备切片不代表真实 R4/R5 活动完成。
批准字段保持空白。

## 证据与范围

[强制政策](evaluation-and-change-policy.md#真实活动就绪门禁)要求在首个真实任务前指定项目、
任务前 Memory Home、未来来源/连续性负责人、验证方式、原始任务保管及固定停止。
现有 Cohort v1 只支持 diagnosis/selective-query-skill，不支持通用系统演进或正常任务漏检审计。
没有来源时停止此类能力扩张；本切片只检查启动资料并修复拒绝输入时的初始化顺序。

两个独立临时开发条件已在真实 eval-cohort-create 复现：缺少真实来源 manifest，或不支持的
workflow 任务协议，均退出 1，但已经创建 Memory Home 和 memory.db。首次失败层为
ensure_initialized 先于输入验证，见[实际复现](evidence/system-meta-reflection/readiness-preflight-reproduction.json)。
修复只把既有协议/来源校验移到初始化之前，不放宽协议、评测器、来源或排名规则。

## 只读审计

新增 maintain-system-campaign-readiness，参数 --project、可选 --memory-home、
--protocol-file、--campaign-manifest、--intent（system_evolution 默认，或 diagnosis_query）和 --json。
没有 --execute。缺归档时不初始化；不打开 Memory 数据库、不访问业务任务/源码正文、模型或网络，
不登记或开始活动。只读取指定有界资料、Runtime 自身代码及本地 Git 元数据。

输入 JSON 限 32 KiB，UTF-8，拒绝重复键。复用既有 validate_protocol / validate_manifest，
分类 internal、external、campaign、evidence：

- internal：实际支持的 diagnosis 合同范围、归档是否存在（不代表完整性已验证）。
- external：项目、来源/负责人/开始点、Memory Home、验证、保管和固定停止资料缺项。
- campaign：资料及协议的结构/绑定检查、目标数量、来源等级；仅返回摘要和有界错误，不返回私密字段。
- evidence：本调用未启动活动、不验证真实性/连续性/收益，不从已有回归数量推断样本数。

system_evolution 始终保留 unsupported_campaign_contract，不能用 diagnosis 协议取得通用活动资格。
生成校准材料不能变成真实来源。只有显式 diagnosis_query 且真实来源声明通过既有验证时，
可返回 inputs_valid_only；这仍不是执行许可、活动已经开始、来源认证或效能通过。

审计绑定目标项目 ID、本地 Git revision/tree/脏状态摘要，及实际 Runtime 代码清单摘要和
宿主检出 revision。宿主 Git revision 不是已安装 Runtime 的发布版本；精确代码摘要保留二者区别。
这些是分次读取的 point-in-time 观察，不提供原子快照或全环境认证。
脏状态仅为 Git 状态摘要，不是当前未提交文件的内容快照。

## 边界与后续

没有真实来源时，只交付资料模板、只读审计及受控机制证据；不开始任务队列或添加通用评测流程。
真实 R4 仍需用户提供来源和冻结合同；R5 的独立对照、漏检分母、泛化及长期收益另行建立。
现有业务 Memory 与已消费密封资产不参与本准备工作。

可安装使用说明见 [Maintain 参考](../skills/agent-memory-maintain/references/system-campaign-readiness.md)，
实际范围和证据见[完成记录](system-meta-reflection-campaign-readiness-completion.zh-CN.md)。
