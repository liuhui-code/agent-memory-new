# Frozen finite contract, before candidate implementation

Request: ASCII case-insensitive `(Locate|Find|Return) executable eviction scan ownership when a cache remains above its entry limit` plus optional final period, maximum 240 characters. Entire original string consumed without stripping, positive-query projection, arbitrary observation slots or negative-tail removal. Only this bounded request is newly supported, not timestamp, FIFO or literal targets.

Source: optional export, class OWNER, exactly one private FIELD:Map<string, ENTRY>=new Map() field, and exactly one METHOD(LIMIT:number):void with this entire body:
```
if(this.FIELD.size <= LIMIT){return}
let SELECTED:string|undefined=undefined
let MINIMUM=Number.MAX_SAFE_INTEGER
for(const [KEY,VALUE] of this.FIELD){
 if(VALUE.MEMBER < MINIMUM){
  MINIMUM=VALUE.MEMBER
  SELECTED=KEY
 }
}
if(SELECTED !== undefined){this.FIELD.delete(SELECTED)}
```
Comments and ordinary whitespace allowed between tokens. Optional semicolons only at statement endings; absent separator requires newline or closing brace. Required punctuation/keywords/operators fixed. No strings, templates, imports, inheritance, other classes/methods/fields, declarations, types or executable tails. ENTRY is an unresolved type spelling only, no type or timestamp claim. Capture identifiers ASCII, reserved/builtin bindings refused. LIMIT/SELECTED/MINIMUM/KEY/VALUE pairwise distinct; OWNER/ENTRY distinct; FIELD/METHOD distinct. Matching `.MEMBER` spelling does not prove getter purity. Whole-file consumption, balanced syntax, exact current owner and method ranges and source digest required.

Consumer: inspect only files already in baseline wiki_matches (max 12); no new recall/query/weight/threshold. Unknown syntax skipped without absence assertion. Positive methods form a non-exhaustive set (1–3 receipts, otherwise atomic baseline fallback). No uniqueness claim; existing FIFO and unknown competitors remain possible. Private request-bound view carries complete method snapshots only within existing budget; no metadata marker grants access. Protect path/log/graph/identity context. Source identity and current generation bind owner/method/file. Copy/deepcopy/JSON and request/view/receipt mutations cannot authorize view.

Frozen acceptance: unchanged original query1 returns complete ExpiryStore.trim and no descriptive-only primary; original query2 remains unchanged/unsupported; exact FIFO and text controls unchanged. Independent renamings preserve syntax matching; 2/3 positives all retained if existing excerpt budget fits, overflow all fallback. Wrong update/key/comparison/receiver/delete, candidate overwrite, missing guard, split/nested/additional statements, string/comment fake, unknown lexical syntax/ASI, reserved aliases all reject. Stale digest, wrong owner/range/generation, conflicting duplicate rows, path escape, protected context, copied/mutated/replayed transport and tiny budget fallback. No full suite or original-group gain claim.
