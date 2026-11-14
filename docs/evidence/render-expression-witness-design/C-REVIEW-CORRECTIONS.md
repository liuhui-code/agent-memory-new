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
