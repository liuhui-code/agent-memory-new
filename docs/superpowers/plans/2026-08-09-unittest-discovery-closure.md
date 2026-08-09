# Unittest Discovery Closure

> Status: complete for repository-controlled work; real campaign intake remains external.

## Goal

Make the repository's declared `unittest` command discover every repository test and make
the hierarchical-localization metric contract executable. This is test-infrastructure work;
it does not alter Runtime retrieval, ranking, graphs, logs, experiences, Skills, or evaluation
outcomes.

## Evidence

- Repository plans and prior verification use `PYTHONPYCACHEPREFIX=.pycache python3 -m unittest discover tests`.
- `tests/test_context_hierarchical_metrics.py` used pytest-style top-level functions, which
  standard `unittest` silently skipped.
- Its expected `informational` value was stale. The current serving-stage contract returns
  `informational_serving_stage`, documented in `docs/system-capability-evaluation.md` and
  persisted in reviewed Context result artifacts.
- Executing the formerly skipped summary test also exposed a controlled evaluator defect:
  a sparse audit with no `code_files` or `code_symbols` entry raised before it could report
  an empty candidate list. Sparse audit inputs are valid for historical or partial observations.
- `docs/real-campaign-readiness-audit.zh-CN.md` remains `no-go` without a user-provided
  Campaign Source Manifest. No fixture, historical repository or generated task can replace it.

## Completed Plan

1. [x] Confirm `unittest` is the repository standard and inventory top-level `test_*` functions.
2. [x] Convert the one skipped module to `unittest.TestCase` methods.
3. [x] Correct the stale status assertion only after confirming the serving-stage contract and
   stored results use `informational_serving_stage`.
4. [x] Make `summarize_context` treat absent candidate tables as empty, preserving its
   existing observation semantics without changing retrieval or scoring.
5. [x] Add an AST-based contract test that rejects future uncollected top-level test functions.
6. [x] Run focused metrics/localizer/Context tests, full `unittest` discovery, compilation,
   diff and 500-line gates.

## Standard Command

```bash
PYTHONPYCACHEPREFIX=/tmp/agent-memory-pyc python3 -m unittest discover tests
```

The test count and failures from this command are the local Python regression baseline.
Environment-restricted loopback tests must be reported separately; they must not be relabeled
as product failures or silently ignored.

## Verification

- Focused hierarchical metric and discovery-contract coverage passes 5/5.
- Adjacent hierarchical localization, Context supply, candidate-loss and localizer-loss
  coverage passes 19/19.
- Standard discovery runs 933 tests. The sandbox reports only two loopback bind errors in
  `tests.test_ollama_benchmark_runner`; no product assertion fails. With local loopback
  permission, that module passes 3/3.
- Python compilation, whitespace validation and the 500-line gate pass.

## External Dependency

The next capability-efficacy phase is blocked on a Campaign Source Manifest containing the
active project, task-stream owner, task-arrival boundary, task-start Memory Home, verification
rule, external raw-task retention policy, stop rule, revision policy and Agent source-sharing
authorization. Until it exists, do not create a real cohort, run a new A/B campaign, or change
serving retrieval based on the current Development fixtures.
