# Post-hoc clean-base comparison:2 local failures closed

Executed once after independent protocol review, in detached clean a012737 worktree using its own CLI/runtime, same Python, no PYTHONPATH inheritance, fresh temporary manager/memory. Case-file SHA and all253 fixture hashes matched the candidate freeze. Only original26 case ID expanded to3 variants. Candidate was NOT rerun or modified based on this result.

| Variant | a012737 | Candidate | Base failing checks |
|---|---|---|---|
| original | fail,1283tokens | pass,1211tokens | minimum anchor precision |
| en-paraphrase | fail,1421tokens | pass,795tokens | minimum anchor precision; forbidden anchors absent |
| zh-noise | pass,878tokens | pass,928tokens | none |

Base original had CollectionPage+SharedRecordCollector+FolderCollectionLoader; base English had RecordPreview+SessionUsageCoordinator+SharedRecordCollector. Candidate returns only SharedRecordCollector in each. This supports2 net fail→pass variants for the combined candidate relative to its exact clean base, with Chinese retained. This is explicitly post-hoc attribution, not a prospective before or independent holdout.

No separate C-versus-E ablation was run. Generic original is outside E grammar, so its improvement is through ordinary retrieval under the combined producer candidate, not new positive-view authority; do not ascribe all2 to terminal E. No global scope change, no runtime aggregation proof or absence inference. Both previously frozen bare independent misses remain.
