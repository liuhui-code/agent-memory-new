The failed-load implementation is `ThumbnailLoader.load()` in `ThumbnailLoader.ts:2–8`. It awaits `fetch(path)` and catches failures, logging `THUMBNAIL_READ_FAILED: load failed`. It does not reset a ready flag.

“Failed operation” refers to the earlier load, not the proposed document replacement. `DocumentSession.swapDocument` is a separate replacement-operation candidate; its implementation was not inspected.

Evidence and budget:
- Used the supplied current-worktree excerpt, `ThumbnailLoader.ts:1–9`, code-symbol record `7`.
- Used `callable_evidence.alternatives` to distinguish the replacement candidate and `relation_hints` for the recorded log relationship.
- Read the specified skill, evidence policy, candidate code-understanding reference, and supplied JSON with `exec_command`.
- Additional source reads: 0; searches: 0; expansion rounds: 0. One source file inspected through the supplied excerpt, within the 7-file budget. No excerpt rereads, Runtime queries, or changes.

Unknown: no runtime log establishes which invocation actually failed, and the relationship between that load and document replacement is unverified. This locates the failed-load implementation, not a verified cause or fix for the ready-flag behavior.
