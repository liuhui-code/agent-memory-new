# 本地 Agent 故障定位流程

## 目标

本流程让 Agent Memory 负责上下文召回，让本地 Agent CLI 负责日志分析、假设、
调用链与因果链推理。临时流水日志不进入 Runtime，也不写入 SQLite。

## 阶段一：问题查询

先把用户现象、触发条件和稳定错误文本作为一个自然语言问题查询：

```bash
python tools/agent_memory.py context \
  --project . \
  --query "个人资料页首次进入白屏，日志出现 profile load failed" \
  --compact \
  --json
```

Agent 重点读取：

- `query_handoff.log_keywords`：搜索流水日志的关键词。
- `query_handoff.log_anchors`：代码日志模板、logger、事件、阶段和源码位置。
- `query_handoff.code_anchors`：首批源码入口。
- `correction_guards`、`semantic_patch_notes`：业务语义与纠正。
- `experience_refs`：历史经验，仅作提示。
- `relation_hints`：紧凑一跳关系，仅作源码导航。

不要从结果排序推断根因，也不要把历史 `likely_causes` 当成当前事实；公开查询
不会返回该字段。

## 阶段二：Agent 直接分析临时日志

Agent 使用 `rg`、`sed` 或其他本地工具直接读取用户日志。先用
`log_keywords` 缩小范围，再围绕关键行查看前后时间窗口。汇总观察时保留：

- 时间、进程、线程、logger 和级别。
- 稳定事件名、错误码、路由、资源或请求标识。
- 同一 request/session/trace 的相邻阶段。
- 失败之前最后一个成功事件和失败之后的恢复行为。
- 缺失的关键阶段或预期日志。

日志原文只用于本次任务。除非用户明确要求，不能复制进记忆数据库。

## 阶段三：建立多个候选原因

Agent 至少列出两个可证伪候选，每个候选包含：

```text
候选原因：具体机制，不是宽泛模块名
支持观察：哪些日志或源码事实支持它
反证：哪些现象与它冲突
区分性检查：什么最小检查可以确认或否定它
```

候选之间应覆盖不同机制，例如“请求未发起”“响应解析失败”“状态更新未触发
渲染”，而不是同一猜测的同义改写。

## 阶段四：逐个候选查询

一次查询只描述一个候选原因：

```bash
python tools/agent_memory.py context \
  --project . \
  --query "ProfileService 请求成功但响应解析失败，定位解析函数和失败日志" \
  --compact \
  --json
```

对每个候选分别记录新增日志关键词、源码锚点、业务语义纠正、历史失败模式和
原始关系边。若查询没有新增事实，应停止重复召回，转向源码、配置、Git 历史、
复现命令或用户补充信息。

## 阶段五：推测代码调用链和因果链

Agent 打开 `code_anchors` 指向的当前源码，并使用符号、导入、调用、回调、状态
流和配置关系扩展阅读范围。调用链应由当前源码确认，图边只能加速导航。

因果链由 Agent 综合以下信息构建：

1. 日志中可验证的时间与关联顺序。
2. 当前源码中的调用、分支、异常和状态传播机制。
3. 业务语义纠正与接口约束。
4. 能排除其他候选的反证或实验结果。

输出中区分：

- `observed`：日志或运行结果直接观察到。
- `source-confirmed`：当前源码明确支持。
- `inferred`：由前两者推测，仍需验证。
- `rejected`：已有反证。

## 阶段六：修改前影响分析

确认候选修改文件后运行：

```bash
python tools/agent_memory.py impact-scope \
  --project . \
  --files src/a.ets \
  --query "修复 Profile 响应解析失败" \
  --json
```

检查反向依赖、下游依赖、测试建议和覆盖缺口。图遍历不能替代编译和测试。

## 阶段七：验证与经验沉淀

修改后执行复现、构建和测试，并记录紧凑影响反馈。只有根因和修复经过验证后，
才把可复用信息写入反思：

```bash
python tools/agent_memory.py reflect \
  --project . \
  --from-last-task \
  --task "个人资料页白屏" \
  --lesson "<已验证根因、修复、适用边界和验证方法>" \
  --json
```

业务语义补充或纠正写为 `correction_experience`；可复用调查步骤写为
`procedure_experience`。不要保存未验证候选原因、完整日志或私有思维过程。

## Agent 自动协议

```text
1. 用用户问题调用 context。
2. Agent 直接读取临时流水日志，使用 query_handoff.log_keywords 缩小范围。
3. 形成多个可证伪候选原因。
4. 每个候选原因单独调用 context。
5. 阅读当前源码，结合原始边推测调用链；结合日志和反证推测因果链。
6. 当前源码、运行结果和测试优先于历史经验。
7. 修改前运行 impact-scope，修改后执行验证。
8. 只沉淀已验证结论和有明确适用边界的经验。
```
