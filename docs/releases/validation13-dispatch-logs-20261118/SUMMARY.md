# 完整 dispatch 日志视图：有限发布摘要

新日志分支认证完整 collector direct/effects 来源、源码与 DB 身份，在原 scope 和预算内恢复验证方法源码。仅 direct 与 depth-1 static wrapped；不扩大 scope、不提高 1500 token 上限。旧 NoLog、touch、compact/accounting 主流程保持。

## 已保存候选证据

- 私有身份与防篡改 14 项通过。
- 集成组 10 项通过；原第 11 项预算 harness 在绑定前因 raw 无 output_budget 触发 KeyError，保留失败，未修改旧 oracle。独立 budget V2 验证 shared terminal transaction 的预算回退，不代表外层端到端预算配置。
- 3 个真实晚失效时点通过，验证实际 DB effects、一次 writer 与最终 sidecars；另有 42 primitive 控制、51 resource 子控制。
- 旧路由 64 + 82 个组件通过，不是全量验收。
- 固定独立开发输入的 AFTER 共 4 个 context：首个已执行结果按事后审查边界记录，其余 3 个在独立协议冻结后前瞻执行并接受；不能把四项都说成同一前瞻冻结验收。raw、control compact、非代码保留和源码/DB/sidecar 门均按各自协议记录。

上述历史证据与 clean 发布源码提交 d505eb1 的回归分开记录：该提交上 71 个固定控制 worker 全部通过并经独立复核，详见 PORTABLE-RESULT.md。432 个 tools 文件和所有执行输入前后不变；后续仅文档与结果记录提交不被说成另一次已执行验收。原 13 仍未闭环，40-path scope 与复杂源码语法问题未由本补丁解决。历史失败与完整私有证据另存，不打包 trace/DB/实际项目源码。

## English scope

This limited release adds complete dispatch-log provenance to the validation source view without increasing scope or budget. Candidate evidence includes 14 private controls, 10 integrated controls (one original budget harness failure retained), three late-fallback controls, a separate shared-transaction budget control, and 64 + 82 prior-route component regressions. AFTER evidence distinguishes one retrospectively reviewed result from three prospectively frozen executions. The fixed portable run on source/test commit d505eb1 passed all 71 workers and independent review; subsequent documentation-only commits are not represented as a rerun. Original case 13 remains open; this is neither a full-suite result nor an aggregate improvement claim.
