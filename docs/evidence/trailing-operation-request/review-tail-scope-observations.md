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

## 14e1eda receiver-prefix review

Additional actual direct `parse_source` observations against `14e1eda`:

| Body | Observed new tails |
|---|---|
| `foo?.bar().padding(8)` | `call:.padding`, line 4 |
| `foo.bar?.().padding(8)` | none |
| `foo[bar]().padding(8)` | none |
| `obj['Render']().padding(8)` | none |
| `new Foo().padding(8)` | `call:.padding`, line 4 |
| `new (Foo())().padding(8)` | none |
| `foo?.Column() { Text("x") }\n.padding(8)` | `call:.padding`, line 5 |
| `foo.bar().padding(8)` | none (existing same-line generic operation dedupe key protects prior detail) |
| `Text("x").width(12).padding(8)` | `call:.width`, line 4 (same-line generic key capacity is partial, not absence proof) |

The optional cases violated the declared unsupported-prefix boundary. New-constructor syntax had no frozen positive support and was requested to remain conservative/unknown. These findings are separate from the known public quoted/negative-conflict compatibility failures. Source safety improvements do not turn those public policies green.

## Final bounded review of isolated d06114c

Immutable SHA `d06114cc68f893407243a207f169a3b11321cb19` was read before and after
`tests.test_arkts_tail_operations` + `tests.test_operation_source_validity`: 16 tests
passed, with no uncommitted `tools/tests` difference. This is not a public policy pass.

One final direct source check found a remaining unsupported-prefix gap:

| Body | Observed new tails |
|---|---|
| `foo?.bar().padding(8)` | none |
| `foo[bar].render().padding(8)` | none |
| `foo[bar]\n .render()\n .padding(8)` | `call:.padding`, line 6 |
| `obj['Render']\n .factory()\n .padding(8)` | `call:.padding`, line 6 |
| `new Foo().padding(8)` | none |
| `class Inner {\n*Paint() { Text("x").padding(8) }\n}` | none |
| `if(ready){}\n.padding(8)` | none |
| `Column(){Text("x")}\n.padding(8)` | `call:.padding`, line 5 |
| `Text("x").fontSize(14)` | `call:.fontSize`, line 4 |

`expression_prefix` is reset on newline, so the computed receiver on the previous
line is no longer seen when validating `.render()`/`.factory()` as the next base.
Those are valid multiline computed access shapes but remain explicitly unsupported
by this candidate's declared contract. The isolated candidate therefore still
cannot receive an unqualified source-safety pass. No further implementation is
requested in this review; preserve this counterexample with the already failed
quoted/negative-conflict public compatibility controls and rejected candidate.
