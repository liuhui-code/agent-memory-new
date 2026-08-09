# Lynx Markdown Harmony Dogfooding Observation

## Classification

- Evidence level: `development_observation`
- Purpose: exercise the four existing Skills on one current public ArkTS-adjacent
  task, then record the evidence boundary.
- Not a cohort, holdout, external gate, Agent A/B result, or serving promotion.
- No Agent Memory Runtime retrieval, ranking, graph, or schema behavior changed.

## Frozen public inputs

| Input | Frozen revision | License | Role |
| --- | --- | --- | --- |
| [integrating-lynx-demo-projects](https://github.com/lynx-family/integrating-lynx-demo-projects) | `f8230ca6aa1c9e629e30272971d0c03450b13e8e` | Apache-2.0 | Harmony host source |
| [lynx-examples](https://github.com/lynx-family/lynx-examples) | `99f4660b8720a905e1b11c2f96d2fd08ccd878df` | Apache-2.0 | Markdown bundle source |
| [lynx-examples#360](https://github.com/lynx-family/lynx-examples/issues/360) | accessed 2026-08-09 | public issue | Task prompt only |

The issue text is not copied into the archive, SQLite, or this document. The
source trees were cloned into an isolated temporary directory and were not
modified. This report retains only public URLs, revisions, commands, and bounded
technical observations.

## Four-Skill trail

### Learn

An isolated archive learned `harmony/HarmonyEmptyProject` from the integration
repository and `examples/markdown` from the example repository. The combined
index contained 54 files, 155 symbols, 17 code-log statements, and 253 edges.
All learned source digests were current at the time of the observation.

### Query

The first compact Context query used the natural-language symptom and produced a
broad host lifecycle anchor with `limited_code_anchor_diversity`; it was not a
diagnosis. A second, artifact-oriented query narrowed the relevant evidence to
the host template fetcher and the Markdown example configuration. Both outputs
stayed within the compact Context budget. The Runtime returned evidence only;
the candidate below is an Agent interpretation of current source and build
output.

### Reflect

The isolated archive stored a `correction_experience` with partial outcome:

> Do not treat a host bundle-name mismatch as a confirmed renderer defect without
> a built artifact and a Harmony runtime observation.

The reusable lesson is to verify generated artifact names and host resource URLs
before proposing a cross-repository deployment patch.

### Maintain

`maintain-health` reported current source state and expected low manual-semantic
coverage immediately after mechanical learning. It also reported a Context P95 of
8118.888 ms from only two samples. That is an informational observation, not a
performance regression or tuning justification; no serving change was made.

## Reproducible artifact observation

The frozen Markdown project declares multi-entry output as
`[name].[platform].bundle`. Its `basic` entry therefore produces
`dist/basic.lynx.bundle` for the Lynx environment. A clean locked build completed
with Node `v26.3.0` and pnpm `11.13.0`:

```text
pnpm install --frozen-lockfile
pnpm --filter @lynx-example/markdown build
```

The build listed 25 `*.lynx.bundle` files, including `basic.lynx.bundle`, and no
new `main.lynx.bundle`. The frozen Harmony host already contains a 1.1 MB default
`rawfile/main.lynx.bundle`; `Index.ets` selects that name and
`ExampleTemplateResourceFetcher.ets` passes it to
`resourceManager.getRawFileContent`.

This establishes a **candidate deployment contract mismatch**: the public steps
say to copy a Markdown bundle to the host, but do not state that the chosen named
output must replace the host's fixed `main.lynx.bundle` (or that the host URL must
change). Leaving the default rawfile untouched would continue to load the default
bundle rather than the Markdown artifact. It does not establish that this is the
reporter's deployment, the only issue mechanism, or a device-side rendering root
cause.

## Design decision

Keep `HarmonyEmptyProject` generic: it has one stable bootstrap resource name and
should not be changed to hard-code a Markdown example entry. The deployment
adapter maps the explicitly selected example artifact to that existing bootstrap
name. This is a task-local resource replacement contract, not a Runtime feature,
source-graph inference, or claim about the application's rendering behavior.

## Staging patch and verification

The frozen host was copied to a separate temporary staging clone. The only change
was a task-local deployment patch:

```text
examples/markdown/dist/basic.lynx.bundle
  -> HarmonyEmptyProject/entry/src/main/resources/rawfile/main.lynx.bundle
```

The staged target and generated `basic.lynx.bundle` both have SHA-256
`5f4d9797be25f0f2e58b6eb385705df4de558ac1fef6ec549642f5212eb4c093`.
This verifies the artifact-to-host resource mapping and preserves the generic
host URL. The staging clone has no other tracked changes and no external pull
request was created.

Hvigor task discovery was attempted using the installed DevEco Studio. The
frozen project targets `6.0.0(20)`, while the local SDK reports API 24 only, so
Hvigor stopped with `SDK component missing` before task enumeration or HAP
assembly. `hdc list targets` also reported no reachable device. Therefore HAP
packaging, installation, and rendered Markdown verification are not claimed.

## Intentionally unresolved evidence

The observation does not include a HarmonyOS device/emulator run, a HAP built
against the project's API 20 SDK, a raw-resource packaging manifest, runtime
logs, or a reporter-provided bundle-mapping procedure. Those missing facts
prevent all of the following claims:

- the public issue is reproduced;
- the candidate is the root cause;
- changing the host URL, renaming a bundle, or copying a resource is the correct
  patch;
- Agent Memory improved task quality or latency.

No external pull request, source patch, case Oracle, evaluation pack, or Runtime
change was created.

## Next evidence before any patch

1. Freeze the exact Harmony raw-resource placement and the intended Markdown
   entry selected by the reproducer.
2. Install the target API 20 SDK component, build the staged host HAP, and verify
   that its packaged rawfile digest remains the staged Markdown digest.
3. Run that artifact on a HarmonyOS device or emulator and retain a bounded,
   source-backed observation of the resource lookup/rendering result.
4. Reproduce the same failure in an independent Development fixture and in the
   public Context handoff before considering a general retrieval change.
5. Only then evaluate a repository patch, with its build and device verification
   reported separately from Memory-system behavior.
