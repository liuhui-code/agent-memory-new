# 局部绑定证据扩展提案（只读评审，未实施）

## 结论与证据前提

不批准把 render 与 keyboard 直接统一成一个“局部 value/reference binding”新架构。

- Render 有独立公开红：`docs/eval/owner-audit-current/render-protocol.json` 与
  `render-independent.json`。MessageSurface 的 build 把 this.plainBody() 返回值传给
  Text，plainBody 对 content 做 replace；无关 DisplaySettings.trim 等也被返回。
- Keyboard 目前确认的只有原组和 clean replay：同目录 keyboard-focus-state-owner.json
  与 context-keyboard-focus-state-owner-clean.json。README 明确将独立正反例列为下一步，
  没有已确认独立键盘公开红。不能以它满足“两类独立缺陷”前提。
- 两者语义不同：render 是同 owner 跨方法的返回值→UI 参数数据依赖；keyboard 原码
  是 height 在 if 条件中控制 editorFocusable=true/false，属于事件回调控制依赖，
  不是把 height 的值赋给 focus。共同点只到词法作用域/符号身份/源码凭证，尚非同一证明。

## 可复用与不可偷换的既有合同

可复用：source_call_scanner 的代码掩码/平衡范围；semantic_ecma 的同 owner 调用目标、
callable 范围、已有 calls/reads_state/writes_state/registers_callback 边；symbol key、
源摘要、typed endpoint 与旧索引 unknown 机制。读取同一源码快照，不造新调用图。

不能直接组合成证明：
1. calls(build, plainBody) 只证明调用，不证明该返回值是 Text 的参数。
2. reads/writes_state 只给方法→状态边，不证明事件参数出现在控制该写入的谓词里。
3. registers_callback 只证明注册关系，不证明具体注册 receiver、event、回调参数和
   状态赋值处于同一次绑定。嵌套方法有既有遮蔽处理，不能把 whole-file 标签抬成方法证明。
4. query_typed_contract 明确只处理显名单参数/返回/声明/literal，不推断数据流；泛词
   “事件”“焦点”“渲染”不授予其匹配权。

Schema 判断：SemanticRelation 现允许 relation 字符串，但只有 source/target/line/detail，
没有返回表达式→参数槽或谓词→受控写入的结构化端点；SemanticMechanism 的 kind 白名单
也没有这两类证明。不能把结构化证据塞进 detail 字符串当授权。若以后证据支持，需要
版本化生产者能力与消费合同；未必需要新的数据库/架构服务，但绝非现有 v1 已证明语义。
本轮不添加字段、关系、schema 或部署迁移。

## 最小下一步：只验证键盘缺陷是否独立存在

固定一份全新 Development fixture，在运行前保存源码、查询、预期身份与 SHA256。
不复用原 DesktopEditorFocusController/KeyboardFocusHint 名称或原问题措辞。

真实目标 FocusBinding.attach 的核心：

```typescript
attach(viewport: WindowViewport): void {
  viewport.on('keyboardHeightChange', (pixels: number) => {
    if (pixels > 0) {
      this.canFocus = true;
    } else {
      this.canFocus = false;
    }
  });
}
```

同一 fixture 固定四个竞争源：RegistrationOnly 仅同事件空回调；FocusPreference
仅普通按钮写 canFocus；StatusText 仅输出“keyboard height focus”文字；OtherViewport
监听另一个 receiver/不同事件并写自己的状态。它们都是相应请求的合法源码，不可全删。

一次运行固定四个 public query，不因结果更换名字或措辞：
1. “键盘高度变化后，请定位根据事件高度设置输入焦点开关的注册回调。”
   预期 FocusBinding 的真实注册和分支写入源码，不能仅按名字选中。
2. “Find FocusBinding.attach source.” 精确方法正控。
3. “Find both FocusBinding and FocusPreference source.” 双目标保全，不能拿单目标精度
   作唯一成功标准；应分别记录 required recall 与额外来源。
4. “Find the literal keyboard height focus.” 真实文本来源正控。

执行仅 init/learn-path/context(raw+compact)，不改服务，不跑原 pack，不改 oracle。
若泛请求本来通过，记录未独立复现并停止，不添加噪声直到失败。若失败，先逐层记录
registration/callback 参数/谓词/写入是否有已产字段，以及第一个原本存在却消失的身份。
没有同层红，不允许基于这个 fixture 修改投影。

## 若出现真实独立红，才冻结下一阶段关系反例

固定控制，不直接上线新规则：
- 正：同回调参数直接 guard 同 this 状态写；闭包同 owner，不宣称真实运行时事件已触发。
- 反：注册空回调+回调外写；参数在无关日志使用+常量写；另一个嵌套回调里的同名参数；
  两个不同 receiver 各提供一半条件；同文件不同 class 各提供一半。
- Unknown：参数/receiver 赋值或别名、解构、computed/optional 调用、逃逸闭包、动态事件名、
  无法解析/模板插值/缺旧索引角色。unknown 不能按“不含该行为”删候选。
- 真多解：两个独立合法事件→状态绑定都必须保留；明确只要 registration 或普通 setter
  的查询不能被新关系反向排除。
- Render 仅作为不同能力参照：调用返回值直接传给 Text vs 调了 helper 但结果未使用、
  Text 消费另一个值、相同方法名不同 owner。不能靠这些名字宣布两个合同已统一。

## 预算与停止条件

保持现有 1500 token、源码读取/摘要/单段与总段限制，不为证明涨预算。记录身份、区间、
实际源码字节、总 token；不能把 range overlap 当完整正文。若证明材料不全或预算截断，
只能标不足，不得以 score 或文件名填补。所有当前 anchors/roles、真日志、双 owner 和
未知分支均需比较；不移除 ranking 字段以外的新内容来凑成功。

本提案不跑测试、不创建生产候选。可执行下一步是上述一次性键盘独立取证；它不预先
保证红例，也不预先批准统一数据流架构。只有该证据和明确类型化关系合同都成立后，
再判断两个能力是否共享仅基础设施，还是确有可以统一且可证伪的证明结构。
