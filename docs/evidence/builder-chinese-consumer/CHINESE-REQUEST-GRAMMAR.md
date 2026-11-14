# Chinese Builder request grammar v1 — finite positive surface

Design for the writer's pre-execution freeze. No parser, evaluation or source change
is made by this document. This is a NEW limited request surface, not a claim that
arbitrary Chinese intent has been parsed. Existing English ATTRS semantics remain
unchanged. The original Chinese request is admitted by the productions below;
no special check of its complete string, project name or clipping keyword exists.

## 1. Full-input syntax

The lexer uses longest matching **literal terminals** from the tables below. There
is no arbitrary CJK, arbitrary word, `.*`, free predicate or free domain-name slot.
ASCII space/tab may occur between terminals (0..8 characters per boundary), never
inside a terminal. At most 16 outer ASCII spaces/tabs are allowed. Newlines and all
other whitespace are unsupported. Maximum complete input length: 256 Unicode
code points. These are admission limits; exceeding them returns unknown, not a
truncated or normalized accepted request.

```
REQUEST     := OBSERVATION COMMA HEAD TAIL? STOP?
             | HEAD TAIL? STOP?
OBSERVATION := SUBJECT "中的" OBJECT "被" PASSIVE_EVENT
SUBJECT     := ORIENTATION? TOPIC? CONTAINER
HEAD        := "请返回" ACTION ATTRS "的" "Builder" "源码"
ACTION      := "设置" | "配置"
ATTRS       := ATTR ("和" ATTR){0,5}
TAIL        := COMMA "不要返回" ROLE ("或" ROLE){0,1}
COMMA       := "，" | ","
STOP        := "。"
```

Only one parse of the entire input is admissible. Zero parses, multiple parses,
remaining bytes, unsupported tokens, repeated clauses or punctuation return
unknown. Do not run positive_retrieval_query/result-alternative stripping before
this parse. Whitespace admission is lexical only; record the exact original input
in the request receipt and check it again when consuming authority.

### Passive observation terminals

| Slot | Exhaustive alternatives for v1 |
|---|---|
| ORIENTATION | 横向 / 纵向 / 水平 / 垂直 |
| TOPIC | 作品 / 消息 / 商品 / 任务 / 设置 / 详情 / 内容 / 数据 / 条目 / 项目 / 图像 / 视频 / 文本 |
| CONTAINER | 列表 / 网格 / 视图 / 面板 / 页面 / 区域 / 窗口 / 容器 / 画布 / 工具栏 |
| OBJECT | 卡片 / 元素 / 内容 / 文本 / 图像 / 图标 / 按钮 / 条目 / 控件 / 组件 |
| PASSIVE_EVENT | 裁剪 / 截断 / 遮挡 / 隐藏 / 覆盖 / 挤压 / 拉伸 / 压缩 / 移位 / 重叠 |

This is a finite UI passive-observation vocabulary, not a general symptom parser.
All ten event alternatives receive prospective acceptance controls; only 裁剪
must not be singled out for special handling. Unsupported but sensible observations
fall back. In particular, this design does not introduce an arbitrary noun slot
with a blacklist as its only protection.

Observation tokens are retained in an AST as context **without using them to grant
owner identity, domain relevance, runtime effect, cause, global uniqueness, or an
absence proof**. For example 作品 is not matched to a file name to select a winner.
The complete query is still preserved for the ordinary retrieval path. The new
selector's positive claim is only its declared Builder plus property-call witness,
not satisfaction of every possible domain interpretation of the observation.

### Attribute terminals and exact requirements

| ATTR surface | Canonical required direct-call spelling |
|---|---|
| 宽度 / width | width |
| 高度 / height | height |
| 内边距 / padding | padding |
| 外边距 / margin | margin |
| 背景颜色 / 背景色 / backgroundColor | backgroundColor |
| 列表排列方向 / 列表方向 / listDirection | listDirection |

ASCII spelling/case is exact. Translate each terminal once through this table,
then reject duplicate canonical requirements, including `高度和height` and
`背景色和背景颜色`. Empty lists, OR lists, unknown attributes, quoted attributes,
parenthesized alternatives and more than six requirements are unknown. Do not add
synonyms based on evaluation output. These labels request static positive source
qualification; they do not assert effect or receiver type.

### Negative role terminals and application

| ROLE surface | Negative-role AST value | Status |
|---|---|---|
| 数据模型 | model | existing language alias |
| 卡片 | card | NEW local descriptor mapping; independent controls required; no global alias change |

Parse and retain the negative AST; do not simply delete it after recognizing HEAD.
Duplicate roles are unknown. Builder, component, method names, arbitrary identifiers,
unknown role nouns, and mixed output requests are not negative ROLE terminals in v1.
Thus `不要返回Builder` or `不要返回其他内容` causes the WHOLE new permission to
fall back, rather than silently ignoring a contradictory/unknown tail.

Admission of a request containing 卡片 is contingent on the separately accepted
local card descriptor and exclusion check being active. Without that support, return unknown for the entire
request; recognizing the characters in this grammar alone is not enough. Apply
all accepted exclusions to each actual complete candidate before qualification,
using the existing file-path/owner-name identifier-token semantics against the
canonical local descriptor. Do not change global NEGATIVE_ROLE_ALIASES; existing
English requests continue through their existing consumer. Do not assume earlier ranking
already filtered them; do not translate role absence into a proof of irrelevance.
The local card descriptor needs positive Card/CardView-name exclusion, non-card lookalike,
real positive Builder-with-card-exclusion, existing model exclusion, and explicit
positive/negative conflict controls. Do not globally change OWNER_KIND aliases. The existing excluded_code_candidate
mechanism is a file-path/owner-name token matcher, not a semantic role resolver.
The local mapping must not change ordinary English/Chinese retrieval. Freeze
quoted negative text, positive requests and lookalike identifier controls. Do not
synthesize an English negative query to impersonate support.

## 2. Operators and unsupported forms

There is no general cleanup stage. The positive lexer/parser admits only the
productions above. To make the refusal boundary testable, all of these operators
are unsupported outside their exact licensed slots, or unsupported everywhere:

- Quotation delimiters anywhere: backtick, ASCII single/double quotes, “ ” ‘ ’,
  「 」 『 』. Do not unwrap quoted requests or property labels.
- Conditions: 如果、若、假如、除非、否则、只要、当、假设.
- Alternate/extra instructions: 同时、另外、并且、然后、再、只、仅、仅仅、也、改为.
- Generation/artifact/wrapper heads: 生成、输出文本、输出代码、示例、说明、模板、
  包装器、调用、委托、代理、实现生成、字符串.
- Negation/conflict operators: 不要、不、非、无、无需、不是、而不是、排除、忽略,
  except that exact 不要返回 is licensed only at TAIL's position.
- Multi-target/alternatives: 两个、多个、各自、分别、同时、以及、或者, and 或 outside
  the negative ROLE list. 和 is licensed only inside ATTRS; it does not add another
  output head. The generic target-scope classifier must not be globally weakened.
- 请返回 is licensed only once at HEAD; 设置/配置 are ACTION only there. 设置 is
  also independently a TOPIC terminal in the passive SUBJECT, not an instruction.

This list is a test inventory, not an open-ended blacklist that lets every other
character through. Any text outside the positive terminal vocabulary is unknown,
even if no listed operator occurs. Semicolons, colons, exclamation/question marks,
parentheses, slashes, additional full stops and nested punctuation are unsupported.

## 3. Original request parse and authority

```
横向作品列表中的卡片被裁剪，
请返回设置列表方向和高度的 Builder 源码，
不要返回卡片或数据模型。
```

The displayed line breaks above are explanatory only; the actual original is one
line. Its AST is:

- observation: orientation 横向; topic 作品; container 列表; object 卡片;
  passive event 裁剪; exact original observation span retained;
- output head: declared Builder source; action 设置;
- requirements: listDirection, height;
- exclusions: card, model; both must be supported and applied;
- receipt: complete exact original query, parsed AST, canonical requirements,
  exclusions, and source proof/member identities, bound together.

This AST alone cannot select a winner. The separately reviewed source witness
must identify requested exact call spellings on one supported syntactic chain in
verified Builder source. That is a sufficient, non-exhaustive positive source
candidate for this generic setting request. It is not a declaration that other
implementations fail to set those properties. Unknown sources stay unknown;
multiple witnessed Builders remain multiple. Existing path/log/graph/identity and
budget guards remain mandatory. Never use the passive observation or rejected
candidate to manufacture unique ownership.

## 4. Minimum prospective request controls before implementation

Positive controls must include:

- the unchanged original whole request, with both negative roles actually checked;
- no-prefix `请返回设置内边距和背景颜色的 Builder 源码。`;
- distinct observation nouns/events, e.g.
  `纵向消息网格中的图像被遮挡，请返回配置宽度和外边距的 Builder 源码，不要返回数据模型。`;
- all six canonical attributes and their aliases/direct spellings; both comma
  forms, the bounded whitespace surface, each passive event, each exclusion alone;
- two separately source-qualified Builders, preserving both rather than using
  observation nouns/rank to choose one.

Whole-request refusal controls include:

- a quote surrounding the entire original request or any quoted property;
- `请返回生成设置高度的 Builder 源码的实现。`;
- `请返回调用 Builder 的包装器源码。`;
- `请返回设置高度的 Builder 源码，同时返回普通组件。`;
- `请返回设置高度的 Builder 源码，不要返回Builder。`;
- an accepted HEAD followed by an unknown negative role or another instruction;
- `如果列表中的卡片被裁剪，请返回设置高度的 Builder 源码。`;
- replacing an observation slot with an arbitrary sentence, instruction, unknown
  word or quoted content; a negated observation or a second comma-clause;
- `高度或宽度`, `高度和height`, `背景色和背景颜色`, wrong ASCII case,
  empty/too-long attribute lists, unsupported property, limits and extra bytes.

Freeze these outcomes before the independent before run. No input is repaired by
stripping, catalog expansion or rewriting after a failed observation. If the local card
exclusion or any whole-query AST guard is not implemented, the unchanged original must
remain ineligible; do not report a different simplified request as its repair.
