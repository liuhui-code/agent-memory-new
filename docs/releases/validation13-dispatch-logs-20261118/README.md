# 可移植聚焦组件回归

从本仓库根目录运行，输出必须使用不存在的全新绝对目录：

```sh
python3 -B docs/releases/validation13-dispatch-logs-20261118/run_portable.py --output /absolute/path/to/new-results
```

不要使用 `-O`、`-OO` 或启用 `PYTHONOPTIMIZE`。runner 显式拒绝优化解释器，以免测试断言被跳过。默认依固定顺序执行全部分组，每项独立子进程和新目录；遇失败保存结果并停止，不自动重试。完整完成时为 71 个控制子进程（另有一个协调进程）：14 private、10 integrated、3 latefallback、42 primitive、1 resource、1 budget。resource 的 1 个 unittest 方法包含 51 项子控制，因此合计 121 项断言义务，不能称为 121 个 unittest 测试或独立缺陷。

`MANIFEST-DRAFT.json` 保留历史文件名，但其 status 已机械更新为 `FROZEN_FOR_PORTABLE_COMPONENT_EXECUTION`；实际输入和完整 runtime 集合须与 manifest 哈希一致。`README-DRAFT.md` 是保留的准备阶段原件，其中外部目录和包根说明不适用于安装后的仓库，请以本 README 为运行说明。冻结依据见 `FREEZE-NOTE.md`。

源码与测试提交 d505eb1 的上述固定回归已全部通过并经独立复核，见 PORTABLE-RESULT.md。后续提交仅增补文档与结果记录，不能称为重新执行过测试。已保存的候选证据与明确限制见 `SUMMARY.md`。原 integrated 预算项的 harness 失败保留且不纳入本次 10 项；独立 budget V2 仅测试 shared terminal transaction。所有被复制的控制和 oracle 原字节保留，只有预算测试模块的文件路径通过 wrapper 重定位，可移植 wrapper 不新增生产函数替换；原冻结控制中的观察与失效注入保持不变。

历史 BEFORE/AFTER 不由此脚本重新执行。AFTER 证据明确区分 1 项事后审查与 3 项前瞻冻结执行；这是独立开发输入的结果，不是原 13 闭环或全量验收。私有 trace、DB 和实际项目源码不包含在包中。生成的测试 DB、副文件和输出留在指定的新结果目录。
