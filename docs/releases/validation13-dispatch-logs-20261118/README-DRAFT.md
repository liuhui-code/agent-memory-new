# 可移植聚焦回归包草案（尚未执行）

仅复制独立冻结控制及其小型合成输入。没有私有 trace、DB、实际项目源字节或历史运行输出。未复制生产代码；生产发布 allowlist 在包根单列。

## 审查入口

`run_portable.py`、`MANIFEST-DRAFT.json`、包根 `PRODUCTION-ALLOWLIST-DRAFT.json`。
安装目标为已审批候选仓库的 `docs/releases/validation13-dispatch-logs-20261118/`，保持此层级。现外部目录没有 tools，故不能用于执行；禁止将生产代码复制进本草案后擅自运行。

runner 默认 DRAFT 门阻止执行。须独立审核、最终发布树 runtime 全 432 文件哈希固定，并由负责人明确冻结后才可改状态为 `FROZEN_FOR_PORTABLE_COMPONENT_EXECUTION`。冻结输入 SHA 保留原值；源文件内历史 DRAFT 注释、原冻结清单引用不等同本包已获新执行授权。原清单是沿革记录，不承担新路径依赖校验，当前 manifest 才列包内所有实际执行输入。

固定组：private 14、integrated 10、latefallback 3、primitive 42、resource 1 个 unittest 方法内 51 个 subcontrols、budget V2 1。因此 121 项断言义务不应宣称为 121 个 unittest 测试或独立机制。每项新进程、新目录、隔离不存在 cache、dontwrite、前后完整 runtime 集合校验，失败保存原异常及输出，停止且不重试。组件自身生成的 DB/WAL/sidecars 完整保留于所选新输出目录，不成为发布包文件。

## 已知失败与边界

原 integrated `over-output-budget` 在绑定前因 raw 缺 output_budget 而 KeyError。其原脚本文字和原 11 项清单原样保留，仅本次明确选 10 项。不能将排除说成已修生产 bug。budget_v2.py 原件逐字节保留，只由 wrapper 设置该测试模块 REPO/EVID 为安装位置；不修改生产 global，不改输入、receipt 或断言。V2 仅验证已有 terminal transaction 的预算回退，不代表外层端到端预算配置。

这不是全量验收，也不证明原 13 已闭环。最终 AFTER 结论及发布摘要待负责人确认，不由草案推断。
