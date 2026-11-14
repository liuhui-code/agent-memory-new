# Finite same-owner source qualification (design only)

This is a new positive qualification, not revival of the rejected marker union/veto. It requires independent review before execution or implementation. The first implementation target would be Chinese complete source requests; existing English controls retain old behavior. It makes no storage/framework runtime guarantee.

## Complete request surface

Exact Chinese tokens, no whitespace/quotes/unconsumed suffix, <=240 characters:

```
[PREFIX，]请VERB同时负责生命周期恢复、状态STATE和持久化的TARGET。
PREFIX := 重启后恢复SUBJECT | SUBJECT保存后重启仍被清空
SUBJECT := 文本 | 草稿 | 编辑内容
VERB := 定位 | 只返回
STATE := 更新 | 写入
TARGET := 源码 | 协调源码
```

The finite symptom prefix is observation only; it does not select a domain owner or certify persistence. Missing prefix is allowed but has no new recall promise. Any generated-text/head, quote, explicit different owner, negation/exclusion, additional conjunction/output, two-owner request or unknown phrase uses the complete old pipeline. English queries are unsupported by this phase and must remain unchanged. No cleaned-query parsing or global alias.

## Complete source shape

Whole file, optional ordinary named relative imports, exactly one plain exported/unexported class, no extends/implements/constructor/accessor/static block. Exactly three distinct zero-argument methods and one text field; an optional declared plain receiver field is allowed. No additional declarations/methods, local shadow, delegated helper, unknown statement or incomplete lexical region. Explicit source identifiers are ordinary ASCII, non-reserved and non-colliding. File <=2 MiB; each method <=32768 characters.

```
[private | @State] TEXT: string = ''
[private RECEIVER: TYPE [= new CTOR()]]
HOOK(): void { this.RESTORE() }
async RESTORE(): Promise<void> { this.TEXT = await RECEIVER_EXPR.load() }
async COMMIT(): Promise<void> { await RECEIVER_EXPR.save(this.TEXT) }
```

HOOK is exactly `onMount` or `aboutToAppear`, from the already recognized lifecycle-name surface. This proves the method's spelling and explicit invocation syntax, not actual framework invocation. RESTORE/COMMIT/TEXT/RECEIVER identifiers are arbitrary distinct names, not original-case constants. RECEIVER_EXPR is either one unresolved bare identifier or `this.RECEIVER` bound to the declared receiver field. The same exact expression must occur in load/save. External types and bare receiver definitions may be unresolved: same spelling is not an object/key identity certificate. `load` and `save` are literal call-spelling observations, not proof of durable storage, restore success or save scheduling.

A typed current class and all three method rows must match source name/range/key/digest/generation/owner. A current `calls` edge must match exact hook and restore IDs, current source digest/generation and extraction metadata. If TEXT is @State its current State row/range/qualified name must also match; ordinary private fields use explicit same-read parsed declaration ranges, not invented rows. The whole source must be consumed; three shapes distributed across owners never combine. COMMIT is not in the hook call chain, so no execution ordering claim.

## Pool and output boundary

Only files with both an already recalled file item and at least one full current method identity in the original bounded pool before focus may be inspected. No full-repository scan, new recall term, larger pool/portfolio cap or score change. Complete positive owners may receive a new private source qualification before ordinary per-item semantic focus; this is not an old source_operation flag or query_supported field.

A complete-source request may choose only positively qualified source owners without claiming unknown competitors lack the behavior. All qualifying owners in the bounded pool must be retained; do not assume the original is unique. More positives than the existing output limit, unresolvable identity, protected explicit/graph/log/path context, or insufficient1500 budget causes the entire old result. No later generic focus may erase a qualified owner while claiming success. The permitted read range is the current indexed complete class verified against the same-read bytes, explicitly new whole-owner read authority rather than pretending the existing save-method range was already the class.

Ordinary raw/JSON/copy content must retain the old baseline; a privately bound query/pool/source receipt may supply an alternate compact view only after complete validation. Source display uses the same verified bytes with snapshot labeling, all qualified class ranges fully present and actual budget<=1500. No partial positive set or truncated class advertised as complete. The final accepted view determines once-only accounting. Any additional collection/serialization cost must be measured and reported, not hidden.

## Existing and additional controls before execution

Reuse all four `docs/eval/semantic-focus-contract/protocol.json` lifecycle source/query/oracles unchanged, including the current independent Chinese red and English/named/both controls. Freeze additional source controls: split owners; different read/write field; discarded load; different receiver; hook not calling restore; extra reassignment/delegation; duplicate methods/field shadow; wrong/stale edge; missing type identity; two complete positive owners; capacity overflow. Request controls include quote/generated/mixed/two-owner/explicit/negative/unknown prefix. No modified old query or added noise to preserve a red.

Before implementation, perform one current independent observation to verify the old Chinese red persists and its pre-focus pool has the required identities. If that fails, stop without tuning inputs. The original18 current audit is supporting first-loss evidence, not a replacement for independent acceptance.
