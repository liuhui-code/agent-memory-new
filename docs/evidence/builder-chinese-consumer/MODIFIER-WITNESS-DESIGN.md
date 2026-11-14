# Proposed bounded Builder modifier witness (design only)

Status: review proposal, not frozen acceptance and not implemented. Base 0a8a8fd;
original unchanged trace retained at 29ad7d7. No new evaluation has run. This is a
new local positive qualification contract, not a correction to the accepted
English consumer's intentionally non-semantic ATTRS labels.

## Evidence and purpose

The original Chinese trace has two genuine, selected Builder declarations. One
contains a List chain with listDirection and height, the other a Row chain with
height and width. Full source is already available. Role-only Chinese grammar
would not distinguish them. Neither scores nor raw-anchor membership establish
which declaration satisfies a request. Proposed evidence is narrowly: an exact
set of call spellings occurs as direct suffix calls on ONE syntactic construction
chain inside a currently verified Builder method. It does not establish runtime
receiver type, layout effects, values, causality, global uniqueness or completeness.

## Source witness boundary to review

Reuse the existing produced arkts_builder identity, generation, full source key,
method range and digest. Read at most the existing 2 MiB limit once, verify hash,
and derive the witness from those same bytes. No new persisted semantic producer,
SQLite schema, global ranking or generic operation facts. Do not reuse the rejected
trailing-operation implementation or borrow source_operation authority.

Require the existing whole-file known lexical mask (including its regex/division,
interpolated-template and unclosed-token unknown boundary). A proposed recognizer
must consume the ENTIRE selected method body as a sequence of bare-identifier
construction calls, optional balanced DSL bodies, and direct identifier-call
suffixes, with optional separators. Mixed delimiters must be balanced, not just
parentheses. Body/control/member-prefix/optional/computed/new/assignment/return/
delegation forms outside that limited grammar yield unknown. Never infer a base
from the character immediately preceding a dot. A construction identifier is a
syntactic shape, not proof that it resolves to an ArkUI constructor.

Inspect only suffixes attached directly to each top-level construction. Nested
DSL bodies may be balanced opaque contents; their callbacks, inner constructions
and modifiers cannot contribute to the outer chain. This permits the WorkGallery
ForEach contents without treating a callback's calls as the Builder's own chain.
Every required exact-case spelling must be on the SAME chain. Never union across
chains, methods, files or delegated Builders. Full method coverage is needed to
avoid certifying an isolated suffix after unknown code. Limits or unsupported
syntax produce unknown, never absence. Do not truncate and certify a prefix.

The existing full-ranked, selected known Builder identity checks remain. Multiple
positively witnessed Builders remain multiple; capacity failure preserves prior
behavior rather than claiming complete retention. No raw-anchor intersection.
The eventual ephemeral proof must bind original request, requirement set, source
identity/range/digest and consumed members. Ordinary JSON/dict copies cannot mint
it. Existing English role-only requests must retain their existing behavior.

## Property-to-call naming proposal, not an existing runtime dictionary

Exact API names may be requested directly, case sensitively. A separately reviewed
bilingual catalog could provide these names, not infer effects or receiver types:

| Chinese label | Exact call spelling |
| --- | --- |
| 宽度 | width |
| 高度 | height |
| 内边距 | padding |
| 外边距 | margin |
| 背景颜色 / 背景色 | backgroundColor |
| 列表排列方向 / 列表方向 | listDirection |

Primary documentation supports these API naming relationships:
- [OpenHarmony size attributes](https://github.com/openharmony/docs/blob/master/zh-cn/application-dev/reference/apis-arkui/arkui-ts/ts-universal-attributes-size.md): width, height, padding, margin.
- [OpenHarmony background attributes](https://github.com/openharmony/docs/blob/master/zh-cn/application-dev/reference/apis-arkui/arkui-ts/ts-universal-attributes-background.md): backgroundColor.
- [OpenHarmony List](https://github.com/openharmony/docs/blob/master/zh-cn/application-dev/reference/apis-arkui/arkui-ts/ts-container-list.md): listDirection and List arrangement direction.

“列表方向” is explicitly a proposed shortened alias, not a claim that this exact
phrase was already a runtime contract. The catalog is new, covers more than the
original two labels, and must be independently tested. size does not count as an
exact height call; background does not count as backgroundColor. API documentation
does not resolve the receiver of an arbitrary source call.

## Request contract still needing a concrete freeze

A new explicit modifier request must identify Builder source as the output head
and a finite list of required modifiers. Suggested independent surface examples:
“请返回同一构造链直接设置内边距和背景颜色的 Builder 源码。” and
“Find the Builder source with padding and backgroundColor on the same construction chain.”
These are proposals, not already accepted queries. Generic English ATTRS must not
silently acquire this meaning. Direct-call spellings and catalog labels need an
unambiguous full-string grammar; duplicated or conflicting requirements, quoted
requests, generated artifacts, wrappers and mixed output heads must not be cleaned
into eligible requests.

The original Chinese request does NOT explicitly say “same construction chain”.
Whether its “设置列表方向和高度” licenses a stricter, sufficient positive witness
without implying completeness is an unresolved review decision. Adding only the
suggested explicit surface would not repair the original and must not be reported
as doing so. The symptom prefix and negative tail must be parsed/retained in full;
no positive_retrieval_query rewrite may grant permission. A broad Chinese prefix
regex is not an acceptable interpretation of arbitrary instructions.

Existing excluded_code_candidate has 数据模型→model but not 卡片→card. Any card
alias addition is a separate existing-language-alias change needing independent
prospective tests. Apply supported exclusions against the actual complete known
candidate before positive qualification; do not assume file ranking already did
so. Explicit identity/role conflicts and unsupported exclusions must fall back.
Unknown candidates are not declared non-Builders or non-matches.

## Independent controls to freeze BEFORE implementation

Use a different source family: two @Builder methods, one Column chain with padding
and backgroundColor, another Row chain with padding and width. Add a same-file
competing Builder and two genuinely qualifying Builders. Do not copy List/height
source or tune noise after observing results. Capture actual public raw/compact
before, full ranked identities and source bytes. Stop if no independent public
red or if the required role/source identity is unavailable.

Required source controls: same-chain positive; cross-chain pair (no combined
witness); nested-only pair; comments/string occurrences; wrong case; computed and
optional receivers including multiline prefixes; if/function/arrow/bare-block
closings; delegate-only and mixed unsupported top-level statements; mismatched
range/digest; stale/old index; full limits; two positive Builders; ordinary
component without role; unknown lexical Builder. Unknown must not mint authority.

Required request controls: text/generated-source/wrapper output heads; explicit
other owner; mixed Builder/component targets; positive/negative conflict; quoted
modifier names and quoted complete requests; supported negative exclusions;
unsupported negative words; duplicated/unknown attributes; source catalog aliases
and exact names; English existing 24 and old-index 5 unchanged. Preserve all
log/path anchors and prior explicit graph/identity protections.

After review, freeze actual source bytes, query strings and precise assertions,
then run one independent before. A separate review must authorize implementation.
Only after fixed-SHA focused regression and independent public checks may original
23's three variants be measured. No full gate and no assumed cumulative gain.

## Current decision gates

1. Is a direct syntactic same-chain call observation a sufficient, non-exhaustive
   positive selector for the ORIGINAL generic setting request, or must requests
   explicitly require direct modifier syntax? The latter does not fix original23.
2. Can the complete original symptom/negative grammar be specified without dropping
   instructions or introducing project-specific labels? No grammar is approved yet.
3. Can the narrow recognizer prove complete top-level coverage with the existing
   lexical unknown rules? The rejected producer demonstrates why balance alone is
   insufficient. No implementation or source-safety result is claimed here.

If these gates cannot be resolved, preserve the trace and select another evidenced
failure rather than implementing an unrelated explicit query feature.
