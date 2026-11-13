# Read-only first-loss addendum for the official documentation observation

Parent explicitly authorized tracing the fixed public request further. No new
query/source variant or scoring change was made. Original protocol and public-before
are untouched. first-loss-audit and branch-audit add return/line tracing only.

Confirmed stages:
1. Public static relation endpoints are code_file6 (TodoListComponent)→code_symbol10
   (ThingComponent), for both passes_property and renders_component. Child component
   range4–45, property thing line5 and build18–44 match extracted bytes. Parent
   child invocation line15 passes the actual iteration item. These are not guessed
   same-name/neighbor relations or a fabricated causal certificate.
2. resolve_candidates yields child at19.55 with graph_relation:passes_property,
   correct symbol ID and range. A second lower imports projection exists too.
3. relation_diverse_neighbors(MAX_GRAPH_NEIGHBORS=2) retains the child alongside
   viewmodel/ThingViewModel.updateTask at37.312 (imports). Thus the two-neighbor cap
   is NOT the first loss. collect_graph_neighbor_matches returns the child.
4. focus_code_candidates returns focused=False and keeps the child. No structural
   or salient narrowing removes it at this step.
5. diverse_code_matches weak-graph branch is the first actual removal. The line
   trace reaches query_code_selection.py110 and then111 (continue), with:
   index12, limit5, seed_score70.5, child score19.55, selected_count4,
   weak_graph_neighbor=True, reserved_graph_lane=False. The child is below half
   the seed score (35.25), so it is discarded rather than deferred. Final slot is
   filled from other deferred direct evidence; child never reaches compact.

This is the explicit existing weak-graph selection policy, not a missing-edge,
range/ID corruption, graph-resolution or MAX_GRAPH_NEIGHBORS implementation bug.
The reserved component-flow position rule does not apply at index12 and does not
currently exempt weak relations. Existing tests intentionally suppress unsupported
or graph-only noise; no inspected contract promises unconditional retention for
all passes_property relations. The natural task does request both source roles,
but the runtime has no demonstrated binding certificate that this graph candidate
is that requested second role. Lowering the threshold or exempting every property
edge would change policy and risk unrelated neighbors. No safe narrow serving fix
has been established by this read-only stage.

Do not count this as an improvement of the original cross-preview case or reuse it
as proof of its different both-strong-endpoints provenance suppression condition.
Full public/return trace: first-loss-public.json and first-loss-raw-trace.json.
Exact branch locals: branch-raw-trace.json, child_diversity_branch entries.
