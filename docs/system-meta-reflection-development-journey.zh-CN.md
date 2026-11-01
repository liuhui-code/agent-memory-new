# 两轮元反思开发闭环：操作顺序与隔离验收

日期：2026-11-01。按用户“完成开发契约与隔离验证，暂不开真实活动”的范围收尾。
本文组合既有 [R1 结果关联](system-meta-reflection-outcomes.zh-CN.md)、
[R2 轮次](system-meta-reflection-rounds.zh-CN.md)、[R3 宿主交接](system-meta-reflection-handoffs.zh-CN.md)
和 [R4 就绪准备](system-meta-reflection-campaign-readiness.zh-CN.md)，不新增运行时能力或评测标准。

## 一轮如何推进到下一轮

```mermaid
flowchart LR
    A[预绑定计划与候选] --> B[检查 验收 显式应用]
    B --> C[窗口结果与一次交接]
    C --> D[保存评估与建议决策]
    D --> E[按授权实际回退或保留]
    E --> F[新计划 新提案 子轮]
    D -.晚到反馈.-> G[追加评估 保留旧决策]
    F --> H[新任务边界内一次交接]
    H --> I[停止与实际代码恢复]
    I --> J[历史查询 Memory保留 就绪复核]
```

每轮的操作依据原始计划、已绑定制品、实际操作回执与新窗口材料。当前 Agent 解释结果并
提交建议；Runtime 提供存储、上下文及显式执行。模型评价、登记次数和 checked/closed
不会自动成为因果收益或下一次部署许可。

| 步骤 | 使用的既有入口 | 推进条件 |
|---|---|---|
| 预声明 | maintain-system-status prepared、candidate、check、accept | 计划在应用前绑定，检查/验收及当前授权齐备 |
| 应用与观察 | maintain-system-apply、follow-up、outcome | 使用实际应用键，保留失败、未知及缺失成本 |
| 开轮 | maintain-system-round-record open | R2 显式安装，轮次键与计划一致，预算/父轮符合 |
| 窗口交接 | maintain-system-round-handoff claim/complete | 预绑定 v2 许可、窗口/新观察/预算齐备；本次领取才授予生成 |
| 建议与实际操作 | round-record decision；apply/rollback 等已有生命周期入口 | 建议写入后，实际文件操作仍按授权及生命周期单独执行 |
| 子轮 | 新提案/计划/应用，再 round-record open | 最新非 stop 已决父轮、新绑定和剩余预算；保持来源谱系 |
| 晚到反馈 | round-record assessment | 非 stop 已决轮内有新上下文及剩余预算，保留 decision_revision |
| 收尾 | round/handoff inspect、campaign-readiness | 保存旧负面/未知结果；真实活动资料不足继续 no_go |

同一任务边界不能在两个自动路径或两个轮次重复领取评审。子轮使用新边界时仍须保留实际
来源关联；换 ID 不会制造独立证据。同一开发 fixture 的两轮始终是一个受控场景。

## 本次真正执行的九个阶段

[集成用例](../tests/test_system_evolution_development_journey.py)实际安装当前 Runtime 和四个
Skill，执行两份候选的检查、验收、应用、监测和回退。窗口任务结果/Agent 意见明确为合成
声明，驱动不调用模型，不采集真实业务任务。以下是 **一个测试中的九个阶段**。
候选对象是 value.txt、added.txt、delete.txt 的受控文件布局；本次证明范围限于本地应用/
恢复及跨阶段协议，不产生算法效果结论。

| 阶段 | 实际观察 |
|---|---|
| 安装与父轮 | 源码/安装 Runtime+Skill 摘要相同，父提案实际处于 monitoring |
| 父轮评估和建议 | 保存评估及 rollback 建议后，应用文件仍为 after |
| 实际父轮回退 | value.txt 恢复前像，应用后的第一条 Memory 写入保留 |
| 子轮应用和关联 | 新计划/提案/候选/实际应用关联到第 2 轮；使用不同的受控任务声明 ID |
| 名额 | 复用父轮任务边界被拒绝；新子轮边界获得一次名额 |
| 晚到父轮反证 | 追加 contradicted 声明，原 rollback/decision_revision 和实际回退记录保留 |
| 子轮完成与停止 | 父轮反馈不改变子轮冻结上下文；子轮完成后 stop，续写及第三轮预算均拒绝 |
| 回退与历史 | 子轮实际回退后两条后写 Memory 保留；删除临时输入后历史/幂等读取可用，旧 unknown 仍在 |
| 查询与 R4 | 非空 query_handoff 前后相同；就绪读取不写库，真实活动保持 no_go/未启动 |

临时输入的删除仅用于核对历史快照读取；实际材料保管规则继续适用。
这不是长期收益样本、独立任务集、真实 Cohort 或完整 RE01–RE14 验收。

## 执行与失败记录

首试一个测试出错，耗时 16.634 秒：测试驱动把 update 不支持的 --json 参数传给了安装版
CLI。另在静态复核时修正候选夹具所属对象。两处修正都限于新测试，运行时未改动。
[首试记录](evidence/system-meta-reflection/development-journey.attempt-1.json)保留原失败范围。

修正后一个完整测试通过，耗时 47.748 秒；
[实际阶段记录](evidence/system-meta-reflection/development-journey.attempt-2.json)含两个完成轮次、
两条保留的后写 Memory、九个阶段及临时根清理。时间为验证成本，不是产品性能指标。

[收尾源码审计](evidence/system-meta-reflection/development-journey-source-audit.json)逐项核对：
[R4 回归](evidence/system-meta-reflection/regression-r4-readiness.json)的全部 342 个文件未变；
仅新增这一个集成测试，当前清单为 343 文件，摘要为
25661923b1f3fcfb73944d36f266ffd443176ff1d3ce2ea14f14e19ed1b5fd47。
该清单在运行后观察，不冒称本轮另有全量开始/结束回归快照，也没有重跑全部历史模块。

当前 Runtime Python 摘要仍为
8e4ecc08b536df6773a2c860eeb3948e0ff5fd555357b6cc0fa00d740e7a0f3f；
实际安装的 Runtime/Skill bundle 摘要为
a392047dd8e0bf322572fccd4af05ec9888a5363c504fc6a53bde728d4d50962。
旧 R3 模型验收仍保留原源码范围，本演练没有运行另一个宿主模型。

## 复跑开发场景

在仓库根目录执行。以下过程只选择这一个开发用例，不写入历史证据文件：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import os, sys, tempfile, unittest

with tempfile.TemporaryDirectory(prefix="memory-development-check-") as root:
    os.environ["TMPDIR"] = root
    os.environ["AGENT_MEMORY_HOME"] = root + "/fallback-memory"
    os.environ.pop("AGENT_MEMORY_REAL_HOST_VERIFY", None)
    os.environ.pop("AGENT_MEMORY_DEVELOPMENT_JOURNEY_EVIDENCE", None)
    tempfile.tempdir = root
    suite = unittest.defaultTestLoader.loadTestsFromNames([
        "tests.test_system_evolution_development_journey"
    ])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
PY
```

所有项目/Memory/备份/候选/恢复目录均在临时根内，使用安装版单一 Runtime 入口。
现有业务 Memory、已消费密封资产和原有未跟踪 memory.md 未读取或改动。
本记录形成于演练收尾时，当时测试、说明和证据尚未提交；后续主分支交付见 Git 历史。
真实项目未部署。

收尾检查：31 份专用文档的 194 个本地链接有效；51 个相关 Python 文件指纹齐备，均不超过
500 行（最多 480 行）；六份既有规范的 draft/proposed 声明及空批准字段保持，解析边界通过。
git diff --check 通过。
