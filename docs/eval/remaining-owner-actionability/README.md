# 剩余 owner 类别可执行性复核（15 类，只读）

审计基线 `e868649`。输入为工作区 `remaining-category-ledger.md`，并逐项阅读下列实际报告、结果及本轮消费诊断；没有运行任何 query、单组或全量测试，没有修改生产。

**时间解释：** 下表基线是实际报告所写的验证基线，不是本次审计基线。报告未可靠记录测试执行时间的，标“执行日未记”，不从目录名或文件 mtime 推断。`record-provenance.json` 单独提供可核查的报告入库提交和作者时间，它们不是测试时间。目录含 `20261114` 也只作为证据名称。除明确写出的单变体新快照，其余均为历史结果，不代表 e868649 全量当前结果。

类型：**缺证**＝需先补同层独立公共复现；**新合同**＝现证据足以定位政策/权限边界，但不能直接变成排他证明；**停止**＝已冻结实验不满足门槛，禁止调样例继续；**已修旁项**＝相关窄实现问题已发布但不等于原组通过。这些类型不是永久不可修。

| 编号 / 类别 | 最后实际验证与时效 | 首失效层 / 具体字段证据 | 现合同能否安全直接修；未解条件 | 最低下一步（不自动执行） |
|---|---|---|---|---|
| 25 archive IO | 执行日未记；发布运行时 4005b65 复查 1/3；隔离 v3 基 27d6afd 后仍 1/3，不能计为当前生产验证 [A] | marker 候选真实 unpack 已召回 coverage=1、score14.5，strong_identity focus 留 ArchiveBadge/AssetCatalog、丢 unpack。v3 单机制 archive 可对，但原合取与其他控制未闭环 | **新合同/停止**。不等于漏召回；>=2、多目标、unknown 保护不能直接解除。v3 未接纳；投影 label/body 身份错配已另修 | 先审核已冻结 generic 的请求机制组合与实际 receiver/path/handle 证明；使用旧正反控制，不能拿 v3 单绿代替原/合取公共闭环 |
| 26 shared record aggregation | 执行日未记；e760097 独立单组 1/3 [B] | 正确文件先 focus；salient 为原文加 FolderCollectionLoader/CollectionPage，为英文加 RecordPreview/SessionUsageCoordinator。collect 范围2–12真实；英文 localizer 先选 recordSuccessfulUse，正文只2–10且truncated | **新合同**。collectionfold 是文件检索 hint；direct/after-loop/deferred 三种都能命中，未承诺循环内同 accumulator 值流。非 typed ID 丢失 | 从已有三种 frozen loop 控制定义直接累积/使用的 scope 合同与真正多 owner 需求；不能简单复制 file marker 或全删补充 |
| 27 keyboard focus | 执行日未记；134cfcb 单组2/3，历史 [C] | 正确 attach 完整正文在；Hint/Page 由 salient 加入。真实 Page 注册 keyboard 事件，Hint 写 state；主要文件仅 structural_behavior，非同 callback 完整语义 witness | **新合同**。现有 state_write 不证明事件参数被该回调消费并写目标 focus；未知竞争者非无操作 | 预注册事件参数→同 callback→目标状态绑定，含 alias/nested/只注册/只写/混合 owner；不复测现已明确范围完整的旧例 |
| 28 native color | 执行日未记；a6c1d93 单组2/3，历史 [D] | focus 只 parseNativeColor；native structural 增 FacetRecord imports；salient 增无 method provenance 的 MessageActionBar 与 system-bar/system 前缀匹配 Clipboard。实际正文2–5，不是宣称完整2–12 | **新合同/已修旁项**。native 正向结构合同仍有效；file 投影无方法证明是设计边界。显名双声明丢 interface 的白名单漏接已修 [E]，不再列待修 | 若选择此类，独立验证 compound-prefix 语义或操作形容词/请求结构角色合同；不能全局拆 native。正文另按已验证身份与预算合同检查，不提高上限 |
| 30 output read loop | 执行日未记；去重阶段基27d6afd附近仍1/3；隔离 v3仍1/3 [F] | 原独立 collect18.5 被 description55.5及重复 file/class 挤出 raw；投影预算去重已修，collect 可进入第五位，但 compact仍选 description。v3单机制受 SingleRead.read exact-symbol veto | **新合同/停止**。预算窄缺陷已经处理；loop方法 witness 不能绕过确切目标/unknown/multiple权限 | 旧冻结操作与真实 literal/read 方法控制用于审核目标归属；不复活 marker-only 或给 read 特判，不声称 raw改善等于任务修复 |
| 32 WebView policy | 执行日未记；a6c1d93 单组2/3，历史，旧1/3过时 [D] | structural=false；access AND navigation→multiple。salient Toolbar，加实际日志来源 DispatchProfile；正确 build range在，正文9–13而要求10–16。独立 generic 被 AccessTelemetry 日志选中 | **新合同**。不是 schema/policy 结构触发 bug；明确日志、双owner、显名 GateRules 控制通过。身份/正文预算与竞争两层要分开 | 对固定 generic 的执行 scheme policy 与描述/日志需求建立受限证据合同；先说明请求绑定，不清空日志或增加排除词 |
| 33 cache eviction | 执行日未记；a6c1d93 实验原组2/3，历史 [G] | timestamp ExpiryStore 有真实范围/候选；局部hint候选后17.29仍低于文本monitor34。ArrivalPool真实FIFO，不是无操作噪声 | **新合同/停止**。method hint 候选公共两红仍失败，已回退；不能把timestamp-only当唯一淘汰证明 | 已冻结两公共红+FIFO/literal正控足以做设计审查，但需先定义算法需求与source-description权限，不继续调marker/权重 |
| 34 source replacement | ed3fd70 本轮仅 original 新raw/compact及clean复验；执行日未记。历史组2/3，本轮不推组分 [H] | focus 正确replaceSource；salient增Deadline/Wrapper。所有event priority0、path未激活；localizer把过去“load failed”的load当exact_symbol：Wrapper38.88 > correct32.5；bounded后compact丢正确源 | **缺证/新合同**。exact_symbol现合同是边界词面，不是用户当前目标指称；未丢事件/typed证书。独立同层当前目标 vs 历史动作红尚无 | 一次冻结当前目标/过去动作归属控制，同时保真正请求load、literal日志、多目标。先明确语义合同，再验证；不得改failure/log权重 |
| 37 command binding | 执行日未记；initializer certainty阶段基2f04b6d对照仍1/3，较property阶段更晚 [I] | 两真execute可已索引；嵌套object owner扁平。display去重曾隐藏同file竞争而certainty误bounded，已修为看完整prepared；不保证nested discard准确。字段数组尚无initializer实体 | **新合同/已修旁项**。FIELD_RE只是类型map，不承诺field范围；伪callback词法及certainty漏接都已修，不可重复计功 | 仅在明确两独立类需求后设计initializer范围/嵌套成员身份；保当前qualified declared owner与unknown控制，不恢复撤回parser |
| 38 comparison visual state | 执行日未记；较新的state-declaration阶段基66050ad候选 comparison-after仍2/3；原首层诊断134cfcb [C,J] | 原中文正确RuleEditor+键盘补充；Rotate读取detailsExpanded，onClick写同state，但跨UI参数/回调的绑定尚无。修private名称/ghost声明/假读写边未令本组通过 | **新合同/已修旁项**。producer真实身份窄bug已处理，不能据旧日志再称缺State名字。disclosure单marker不授权排他 | 使用已校正state身份设计同owner UI属性读/回调写绑定和真实编辑器/创建器比较；先定义范围，不降低>=2 |
| 39 cross-layer error | 执行日未记；typed引用修复阶段23e00f1附近仍1/3，历史 [K] | 两英文raw两必要owner均在；localizer却选retryFailedParcel或NotificationDetails.build，compact跟随丢正确来源。不是range去重或typed namespace首失效 | **缺证/新合同**。typed引用丢真实import已修但该组未变；未有证明跨层错误传播/映射请求的已授排他证书 | 先固定跨层传播/转换与真实retry/literal竞争的同层公共red；不以另一typed namespace红替代，不直接增error词权重 |
| 40 canonical preview | 3a7aea5 本轮仅剩英文一次public；执行日未记。历史组2/3，不推新组分 [L] | preview已排除；focus三正确方法，salient后加ParcelRetry直接候选、AccountSettings真实imports。正确8–9写入在正文；不是artifact误分类或typed-ID损坏 | **新合同/停止旧探针**。canonical不等于排他；multiple/graph守卫按现合同工作；旧独立泛query exact字段初focus不同 | 不再改原query。先建立任务角色与具体关系的保留/排除权限；直接salient冗余与graph资格分开证明，不能全免图或全删邻项 |
| 42 indirect dialog caller | 执行日未记；a6c1d93显式callee身份阶段原组仍1/3，历史 [M] | 原正确caller后salient/weaklog加来源，graph保宽；改写uncertain。曾对明确A.finish误采同file A.reset入边，项目全域ID消歧修复已发布；原query不含该qualified目标 | **新合同/已修旁项**。4seed/2caller是有界集合，非全局唯一；完整方法目标ID合同已补，不覆盖泛caller请求 | 既有独立strict caller-only仍保callee上下文而红；先规定任务是否需要callee/其他source，再建立多caller/真实log正控，不删所有非caller |
| 43 preference restore | 历史0dc58f2及23e00f1对照同2/3；ed3fd70只读消费审计，未新跑原query。独立before基ed3fd70已执行 [N] | 原Session是graph/imports，ProfilePage是wrapped-log；正确onCreate bounded，graph guard全保。独立before却选Repository.load且无graph flags，未覆盖原分支；双目标另为1491预算正文截断 | **缺证/停止**。箭头read unresolved是静态限制；不能升证。恢复只处理精确single-range callable primary，双range/alternative不适用；copy追加到10为1522>1500 | 保留原两个通道，需真实独立同层“正确primary+graph+wrapper”证据；既有实验stop，不调它造红。预算问题非可直接扩大恢复权限 |
| 44 native result listener | 执行日未记；e760097单组2/3，initializer certainty阶段再次2/3 [O,I] | attach7–16、ResultListener参数及callback_binding机制均入pool；retry38>onFailure36>attach34.5，compact照排位。不是丢范围；公开Relay泛bind红、四显名/literal正控绿 | **新合同**。typed_contract_match=false；注册→回调→同receiver转发尚无认证，描述文本不能自动判噪声 | 现有独立红可用于新合同设计审查，先定义receiver/registration边界与unknown，再必要正反；不把signature匹配直接升级唯一owner |

## 本轮选择结论

这15类中没有找到**尚未处理、且现有同层独立红和保护控已足以直接实施**的既有契约漏接。曾明确可修的 interface 类型漏项、typed reference、显式callee ID、同file certainty、投影预算重复项已完成，不能当下一项未处理任务。

这不是 all-blocked：
- **最短设计审查材料已齐但缺权限合同**：33 cache、44 listener；已有真实公共竞争红及相应literal/真实操作正控，可以先审核具体证据权限，而不是再采样。
- **需补匹配首层证据**：34过去动作/当前目标，39跨层传播；原层已知但独立红未覆盖。43现一次实验已明确stop，不无限找样例。
- **真实关系/值流设计工作**：26、27、38；已有字段/范围不等于请求所需完整同scope关系。
- **策略和预算边界而非漏接**：28、32、40、42、43；先确认要牺牲何种证据以及什么资格，不能默认“少owner”优于来源完整。
- **已拒实验保持隔离**：25/30 v3、33 marker-only；生产未闭环不能以unit绿或原个别变体改善发布。

建议下一步由协调者从33或44选一个**合同审查**，先给出可证伪的窄权限定义与unknown拒绝条件，复用已经冻结的正反材料；未批准前不新增producer或改ranking。若目标是只做已有实现合同修复，目前这15项没有立即可接纳候选，应转其余编号的证据审计，而非把旧同层红反复运行。

## Sources（仓库相对路径；外部历史材料显式标注）

- [A] 外部隔离记录 `archive-v2-check-work/docs/evidence/archive-v2-check/result.md`；`archive-owner-followup-work/docs/evidence/archive-owner-followup/result.md`；`output-loop-proof-work/docs/evidence/source-operation-v3/result.md`。ledger 的 `recovery-current/archive-contract-evidence/latest-verified-target.json`仍为1/3。隔离候选不在本基线生产。
- [B] `docs/evidence/shared-record-current/README.md`、`public.json`、`original-intent.json`、`independent-protocol.json`。
- [C] `docs/eval/owner-audit-current/README.md`、`keyboard-focus-state-owner.json`、`comparison-target-visual-state-owner.json`。
- [D] `docs/eval/structural-role-current/README.md`、`color.json`/`webview.json`、clean/traced public 与 `independent.json`。
- [E] `docs/eval/named-interface-retention/README.md`：单行interface guard修复已接纳。
- [F] `docs/evidence/output-loop-followup/result.md`、`dedupe-result.md`；另见[A]隔离v3，严格loop red没有变绿。
- [G] `docs/evidence/cache-eviction-current/README.md`、`candidate.txt`、`rejected-hint.patch`。
- [H] `docs/evidence/source-replacement-first-loss/README.md`、`public.json`、`clean-public.json`。
- [I] `docs/evidence/initializer-scope-current/README.md`；`docs/evidence/property-callback-lexical/README.md`与`command-after.json`。
- [J] `docs/eval/state-declaration-lexical/README.md`、`comparison-after.json`；`docs/eval/comparison-state-audit/README.md`。
- [K] `docs/evidence/contract-path-followup/result.md`、`typed-reference-result.md`、`typed-original.json`。
- [L] `docs/eval/canonical-retention-latest/{protocol,public}.json`、`README.md`、`trace-2.json`；旧`docs/eval/canonical-current/README.md`。
- [M] `docs/eval/indirect-caller-current/README.md`及冻结前后公共输出；原泛query未改写为qualified形式。
- [N] `docs/eval/restore-current-20261114/README.md`、`context-persistence-key-restore-owner-clean.json`；`docs/eval/restore-owner-retention-current/README.md`；`docs/eval/restore-owner-retention-before/{README,SOURCE-BUDGET-AUDIT}.md`。
- [O] `docs/eval/native-listener-current-20261114/README.md`与协议、raw rank trace；后续[I]再次原组不变。
