# Typed field aliases: exact static module/class/method identity

Original freeze92bbae2 at17ad3ae; implementation base0f0beb6 with unchanged freeze
cherry-picked as e859bfb. See BEFORE.md and REVIEW-HISTORY.md for the exact original,
supplemental and candidate-counterexample history. No first-try success claim.

## Actual producer/consumer defect

A field declared LocalStore after `import {ActualStore as LocalStore}` generated
LocalStore.read rather than ActualStore.read. With two same-module read methods,
the unique fallback produced no edge; if the imported class lacked read but another
class had it, the fallback produced a real wrong typed edge. Fresh public list and
context evidence, not helper-only inference, demonstrated both cases.

## Accepted conservative subset

Reuse existing named-import alias metadata, but do not borrow the bare-function
alias proof. New field alias relations require a known unique module-top-level
class/component, a verified direct field declaration with exactly a bare alias
type, and an explicit root this.field access in a straight-line own callable body.
Strict masking must succeed. Composite/qualified/generic types, duplicated imports
or owners, generic owner headers, local type declarations, explicit this parameters,
static methods, nested scopes, unsupported syntax and any full-file arrow do not
receive new alias authority. Complete()[]{} prefix state, not brace depth alone,
proves the accepted top-level subset. This does not parse arbitrary TypeScript.

Calls and awaits share the same cached accepted field bindings and strict masked
source. Both carry a distinct aliased-typed-field detail. The consumer only accepts
an exact unique (module path,qualified class.method) target for these relations;
missing/ambiguous/overloaded qualified targets never fall back to another class or
module by method name. Nonalias paths retain their existing behavior. Unsupported
alias guesses may disappear, but that is unknown, not proof no call can occur.

The relation is a STATIC DECLARED-TYPE relation, not proof of the runtime object,
value flow, receiver mutation, dispatch order, exclusivity or causality. Reassigning
a field does not make this patch a runtime-target analyzer. No schema is introduced.

## Bounded work and compatibility

Private context construction caches full-file lexical evidence once and direct
owner proof once. Callable processing consults that cache and scans only its own
body; no alias/no accepted field returns before scanning. A formal scan-count test
with12 methods checks one file scan plus12 body scans, and no-alias performs zero
new scans. Context extraction preserves existing field/state/import maps. The old
field wrapper still returns whole legacy input on unknown; the NEW alias authority
consumes only verified non-None evidence. semantic_ecma remains474 lines, leaving
space for the separately integrated lexical-import stage.

## Verification

-64 focused tests pass,0 failures/errors/expected failures, including public typed
  alias targets/unknowns, named function aliases, field ownership, semantic indexing,
  typed references, callable headers/body/scan cost and caller ownership.
- Public positive target paths,qualified identities,symbol keys,digests and exact
  callable ranges are asserted. Same class name in another module binds that module
  only. Calls and awaits agree. Existing direct-type positive controls survive.
- Candidate failures for explicit this, outer generic functions and generic-arrow
  class expressions are preserved rather than relabeled as original defects.
  Independent read-only final review reran the new tests and generic-arrow control.
- Independently tested SAME source/memory from0f0beb6: before5 typed relations,
  code-only5, normal learn-path merge6. Four missing correct calls/awaits are added;
  three wrong MissingConsumer/MissingAwaitConsumer relations are removed; original
  direct-type controls stay correct. No migration or automatic refresh is claimed.
- An initial activation assertion incorrectly required SQLite numeric IDs to remain
  stable. Normal merge rebuilds IDs. The failed probe/diagnostic are retained;
  corrected checks join typed IDs WITHIN each snapshot and verify stable semantic
  key,path,qualified identity,range,digest across snapshots. No identity loss found.
- Original shared-record group remains1/3 before/after; no original231 precision
  gain and no full-suite claim. This is a verified static identity bug fix only.
