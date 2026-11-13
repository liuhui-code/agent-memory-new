# 15 类剩余消费问题可执行性审计

审阅基线 **e868649**，只读保存的报告、public JSON、trace；本轮没有新查询、测试、全量评测或生产修改。编号来自工作分类账。不能将这些不同版本的最后结果拼成当前总分。

**日期口径：** 原评测 JSON 多数不记录执行日，不能把目录的 `20261114` 当实际执行时间。下表日期是最后相关证据的 Git 记录日（统一 UTC+09:00），不是伪造的测试时间；执行日期未独立认证。完整原始时间、SHA、文件哈希在 [sources.json](sources.json)。06 为隔离保存件，执行日期未知。所有“最后验证”均是所列版本的历史定点，**不是 e868649 重验**。后续修复不自动证明旧通过或旧失败保持。

## 按类别的证据、合同与下一步

|编号 / 类别|最后保存验证 / 记录日 / 基线|首丢层与真实字段证据|现有合同能否直接安全修复；未解条件|最小下一步（不是自动批准实现）|
|---|---|---|---|---|
|02 cross-component-preview|1/3；11-14；8ce567b，证据 bc92352|最新英文 raw **已有 MessageRow 与 QuotedMessagePreview**，不是旧账的缺召回。实际 imports、renders_component、passes_property 存在；promote_neighbor 因 50.17<67.5、反向54.52296<56 不添加 graph provenance；bounded MessageRow.build 在 compact 按文件裁掉 child。|**有明确可审计的 score/provenance 耦合点，但尚不可直接发布补丁。** 两版独立四控全绿，仅反向抑制，未覆盖双端高分。同层公共红缺失；真实 edge 也不自动授权所有请求保留双端。|优先核内部 `promote_neighbor` 已有返回/元数据合同：实际 typed edge 与 endpoint ID 不变时，已有更高分是否必须丢关系来源。做确定性内部边界检查之前先冻结，不能伪称 public 红；是否进入公共复现必须另审，不改词制造高分。|
|04 arkts-ui-operation-owner|0/3；11-14；import-traversal 后1105717|最新原组仍0/3。旧原文 raw InventoryList 首位，localizer 选 WorkspaceAbility；其他两项正确 divider 源码伴额外owner。独立 GlyphList 语言query被 EntryAbility 污染。|没有已确认的丢失UI证书。全局 ArkTS/ETS language-only拆分虽修独立UI，却破坏四条真实隐式startup控，已撤回；不可重试该方案或加启动特例。|复用已固定UI与四startup反例审“语言限定 vs 隐式平台目标”的输入角色边界；需新明确合同，当前不可直接改 query_tokens。无需继续parser调查。|
|05 domain-model-versus-render-owner|2/3；11-13；134cfcb|正确 ArticleMarkupView 正文已完整，AccountSettings/NotificationDetails 为直接词面/补充候选。独立 MessageSurface 红同样混入 Record 与无关 trim；不是 proved callable winner 被投影擦除。|没有现有 transform→render 值依赖证书。replace/trim、Text 调用都真实，不足将其他候选判无操作；角色名 Record 不授权删除。|先说明清洗方法输出如何被 build 消费，独立绑定正反证明后才讨论源值依赖表示；当前不做 post-focus 删除。|
|06 query-owner-and-consuming-page|1/3；日期未知；ed18df2历史保存件|原 raw page/service俱在，compact单primary。固定独立 SQL参数owner+提交渲染page query：raw EntryService.search+EntryPage.submit，bounded后只留service。普通“query service and consuming page”却保两端。|现有 named-pair保护只涵盖明确实体身份，不是泛 SQL owner/consumer角色认证；未知范围不能冒认。没有证据说明 typed service合同已产生而漏消费。|读已存同一 query 的 scope、portfolio与typed-role字段，界定是否某个**已存在**双端授权被丢。若没有，需角色→已召回实体绑定合同；不要把所有 both/two动作放行。保留普通literal控制的extra，不称全精度绿。|
|07 abstract-scroll-structure|1/3；11-13；623981f|目标ShipmentTimelinePage.build ID316、6–16、vertical/listdirection/height齐全；generator ID80、2–4压主选。独立21.39>20.84同型，**uncertain且两源保留**，不是bounded排他丢目标。|无现有任务元语言/领域词code归因合同。全局stopword不安全；source-code-for/of固定两族仅一族red，按停止规则结束。|不重跑停止实验；若提出新的语言归因表示，先证明能兼容领域生成/解析、引用和未知请求，不能拿此例算historical-load排他丢源的第二类。|
|08 abstract-reactive-aggregate|1/3；11-14；80feab8|reloadSummary ID295、9–16与两个writes_state边存在；24项行为召回包含它。coverage2与UI方法并列，strongest_semantic前两文件保BackupCommandPanel/ProductSearchPage，真实numeric目标被focus删。|不是producer缺失。writes_state不证明数值累积，foreach/watch概念也不证明算术；独立5固定query全部满足冻结retention，未复现top2同层red。|先界定请求要求的numeric证据如何获得权限，再考虑独立同分竞争合同；不能扩top2/调权或排除真实UI ForEach。现阶段保留原first-loss，不补无收益marker。|
|09 abstract-visual-overlap|1/3历史组；11-13；3d62965；后续14064c5实验|InventoryOverlay.build focus输入32.5已在，TouchOverlay35.5因真实Stack/overlay两marker胜backgroundcolor一项；独立AmountSurface/GestureLayer同层red。|当前alternative marker与多要求覆盖未区分，不是已承诺background优先被漏用。非擦除veto实测仍red，已拒，不能再启用。|需要请求目标/替代机制合同；保存真Stack和多layout正控。不得将partial方法数/文件marker赋排他，当前没有可直接打补丁的既有误用。|
|10 fallback-recovery-owners|2/3；11-13；134cfcb，member修后e760097报告|最后英文 raw两恢复来源在，compact保DeviceSyncStore、缺TransportRegistry。member词法修复并未改变此原失败。|尚无可信双恢复角色的绑定证据，也没有证明一个方法两动作必然两owner。新基线未经复验，不能说当前已解决或完全受阻。|先从保存public核已有calls/typed identity能否连接两个要求的角色；这是证据覆盖不足的类，优先只读补trace，不再造callback假实体。若无绑定，再冻结双角色/单owner两动作控。|
|11 post-action-refresh-owner|2/3；11-14；bc92352(runtime8ce567b)|focus正确LightingStore，salient加InteractionState/CommandOutputPage；bounded DraftPage.reloadPreview34.735 **不在raw anchors**，compact因此原样保留。目标range1–13而actual excerpt1–9，1479token，缺refresh body。|现recover_partial_primary要求primary恰匹配已选anchor及typed digest来源，缺主源时拒读是遵守合同，不能用第一anchor替代。独立四控primary均在raw，全部retention过，未重现缺对齐红。|不绕过来源证明补全文；需先有已选目标与localizer主选的对齐权限合同及独立同层red，不能删extras凑预算。停止固定探针后不追加噪声。|
|13 validation-stop-owner|1/3；11-14；8ce567b|英文focus正确后salient两额外owner；中文AccountSettings在focus输入14，OrderCommit在13，均score6，结构coverage贪心删正确字段域。词法/==修复只纠正hint，原1/3不变。|guard/toast/return/dispatch两竞争源都真实；缺字段对象→动作域绑定。固定18cells中唯一中文red为无marker的localizer失效，不匹配原中文focus层；不能偷换成结构修复证据。|保留英语真绿、中文非同层红，暂不再追statewrite旁支；若绑定合同设计要开始须明确displayName/customerCode等源身份与请求的对应，不许添词或提升file hint。|
|15 combined-commit-owner-precision|2/3；11-13；8d03c8a|中文commitOrder8–15完整保留，primary ConsoleFailureReporter.report由真实错误/日志词匹配，额外wrapped caller在compact；并非真实commit源被删。|未有共同dispatch+save owner的排他证书。multiple不能被终端one启发式撤销，错误词不能全局降级。|限定请求级日志vs操作归因证据，先复用已有public字段判断；不与source-replacement“丢目标”冒称同一结果，不重启被拒scope语法。|
|16 gesture-state-owner|2/3；11-13；8d03c8a|正确BoardGestureSurface.build5–12完整；uncertain与InteractionState.selectPointer竞争，CanvasInteraction真实gesture callback仍在。|producer实体/范围完整。出现gesture不能证明特定参数→状态绑定，也不能认证另一真gesture源absent。|仅在独立同callback参数与所写目标state的绑定证据充足时设计合同；不自动继续parser边角。|
|18 lifecycle-persistence-owner-precision|1/3；11-13；f9ecd08，后续拒绝实验14064c5|正确DraftSessionCoordinator class/file/三个方法都有；restore49、save46.25，仍被ConversationDraftStore单方法两marker focus删。中文独立PendingQueue竞争复现，英文控制仍过。|当前允许partial>=2；跨方法owner完整性尚无证书。非擦除veto提升召回却留禁TextPanel仍red，已拒；全文件hint不能复制给每method。|最小新设计必须同owner typed method identities+分方法覆盖+hook/调用边界，不推因果；缺第二独立缺陷支持同一聚合架构，不能用视觉替代机制凑数。|
|20 touch-access-safety-owner|2/3；11-14；ed3fd70候选定点（生产base b9d01e2）|原中文touch源在，JobDispatch/WrappedProfile extras。独立touch+logger red：multiple scope使admitted_log_owners保留，file projection不是两marker方法证书。新inline onTouch5–11→5–7仅修list兄弟污染，context原已收窄正确，原组仍2/3。|scope守卫和无强path不足以删真日志。已修opening-column合同不应重复修或算原收益。|只读审当前请求角色和完整method证据是否真能成立；没有则需先独立证明日志非目标，不能强改multiple/复制file marker。|
|23 builder-layout-source-focus|2/3；11-14；80feab8 alias阶段后复验；角色诊断640f90b|正确@Builder renderStrip4–11已召回，独立LayoutGuide.build29.9 > renderStrip19.29；全部owner_kind=component/target_owner_kind_match=True。importalias错callee已另修，但本组未变。|**具体缺Builder decorator→callable角色**，不是既有角色漏消费。当前Builder映射component是粗合同；纯文本目标也是真正应保留的正控。不能直接把component改成Builder-only。|可实施前置是只读核decorator位置与现symbol绑定接口，冻结真@Builder/注释/BuilderParam/参数/重载/unknown控；是否新增源角色须合同审查，不可借已修alias当第二类架构证据。|

## 选择一项下一步，而不是继续 parser 旁枝

**第一优先：02 的 provenance 与分数耦合，限内部合同核验。** 已保存原公开输入存在真实双端边，endpoint typed identity/range齐全；分数提高反而消掉关系来源是一个明确、可证伪的实现条件，比继续猜owner权重具体。但现独立公共两版没有覆盖双端抑制，所以目前**不是可直接发布的修复**。可以先读/冻结 `promote_neighbor` 的内部合同，使用现有真实图边与ID做确定性边界核验：只改变已有matched-score的比较关系，检验评分不变时来源是否应可单独保留。内部注入分数不是正式CLI红，必须明确标内部Development，不以此替代公共验收；也不自动修改graph guard使所有关系有保留权。若当前合同明确只记录获晋升候选，应记录其为缺少独立来源通道而不是bug，停止实现。

**第二优先（证据不足而非不可修）：10 的原恢复角色链只读trace。** 相较已结束的多轮实验，该组尚缺精确第一次裁源与已有 typed/call edge 对应；先补读取保存材料，未找到才申请一次有限冻结探针。06的已有独立raw→compact丢双角色也可为同一请求角色合同提供候选对照，但必须实际核身份/作用域，不能仅因都双owner便合并。

**不立即启动：** 23新增Builder源角色、18跨方法聚合、05 rendered-value flow都是真实可设计方向，却不是当前既有证书误用的窄修。07已停止元语言实验、09/18拒绝veto、13固定竞争未同层、11固定对齐控未红不重复。以上分类区分“有红但缺安全授权”“缺同层红”“证据覆盖未完整”，没有将15类笼统宣称全blocked。

## 证据定位

本文件每一行对应 sources.json 同编号清单，报告相对路径均指本仓库，`@`指共享工作区历史隔离件；记录SHA256避免后续误读改版。06额外检查了 role-competition-before 的六固定查询、raw/compact原stdout，第一自然角色pair丢page、一般query-service pair保两端，literal控仍有extras，未重新标成全绿。来源日期和老基线保留，不以本次文档commit时间冒充执行日期。
