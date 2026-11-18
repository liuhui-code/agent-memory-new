# Original37 current single-group verification

Runtime baseline remote c195b960 (local b41ca4c); no production change. The prior 2/3 record predates the finite UI dispatch-table consumer now present. Rechecked only context-command-binding-owner-precision, its unchanged original/en-paraphrase/zh-noise queries and original oracle.

Result: 3/3 pass, one stable scenario, anchor precision1.0, source span recall1.0. Compact manual observation: only BackupCommandPanel for all three; tokens936/1293/1162, no output truncation. This is current original-group verification, not a new code repair, aggregate score, external holdout or proof of runtime command causality. Hierarchical callable/range informational metrics are retained exactly; do not reinterpret them as all1.0.

All250 copied input files byte-match the original Development fixture. Governance is development/editable/project_neutral and reviewed synthetic. Case pack and expected oracle unchanged. First eval invocation omitted explicit --source and failed resolving the pack-relative path from workspace root before evaluation; failure retained. Final invocation supplied the verified copied original source directory and selected only this case ID. No full suite.

Command (paths relative to workspace root):
```
python3 -B concrete-plan-work/repo/tools/agent_memory.py eval-context-capability --project "$PWD/concrete-plan-work/command37-current/source" --memory-home "$PWD/concrete-plan-work/command37-current/seed" --source "$PWD/concrete-plan-work/command37-current/source" --cases "$PWD/concrete-plan-work/repo/docs/eval/system-capability-cases.json" --case-id context-command-binding-owner-precision --json
```

The separate nested-property identity expressiveness proposal is not implemented by this verification. It is not necessary to label this original scenario open now that its current unchanged gate passes.
