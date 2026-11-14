# Independent tail-operation scope review observations

These are direct `parse_source` observations, not public query or original-case runs.
The reviewer did not edit candidate code. Each body below was wrapped unchanged as:

```text
@Component
export struct Control {
 build() {
<BODY>
 }
}
```

`parse_source(SimpleNamespace(root=Path('/tmp')), Path('/tmp/Control.ets'), source.encode(), 'ArkTS', True)` was invoked in the candidate checkout. Only mechanisms whose detail starts `call:.` are shown. The source was supplied as bytes, not read from an invented on-disk project. This records the actual earlier console observations; the initial candidate was subsequently corrected.

## Initial uncommitted candidate

Base `873f698850770331214a014ee269936c94ff87f9`.
`arkts_tail_operations.py` SHA-256: `6b877c58248c9cb0c368d7800c05568b98d6c72aa6da4d4ea24a147e427d52f2`.

| Body | Observed new tails |
|---|---|
| `if (ready) { Text("x") }\n .padding(8)` | `call:.padding`, line 5 |
| `if (ready).padding(8)` | `call:.padding`, line 4 |
| `const callback = () => { Text("x") }\n .padding(8)` | `call:.padding`, line 5 |
| `function nested() { Text("x") }\n .padding(8)` | `call:.padding`, line 5 |
| `{ Text("x") }\n .padding(8)` | `call:.padding`, line 5 |
| `Column() { Text("x") }\n .padding(8)` | `call:.padding`, line 5 |
| `Text("x").padding(8)` | `call:.padding`, line 4 |
| `Text("x")?.padding(8)` | none |

The first five are not known completed-expression/ArkTS-construction bases; they exposed a false-positive eligibility path. The DSL and ordinary-call controls remain intended positives; optional syntax remains unsupported.

Second initial probe: each following nested body contains `Text("x").padding(8)` on its second line.

| Nested body header | Existing callable identities | Observed new tails |
|---|---|---|
| `function Paint() { ... }` | only `Control.build` 3–7 | `call:.padding`, line 5, assigned to outer `symbol:436625de1683b12696da4abc` |
| `function* Paint() { ... }` | only `Control.build` 3–7 | same |
| `function paint() { ... }` | only `Control.build` 3–7 | none |
| `const thing = function Paint() { ... }` | only `Control.build` 3–7 | `call:.padding`, line 5, outer |
| `class Inner {\nPaint() {\nText("x").padding(8)\n}\n}` | `Control.build` 3–9 and `Inner.Paint` 5–7 | none |
| `const obj = {\nPaint() {\nText("x").padding(8)\n}\n}` | `Control.build` 3–9 and `obj.Paint` 5–7 | none |

This proved uppercase alone was not construction qualification and that the existing callable inventory did not cover all nested declarations.

## Completed-base revision, committed as b98052f

The revised `completed_call_base` rejected the earlier uppercase function and if-block-tail probes, while the `Column(){...}.padding` positive remained. The following additional direct observations still exposed unknown nested-class scope:

| Body | Existing callable identities | Observed new tails |
|---|---|---|
| `class Inner {\n*Paint() {\nText("x").padding(8)\n}\n}` | only `Control.build` 3–9 | `call:.padding`, line 6, outer |
| `class Inner {\nget Paint() {\nText("x").padding(8)\n}\n}` | only `Control.build` 3–9 | `call:.padding`, line 6, outer |
| `class Inner extends Factory() {\n*Paint() {\nText("x").padding(8)\n}\n}` | only `Control.build` 3–9 | `call:.padding`, line 6, outer |

These are review counterexamples, not extra acceptance successes. Unknown nested blocks must not acquire outer-method ownership merely because a nested head is uppercase and the existing callable parser did not recognize it. Consumer permission remains outside this review and was not changed.
