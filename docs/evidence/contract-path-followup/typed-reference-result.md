# Typed provenance in compact relation selection

## Independent public red

`test_context_typed_references.py` uses the frozen PreferenceEditor / PreferenceApi
sources and query 4 from the independently frozen query protocol. Public learn and
context retrieve a real file-to-file import. The code anchor projects a callable
location onto a file record, retaining the legitimate file ID. Before this change,
compact relation selection treated that ID as a code_symbol ID and lost the import.
A real code_symbol with the same numeric ID is a generated vault heading, not the
selected method. This is a missing correct relation, NOT an observed invented edge.
The unit collision checks additionally guard against wrong-type relation admission.

## Scope and compatibility

Raw anchors now carry `record_type` alongside existing `record_id`, based on the
actual wiki kind or direct/wrapped log source. No file ID is relabeled as a method
ID. Compact preserves the public `record_ids` list unchanged. Homogeneous typed
references use `record_type`; merged mixed or partly unknown provenance uses
`record_refs` as `[type, id]` pairs for the known entries. Legacy unknown IDs remain
available as provenance but cannot authorize graph relation selection.

The existing relation selector still excludes containment, uses either endpoint,
and caps output at four existing relations. No graph edge is created. All existing
range, excerpt, ranking and candidate-selection logic is unchanged. The separate
nested-class/method identity hypothesis is not fixed or claimed closed here.

## Targeted validation

48 focused tests run: 47 pass and 1 pre-existing expected failure in operation
anchor tests remains expected. This includes the independent public import red,
namespace collision controls, same-type and mixed-type merges, old unknown IDs,
direct/wrapped logs, source-operation identity, weak log owners, path quality,
primary budgets and lossless ranges. No full suite or full 231 gate was run.

Causal-profile-path remains 3/3 with strict 1500 token budget, average 1496.67.
Other original groups are reported in typed-original.json; this change is not
claimed as resolving their localization/precision failures.

Final original comparison: cross-layer, indirect-dialog, validation-stop and
shared-record each remain 1/3 (12 queries total, same four passes as baseline).
Thus there are zero newly closed original failures in this stage.
