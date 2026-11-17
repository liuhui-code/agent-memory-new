# Finite auxiliary console template repair

Development-only repair; original case 13 remains open.

## Change and evidence
The validation-local lexer now recognizes one finite template argument only in an existing auxiliary console call: exactly one declared non-shadowing string parameter, printable ASCII literal chunks, one physical line, sole argument. Original source bytes, token offsets and line numbers are preserved. Shared tokenizer behavior, validation facts, authority, logging, selection, caps and budgets are unchanged. Other template positions and unsupported expressions fail closed.

An independently reviewed four-source fixture changed only its existing auxiliary log literal. Actual BEFORE scope parsing refused the backtick on line 11, offset 328, and public compact output lacked the Member validation method. The ordinary-string control returned both complete methods. Full 13-row/4-path pool identity and stored log provenance were independently checked before implementation.

The initial implementation passed the frozen 35 cells but code review found unintended template positions and token-kind leakage. That candidate was rejected and retained. The final candidate preserves full template token text, limits consumption to the approved console argument, restores strict string-only positions, and adds dedicated negative tests. The frozen 35 cells were not changed.

## Verification and limitations
- Final candidate and clean release source tree each pass the same eight-module, 74-test-method focused suite, including the frozen 35 subcases. These are not 74 plus 35 independent tests.
- AFTER performed four actual context calls total: two controls retrospectively rechecked with a corrected checker, followed by two prospectively frozen main calls. The first run stopped because the checker incorrectly required one historical renderer event instead of selecting its actual terminal dispatch parent. The original STOP is preserved; controls were not rerun. This is not four uniformly fresh prospective acceptances.
- Both raw outputs and control compact equal their original saved outputs. Main compact supplies original method IDs 2 and 13, each complete lines 3–9, with authentic source and unchanged full pool.
- Actual scope, log verification, private receipts, registry/terminal handling and facade accounting were verified. Each pair checks all 97 DB tables and observed usage/task/performance writes and sidefiles.
- Main retains both logs and all existing compact non-code information. Budget improves from 1490 to 1090 of 1500 tokens. The pre-existing global truncated=true flag is preserved; both method excerpts are untruncated. No claim that compact retains every raw metadata field is made.
- No original evaluation replay, full-suite result, external generalization, Agent parity, or original case-13 closure is claimed. Its 40-path/cap-12 and separate Deadline syntax limitations remain.

## Reproduce focused components
Run from repository root with a fresh absent cache prefix:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/template-review-new-absent-cache PYTHONPATH=tests:tools:. python3 -B -m unittest test_validation_aux_template test_validation_field_source test_validation_field_request test_validation_field_selection test_validation_no_logs test_validation_empty_aux test_validation_marker_equality test_validation_marker_lexical
```

Do not replay the consumed public acceptance runs. Complete private execution evidence and recoverable Git histories are retained separately; this publication excludes large database/trace artifacts.
