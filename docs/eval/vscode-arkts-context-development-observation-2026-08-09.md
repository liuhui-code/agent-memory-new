# vscode-arkts Context Development Observation

## Classification

- Evidence level: `development_observation`.
- Purpose: validate the existing Learn and Context evidence handoff on a fresh,
  public TypeScript/ArkTS-adjacent source family.
- Not a prospective cohort, external gate, holdout, Agent A/B result, diagnosis,
  or serving-promotion claim.
- The repository's only open public issue was reviewed and excluded: it reports a
  README link redirect, not a source-backed runtime diagnosis task.

## Frozen public inputs

| Input | Frozen revision | License | Role |
| --- | --- | --- |
| [FadingLight9291117/vscode-arkts](https://github.com/FadingLight9291117/vscode-arkts) | `468eaa7bac2980435247b5e85e5a584fa378c1ab` | MIT | source archive |
| [vscode-arkts#1](https://github.com/FadingLight9291117/vscode-arkts/issues/1) | accessed 2026-08-09 | public issue | reviewed and excluded |

The repository was cloned shallowly into an isolated temporary directory. Its
working tree was clean before learning; no source, issue, or pull request was
modified. The archive and Memory Home are outside this repository.

## Learn observation

Learning `src` indexed 18 TypeScript files, 246 symbols, six code-log statements,
and 404 active graph edges. The TypeScript static Adapter reported 146 emitted
semantic relations, including 24 `calls`, and 63 unresolved relations. The latter
are retained as bounded extraction gaps; they are not filled with inferred runtime
paths.

## Context observation

The source-derived query was:

```text
ArkTS language server failed to start MCP tools remain available
```

The compact public handoff returned:

- a direct code-log anchor in `src/extension.ts:startLanguageClient` with the
  template `ArkTS language server failed to start:`;
- a bounded callable primary for `startLanguageClient`, with source range 33-122;
- two path candidates and `ready_for_agent_inspection` sufficiency;
- `limited_code_anchor_diversity` as an explicit evidence gap.

It returned no `relation_hints` for this query. That is not treated as a failure:
the Agent can inspect the primary source range and compare an actual temporary log
before deciding whether language-server startup, MCP availability, or another
boundary is relevant. Runtime did not parse a user log, select a cause, or claim
that either path executed.

## Decision

This fresh source family establishes only that the current four-Skill runtime can
index a small TypeScript/ArkTS-adjacent codebase and supply locatable static log
evidence without fabricating relationships. It does not provide a source-backed
task Oracle and therefore cannot test whether primary-adjacent static edge evidence
improves Agent investigation.

The prospective cohort remains no-go. A public issue stream is not a substitute for
a user-controlled future task source, continuity owner, task-start Memory snapshot,
objective verification plan, raw-task custody policy, and source-sharing approval.
Those requirements remain in `docs/real-campaign-readiness-audit.zh-CN.md` and
`docs/static-relation-evidence-decision.zh-CN.md`.
