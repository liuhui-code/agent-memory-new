# qs-arkts Module Callable Development Observation

## Classification

- Evidence level: `development_observation`.
- Purpose: validate whether a frozen public ArkTS performance report can receive
  locatable implementation context through the four existing Skills.
- This is not an external gate, holdout, quality claim, performance benchmark,
  diagnosis, or source patch.

## Frozen public inputs

| Input | Frozen revision | License | Role |
| --- | --- | --- | --- |
| [wgli-collab/qs-arkts](https://github.com/wgli-collab/qs-arkts) | `e062a6967e4a5c03da207d6e829f5f5d3ecfc165` | BSD-3-Clause | source archive |
| [qs-arkts#1](https://github.com/wgli-collab/qs-arkts/issues/1) | accessed 2026-08-09 | public issue | task prompt only |

The isolated source tree and its Memory Home are outside this repository. No
external source, issue, evaluation case, Oracle, or pull request was changed.

## Four-Skill trail

### Learn

Learning only `library/src/main/ets` indexed nine ArkTS files. The final static
index contains 66 stored symbols, 63 semantic entities, and 50 emitted
relations at the frozen revision. It has no code-log statements, which is
expected for this library scope and is not treated as missing runtime evidence.

### Query

The issue-derived query named large query strings, `hasOwnKey`, `merge`, and
`Object.keys`. The initial compact handoff selected unrelated
`SideChannel.has`: the semantic index had omitted exported module-level arrow
functions. The first proven failure layer was bounded callable-header parsing,
not Agent reasoning, a performance diagnosis, or the issue's asserted cause.

An independent Development fixture reproduced that exported arrow functions
were absent from both the code-symbol index and compact callable primary.
The shared bounded parser now recognizes direct and typed variable declarations
such as `export const f = (...) => {}` and
`export const f: (...) => T = (...) => {}`. The final frozen compact handoff
selects `utils_merge.ets:merge` as primary and supplies source anchors for
`merge`, `parseKeys`, and `hasOwnKey` within 1,383 of 1,500 target tokens.

The newly available callable evidence initially disappeared during compact
budget enforcement. A separate high-density, project-neutral composition
fixture reproduced that failure. Compact output now retains one minimal,
locatable primary while removing alternatives and explanatory metadata first.

### Reflect

No reflection was written from the public issue. The Runtime records no claim
about complexity, user-visible slowdown, or a repair. An Agent may inspect the
provided source anchors and form its own hypotheses.

### Maintain

The source scope was rebuilt with `--replace` after the parser change. The
rebuilt archive is an isolated Development artifact, not a refresh of user
memory or a serving evaluation corpus.

## Static graph follow-up

The initial graph lacked edges for imported, unqualified module calls. An
independent fixture reproduced that `parseQuery -> hasOwnKey` was absent. The
static Adapter now emits a `calls` edge only when the called identifier exactly
matches an already-resolved relative import alias. Rebuilding the frozen archive
records `merge -> hasOwnKey` and `merge -> isProtoKey`. These are static edges,
not a Runtime claim about a real execution path or issue cause.

The same formal `query_handoff.edge_matches` contains only the early candidate
relations for this query (ten `imports` edges) and does not expose either static
`calls` edge. Compact Context still returns `merge`, `parseKeys`, and `hasOwnKey`
as locatable code anchors. This is a Development observation about stage
alignment, not proof that an Agent cannot investigate from the existing anchors.
It therefore authorizes no serving projection, relation-hint change, path
construction, Agent A/B claim, or quality conclusion. The governing decision and
the required independent evidence are recorded in
`docs/static-relation-evidence-decision.zh-CN.md`.

## Verification

Focused semantic, callable, source-focus, and compact-budget regressions passed
48/48; the repaired Context sufficiency and Development reproduction coverage
passed 8/8. Full `unittest` discovery ran 945 tests with no product assertion
failure. Its two errors were the sandbox prohibition on binding `127.0.0.1` in
the Ollama runner tests; that module passed 3/3 when rerun with local loopback
permission. Compilation, diff hygiene, and the repository-wide 500-line gate
pass.
