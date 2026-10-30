# 元反思生命周期完成证据与交付边界

日期：2026-10-30。当前状态：本轮当前仓库实现及隔离安装/真实宿主验收完成。
本文件不把隔离安装副本冒充为已升级的用户业务项目，也不作为外部发布或效能门禁。

## 要求与证据

| 要求 | 权威证据 | 结果与范围 |
|---|---|---|
| 四个 Skill、单一 Runtime、SQLite 真源、查询隔离 | 安装器用例、治理/查询用例及当前源码 | 通过；未引入模型服务、后台守护进程或平行数据库 |
| 用户当前模型执行收尾评审 | [最终真实宿主记录](evidence/system-meta-reflection/real-host-smoke.final.json) | Codex CLI 0.165.0 实际读取项目本地 Query/Reflect；context 真实退出 1，随后名额和保存命令退出 0；一个名额、一个建议性评审 |
| 结构、报告和提案约束 | test_system_evolution / triggers 用例 | 通过；有界输入、修订、幂等、任务关联和普通记录隔离 |
| 候选与检查主体 | candidates / checks / lifecycle 用例 | 通过；实际独立 Git 候选、v1/v2 兼容和 v3 新产物摘要观察 |
| 完整声明晋级 | acceptance 实现与 lifecycle 用例 | 通过；预先绑定计划、全部断言和政策项、当前 Agent 审查及实际未变产物，不能只提交状态或零退出码 |
| 实际应用与安装布局 | lifecycle / delivery 用例 | 通过；物理新增/修改/删除，更新安装副本 Runtime/Skill 字节；记录跳过项，保留无关业务文件 |
| 代码回退及后续数据保留 | 完整生命周期、安装布局回退用例 | 通过；代码前像恢复、Git index 不变，应用后新增 Memory 事实仍存在 |
| 数据迁移、失败恢复及降级边界 | migrations 用例 | 通过；备份有效，实际重建后抛错回滚，外键/ID 保留，降级保留升级后写入，高级状态阻止不兼容降级 |
| 旧普通读写兼容 | 固定 Git 基线 compatibility 用例 | 实际执行 2ade686f… 的 Runtime，对治理 v2 归档普通读写成功，公共 query_handoff 与新版一致；基线固定为完整提交 ID，不随交付后的 HEAD 变化 |
| 活跃锁和硬退出恢复 | live_writer_lock_and_hard_process_exit 用例 | 活进程持锁时拒绝恢复；已知进程实际退出 77 后恢复 running 记录，跳过已写文件，mtime 不变 |
| 恢复预览、中止与失效 | resolution_preview_abort / hard_process_exit 用例 | 有效预览退出 0；显式中止和重试保留原操作 failed；checked 可退回补证，未知子进程拒绝清除 |
| 后续观察与关闭 | 完整生命周期及失败监测用例 | 通过；实际应用目录检查后进入 monitoring/closed，失败退出 7 与缺产物同时保留，未伪称成功 |
| 文件模式位保留 | existing_executable_mode_bits 用例 | 复现 0744 被扩为 0755，修复后保留 0744；0600 场景及安装回退同时回归 |
| compact/full 查询协议 | 非空查询用例与兼容用例 | 两种视图前后字段集合及 query_handoff 一致；未声称覆盖所有未来数据/环境组合 |
| 规范、上下文和 ADR | [生命周期规格](system-meta-reflection-lifecycle.zh-CN.md)、[CONTEXT](../CONTEXT.md)、[ADR](adr/0001-system-meta-reflection-lifecycle.zh-CN.md) | 已同步；规范批准字段留空，不补造维护者批准 |
| 额外业务项目部署（非本轮必需项） | 如用户指定实际项目与 Memory Home 后执行 | 未请求具体目标，不推测其他项目；不作为已完成安装副本验收的新增前置 |

## 最终测试记录

[机器回归记录](evidence/system-meta-reflection/regression-final.json)由实际测试进程生成：

- 56 项被发现，55 项普通隔离回归通过，0 失败、0 错误；1 项真实宿主用例在此普通批次按设计跳过。
- 交付前固定旧兼容基线后的测试执行 251.775 秒；记录器连同临时根清理计时 252.070 秒。不是产品性能或模型效能指标。
- Runtime、Skill 和相关测试文件的开始/结束摘要相同，清单和摘要写入该 JSON。
  source_unchanged_during_run 表示这两次观察相等，不是文件系统冻结、真实性认证或外部 seal。
- 真实宿主另行显式运行并通过，最终一次用例耗时 96.919 秒；没有把普通批次的 skip 当作宿主通过。
- 该宿主记录绑定当时的源/安装副本相同摘要及项目本地 Skill 读取路径。后续文件模式位和
  恢复命令返回码修复改动生命周期模块，未改宿主触发协议；当前代码及补充用例已包含在最后 55 项普通回归快照中。
- 更早的 53、54 项普通回归批次、退出码采集、权限和恢复预览缺陷的定向运行均保留在 gitlog。
- 收尾审计核对 320 个 Runtime/Skill/测试文件，与最终回归清单逐项相同；16 份专用文档
  的 89 个本地链接均有效，31 个新增/修改 Python 文件的指纹与 500 行门禁通过，最大 480 行。
  git diff --check 通过。ADR/规格批准字段继续留空。

宿主成本字段来自 CLI 的实际 usage；scope 是整个宿主示例回合，含查询与复核，不能
拿它冒充单独元反思增量 Token 成本。无 API 金额或效能收益推算。

普通隔离回归可在仓库根目录按机器记录的模块集合复验；默认不启动真实宿主或模型：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

record = json.loads(Path('docs/evidence/system-meta-reflection/regression-final.json').read_text())
with tempfile.TemporaryDirectory(prefix='agent-memory-meta-verify-', dir='/private/tmp') as isolated_root:
    os.environ['TMPDIR'] = isolated_root
    os.environ['AGENT_MEMORY_HOME'] = isolated_root + '/unused-default-memory-home'
    os.environ.pop('AGENT_MEMORY_REAL_HOST_VERIFY', None)
    tempfile.tempdir = isolated_root
    suite = unittest.defaultTestLoader.loadTestsFromNames(record['modules'])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    succeeded = result.wasSuccessful()
sys.exit(0 if succeeded else 1)
PY
```

真实宿主用例在 tests/test_system_evolution_host.py，必须显式启用其运行环境变量，
且需现有可用 CLI/模型及相应执行权限；普通回归的 skip 不代替该项验收。

## 保留的失败与未知

- [初始沙箱权限拒绝](evidence/system-meta-reflection/real-host-smoke.json)：未产生模型/工具事件，不记宿主功能通过。
- [首个带验收语境的宿主运行](evidence/system-meta-reflection/real-host-smoke.normal-host.json)：进程完成但无评审记录，原因未建立；未通过改写 Runtime 来凑结果。
- [普通示例任务运行](evidence/system-meta-reflection/real-host-smoke.ordinary-task.json)：实际完成错误观察、一次名额与建议性评审；最终记录进一步核对了项目本地读取和成功命令。
- 当前 Agent 的审查不是审查者身份认证，检查产物摘要不是 Oracle 认证，checked 不授予外部发布资格。
- 其他宿主、任意新数据模型、长期使用效果和脱离受控进程组的工作不由本轮自动认证。

## 可选的真实项目部署

用户本轮要求的实现、实际文件应用、迁移/回退、安装副本和真实宿主验证均已完成。
此前询问额外安装落点仅作为后续部署偏好，不作为本轮完成的审批门槛。
若需要部署到当前仓库本地或其他真实项目，将先绑定该目标及 Memory Home，保存必要备份，再用相同版本复制、
运行已授权的安装/检查和必要治理迁移，保留实际安装证据；不覆盖升级后写入或自动发布。
当前没有读取或改动未指定项目的 Memory 数据，原有未跟踪的 memory.md 未被纳入本任务。
