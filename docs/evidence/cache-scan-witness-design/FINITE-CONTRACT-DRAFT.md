# Finite template and full request proposal (not approved or executed)

This is a deliberately supported source shape, not a general value-flow analyzer.
No schema/index changes, source_operation roles or global query aliases proposed.
Unknown syntax or any unmatched executable statement remains unknown. Original
query bytes/oracles and the old denied literal gate remain unchanged.

## Full request surface proposed for independent review

Only these complete strings (case-insensitive English, optional final period):
- `Locate the timestamp scan and delete implementation for a cache exceeding capacity.`
- `The bounded cache fails to remove its oldest entry after capacity is exceeded; return the timestamp scan and delete implementation rather than cache policy or models.`

No partial suffix extraction, historical-prefix stripping, generated-program/head
rewrite, generic eviction admission, explicit identifier redirection, or arbitrary
negative-tail removal. The second is a complete task sentence, not a promise that
Runtime proves the observed failure. Its rather-than clause remains part of the
AST, with existing local policy/model exclusion applied rather than lost.

This does not cover generic executable/FIFO queries or Chinese: preserve old outputs.
The old ExpiryStore.trim query cannot gain template qualification without the newly
required explicit clock write; its missing Entry definition is still unknown.

## Entire method template proposal

Names below are captured identifiers, not literal project or case names. Whitespace,
ordinary comments and optional statement semicolons may vary only where grammar
allows. Balanced lexical/body checks and current typed method identity are required.

```
METHOD(KEYARG: string, VALUEARG: string): void {
  this.COLLECTION.set(KEYARG, { CLOCKFIELD: Date.now(), VALUEFIELD: VALUEARG })
  if (this.COLLECTION.size <= this.CAPACITY) { return }
  let SELECTED: string | undefined = undefined
  let MINIMUM: number = Number.MAX_SAFE_INTEGER
  for (const [ITERKEY, ITERVALUE] of this.COLLECTION) {
    if (ITERVALUE.CLOCKFIELD < MINIMUM) {
      MINIMUM = ITERVALUE.CLOCKFIELD
      SELECTED = ITERKEY
    }
  }
  if (SELECTED !== undefined) { this.COLLECTION.delete(SELECTED) }
}
```

Type annotation omission or alternate extrema/collection APIs are NOT silently
accepted; decide them before freeze if needed. The admitted source must declare
this.COLLECTION as a Map<string, ENTRY> field and this.CAPACITY as a number field
or constructor parameter property. ENTRY is a same-file declared interface with
CLOCKFIELD:number and VALUEFIELD:string. Interface and member names must resolve
without ambiguity to current source declarations. Import/global/local shadowing
of Map, Date or Number is unknown; nested scope/control/callback is unknown.
All captured variable names and receiver/member comparisons must agree exactly.
A token named timestamp elsewhere cannot satisfy this chain. No code before or
after the shown statements, alternate writes, changed selected key, changed minimum,
wrong comparison, wrong receiver, key alias, nested closure or cross-method bridge
may be admitted. Signature/header effects and unsupported decorators also refuse.

## Exact positive conclusion and its limits

The CURRENT complete source has an explicit Date.now call whose result is written
into the same member subsequently read by the shown comparison; that same branch
assigns the iterated key to SELECTED, and the guarded delete uses that SELECTED on
the same syntactic declared collection receiver. This is positive static template
evidence for the requested clock-field scan/delete implementation.

It does NOT prove all existing cache values came from that write, immutable Map or
Date builtins at runtime, temporal correctness, real global oldest entry, handling
all numeric values, eventual capacity compliance, call reachability or LRU. Missing
old-entry provenance is not absence. No candidate is declared globally unique.
If these limits cannot satisfy the request's positive source requirement without
claiming algorithm correctness, reject the consumer rather than drop timestamp.

## Prospective strong controls

Clock written to an unused member; comparison reads a different member; numeric
member with no Date.now write; different collection for set/iteration/delete;
SELECTED reassigned after scan; MINIMUM or key update outside matching branch;
reversed comparison; deleting ITERKEY outside its scope; unresolved/shadowed ENTRY,
Map, Date or Number; arbitrary calls, nested callback and split methods; string or
comment spelling the template; genuine FIFO; explicit descriptive monitor; generated
code/HTML artifact; mixed/historical/unknown requests. All to freeze before running.
