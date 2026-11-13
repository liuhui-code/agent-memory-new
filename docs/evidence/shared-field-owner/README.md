# Existing typed field map: lexical and direct-container scope

Base80feab8. Independent public red4faa2d7. This is not a new field entity,
initializer schema, nested-member resolver or architecture promotion.

A genuine private store:RecordStore was overwritten in the existing field map by
(a) a class comment containing store:PreviewStore, and (b) a method-local object
type containing store:PreviewStore. Public init/learn/list produced actual
code_symbol→code_symbol calls edges from CommentCollector.collect and
NestedTypeCollector.collect to PreviewStore.read. These two independent pollution
forms exercise the existing field-map contract, not permission for new architecture.
DirectCollector and a real PreviewStore-typed owner are positive controls.

## Narrow change

The existing FIELD_RE and qualified target resolution remain unchanged. A helper
filters only the lines supplied to that regex. For lexical/scope input supported
by the existing strict callback mask and a balanced bracket stack, only direct
container-member lines outside parentheses/brackets are eligible. Comments/plain
strings/plain templates cannot supply field types; method-local object types and
parameters cannot overwrite class fields. Original source line numbers are not
rewritten and no source entities or ranges are widened.

Unknown slash/interpolation/unclosed/mismatched syntax returns the original whole
container field input. Existing false edges in such input remain possible; no
complete lexer or general nested-scope resolution is claimed. Multiple declarations
on one line retain the original first-field-only regex behavior, not new support.
The field map is built once per container in build_file_context, not per callable.

## Evidence and verification

- Fresh public before/after retains typed references. Tests verify exact qualified
  targets, nonempty symbol keys, source digests and source/target callable ranges.
  Both polluted calls now reach RecordStore.read; both true owner controls retain
  their original target. No numeric IDs are joined across namespaces.
-4 new tests and the related suite total52 passes,0 failures/errors/expected failures.
  Controls include two classes with same-named fields; local object type; multiline
  parameter; comments/string/plain template; fields after nested bodies; semicolon
  legacy behavior; whole-container unknown fallback against the old field map.
  Existing callable scan-cost checks pass; no new throughput guarantee is made.
- An initial related command named a nonexistent test_semantic_performance module;
  its import failure is retained in related-invalid-module.txt. Corrected actual
  headers/body/scan-cost suite is the52-pass related.txt.
- Independently tested SAME source/memory activation: before and runtime-code-only
  snapshots retain the two wrong calls; normal learn-path merge replaces just those
  targets with RecordStore.read and preserves Direct/RealPreview. No schema migration
  or automatic cleanup on code install alone is claimed. See activation.json.
- Original shared-record aggregation group remains1/3 before/after, all three
  statuses unchanged. This producer fix is NOT an original precision improvement.
  No full suite, score/query tuning, exclusion authority or causal proof added.

Read-only reviewer checked the helper/public controls and found no code blocker.
