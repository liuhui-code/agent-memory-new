# Complete finite render expression proposal, before execution

This is a local same-read source witness; no existing calls edge is authority.
These are all supported syntax positions proposed, not examples to extend after a run.

## Request AST

```
REQUEST := [OBSERVATION] HEAD [EXCLUSION] ["."]
OBSERVATION := NP " details still display markup tags. "
HEAD := VERB " the UI rendering cleanup owner"
VERB := "Locate" | "Find" | "Return"
EXCLUSION := " rather than the " NP " data entity"
NP := WORD | WORD " " WORD | WORD " " WORD " " WORD
```

Case-insensitive ASCII terminals, one literal space at boundaries,400char maximum;
WORD is alphabetic. No quotes, unknown sentences, commands, mixed output, arbitrary
stripped prefix or trailing clause. NP cannot contain reserved operators
and/or/not/only/except/exclude/return/find/locate/source/code/render/generate/caller/
wrapper. The optional observation is retained as context, not proof of runtime
failure, ownership or domain identity. Exclusion retains the complete NP and data-
entity target; it is never removed to mint a positive request. Neither NP supplies
a global domain alias or permission to select a similarly named non-component.

Only the exact supported UI-template source witness may supply positive qualification.
Two observed positive components cannot be forced into one using the observation
noun. Current ordinary explicit-name/graph/log/path protections remain; unsupported
entity/text/generated/mixed requests use old behavior. This is non-exhaustive source
selection, not proof every other candidate is non-cleanup code. If preserving these
limits prevents the original precision oracle, report that result rather than add
a domain ranking rule.

## Current owner/build/helper binding

One current typed ArkTS component/struct owner with unique build and HELPER methods
under the same source digest/generation. Build and helper ranges must be fully
contained in that owner; source key, method/header identity and actual text agree.
HELPER is a zero-parameter synchronous method with explicit string return type,
not a getter, setter, overload, constructor, inherited or assigned-field callable.
No same-named field or second method can make resolution ambiguous. No external
receiver, alias, parameter/default effects, intermediate variable, second helper
or callback is admitted. HELPER cannot be build/Text/Column/Row/RegExp or a reserved
syntax name. Same-read source bytes are capped2MiB before and after read; method
slices<=32768characters; exceeding limits is unknown, never partial certification.

## Entire build method body

```
BUILD := "build()" [": void"] "{" CONTAINER "() {" TEXT (SEPARATOR TEXT){0,7} "}" "}"
CONTAINER := "Column" | "Row"
TEXT := "Text(" ARG ")" [";"]
ARG := THIS_FIELD | STRING_LITERAL | "this." HELPER "()"
THIS_FIELD := "this." IDENT ["." IDENT]
```

Exactly one Text argument is this.HELPER(); other Text arguments are fields or
literal labels, not calls or assignments. Real newline or semicolon separates
Text statements. No suffix modifiers, nested container/callback/control blocks,
spread/second arguments, optional/computed calls, concatenation or executable tails.
The whole build body must be consumed, not a substring found inside another scope.
Text/Column/Row bindings cannot be shadowed by a same-file import, declaration,
parameter, field or method. Full-file lexical unknown falls back; foreign runtime
redefinitions are outside this static claim and never proved impossible.

## Entire helper body and replacement grammar

```
HELPER := IDENT "(): string { return " BASE REPLACE{1,8} [";"] "}"
BASE := THIS_FIELD
REPLACE := ".replace(" TAG_LITERAL "," REPLACEMENT_LITERAL ")"
         | ".replace(new RegExp(" TAG_PATTERN ["," FLAGS] ")," EMPTY_LITERAL ")"
```

The return keyword and BASE must be on the same physical line (comments cannot
hide a line terminator and trigger an empty ASI return). Remaining whitespace and
comments may occur between grammar tokens, never inside identifiers. No preceding
or following executable statements, try/finally, assignments, other methods or calls.

STRING_LITERAL supports quoted single/double strings with only known escaped quote,
backslash and newline spellings; no template literals or interpolation. TAG_LITERAL
is a decoded simple tag: `<name>`, `</name>` or `<name />`, name1+ASCII letters then
letters/digits. No attributes or arbitrary angle-bracket text. REPLACEMENT_LITERAL
is empty or a single newline. TAG_PATTERN is decoded exactly `<[^>]+>` or `<[^>]*>`;
FLAGS absent, empty or `g` only. EMPTY_LITERAL is exactly empty. RegExp cannot be
shadowed by a same-file declaration/import/member/parameter. Literal regex syntax
is deliberately unsupported in this version, so no generic regexp parser is added.

This proves only the two directly nested source expressions: supported tag-shaped
replacements in the helper return and that helper call used as this Text argument.
It never proves all HTML removed, XSS safety, runtime string/Text types, invocation,
actual display, total correctness or globally unique owner.

## Mandatory source and request controls before implementation

Consumed versus discarded helper return; helper on other receiver; second Text arg;
assignment then Text(variable); callback/nested invocation; duplicate helper or field;
same helper name in another owner; two helpers; two valid owners; generated/literal
code text; unknown regex/flags; RegExp/Text shadow; return-newline ASI; stale digest;
wrong method range/owner and missing index fields; copied/mutated request proof.
Explicit helper/entity/literal/multi requests and existing graph/log/path contexts
retain original semantics. Full public before must show matched source-selection
loss; a snippet-window observation cannot substitute for that gate.
