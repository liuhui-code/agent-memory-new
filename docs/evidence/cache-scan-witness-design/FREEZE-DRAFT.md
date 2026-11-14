# Composable request and fixed source grammar, before execution

Review draft refining9e2bac1, not new experimental evidence. No parser whitelist of
whole original query strings, no source_operation field, no persistent graph facts.

## Request AST (complete original string only)

```
REQUEST := [OBSERVATION] HEAD [CONTEXT] [EXCLUSION] ["."]
OBSERVATION := "The " QUALITY " cache fails to remove its oldest entry after capacity is exceeded; "
QUALITY := "bounded" | "limited"
HEAD := VERB " the timestamp scan and delete implementation"
VERB := "Locate" | "Find" | "Return"
CONTEXT := " for a cache exceeding capacity"
EXCLUSION := " rather than " ROLE [" or " ROLE]
ROLE := "cache policy" | "models"
```

ASCII case insensitive terminals; exactly single spaces at boundaries, optional
final period only. No whitespace controls, quotes, extra sentences, generated-code
head, partial prefix/suffix parsing, aliases, implicit source cues or query cleanup.
Maximum400characters. Duplicate ROLE fails. AST retains observation/context/excluded
roles; negative words are never discarded to reparse a positive permission. A local
candidate exclusion uses the existing path/owner token semantics for policy/model,
not method-name tokens or global query aliases. Missing positive proof is unknown,
not absence; unsupported requests retain exact old behavior.

## Entire source file grammar supported

Only optional `export` interface ENTRY and optional `export` class OWNER, in that
order, plus lexical comments/whitespace. No imports, decorators, inheritance,
namespace, other declarations, class expressions, accessors or computed members.
Interface has exactly CLOCKFIELD:number and VALUEFIELD:string, either order;
ordinary member separators newline/semicolon; unique definition in the entire file.
Class has exactly these members in this order:
1. `private COLLECTION: Map<string, ENTRY> = new Map()` (optional semicolon).
2. `constructor(private CAPACITY: number) {}`.
3. `METHOD(KEYARG: string, VALUEARG: string): void { BODY }`.
No other mutable syntax positions or template alternatives in this trial.

BODY is exactly the fixed statements in FINITE-CONTRACT-DRAFT, in that order.
Semicolons are optional only at statement ends; braces/parentheses and commas are
required. Comments/whitespace may separate tokens, but cannot synthesize identifiers.
Object insertion has CLOCKFIELD first, VALUEFIELD second. No string interpolation,
regular expressions, unsupported lexical fallback, extra statements or nested
function scopes. Whole file and method must be fully consumed; a successful early
pattern cannot ignore executable tails. The maximum source read is2MiB, checked
both before and after the same byte read used for digest and lexical interpretation.

Capture names are ASCII identifier tokens, exact case compared. Lexical bindings
KEYARG, VALUEARG, SELECTED, MINIMUM, ITERKEY, ITERVALUE must be pairwise distinct;
none may be Map,Date,Number,undefined or reserved syntax words. COLLECTION and
CAPACITY are distinct ordinary fields; CLOCKFIELD and VALUEFIELD are distinct
members. ENTRY and OWNER are distinct and not reserved builtin names. Field/member
names can equal local value names because those are different namespaces (the
original VALUEFIELD:VALUEARG spelling may legitimately repeat `value`). No getter
or setter can masquerade as COLLECTION. Only `this.COLLECTION` is accepted; aliases,
optional/computed/member chains and another receiver remain unknown.

## Positive binding and consumer trial boundary

The method row must be complete, current typed TypeScript/ArkTS static identity,
range/key/digest/generation, same source as the unique OWNER declaration and the
parsed METHOD range. Source proof is created in the current query only. Candidate
absence/unknown is not a negative certificate. Multiple positive methods must not
be called globally unique; existing selected-candidate/size limits remain. A copied
JSON or reused/different original request cannot re-authorize selection.

Serving effect requires separate reviewer approval after independent public before:
request-bound positive method selection may preserve verified candidate body as the
requested source; it cannot remove actual log/path/graph context or relax budgets.
No rank coefficients, exact identity reasons, source_operation/certainty fields or
producer metadata may be borrowed. Initial plan is to reuse the existing private
bounded-declaration transport pattern, with an independent capability type, rather
than invent new general data-flow plumbing. Explicit unsupported/FIFO/text/unknown
requests remain unchanged. New public fields, if any, must say only static template
observation and non-exhaustive/behavior-unproven, never runtime eviction correctness.
