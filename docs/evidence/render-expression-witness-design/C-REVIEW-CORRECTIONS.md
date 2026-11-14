# Pre-public 0eb13ed review corrections

Independent review injected a Protected.ets anchor into the normal test fixture.
On 0eb13ed, baseline identity_match, trial identity_match, baseline graph_neighbor,
and baseline log_identity_match each still returned RenderContext and omitted that
protected source. This is a genuine implementation guard defect, not a waived
control. The corrected guard checks both complete baseline and trial handoffs for
identity, graph, log identity, log anchors and activated/wrapped path protection.
All such contexts return baseline. New tests cover both contexts for each flag.

The initial wrapper also passed the ordinary baseline mapping to miss accounting.
A successful head-only private projection could therefore count as a miss because
its baseline was empty. Accounting now receives the validated adopted view once;
the API object's public mapping still stays baseline to make lost permission safe.
Tests check the actual passed object and its nonempty selected anchors, not merely
call count. This does not change public frozen queries or negative acceptance.

42 focused tests pass after these fixes. Public after has not yet run on C.

Fixed feacb99 public13 completed but all requests fell back to the baseline:
generic remains three sources, head-only empty. This is not accepted or hidden.
ContextFacade adds path_context/source_freshness after limited_context, legitimately
invalidating the whole baseline snapshot. A narrow, explicitly reviewed enrichment
transport is required; the permission binding will not simply ignore path changes.

The separately requested capacity control exposed a real defect: a valid 1700-char
Text label made the selected build excerpt incomplete, yet selection survived.
Two/three positive-owner controls passed. The failed capacity log is retained.
A preflight compact projection now requires every positive complete method range
and exact snapshot content to fit the unchanged 1500 budget before receipt minting;
otherwise it returns whole baseline. This adds deterministic bounded projection
work, not an increased budget. Fixed44 focused tests pass after that correction.

Facade transport now validates before mutation, permits only empty inactive payload
fields with no seeds/gaps and unchanged baseline freshness, preserves the trial's
own freshness report, and repeats complete snapshot budget preflight after enrichment.
Unknown payload fields conservatively fall back; this preserves the actual existing
inactive_payload schema rather than assuming arbitrary false-activated metadata safe.
The initial new unknown-extra test failed because compact legitimately ignored that
field; the closed transport guard now explicitly rejects unknown fields. Initial
failure retained. All 46 focused tests then pass.

Successful private RenderContext accounting is deferred to final Facade selection;
ordinary baseline contexts retain their original limited_context accounting. Tests
check both final active-path fallback (empty baseline, miss) and valid inactive
transport (positive adopted view) are recorded exactly once, not earlier R state.

Independent87 review identified direct limited_context consumers in attribution and
focused evaluators which never reach Facade. Deferral is now explicit, default
False, and only the context_composition Facade wrapper requests it. Direct calls
record the adopted view once as before; Facade records only an explicitly pending
receipt and clears that pending state. Ordinary contexts keep old accounting.
New tests cover direct successful once, explicit composition deferral, final valid
Facade once and protected fallback once. All47 focused tests pass. No evaluator
full suite was run or changed.
