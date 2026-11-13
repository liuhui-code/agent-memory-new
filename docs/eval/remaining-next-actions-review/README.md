# 30 类剩余问题：下一步与证据边界

只读汇总基线 `f8191a5`。读取两份 15 类账本及本轮 fallback、cache/output、WebView 报告，未执行新 query、测试或修改运行时。**累计已验证原失败修复仍为 20；未跑全量，不计算当前总通过率。** 以下历史定点不等于当前版本重验，原记录的基线/时间见链接账本。

基础来源：[消费侧15类](../../evidence/remaining-consumer-feasibility/README.md)、[owner侧15类](../remaining-owner-actionability/README.md)。下表编号沿用工作账本，跳号不是遗漏。类型可重叠：**缺证**＝缺匹配首失层的独立公共红；**合同**＝需更明确源/请求权限；**否证**＝特定候选失败应停止；**旁修**＝实现问题已修但原组未闭环。均不等于永久 blocked。

## 逐类最小行动

|编号 / 类别|首失层与已有证据|为何暂无安全小修；最小下一步|
|---|---|---|
|02 跨组件 preview|raw 两端及真实 imports/renders/passes_property 边齐；高分 endpoint 不晋升便不带 graph 来源，bounded 后裁 child。[证据](../cross-preview-current/README.md)|**缺证/合同**。两组独立控未覆盖双端同时高分。优先只读确认 provenance 是否本就仅指晋升；若不是，可冻结内部真实边/ID的分数边界检查。内部红不能冒充公共红，也不自动授权双端保留。|
|04 ArkTS UI operation|语言词把独立 UI 引到 Ability；全局语言-only 拆分破坏真实隐式 startup 控。[账本](../../evidence/remaining-consumer-feasibility/README.md)|**否证/合同**。停止旧 alias 拆分。先定义语言限制与平台目标的请求角色，保留 startup/lifecycle，不做启动特例补丁。|
|05 model versus render|正确渲染正文完整，真实 trim/replace 与模型候选共存；独立竞争红存在。[账本](../../evidence/remaining-consumer-feasibility/README.md)|**合同**。方法操作真实但无 transform 返回值被 render 消费的绑定。若做设计，先逐个绑定返回值与 render 输入；不能删除名称像 Record 的真实类。|
|06 query owner + consuming page|固定独立 SQL owner/page query raw 两端在，bounded 后只留 service；一般双角色措辞却保两端。[账本](../../evidence/remaining-consumer-feasibility/README.md)|**合同**。需要角色短语到已索引实体的绑定，不是 named pair 漏消费。与10可作设计对照，但须核角色语义，不能仅凭都双端拼架构。|
|07 scroll structure|独立 generator 主选压 layout，但 uncertain、两源仍保留；红是 primary 身份。[证据](../../evidence/scroll-structure-current/README.md)|**合同/否证**。任务元语言 code 与领域 code 未区分；旧 source-code-for/of 实验未满足门槛已停止。不能当34排他丢源第二类。|
|08 numeric aggregate|正确方法及 writes_state 已召回，semantic coverage 并列时前两文件删除它；独立5控全绿。[账本](../../evidence/remaining-consumer-feasibility/README.md)|**缺证/合同**。状态写不等于数值累积。若推进，先定义同方法算术作用与请求绑定；不改 top2、排除 UI ForEach 或再添同义词。|
|09 visual overlap|真 Stack/overlay 两 marker 胜 backgroundColor 单 marker；独立同层红。[账本](../../evidence/remaining-consumer-feasibility/README.md)|**合同/否证**。替代机制和合取需求未区分；non-erasure 候选仍红已拒。需要目标/替代机制语义，不是一行覆盖阈值。|
|10 fallback recovery|本轮确证 raw 两 owner 完整、scope=multiple，但普通跨文件 portfolio 装入词面 store 竞争者而漏 registry；focus 后首次删 registry。[更新](../../evidence/fallback-consumer-current/README.md)|**合同/缺独立验收**。不是 single 误判，也无 registry→store 注入/调用边。下一步只设计两角色到真实身份的绑定及一owner两动作负控；不放开 multiple 或投影错误 portfolio。|
|11 post-action refresh|localizer primary 不在 raw；正确 retained 源正文被截尾。现 recovery 拒绝未对齐主源是正确保护；固定四控未复现。[账本](../../evidence/remaining-consumer-feasibility/README.md)|**缺证/合同**。需已有所选目标与主源对齐权限及匹配公共红；不能把第一 anchor 当 primary 补读或删 extras 凑预算。旧探针已停止。|
|13 validation stop|中文在 structural focus 丢字段域目标，英文主源保留但有 extras；独立唯一中文红发生另一层。[账本](../../evidence/remaining-consumer-feasibility/README.md)|**缺证/合同/旁修**。字段对象→动作域绑定未定义；词法与比较符假 write 已修。先说明源字段/请求对象身份，不扩大 statewrite 或 error 词补丁。|
|15 combined commit|真实 commit 正文完整，真实日志/错误词选 reporter，wrapped caller 伴随。[账本](../../evidence/remaining-consumer-feasibility/README.md)|**合同**。缺请求级日志与操作归属，未有唯一共同 dispatch/save owner 证明。先审现 trace 的任务角色，不冒称源码丢失，不复活终端 one 规则。|
|16 gesture state|目标 body 完整，真实另 gesture callback 与状态源竞争。[账本](../../evidence/remaining-consumer-feasibility/README.md)|**合同**。需同 callback 参数到目标 state 的绑定；真 gesture 竞争者不能视为 absent。停止无关 parser 边角。|
|18 lifecycle persistence|跨方法正确 owner 被单方法两 marker focus 排除；独立同层红，non-erasure 仍带 forbidden extras。[账本](../../evidence/remaining-consumer-feasibility/README.md)|**合同/否证**。需同 owner 方法身份及 hook/read/write 关系，不把全文件 marker 灌每方法；视觉替代机制不能充作同一聚合架构的第二类。|
|20 touch safety|正文原已完整，真实日志与多目标保宽；inline callback list 范围污染已修，原组仍2/3。[账本](../../evidence/remaining-consumer-feasibility/README.md)|**合同/旁修**。scope/日志守卫没违约。先证明当前操作请求不授权日志；不强改 multiple，不重复修 opening_column。|
|23 builder layout|真实 Builder 方法已召回却输给 component build；当前 Builder→component 是粗角色合同。[账本](../../evidence/remaining-consumer-feasibility/README.md)|**合同，可做有界设计**。先核 decorator 到 callable 的源位置绑定接口，再预注册真Builder/注释/BuilderParam/unknown控。新增角色不自动授排他，也不借 alias 修复充架构证据。|
|25 archive IO|unpack 已召回，strong identity focus 留 badge/catalog；隔离 v3 单机制绿但合取/其他控未闭环。[账本](../remaining-owner-actionability/README.md)|**合同/否证**。审核旧冻结 receiver/path/handle 与请求组合，不放开多目标/unknown，不发布 v3 局部绿。|
|26 shared aggregation|正确文件 focus 后 salient 加源；英文 localizer 错主选且正文截尾；独立 loop 三控仅检验 hint 边界。[证据](../../evidence/shared-record-current/README.md)|**合同/缺公共红**。direct reduction→return 不是 cache argmin→同receiver delete；broad query 明确 exploratory。不可拼第二类或复制 collectionfold marker。先定义源值/请求角色。|
|27 keyboard focus|正确 attach 完整，真实注册/写state 来源竞争；后来固定四独立控全满足，不是事件值流公共红。[账本](../remaining-owner-actionability/README.md)|**合同/缺证**。只注册或只写不能证明同 callback 消费事件并写目标；既有绿控按 stop 保存，不加噪声造红。|
|28 native color|正文2–12已恢复，仍因 structural/import/salient 竞争精度失败。[账本](../remaining-owner-actionability/README.md)|**合同/旁修**。操作形容词 native 与结构目标需区分；不全局拆词，interface 显名保留已修，不重复报源码收益。|
|30 output loop|早期重复投影挤掉 collect 已修；后 raw 有 collect，bounded descriptive label 独占 compact。[证据](../../evidence/output-loop-followup/dedupe-result.md)|**合同/否证**。marker/v3 未闭环；新 literal 负事实提案的请求 gate 又被否证，见下文。不能删 label 后直接把 SingleRead 认证为 loop。|
|32 WebView policy|正确 typed build 在，但主选别文件/英文 component 与选中方法不等；nested Column 实际尾部不全。[更新](../webview-range-contract-audit/README.md)|**合同/缺匹配独立红**。嵌套机制优先是既有设计，非 ID 被改名。现恢复只补同interval，不能扩为 enclosing。若研究完整正文需新分配/投影合同及真实预算证据，不绕权限补读。|
|33 cache eviction|独立真实 scan/delete 输给纯描述 monitor；真实 FIFO/literal 控保留；hint 候选仍公共红。[证据](../../evidence/cache-eviction-current/README.md)|**合同/否证**。原任务是 oldest/timestamp scan+delete，不需 LRU/get刷新/最终容量保证。不能再给附加门槛；但负事实请求 gate 已失败，不能偷改 source_operation 支持集。|
|34 source replacement|独立 focus 唯一 swap 后，被历史 load 词面的 bounded localizer 排他裁源；真实load/literal两绿。[证据](../../evidence/history-action-before/README.md)|**合同，有匹配公共红**。历史动作与当前目标归属未定义，early focus 不是权威。最小设计需反向冲突（早focus错、后localizer对）、引号/歧义/多目标；不重复 before，不以07凑两类。|
|37 command binding|嵌套 object/initializer 身份粗；同file重复隐藏造成 certainty 错判已修，原仍红。[账本](../remaining-owner-actionability/README.md)|**合同/旁修**。field type map 未承诺 initializer 实体范围。新 nested/initializer身份设计须有独立需求与unknown规则，不能恢复撤回 parser。|
|38 comparison visual state|真实 state 名/边已修；Rotate读、回调写跨 UI 参数尚无请求绑定。[账本](../remaining-owner-actionability/README.md)|**合同/旁修**。同变量读写不是编辑/创建角色证明。设计同owner UI读/回调写与真实比较请求，不降低marker阈值。|
|39 cross-layer error|raw 两必要owner在，localizer选retry/detail并裁源；旧独立错误实验失层不匹配。[账本](../remaining-owner-actionability/README.md)|**缺证/合同**。尚需固定跨层转换/传播同层红及真实retry/literal控制；不是再修已完成 typed import。可作有界证据审计，但不先设计全值流。|
|40 canonical preview|preview已排除，正确写入正文完整；salient retry和真实imports剩余。[账本](../remaining-owner-actionability/README.md)|**合同/停止旧探针**。canonical非排他证书。分别证明直接补充与graph保留资格，不全删邻项、不再改原query。|
|42 indirect caller|具体 qualified callee 的错method入边已修；原泛query仍加callee/log/graph上下文。[账本](../remaining-owner-actionability/README.md)|**合同/旁修**。有限caller集合不是全局唯一；需明确caller-only任务是否保callee及日志，保多caller/真日志控。|
|43 preference restore|原正确primary下graph/import+wrapped log保宽；独立before却主选repository、未到同分支，双目标另有预算截断。[账本](../remaining-owner-actionability/README.md)|**缺证/停止**。现实验不能证明原分支误用；不追加样例调成红，不给alternative/双range恢复新权限。下次只能按明确新问题冻结合同。|
|44 native listener|真实 attach/callback/参数存在，但retry/onFailure词面排名更高；独立generic旧红与四正控齐。[账本](../remaining-owner-actionability/README.md)|**合同/旁修**。注册→回调→同receiver转发尚非typed证明。先审核现固定接收者/注册义务；raw同名ID去重及weak-covered保留已修，不能重复计入。|

## 本轮改变了哪些“下一步”判断

- **fallback 10 不再是尚未追清的原trace**：实际首丢、multiple、错误portfolio、无跨owner call/import 都已核清。现在缺的是角色身份请求合同与独立验收，不能继续泛泛查丢在哪。
- **cache/output 33/30 不再处于“可直接启动 literal classifier”**：[请求 gate 实验](../../evidence/literal-intent-shadow/RESULT.md)固定11格有3个不符：HTML artifact错误获可执行权限；timestamp与output原必需query未准入。其余多数绿只是gate未激活。停止该候选，不增HTML/SQL例外或绕multiple。sole-literal源事实虽可描述，但未获安全消费权限；不据两域红自动发布。
- **WebView 32 不再只是泛范围不匹配**：原callable primary在别文件，英文component/method/nested区间不同，中文nested不截断。角色primary标签不授恢复权。源码真实缺尾与精度失败独立，且saved trace尚未标定char分配还是最终token裁剪首丢。没有证据支持同identity漏接修复。
- **保持计数纪律**：窄producer/身份/正文修复可以有价值，但没有让原冻结case通过就不增加20；历史表格不能拼成新总分。

## 建议排序：不要继续同义词和旧样例循环

1. **02：既有 provenance 与分数耦合的内部合同核验。** 仍有明确未穷尽的实现接口问题，且不需要发明语义权威。先读其 documented 返回语义；若只承诺晋升结果，则记录缺独立关系通道而非bug。若存在独立来源保留承诺，再冻结真实边/ID内部边界；必须另有公共闭环才可发布。这是目前最小、可证伪且尚未做完的一项。
2. **23：Builder 源角色的有界设计审查。** 有真实可观察源码标记和已知粗映射，适合先核身份、范围、unknown，不是全算法证明。仅新增事实是否值得、请求怎样使用仍需审；不保证能减原失败。
3. **34 或44：选一个窄请求/关系合同审查，勿并行堆新架构。** 34已有匹配红，重点历史/当前归属；44有真实receiver/registration义务。二者不能仅因竞争就当同一算法，不预先承诺成功。

暂不优先：已否证literal gate/semantic veto/language拆分、缺匹配红但固定试验已停止的11/43、以及已修完的词法/范围旁枝。39确实还缺同层证据，但比02更易滑向泛error/dataflow推测，只有固定有限问题才值得启动。

长期未减失败的具体原因是：剩余失效多在**请求所指角色与真实来源之间的授权**，而不是源码是否被索引；已有精度oracle还要求不要保留无关但真实来源。提高召回、补全文或负向排除描述都未必修正primary/精度，强行放宽保护又已产生startup、literal artifact等反例。证据限制只约束已尝试方案，不表示30类已被证明无解。
