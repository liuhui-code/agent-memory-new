# Proposed finite role-spelling contract (pre-execution)

This narrows READ-FIRST's unresolved semantic gate. It does not cover generic `repository selection and synchronization trigger` requests, Chinese requests, or arbitrary two-action requests. No runtime implementation or experiment is approved by this file.

## Complete request

ASCII case-insensitive, whitespace separated, total <=400 characters:

```
[The NP remains after NP; ] VERB the registry branch and store sync owners[.]
VERB := Return | Locate | Find
NP := WORD | WORD WORD | WORD WORD WORD
WORD := [A-Za-z][A-Za-z-]*
```

NP is contextual observation only. Reject NP tokens `and or not no only except exclude without return locate find source generated quoted literal both`, quotation characters and all punctuation other than internal hyphens. No stripping unknown prefix/tail, negative or mixed output clause. No implicit request-language translation or global alias. Parse the exact original request, not a cleaned retrieval query. Head-only and the optional observation form are composable, not a list of original query strings.

## Declared role spelling, not runtime semantics

Use case-sensitive current source declaration identity and existing identifier component splitting (case-insensitive component comparison). The registry role requires an independent `registry` component of the owner class name. The store role requires independent `store` in the owner and `sync` in the method. No substring, plural stemming, file-path-only role, Remote/Demo/Device list, or type-name inference. `RegistryStore` may carry both roles; `RegistryLike` is a component match but still requires the full local source witness. `Preregistry` is not.

The owner may reference unresolved external types and zero-argument constructors. Those are source spellings only. The original DeviceRepository, RemoteDeviceRepository and DemoDeviceRepository have no definitions in the fixed fixture: this contract does not establish their implementations, actual repository interface, connectivity, data freshness or injection between owners.

## Bounded source grammar

Each contributing file must be fully consumed as: optional ordinary named relative imports, followed by exactly one exported or unexported plain class with a simple identifier, no extends/implements/generics/accessors/static blocks/constructor. Comments are lexically masked, string literals only in approved positions; unknown template/regex/slash or malformed delimiter returns unknown. Fields and complete supported methods may appear in any order; duplicate field/method identifiers or collisions fail closed. Max four fields and two methods, source <=2 MiB and each method <=32768 characters.

Fields are limited to (a) `private FIELD: TYPE[ = new CTOR()]` and (b) `@State STATE: TYPE[] = []`, optional semicolons. TYPE/CTOR are simple identifiers, not semantic certificates. Local variable, parameter, FIELD and STATE names must be distinct; method identifiers cannot collide with fields or the constructor name.

Selection method:
```
METHOD(FLAG: boolean): void {
  if (FLAG) { this.FIELD = new LEFT() }
  else { this.FIELD = new RIGHT() }
}
```
Exactly these two branches; same declared plain FIELD; distinct LEFT/RIGHT source identifiers; no return, alias, side statement, alternate receiver, nested scope or reassignment. No method-name requirement beyond unique identity.

Synchronization method:
```
async SYNC(): Promise<void> {
  const LOCAL = await this.FIELD.READ()
  this.STATE = LOCAL
}
```
SYNC must contain the independent sync component. FIELD is declared plain field, STATE the same owner's declared @State field; LOCAL is the exact unique binding. No parameters, extra arguments, assignment chain, aliases, control flow, cross scope or additional statements. READ is a simple spelling, not proof of external execution behavior.

The parser attests these finite complete source shapes only. No general def-use/CFG, new persisted relationship, producer/source_operation field, runtime sync or registry-to-store relationship is claimed.

## Consumption proposal (subject to before evidence)

Only consider current typed class/method/field identities representing already admitted raw source anchors, with same-read digest/range binding. No adding candidates, raising source-range or portfolio caps, creating new source ranges, or replacing other owners. Require exactly one fully qualifying declaration identity for each role in the bounded admitted pool; one owner can satisfy both. Multiple positive identities for either role return to old output, never choose by domain terms. Unknown source is not negative evidence.

Preserve existing selected ranges only if normal callable focus actually removes a required role. Keep every normal focused anchor and its order. Select original representatives by full identity/range, not path alone; if no safe representative or final original 1500 budget cannot retain all required existing ranges without changing protected code/log/path/relation content, use the complete old output. No authority on ordinary dict/JSON copies, changed original request or changed anchor snapshots. Graph/log/path protection is not relaxed. All claims are non-exhaustive within the admitted pool, not global uniqueness.

## Required frozen controls before execution

Independent naturally named registry/store pair; two legal request forms; head-only. Same owner named `...RegistryStore` with both methods. Two registry positives and two store positives (ambiguity). Names without independent role components. Different branch fields, same constructor both branches, discarded/reassigned await local, non-State target, wrong receiver, missing field, duplicate or shadowed declaration, inherited/unknown class body. Single/quoted/generated/mixed/negative requests retain old output. Explicit source identifiers retain old behavior. Old/stale/partial identities, unmatched range, protected graph/log/path and budget insufficiency fall back. No fixture runs until source/query/oracles and exact representative guard are frozen and reviewed.
