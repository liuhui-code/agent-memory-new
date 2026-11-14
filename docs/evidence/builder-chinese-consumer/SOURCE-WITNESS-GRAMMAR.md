# Source witness proposal v2 (pending joint freeze)

This refines 5bcdd88 after review. No implementation or new run. Coordinator accepts
same-chain direct calls as a sufficient, not necessary, static source witness for
a generic request to set the named properties. No runtime/value/unique-owner or
other-source absence claim follows. The original request need not say same-chain.

## Exact range and grammar

Use the current valid produced Builder row with full identity, generation, range
and same-read byte digest. Whole-file callback_mask_lines must succeed. Resolve
named_callable_header at the recorded declaration start, require exact name and
body_start, then locate its matching closing brace with a mixed-delimiter stack.
Do not use the first brace (parameter/return-type braces can precede the body).
The body close must match the recorded method end; extra executable text in the
recorded range is unsupported. Unsupported/missing header or range gives unknown.

Within the resulting body, the proposed masked-token grammar is:

    body       := WS* chain (separator chain)* WS* ';'? WS*
    chain      := IDENT WS* arguments WS* dsl_body? suffix*
    suffix     := WS* '.' WS* IDENT WS* arguments
    arguments  := balanced '(' ... ')'
    dsl_body   := balanced '{' ... '}'
    separator  := WS* ';' WS* | WS_WITH_AT_LEAST_ONE_NEWLINE
    IDENT      := [A-Za-z_$][A-Za-z0-9_$]* except reserved statement keywords

Parse the chain's full suffix run before recognizing a newline separator:
`Column()\n.padding(1)` is one chain. `Foo()Bar()` is not two chains. A semicolon
terminates a chain; a subsequent dot cannot be attached across it. Comments cannot
invent tokens or method boundaries. Empty bodies and chains lacking all requested
suffixes yield no positive witness. No concatenation across two chains.

Reserved top-level head words are ECMAScript control/declaration/operator forms,
including if/else/for/while/do/switch/case/default/try/catch/finally/with/function/
class/return/throw/new/delete/void/typeof/instanceof/in/of/yield/await/import/export/
const/let/var/break/continue/debugger/super/this. The final implementation must
freeze the actual set before tests; no source/project/API name blacklist.

All delimiters in arguments and the optional DSL body must balance. Their nested
contents are opaque for this witness and cannot contribute modifiers. This is not
a complete parser or semantic validation of those contents. Lexical unknowns from
the existing full-file mask still block the whole file. Extra top-level syntax
(assignment, optional/computed/member-prefixed base, return, control block,
function declaration, arithmetic, etc.) makes the whole method unknown. No loose
scan may recover an eligible-looking suffix after such syntax.

Only direct suffix IDENT spellings, preserving exact case, contribute to a chain's
set. Arguments are not property-value evidence. Calls in arguments/nested DSL,
callbacks or delegated methods are never joined into the set.

Correction to v1 delegation wording: `helper().padding(1).backgroundColor(x)` has
both direct suffixes and can be a positive syntactic witness. No receiver resolution
is claimed, so the name helper cannot be blacklisted. `helper()` alone and a Builder
that merely calls another Builder cannot inherit that other method's modifiers.
Likewise a bare identifier head is not proof of an ArkUI constructor identity.

## Limits and transport

Keep current 2 MiB bounded source reading and existing selected-candidate/source
caps. Do not raise any output or source-operation budget. A single bounded scan
may inspect the complete file/range; if an added explicit scan limit is necessary,
freeze it before before/after and make exhaustion unknown (not prefix success).
No per-line 8 / per-callable 16 generic-operation store is used or expanded.

Bind request AST, exact requested spelling set, same-read digest/range/source key,
and consumed members to a local private proof; invalidation/copies fail closed.
No static fact is written into old source_operation or generic mechanism fields.
A source witness cannot override original-query negatives or graph/path/log/identity
protections. Matching multiple known declarations preserves them within existing
capacity, otherwise use unchanged fallback; never pick the first matching Builder.

## Prospective source control matrix

- Positive different-family Column padding+backgroundColor; Row padding+width is
  not a witness for the pair. Exact case preserved.
- Two qualifying Builder methods, including same-file methods, both retained.
- Pair split across separate chains, nested DSL/callback, argument expression or
  another delegated Builder: no combined witness.
- helper().padding().backgroundColor() positive syntax; helper() delegation only
  no witness. Do not claim either resolves to the framework.
- Comment/string modifier mentions not counted; comment newline handling tested.
- Foo()Bar() rejected; Foo();Bar() valid separate chains; modifier across newline
  belongs to its base; modifier after semicolon rejected.
- Wrong method header/range/digest/generation, stale/old-index role, copied/private
  proof mutation, and unsupported lexical file: no new authority.
- Bare/control/arrow/function closing before dot, optional/computed receivers
  including multiline forms, return/assignment/member prefix/new: unknown.
- Method parameter or return-type braces cannot replace true body_start.
- Full-range coverage and existing output-cap exhaustion preserve old output.

Independent fixture bytes and actual public requests will be frozen separately
only after joint grammar review; none of these rows is a claimed test result.
