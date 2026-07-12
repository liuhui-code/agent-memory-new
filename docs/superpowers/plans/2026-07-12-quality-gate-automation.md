# Quality Gate Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `eval-quality` easier to use in scripts and review loops by adding per-gate rerun commands and an optional failing exit code.

**Architecture:** Keep `eval-quality` as a thin orchestrator over existing eval modules. Add command metadata to each gate result, include summary lists for passed/failed/skipped gates, and add `--fail-on-fail` so callers can opt into a non-zero exit when the combined gate fails.

**Tech Stack:** Python 3.9+, argparse, existing JSON CLI output, unittest.

---

## Tasks

### Task 1: Tests

**Files:**
- Modify: `tests/test_quality_gate_eval.py`

- [ ] Add assertions that each gate result includes `next_command_template`.
- [ ] Add assertions that failed gates are listed in `summary.failed_gate_names`.
- [ ] Add a test that runs `eval-quality --fail-on-fail --json` against a failing log-signal case and verifies process exit code is `1` while JSON output remains parseable.

### Task 2: Implementation

**Files:**
- Modify: `tools/agent_memory_runtime/quality_gate_eval.py`
- Modify: `tools/agent_memory_runtime/cli.py`

- [ ] Extend gate metadata from `(name, filename, runner)` to include the specific eval command name.
- [ ] Add `next_command_template` to every pass/fail/skipped gate:

```bash
python tools/agent_memory.py <eval-command> --project . --cases <case-file> --json
```

- [ ] Add summary lists:

```json
{
  "passed_gate_names": ["retrieval"],
  "failed_gate_names": ["log_signal"],
  "skipped_gate_names": ["governance"]
}
```

- [ ] Add parser flag:

```python
p.add_argument("--fail-on-fail", action="store_true")
```

- [ ] In `eval_quality_command`, emit JSON first, then raise `SystemExit(1)` only when `--fail-on-fail` is set and `quality_gate == "fail"`.

### Task 3: Docs

**Files:**
- Modify: `docs/runtime.md`
- Modify: `docs/usage-guide.md`
- Modify: `skills/agent-memory-maintain/SKILL.md`
- Modify: `gitlog.md`

- [ ] Document `--fail-on-fail` for automation.
- [ ] Document `next_command_template` as the preferred drill-down path after a failed aggregate gate.

### Task 4: Verification And Commit

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_gate_eval tests.test_eval_case_seed
PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory_runtime/quality_gate_eval.py tools/agent_memory_runtime/cli.py
git diff --check
ls -1 skills
```

Expected:

- Tests pass.
- Compile exits 0.
- Diff check exits 0.
- The official skill list remains exactly four skills.

Commit:

```bash
git add docs/runtime.md docs/usage-guide.md gitlog.md skills/agent-memory-maintain/SKILL.md tools/agent_memory_runtime/quality_gate_eval.py tools/agent_memory_runtime/cli.py tests/test_quality_gate_eval.py docs/superpowers/plans/2026-07-12-quality-gate-automation.md
git commit -m "Add quality gate automation hints"
git push
```

## Self-Review

- Spec coverage: rerun command templates, summary names, fail-on-fail behavior, docs, tests, and verification are covered.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: gate metadata and output names match existing `eval-quality` structure.
