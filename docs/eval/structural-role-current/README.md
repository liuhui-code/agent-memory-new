# Structural words versus requested ownership: current diagnostic

Development only, base a6c1d93 (published mapping 837b7ca supplied by coordinator).
No runtime, test oracle, ranking weight, intent or budget change. No full suite.
The 8-query independent protocol was committed as 328fb73 before execution.

## Current original groups

Only the two requested groups were executed, with their unchanged three variants:

- Native color: original and Chinese pass; English paraphrase fails precision (2/3).
- WebView scheme policy: English and Chinese pass; original fails precision (2/3).
  The older WebView 1/3 record is stale. No change here caused its Chinese pass;
  this checkpoint does not attribute a new original failure repair.

Both groups retain the correct target first and declared callable ranges. A crucial
reporting correction: `source_span_recall=1` is based on overlap, NOT full excerpt
containment (`context_capability_quality.span_is_observed/line_ranges_overlap`).
Raw handoff has source ranges, not full excerpt content. Current compact English
color contains target lines 2–5 (required interval 2–12); original WebView contains
lines 9–13 (required interval 10–16). These are actual truncated budgeted excerpts,
not proof of full body delivery. No evaluator change was made. This observation
does not itself establish a new extractor defect or authorize a budget increase.

## First demonstrated selection layer

`trace-cli.py` wraps three selection functions, records inputs/results and returns
those results unmodified. Each raw and compact anchor list is exactly identical to
its separate clean public CLI replay, including source content (4 comparisons).

### Native color

1. `focus_code_candidates` selects only parseNativeColor correctly.
2. `preserve_structural_boundary_neighbors` adds FacetRecord from a real imports
   graph relation. Positive query contains native, so its existing broad structural
   predicate is true. This is not missing producer identity or source span.
3. Salient supplements add MessageActionBar (file-level projection, no method/string
   provenance) and ClipboardContentReader (source match system-bar against system
   through the existing symmetric prefix matcher). The guards preserve graph,
   missing provenance and novel matches. None is silently discarded by a consumer.
4. File projection intentionally copies location fields without changing entity
   identity. It does NOT promise that a file evidence row is a callable proof.
   Copying arbitrary method evidence to it would invent that proof.

Changing native to never request structural evidence or declaring those guards
false would change existing contracts, not repair a proven dropped field. A future
work item needs an explicit operation-adjective versus requested-boundary contract;
compound-token prefix semantics is a separate issue requiring independent controls.

### WebView policy

The structural predicate is **false**. Neither schema nor policy belongs to its
marker tuple. The query's access AND navigation clause sets target scope multiple.
Method focus is correctly build in SecureDocumentBrowser. Salience retains a real
settings/string-evidence candidate and NavigationToolbar file evidence; later
projection excludes the settings path, while final anchors still include toolbar
and wrapped log caller DispatchProfileService. The latter originates in actual
code_log_matches, not a fabricated graph relation. Its retained log context is weak
lexical relevance, not proof of executable navigation ownership.

Thus no evidence supports treating both failures as the same structural keyword
bug. A producer-side scheme-operation proof versus descriptive string/log evidence
could help, but existing source-operation contracts do not certify generic policy
ownership from this wording. Do not add case words as exclusions or remove all logs.

## Independent public controls, unchanged runtime

`protocol.json` freezes five fresh TS sources and eight queries with exact owner
sets and body markers. `independent.json` contains complete raw/compact outputs.

- Native packet scaling and the same query without native both return PacketScaler
  with Math.round. This does NOT reproduce a blanket native-adjective failure.
- Explicit native import query naming both PacketScaler and UnitSpec returns only
  PacketScaler in compact: RED. Raw recalls both declarations. This is a distinct
  non-callable/interface composite projection gap, not evidence for deleting native.
- Generic scheme policy operation returns AccessTelemetry instead of GateRules:
  RED. Raw ranking already favors real logging text; localizer retains allowScheme
  as an alternative (19.5 versus log reportPolicy 31.5). No parser/source loss.
- Explicit GateRules.allowScheme, explicit SchemaRecord declaration, both GateRules
  and AccessTelemetry, and actual console error log request all pass their frozen
  source and ownership checks. No false expectation was changed to force green.

The two independent red cases are retained, not expected-failure tests or repaired
claims. The explicit interface composite gap deserves a separate narrow audit:
compare named declaration identities in raw anchors with compact callable portfolio
admission; preserve true multi-callable portfolios and unknown roles. It cannot be
used to justify single-owner pruning in the original examples.

## Existing positive contracts rechecked

20 targeted tests pass across test_structural_query_exclusions,
test_salient_source_retention and test_salient_source_public. This includes actual
raw/compact native build-import preservation, explicit multiple owners and genuine
caller/emitter log requests. Their existing oracles are unchanged. No new test was
installed, no architecture or serving change was made. Independent red observations
above remain red despite these existing positive tests passing.

Next: separately investigate explicit named non-callable composite projection;
otherwise require independently specified target-role/source-operation evidence,
not broad keyword splits, unknown-to-absent filtering or original-case tuning.
