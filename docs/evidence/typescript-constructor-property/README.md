# TypeScript readonly constructor parameter-property graph

## Development evidence

On baseline `a79313be`, a small TypeScript audio editor learned
`MixdownPanel.exportCurrentMix` and `WavExport.saveMix`, but its public
`list --type memory-edge` lacked both `calls` and `awaits` between them.
The receiver was `constructor(private readonly wav: WavExport) {}`; the
method uses `await this.wav.saveMix('current')`. Source, query and expected
outcomes were frozen before the experiment. No actual encoder was executed.

| Receiver source | Before | After |
| --- | --- | --- |
| Readonly constructor parameter property | neither edge | both edges |
| Equivalent explicit type field and constructor assignment | both edges | both edges |
| Plain constructor parameter with a separate object-backed field | neither edge | neither edge |

The new edges link the exact indexed methods at call-site line 8, carry the
source digest and remain static evidence, not a runtime call observation.
The frozen ordinary context request still returns the same anchors and no
compact relation hints. This is a source-index correction, not a default
context or Case 39 repair; Case 39 was not rerun.

## Scope and existing archives

Reuse the existing method-header parser and strict rooted field-receiver
checks. Admission requires a verified top-level TypeScript class, a single
constructor, a simple explicitly typed readonly parameter property, and an
unambiguous named relative import. Unsupported parameter syntax, visible
type or field collisions, explicit instance writes and computed receiver
access do not get the new edges. Bare, static or nested-body receiver
spellings do not gain an edge. Legacy field and alias behavior is unchanged.

No database migration or auto-reindex was added. In the same existing
archive, installing/running newer code did not rewrite old edges on read.
Running the ordinary `learn-path --path .` command afterward, on unchanged
sources, added both static edges. The installer recursively copies the
runtime package, including the new module.

## Regression

Run from the repository root:

```sh
python -m unittest tests.test_ts_parameter_properties tests.test_typed_import_alias \
  tests.test_semantic_index tests.test_semantic_physical_lines \
  tests.test_ecma_callable_headers tests.test_ecma_callable_scan_cost \
  tests.test_ecma_callable_body_ranges
python tools/check_line_limits.py
python -m compileall -q tools/agent_memory_runtime
```

50 focused tests passed; line-limit and compile checks passed. No aggregate
capability gate or sealed evaluation was run.
