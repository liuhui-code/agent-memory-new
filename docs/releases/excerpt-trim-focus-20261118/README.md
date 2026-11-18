# Focus-preserving excerpt trim

This local formatter correction preserves a valid source focus line when it fits the existing character limit, then adds only fitting contiguous context. A longer focus line retains a truthful partial prefix. Source coordinates use LF boundaries, not Unicode separators. Missing or invalid focus keeps the legacy character-prefix fallback; a clipped separator before an undisplayed nonempty line no longer falsely extends the end coordinate. Real empty lines remain represented.

The 64-character minimum, 240-character decrement, global budget, ranking, ownership and all unrelated metadata are unchanged. Invalid focus pointers themselves are not repaired.

## Evidence and limits

- The unchanged nonsealed Development Actual.ets lines 7–8 provide the mechanical BEFORE: its 92-character input lost the fitting focus line 8 and falsely reported that line after truncation.
- Independent V3 pure AFTER uses the same frozen input once: exact line 8, 21 characters, start/end/focus 8, truncated true. The earlier BEFORE and candidate versions/results are retained, not reclassified.
- Candidate verification passes 42 explicitly selected helper/render tests, including six new methods. Final-tree verification uses the same selection and is recorded in the release audit/commit.
- These are pure formatter/source-file checks: zero public CLI and database calls. There is no demonstrated public budget-chain reproduction, original32 closure, full-suite or CI claim.

Targeted command:

```sh
python -B -m unittest -v tests.test_excerpt_trim_focus tests.test_context_primary_budget tests.test_context_source_excerpt_quality tests.test_context_truncation_flags.SourceExcerptTruncationTests tests.test_context_truncation_flags.OutputBudgetTruncationTests
```
