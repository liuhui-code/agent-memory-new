# Report path identity

Only report-path list normalization in load_test_evidence preserves case while retaining whitespace stripping, empty filtering, stable exact deduplication and MAX_REPORTS20. No path resolution/casefold/alias equivalence. Existing provenance, command and legacy semantics unchanged. Both design-verify and design-progress consume this shared helper. Mixed-case original tests and frozen public controls are required, not just a lowercase workspace workaround.
