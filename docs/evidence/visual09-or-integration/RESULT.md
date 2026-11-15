# Visual OR integration verification

Base local db4e638 (published as 57b174e). Fast-forwarded the complete reviewed
visual09 branch to 320f3e5, with no source conflict or extra runtime edits.
Gesture16 and archive25 diagnostic branches were not merged.

Integration verification after the fast-forward:
- 123 selected tests pass (30.542s), covering visual alternatives, old cleanup/
  background/source/request/selection/recall, trial hooks, output-loop source/
  request/selection/public, command source/selection and direct sink bindings.
- Frozen independent union public controls: 15/15.
- Old independent09 controls: 4/4.
- Unchanged original09 single-group Development evaluation: 3/3. The newly fixed
  English paraphrase retains both InventoryOverlayPanel and TouchOverlay. Only
  that one original variant is newly attributable; no full-score extrapolation.
- git diff --check passes. Source tree equals the reviewed worker source.

This adds one accepted local original repair, taking the cumulative ledger from
27 to 28 once this stage is recorded; it is not a new aggregate pass rate. Earlier
failed/WIP source and harness versions remain traceable in the branch history,
not separately accepted. No full, sealed/holdout or performance gate ran. No
GitHub mutation happened in this integration step; publication needs the applicable
scope/permission check. Main is unchanged.

Commands:
```
PYTHONPATH=tests:. python -m unittest test_visual_alternative test_render_source test_render_selection test_render_capability_recall test_render_request_zh test_context_trial_hooks test_output_loop_source_rebuild test_output_loop_request_rebuild test_output_loop_selection_rebuild test_output_loop_public_rebuild test_command_source_redo test_command_selection_redo test_direct_sink_binding test_direct_sink_binding_bounds
PYTHONPATH=tests:. python docs/evidence/visual09-english-alternative-20261115/run-union.py integrated
PYTHONPATH=tests:. python docs/evidence/rebuild-visual09-20261115/run.py integrated-english-or
```
