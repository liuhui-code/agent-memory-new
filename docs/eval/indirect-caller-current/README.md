# Explicit called-method identity in caller-owner retrieval (Development)

Base a6c1d93817dabd7d66a6777687a012ff63de8e4a; frozen public invariant/tests232df8e.
No score, source parser, relation creation, schema, scope or global uniqueness change.

## Concrete implementation bug

collect_bounded_caller_owners collected incoming symbol edges to ANY target symbol
in each of up to four seed files, even for an explicitly requested qualified method.
Independent ModalBridge.finish and ModalBridge.reset have different incoming UI
callback callers ConfirmPanel and ResetPanel. Public `Find the actual caller of
ModalBridge.finish.` selected ResetPanel.onClick as caller_owner and excluded the
real ConfirmPanel. edge-identity.json verifies real active code_symbol IDs, not
mere same-name text. SQL file-wide target membership was the first false-authority
boundary: a true edge to reset was being used as a caller of finish.

## Narrow correction and limits

Recognize explicit English `actual caller(s)`, `caller context`, or `call site(s)`
`of/for` followed by a qualified target, optionally a comma/and target list. Incidental
console.error before/after the target does not authorize or replace it. Quoted message
text, generic request forms and unrecognized target phrasing retain the old route.
Complete exact file references keep all known target symbols in that seed file.

A member reference resolves against CURRENT PROJECT code_symbols by exact owner and
symbol, LIMIT2 to distinguish a unique identity from ambiguity across ALL files, not
just the four retrieved seeds. Only a single matching symbol ID can constrain incoming
edges; unknown or duplicate identities supply no unrelated caller authority. The
existing edge target_type/source_type/project_id/valid_to/relation filters remain.
The existing four-seed/two-caller bounds remain, so this does not certify a global
unique caller or enumerate all callers. Generic file-seed behavior is unchanged.
The query-time consumer uses existing symbols/edges; no new producer/schema or index
migration is added. Existing identities must already be indexed for resolution.

## Actual public result versus stronger unsolved oracle

New public identity invariant is green: finish now has ConfirmPanel.onClick rather
than ResetPanel.onClick as caller_owner, and compact contains ConfirmPanel without
ResetPanel. It also retains ModalBridge callee context. Therefore the original strict
probe's caller-only paths equality remains FALSE. Do not label independent-before/
final strict outcomes all green or claim complete precision fixed. Both/broad caller
probe outputs still omit a true caller after downstream bounded selection; unchanged
and outside this ID-filter fix. Direct collector control verifies two REAL callers of
one method remain admitted; no global single-caller assumption was introduced.

Original indirect-dialog scenario remains1/3 before/after: original correct caller
plus salient/log supplements, paraphrase uncertain with extras, Chinese passes.
Those original requests do not provide a qualified called-method target and are not
silently reinterpreted. No original failure-count gain is claimed.

## Validation

Eight new tests cover public wrong-method caller replacement, explicit method vs
complete file, two requested member targets, two actual callers, unknown member,
unrecalled duplicate definition (actual indexed public fixture), no graph relation,
real log request, incidental qualified context, declaration/literal non-targets.
Final32 related tests:31 pass and1 previously expected weak-log failure. Suites:
test_caller_target_identity, test_query_caller_ownership,
test_context_typed_references, test_weak_log_owner_admission,
test_query_graph_neighbors, test_exact_symbol_boundary.

The first parser candidate failed sentence-final punctuation; the corrected target
scanner accepts the terminal period. Early seed-local ambiguity was strengthened to
project-wide bounded lookup before acceptance. Initial failed logs remain alongside
final ones. Tests use unchanged required identities; no original evaluator/oracle is
modified. Runtime186 lines, fingerprints/compile/diff checks pass. No full aggregate,
new holdout or remote write. Final read-only review found no remaining blockers.
