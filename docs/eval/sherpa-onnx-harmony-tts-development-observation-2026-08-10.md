# sherpa-onnx Harmony TTS Development Observation

## Classification

- Evidence level: `development_observation`, **repeated source family**.
- Purpose: exercise Scope-first relearning against an already-used source-backed
  HarmonyOS case and record the public handoff boundary without treating the
  replay as independent evidence.
- Not a reproduction, root-cause conclusion, source patch, Agent A/B result,
  holdout, external gate, or serving-promotion claim.

## Frozen public inputs

| Input | Frozen revision | License | Role |
| --- | --- | --- | --- |
| [k2-fsa/sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) | `v1.13.3` / `330609dab49be6ee8b30702918ca7abbbad1286a` | Apache-2.0 | exact package-source tag |
| [sherpa-onnx#3759](https://github.com/k2-fsa/sherpa-onnx/issues/3759) | accessed 2026-08-10 | public issue | source-backed symptom and log provenance |

The issue reports an actual HarmonyOS `SIGABRT` while constructing `OfflineTts`;
its stack identifies `SherpaOnnxCreateOfflineTtsOHOS`, gives a package version,
model configuration and a bounded fatal-message excerpt. The source was first
cloned for exploration, then explicitly checked out at the exact `v1.13.3` tag
before the recorded learning and query. No source, model, device, issue or pull
request was modified.

This source family and issue were already used by the 2026-08-02 cross-language
Adapter development work and the existing
`docs/eval/sherpa-onnx-harmony-log-longitudinal-cases.json` Development pack.
Consequently, this document is a contamination-explicit repeat observation: it
cannot establish generalization, authorize a serving change, evaluate an Agent,
or be counted as a second defect class.

## Scoped learning

The first Scope contained the Harmony HAR's
`harmony-os/SherpaOnnxHar/sherpa_onnx/src/main` directory: 38 files, 10 ArkTS
files, 22 C/C++ files, 358 symbols, no source log statements, and 431 static
semantic relations. The absence of source log statements is expected: the issue's
fatal log is temporary runtime evidence, which the Runtime must not ingest or
interpret as a stored diagnosis fact.

The stack's C API implementation is an explicit in-repository dependency outside
that first Scope. It was then learned through the separate,
`sherpa-onnx/c-api` Scope (eight files) without resetting the first Scope. This
is intentional scope expansion, not automatic repository-wide indexing.

## Public Context observation

The same focused query was used before and after the dependency Scope expansion:

```text
SIGABRT SherpaOnnxCreateOfflineTtsOHOS OfflineTts vocoder ai.onnx.ml opset
```

Before expansion, compact Context returned the ArkTS `OfflineTts` constructor and
the Harmony N-API `CreateOfflineTtsWrapper` excerpt. It also reported
`no_log_anchor` and did not construct a causal path.

After learning the explicit C API Scope, the unchanged public compact handoff
returned all of the following current-source evidence:

1. ArkTS callable primary: `NonStreamingTts.ets:OfflineTts.constructor`, whose
   locatable range is 149-155 and can be read under the existing source-inspection
   contract; the compact payload did not retain this body's text after allocating
   excerpt budget to more query-specific native matches.
2. Harmony N-API wrapper:
   `non-streaming-tts.cc:CreateOfflineTtsWrapper`, whose OHOS branch calls
   `SherpaOnnxCreateOfflineTtsOHOS(&c, mgr.get())`.
3. C API implementation:
   `c-api.cc:SherpaOnnxCreateOfflineTtsOHOS`, which builds the native
   `sherpa_onnx::OfflineTts` with the resource manager and converted config.

`relation_hints` remains empty and `callable_evidence.certainty` remains
`uncertain`. Those fields are correctly conservative: the learned static adapters
do not prove that the ArkTS dynamic import resolves to a particular N-API export,
nor that the public crash followed this exact path. The returned source anchors
allow the Agent to inspect that boundary and compare it with the real user log;
the Runtime does not select a path or root cause.

## Decision

This repeat observation shows only that, at this already-used source revision and
with a deliberately complete learned Scope, the current handoff supplies a
locatable ArkTS primary plus wrapper and C API source excerpts while
`relation_hints` is empty. It neither proves that an empty `relation_hints` list
is generally harmless nor establishes that additional static edge projection would
improve Agent accuracy, cost or source exploration.

No Runtime query, ranking, compact projection, code graph, log graph, causal
chain, evaluation threshold or Agent wrapper changed. The `no-go for serving
change` decision in `docs/static-relation-evidence-decision.zh-CN.md` remains in
force. Device reproduction, the referenced model binary, an independent source
family and a shared Agent investigation experiment are intentionally outside this
observation.
