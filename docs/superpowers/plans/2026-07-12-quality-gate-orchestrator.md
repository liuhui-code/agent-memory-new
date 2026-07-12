# Quality Gate Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one read-only `eval-quality` command that runs all available golden quality evaluations and reports one combined pass/fail gate.

**Architecture:** Keep existing eval modules as the source of truth. Add a small orchestrator module that discovers known case files from a directory, calls existing `evaluate_*` functions, and returns a bounded summary plus per-gate details. The command must skip missing case files by default and fail only when an available gate fails or a requested strict mode finds no cases.

**Tech Stack:** Python 3.9+, argparse, pathlib, JSON, existing unittest CLI tests, SQLite runtime.

---

## File Structure

- Create `tools/agent_memory_runtime/quality_gate_eval.py`
  - Owns case-file discovery, per-gate execution, combined summary, and CLI command body.
  - Imports existing eval loaders/evaluators instead of duplicating logic.
- Modify `tools/agent_memory_runtime/cli.py`
  - Add `eval-quality --cases-dir docs/eval --json`.
  - Add optional `--strict` to fail when no known case files exist.
- Modify `tools/agent_memory.py`
  - Import `eval_quality_command` and add it to the command map.
- Create `tests/test_quality_gate_eval.py`
  - Verifies missing files are skipped, available gates run, failing gates fail the combined gate, and strict mode reports no-case failure.
- Modify `docs/runtime.md`, `docs/usage-guide.md`, `skills/agent-memory-maintain/SKILL.md`, and `gitlog.md`
  - Document `eval-quality` as the default one-command gate before changing query, calibration, governance, log, or evidence behavior.

## Known Case Files

Use these filenames under `--cases-dir`:

```text
golden-retrieval.json
golden-calibration.json
golden-governance.json
golden-log-signal.json
golden-evidence-attribution.json
```

Each gate maps to the existing evaluator:

```text
retrieval -> evaluate_retrieval_cases(project, load_eval_cases(path))
calibration -> evaluate_calibration_cases(project, load_calibration_cases(path))
governance -> evaluate_governance_cases(project.project_id, load_governance_cases(path), collect_eval_governance_actions(project))
log_signal -> evaluate_log_signal_cases(load_log_signal_cases(path))
evidence_attribution -> evaluate_evidence_attribution(project, load_cases(path))
```

## Output Shape

```json
{
  "project_id": "...",
  "quality_gate": "pass",
  "summary": {
    "gate_count": 3,
    "passed_gates": 3,
    "failed_gates": 0,
    "skipped_gates": 2
  },
  "gates": [
    {
      "name": "retrieval",
      "status": "pass",
      "case_file": "docs/eval/golden-retrieval.json",
      "summary": {}
    },
    {
      "name": "calibration",
      "status": "skipped",
      "case_file": "docs/eval/golden-calibration.json",
      "reason": "case file not found"
    }
  ],
  "strict": false
}
```

## Task 1: Write Failing Tests

**Files:**
- Create: `tests/test_quality_gate_eval.py`

- [ ] **Step 1: Add CLI test helper and retrieval/log case fixtures**

```python
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = REPO_ROOT / "tools" / "agent_memory.py"


class QualityGateEvalTests(unittest.TestCase):
    def memory_home(self, project: Path) -> Path:
        return project.parent / f"memory-home-{project.name}"

    def run_memory(self, project: Path, *args: str, memory_home: Optional[Path] = None) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(RUNTIME), *args, "--project", str(project)]
        command.extend(["--memory-home", str(memory_home or self.memory_home(project))])
        return subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=True, env=os.environ.copy())
```

- [ ] **Step 2: Add passing orchestration test**

```python
    def test_eval_quality_runs_available_gates_and_skips_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            cases_dir = root / "eval"
            project.mkdir()
            cases_dir.mkdir()
            self.run_memory(project, "update", "--type", "semantic", "--fact", "ArkTS route diagnosis checks router.pushUrl.", "--source", "test")
            (cases_dir / "golden-retrieval.json").write_text(json.dumps([
                {
                    "name": "route-anchor",
                    "query": "ArkTS route diagnosis",
                    "expected": [{"type": "semantic_facts", "text": "router.pushUrl"}]
                }
            ]), encoding="utf-8")
            (cases_dir / "golden-log-signal.json").write_text(json.dumps([
                {
                    "name": "good-log",
                    "logs": ["07-11 12:00:00.100 EntryAbility E Router: event=route_failed route=pages/Profile request_id=req-1 reason=target_missing result=failed"],
                    "min_good_rate": 1.0,
                    "max_low_signal_rate": 0.0
                }
            ]), encoding="utf-8")

            result = self.run_memory(project, "eval-quality", "--cases-dir", str(cases_dir), "--json")
            data = json.loads(result.stdout)

        self.assertEqual("pass", data["quality_gate"])
        self.assertEqual(2, data["summary"]["gate_count"])
        self.assertEqual(2, data["summary"]["passed_gates"])
        self.assertEqual(3, data["summary"]["skipped_gates"])
        self.assertEqual("skipped", next(gate for gate in data["gates"] if gate["name"] == "calibration")["status"])
```

- [ ] **Step 3: Add failure aggregation test**

```python
    def test_eval_quality_fails_when_available_gate_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            cases_dir = root / "eval"
            project.mkdir()
            cases_dir.mkdir()
            (cases_dir / "golden-log-signal.json").write_text(json.dumps([
                {"name": "bad-log", "logs": ["failed"], "min_good_rate": 1.0, "max_low_signal_rate": 0.0}
            ]), encoding="utf-8")

            result = self.run_memory(project, "eval-quality", "--cases-dir", str(cases_dir), "--json")
            data = json.loads(result.stdout)

        self.assertEqual("fail", data["quality_gate"])
        self.assertEqual(1, data["summary"]["failed_gates"])
        self.assertEqual("fail", next(gate for gate in data["gates"] if gate["name"] == "log_signal")["status"])
```

- [ ] **Step 4: Add strict no-case test**

```python
    def test_eval_quality_strict_fails_when_no_cases_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            cases_dir = root / "eval"
            project.mkdir()
            cases_dir.mkdir()

            result = self.run_memory(project, "eval-quality", "--cases-dir", str(cases_dir), "--strict", "--json")
            data = json.loads(result.stdout)

        self.assertEqual("fail", data["quality_gate"])
        self.assertEqual("no_case_files", data["summary"]["failure_reason"])
```

- [ ] **Step 5: Run tests and verify failure**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_gate_eval
```

Expected: fails because `eval-quality` is not registered.

## Task 2: Implement Orchestrator

**Files:**
- Create: `tools/agent_memory_runtime/quality_gate_eval.py`
- Modify: `tools/agent_memory_runtime/cli.py`
- Modify: `tools/agent_memory.py`
- Test: `tests/test_quality_gate_eval.py`

- [ ] **Step 1: Add `quality_gate_eval.py`**

```python
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Callable

from .calibration_eval import evaluate_calibration_cases, load_calibration_cases
from .evidence_attribution import evaluate_evidence_attribution, load_cases as load_evidence_cases
from .governance_eval import collect_eval_governance_actions, evaluate_governance_cases, load_governance_cases
from .log_signal_eval import evaluate_log_signal_cases, load_log_signal_cases
from .models import Project
from .records import output
from .retrieval_eval import evaluate_retrieval_cases, load_eval_cases
from .storage import ensure_initialized, resolve_project


GateRunner = Callable[[Project, Path], dict[str, Any]]


def eval_quality_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    data = evaluate_quality_gates(project, Path(args.cases_dir), strict=bool(getattr(args, "strict", False)))
    output(data, args.json)
```

- [ ] **Step 2: Add gate registry and runners**

```python
def run_retrieval(project: Project, path: Path) -> dict[str, Any]:
    return evaluate_retrieval_cases(project, load_eval_cases(path))


def run_calibration(project: Project, path: Path) -> dict[str, Any]:
    return evaluate_calibration_cases(project, load_calibration_cases(path))


def run_governance(project: Project, path: Path) -> dict[str, Any]:
    actions = collect_eval_governance_actions(project)
    return evaluate_governance_cases(project.project_id, load_governance_cases(path), actions)


def run_log_signal(project: Project, path: Path) -> dict[str, Any]:
    data = evaluate_log_signal_cases(load_log_signal_cases(path))
    data["project_id"] = project.project_id
    return data


def run_evidence_attribution(project: Project, path: Path) -> dict[str, Any]:
    return evaluate_evidence_attribution(project, load_evidence_cases(path))


GATES: list[tuple[str, str, GateRunner]] = [
    ("retrieval", "golden-retrieval.json", run_retrieval),
    ("calibration", "golden-calibration.json", run_calibration),
    ("governance", "golden-governance.json", run_governance),
    ("log_signal", "golden-log-signal.json", run_log_signal),
    ("evidence_attribution", "golden-evidence-attribution.json", run_evidence_attribution),
]
```

- [ ] **Step 3: Add summary builder**

```python
def evaluate_quality_gates(project: Project, cases_dir: Path, strict: bool = False) -> dict[str, Any]:
    gates = [evaluate_gate(project, cases_dir, name, filename, runner) for name, filename, runner in GATES]
    passed = len([gate for gate in gates if gate["status"] == "pass"])
    failed = len([gate for gate in gates if gate["status"] == "fail"])
    skipped = len([gate for gate in gates if gate["status"] == "skipped"])
    executed = passed + failed
    no_cases_failure = strict and executed == 0
    quality_gate = "fail" if failed or no_cases_failure else "pass"
    summary: dict[str, Any] = {
        "gate_count": executed,
        "passed_gates": passed,
        "failed_gates": failed,
        "skipped_gates": skipped,
    }
    if no_cases_failure:
        summary["failure_reason"] = "no_case_files"
    return {
        "project_id": project.project_id,
        "project_path": str(project.root),
        "quality_gate": quality_gate,
        "summary": summary,
        "gates": gates,
        "cases_dir": str(cases_dir),
        "strict": strict,
    }


def evaluate_gate(project: Project, cases_dir: Path, name: str, filename: str, runner: GateRunner) -> dict[str, Any]:
    path = cases_dir / filename
    base = {"name": name, "case_file": str(path)}
    if not path.exists():
        return {**base, "status": "skipped", "reason": "case file not found"}
    try:
        data = runner(project, path)
    except SystemExit as exc:
        return {**base, "status": "fail", "reason": str(exc), "summary": {}}
    status = "pass" if data.get("quality_gate") == "pass" else "fail"
    return {
        **base,
        "status": status,
        "quality_gate": data.get("quality_gate"),
        "summary": data.get("summary") or {},
        "thresholds": data.get("thresholds") or {},
        "case_count": int((data.get("summary") or {}).get("case_count") or 0),
    }
```

- [ ] **Step 4: Wire CLI**

Add to `tools/agent_memory_runtime/cli.py` near other eval commands:

```python
    p = sub.add_parser("eval-quality")
    add_project(p)
    p.add_argument("--cases-dir", default="docs/eval")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("eval_quality_command"))
```

Add to `tools/agent_memory.py`:

```python
from agent_memory_runtime.quality_gate_eval import eval_quality_command
```

and command map:

```python
"eval_quality_command": eval_quality_command,
```

- [ ] **Step 5: Run tests and verify pass**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_gate_eval
```

Expected: 3 tests pass.

## Task 3: Documentation And Regression

**Files:**
- Modify: `docs/runtime.md`
- Modify: `docs/usage-guide.md`
- Modify: `skills/agent-memory-maintain/SKILL.md`
- Modify: `gitlog.md`

- [ ] **Step 1: Document command**

Add this guidance near existing eval sections:

```markdown
For a one-command local quality gate, run:

```bash
python tools/agent_memory.py eval-quality --project . --cases-dir docs/eval --json
```

The command skips missing golden files by default and combines all available gates into one pass/fail result. Use `--strict` in CI-like checks when the absence of all golden files should fail.
```

- [ ] **Step 2: Update maintain skill**

Add:

```markdown
When several golden case files may exist, prefer `eval-quality --cases-dir docs/eval --json` before running individual eval commands. If it fails, inspect the failing gate and then rerun the specific eval command for full case detail.
```

- [ ] **Step 3: Update gitlog**

Add a top entry with changed files, why, verification, and rollback notes.

- [ ] **Step 4: Run focused verification**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_quality_gate_eval tests.test_quality_closed_loop tests.test_retrieval_eval tests.test_log_signal_quality
PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/quality_gate_eval.py tools/agent_memory_runtime/cli.py
git diff --check
ls -1 skills
```

Expected:

- All tests pass.
- Compile exits 0.
- Diff check exits 0.
- Skill list remains exactly `agent-memory-learn`, `agent-memory-maintain`, `agent-memory-query`, `agent-memory-reflect`.

## Task 4: Commit And Push

- [ ] **Step 1: Review diff**

Run:

```bash
git status --short
git diff --stat
```

Expected: only planned files changed plus existing untracked `memory.md`.

- [ ] **Step 2: Commit**

Run:

```bash
git add docs/runtime.md docs/usage-guide.md gitlog.md skills/agent-memory-maintain/SKILL.md tools/agent_memory.py tools/agent_memory_runtime/cli.py tools/agent_memory_runtime/quality_gate_eval.py tests/test_quality_gate_eval.py docs/superpowers/plans/2026-07-12-quality-gate-orchestrator.md
git commit -m "Add quality gate orchestrator"
```

- [ ] **Step 3: Push**

Run:

```bash
git push
```

Expected: current branch pushes to GitHub.

## Self-Review

- Spec coverage: The plan covers discovery, gate execution, skip behavior, strict no-case behavior, CLI wiring, docs, regression, commit, and push.
- Placeholder scan: No TBD/TODO placeholders remain.
- Type consistency: The command uses `Project`, `Path`, `dict[str, Any]`, and existing evaluator signatures consistently.
