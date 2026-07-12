# Quality Gate Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `eval-quality --gate <name>` so agents can run only selected aggregate quality gates while preserving the same output shape.

**Architecture:** Keep the existing gate registry and filter it before execution. Summary counts, skipped gates, selected gate names, and delta comparisons should apply only to selected gates. Do not add storage, schema, or new eval logic.

**Tech Stack:** Python 3.9+, argparse, existing JSON eval output, unittest.

---

## Tasks

### Task 1: Tests

**Files:**
- Modify: `tests/test_quality_gate_eval.py`

- [ ] Add a test with both retrieval and log-signal cases, then run `eval-quality --gate log_signal --json`.
- [ ] Assert only `log_signal` appears in `gates`.
- [ ] Assert `summary.selected_gate_names == ["log_signal"]`.
- [ ] Assert retrieval is not counted as passed/skipped.

### Task 2: Implementation

**Files:**
- Modify: `tools/agent_memory_runtime/quality_gate_eval.py`
- Modify: `tools/agent_memory_runtime/cli.py`

- [ ] Add `--gate` as a repeatable CLI option.
- [ ] Add `GATE_NAMES`.
- [ ] Add `selected_gate_names(values)` validation.
- [ ] Extend `evaluate_quality_gates(project, cases_dir, strict=False, gates=None)`.
- [ ] Filter the registry before evaluating.
- [ ] Add `selected_gate_names` to summary and top-level output.
- [ ] Filter previous failed gate names to selected gates when computing `quality_gate_delta`.

### Task 3: Docs And Verification

**Files:**
- Modify: `docs/runtime.md`
- Modify: `docs/usage-guide.md`
- Modify: `skills/agent-memory-maintain/SKILL.md`
- Modify: `gitlog.md`

- [ ] Document:

```bash
python tools/agent_memory.py eval-quality --project . --cases-dir docs/eval --gate log_signal --json
```

- [ ] Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_gate_eval tests.test_eval_case_seed
PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory_runtime/quality_gate_eval.py tools/agent_memory_runtime/cli.py
git diff --check
ls -1 skills
```

Expected: tests pass, compile exits 0, diff check exits 0, official skill list remains four.

Commit:

```bash
git add docs/runtime.md docs/usage-guide.md gitlog.md skills/agent-memory-maintain/SKILL.md tools/agent_memory_runtime/quality_gate_eval.py tools/agent_memory_runtime/cli.py tests/test_quality_gate_eval.py docs/superpowers/plans/2026-07-12-quality-gate-filter.md
git commit -m "Add quality gate filter"
git push
```

## Self-Review

- Spec coverage: selected gate execution, output, delta filtering, docs, tests, and verification are covered.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: gate names match the existing registry names.
