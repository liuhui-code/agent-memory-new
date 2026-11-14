# Pre-implementation representation revision

The dc68e4f grammar text requiring typed field identity is preserved. Actual b105 before has only class/method/State rows; ordinary repository fields do not have independent rows. That prerequisite was not met as written. Independent review permits this explicit representation revision before implementation, without changing source/request/oracle or role semantics:

- Bind ordinary fields by current typed complete class identity and same-read whole-class parsing, not fabricated field IDs. The witness retains field name, declared type spelling, declaration character offsets/line range, enclosing class range and the source digest. Fully consume the class and reject duplicate declarations, local shadows or collisions.
- Method rows still require current key/digest/owner/qualified_name/range consistency with the source witness.
- @State still requires its actual current row key/digest/qualified_name `Class.field` and precise range. Actual State owner_name is empty; do not demand or synthesize that field.
- Additional implementation-before negative controls: same spelling under a different owner, duplicate field name, parameter/local shadowing field, missing field declaration, and State row with mismatched source range/qualified name/digest. Unknown means old output, not absence.

This is a new local source-evidence representation for the already frozen role contract, not proof that the old field-row prerequisite passed. No producer/schema changes. The original independent three focus-loss reds remain the input evidence; no rerun to manufacture a favorable before.
