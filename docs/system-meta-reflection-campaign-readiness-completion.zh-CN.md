# R4 开发准备完成记录

日期：2026-11-01，基于 4d5e068 和工作区 R1/R2/R3 更新。
用户明确选择：先完成开发契约与隔离验证，暂不开真实活动。
本文只覆盖[就绪门禁切片](system-meta-reflection-campaign-readiness.zh-CN.md)，不标记 R4/R5 真实活动完成。

## 实际交付

- 只读 maintain-system-campaign-readiness，按 internal/external/campaign/evidence 返回范围与缺口。
- 输入有界、重复键拒绝，复用原协议/来源检查，保留诊断与通用演进合同边界。
- 绑定实际 Runtime Python 代码摘要和目标 Git 元数据；不把宿主 Git revision 当 Runtime 发布版。
- inputs_valid_only 仅代表原 diagnosis 声明校验通过，不提供执行许可、来源认证或真实收益。
- 已复现并修复 eval-cohort-create 拒绝非法输入时仍先建库的问题：资料校验先于初始化。
- 安装版 Maintain 增加按需说明；不新增表、评测器、模型、任务队列或后台任务。

## 实际复现与隔离验证

[改动前复现](evidence/system-meta-reflection/readiness-preflight-reproduction.json)来自两个独立临时
CLI 场景：真实来源 manifest 缺失、workflow 协议不受支持；均退出 1 且已创建数据库。
初次失败层是初始化顺序，不是检索或结果评分。修复只移动既有校验顺序，不改通过条件。

[八个独立用例](../tests/test_system_evolution_campaign_readiness.py)核对：

| 范围 | 实际核对 |
|---|---|
| 默认无资料 | 六组缺项、通用合同 unsupported；临时目录和 Memory 不被创建 |
| 合同范围 | 既有完整 diagnosis 声明只为 inputs_valid_only，通用活动/校准/不支持任务仍 no_go |
| 有界及保密 | 错档、重复键、超长/非法 JSON 拒绝；路径、负责人和原始标记不回显 |
| 拒绝顺序 | 四种非法 create 输入均不创建 Memory；原有归档在拒绝后字节不变 |
| 数据库与查询 | 实际拦截 sqlite3.connect 证明审计不打开库；非空 query_handoff 保持 |
| 安装与版本 | 安装副本实际调用，Runtime 代码摘要与源码一致；目标 Git revision 与脏状态分账 |

首轮 41 项通过，耗时 73.672 秒，其中包含由导入 TestCase 类额外发现的 10 项候选用例。
已改为模块导入，最终批次不包含这类重复发现。八项新用例及既有来源/Cohort 用例均实际通过。
最终影响面批次单独保存在[R4 机器记录](evidence/system-meta-reflection/regression-r4-readiness.json)，
选定就绪、来源、Cohort、治理基础、旧版普通读写与安装模块；不冒称重跑了整个 R3 生命周期批次。

最终批次 43 项全部通过，0 失败/错误，无跳过。执行 79.712 秒，含记录/清理 79.917 秒，
Python 3.9.6、SQLite 3.51.0；临时根清理完成。全部八项当前就绪用例在该批次通过。
开始/结束及收尾重算的 342 个 Runtime/Skill/测试文件清单一致，摘要为
ecf0438adb1acce1d92ca8593564680395b96c57c3f49b4248cba25f17057178。
清单包含所用 Cohort/来源测试及此前元反思源码，不表示所有历史模块本次都重新执行。

收尾检查：30 份专用文档的 181 个本地链接有效，50 个相关 Python 文件指纹齐备且不超过
500 行（最多 480 行）；六份更新规范通过既有解析器大小/头部/状态检查，批准字段为空。
git diff --check 通过。运行时长是验证成本，不是产品性能或效能指标。

## 当前开发探针与真实边界

[开发就绪记录](evidence/system-meta-reflection/readiness-r4-development.json)通过真实单一 Runtime
命令生成。观察目标为当前开发仓库，Memory Home 明确指向临时未初始化目录；它们没有被选定
为真实活动项目/归档。临时探针未创建任何归档，已清理；本切片采集真实任务数为零。
审计结论 no_go：外部六组资料未提供，通用演进活动合同 unsupported。没有把旧诊断合同放宽
成正常任务漏检或跨组件效能合同，没有读取或重建任何真实业务任务。
开发探针的 Runtime 代码摘要为
8e4ecc08b536df6773a2c860eeb3948e0ff5fd555357b6cc0fa00d740e7a0f3f，收尾重算一致。

R3 真实宿主记录保留原源码范围，本准备切片未重复调用模型；没有 R4 宿主或长期效能通过声明。
Skill 仅增加引用/说明，frontmatter 沿用已核对版本；PyYAML 缺失的专用验证器未冒称已运行。
现有业务 Memory、已消费密封资产及原有未跟踪 memory.md 未读取或改动。
本记录形成于 R4 准备收尾时，当时改动尚未提交；后续主分支交付见 Git 历史。真实项目未部署。

后续[两轮集成演练](system-meta-reflection-development-journey.zh-CN.md)在不改变本次 342 文件的
情况下新增一个组合测试；它独立记录两轮安装版流程，不回写这里的 43 项或声明真实活动完成。
