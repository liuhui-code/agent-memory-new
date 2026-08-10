# ArkTS Cross-Library Resource Development Observation

## Classification

- Evidence level: `development_observation`.
- Purpose: exercise the four fixed Skills against one current, licensed public
  ArkTS language-service issue and record both useful context and the boundary
  on an implementation candidate.
- This is not a cohort, holdout, external gate, Agent A/B result, promotion, or
  evidence that Agent Memory improves an external project.
- No Agent Memory Runtime retrieval, ranking, graph, schema, or Skill behavior
  changed.

## Frozen public inputs

| Input | Frozen revision | License | Role |
| --- | --- | --- | --- |
| [ohosvscode/arkTS](https://github.com/ohosvscode/arkTS) | `25fda87a6677c3e92f3b7ed41adbab82c3847929` (`next`) | MIT | language-service source |
| [openharmony/third_party_typescript](https://gitcode.com/openharmony/third_party_typescript) | `0b986adba8feeb3180a31e9231a19eaa52dbc49b` | Apache-2.0 | locked `ohos-typescript` submodule |
| [arkTS#265](https://github.com/ohosvscode/arkTS/issues/265) | accessed 2026-08-09 | public issue | task prompt only |

The issue remains open at access time. The frozen source and isolated staging
copy are outside this repository and were not committed or submitted upstream.

## Four-Skill trail

### Learn

An isolated archive learned `packages/language-service`: 58 files, 1,037
symbols, 291 semantic entities, 249 emitted relations, and two code-log
statements. Learning completed at the frozen source revision. It reported
unresolved await targets but no semantic-adapter error.

### Query

The natural-language Context query was broad: it selected a test-file code
anchor and reported limited anchor diversity. A second query naming
`resource-provider`, `getArktsDiagnostics`, `sys`, and `app` localized the
source correctly to `getArktsDiagnostics` (lines 591-668 in the frozen source).

The initial focused Context output selected an unrelated `Resource.getProduct`
callable as its primary callable despite listing `getArktsDiagnostics` as a
much higher-scoring alternative. At that point this was a Development
observation of callable projection only; the independent reproduction and
public-handoff verification described below were required before changing
serving behavior.

### Reflect

The isolated archive receives a bounded correction reflection after this
observation. Its rule is: reject a cross-module resolver that infers visibility
from project co-location when the project model has not proved the dependency
edge.

### Maintain

`maintain-health --verify-graph-quality` is run only against the isolated
archive. Its output is a local data-health observation, not a performance or
promotion claim.

## Source-backed behavior and staging result

The public issue's attached editor image shows a library-qualified expression
of the form `$r('[basic].string.spectrum')`. In the frozen implementation,
diagnostics, definition, completion, and media-hover logic each branch on
`sys` or `app`; diagnostics therefore emit `INVALID_RESOURCE_SCOPE` for that
form.

An isolated staging copy added a 37-line resource-scope parser and a minimal
cross-module fixture containing an `entry` module with a declared local
`basic` dependency. The focused regression first failed with
`INVALID_RESOURCE_SCOPE`. The candidate then passed both of these assertions:

1. the valid `[basic].string.spectrum` reference returns no diagnostic;
2. completion at `[basic].string.` returns
   `[basic].string.spectrum`.

The affected language-service package built successfully and its complete local
test run passed: 3 files and 7 tests. Vite emitted a pre-existing warning that
the frozen `ohos-typescript/lib/typescript.js.map` file is absent; this did not
alter the zero exit status. A direct project-detector `findAll()` attempt did
not produce a result within 30 seconds and was manually stopped, so the staging
test used the language-service's typed project/product contract rather than
claiming detector integration verification.

## Rejected candidate and decision

The staging implementation is **rejected**, not an external patch. Its resolver
can enumerate same-project modules by module name, but the current
`Project`/`Module` abstraction does not expose a resolved Library dependency
graph. It could therefore accept a `[module]` resource from a sibling module
that the current module has not declared as a dependency. Treating workspace
co-location as accessibility would be an unsound semantic change.

The source file that owns the existing provider is already larger than the
repository's 500-line architectural rule (915 lines after staging). Extending
that provider further would make the boundary less maintainable. Neither fact
is evidence of an Agent Memory defect; together they explain why the candidate
must not be submitted.

## Next evidence before an external patch

1. Extend the upstream project model with a dependency-graph port that exposes
   resolved local/HAR Library edges, including product/target compatibility.
2. Build an independent fixture with one declared and one undeclared sibling
   Library. Verify diagnostics, definition, completion, and hover accept only
   the declared edge.
3. Extract scope parsing and owner resolution behind that port before changing
   all feature providers, keeping each new source file below 500 lines.
4. Re-run package tests and a project-detector integration test that completes
   under a bounded timeout. Device or Hvigor verification is unnecessary for a
   language-service-only behavior claim, but no result may be inferred from its
   absence.
5. Separately reproduce the callable-primary projection observation in an
   editable Agent Memory Development fixture and the public `query_handoff`
   before considering a Runtime change.

## Callable identity follow-up

The callable-primary observation was reproduced in two independent places:
an editable, project-neutral Development fixture and the frozen archive's
actual public `query_handoff`. In each, the focused query contained the natural
word `resource` and the file stem `resource-provider`; the generic owner name
`Resource` was therefore incorrectly treated as an explicit owner identity.

The first failing serving layer was the callable owner-identity predicate,
before the final callable ordering. The correction accepts an owner identity
only when it is a distinctive, standalone compound identifier. A generic
single-word owner such as `Resource` cannot gain the owner-identity promotion
from ordinary query prose. This preserves exact promotion for identifiers such
as `FullPlayerPagerSpec` without treating lexical relevance as identity.

The Development fixture now makes `DiagnosticProviderImpl.getArktsDiagnostics`
the compact `query_handoff` primary for the same query. The frozen ArkTS archive
also now selects that callable as primary (score 96), with its source range
617-621. The Runtime still provides retrieval and graph context only: it did
not infer an issue cause, read transient logs, or make a diagnosis decision.

Focused identity and callable/context regressions passed 45/45. The complete
suite completed 940 tests; its only two errors were the sandbox's prohibition
on binding `127.0.0.1` in the isolated Ollama runner tests. Those three runner
tests passed 3/3 when rerun with local loopback permission. This is not an
external quality or promotion claim, and it does not validate the rejected
cross-library staging candidate.

No external source patch, pull request, evaluation Oracle, or external quality
claim was created from this observation.
