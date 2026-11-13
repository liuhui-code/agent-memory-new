# Bounded official-source discovery (design material only)

One bounded search pass used OpenHarmony's official repositories/documentation,
not original-case vocabulary or retrieval scores. No repository clone, dependency
installation, runtime test, fixture execution, or production edit was performed.
No upstream source files or media were copied into this repository.

## Accessible, revision-bound documentation candidate

Official document: OpenHarmony MVVM V1, section Sample Code.
https://github.com/openharmony/docs/blob/f41b9345badd47c7ab0c263344cd7f4b5a549afb/en/application-dev/ui/state-management/arkts-mvvm.md

Verified repository revision: f41b9345badd47c7ab0c263344cd7f4b5a549afb.
Verified document blob: 7b4cfa80997fa337480ecd137cbe0146799a3fbb.
The connector returned the same blob when fetching this exact revision as master.
The docs repository LICENSE identifies Creative Commons Attribution4.0 International:
https://github.com/openharmony/docs/blob/master/LICENSE
Observed license blob:2f244ac814036ecd9ba9f69782e89ce6b1dca9eb.
Do not automatically apply the application repository's Apache license to this
separate documentation snapshot.

Two separately named file examples have a genuine direct relation:
- views/TodoListComponent.ets: document lines864–892, imports ThingComponent;
  its list iteration passes each item into that child at line881.
- views/ThingComponent.ets: document lines790–842, accepts an ObjectLink model;
  its build renders task name at821, font size24 at822 and completed-task
  strikethrough immediately after, plus completion icon handling.

This is static source-visible object argument passing and child rendering, not a
claim of tested device execution, simple scalar @Prop, or inferred runtime causality.
Both have ViewModel dependencies, resources and builder callbacks. A later
extraction would need explicit documented-file provenance and dependency boundaries;
these are not a self-contained two-file runnable app.

Proposed natural query (not executed/frozen as a benchmark):
“Locate both the to-do list's item-component wiring and the child code that styles
completed task names.”
Expected evidence would be the parent's import/list-child invocation and the
child's ObjectLink/build text/decoration. There is no reported production defect,
no red claim and no expectation that the score/provenance threshold is crossed.
A single-child styling request would be a separate non-expansion control.

## Native sample paths not independently retrievable in this pass

The official document explicitly links each example to:
https://gitcode.com/openharmony/applications_app_samples/blob/master/code/DocsSample/ArkUISample/ArktsMvvmSample/entry/src/main/ets/views/TodoListComponent.ets
https://gitcode.com/openharmony/applications_app_samples/blob/master/code/DocsSample/ArkUISample/ArktsMvvmSample/entry/src/main/ets/views/ThingComponent.ets

Both GitCode source pages were inaccessible through the read tool. The corresponding
paths in the official GitHub applications_app_samples mirror returned404. Therefore
no native sample file revision/content identity was verified; the revision above
belongs ONLY to docs. The sample repository LICENSE was readable and distinguishes
Apache2.0 code from separately licensed testing/media materials, but it does not
resolve this missing native file identity. No media were fetched or republished.

Conclusion: a revision-bound OFFICIAL DOCUMENTATION example is available as design
material. A native repository source-pair snapshot remains unverified. Stop this
bounded discovery here; do not silently present document snippets as fetched native
files, a holdout, or an accepted fix. No further search or public tests were run.
