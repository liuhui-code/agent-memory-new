# Golden Case Seed Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe golden-case seed pack that helps projects bootstrap eval cases without making the default `eval-quality --cases-dir docs/eval` fail on generic templates.

**Architecture:** Add a small template writer command that emits editable example JSON files into a non-default directory. The default target is `docs/eval/examples`, while the active quality gate still reads `docs/eval`. This keeps templates close to the runtime but prevents unedited examples from being executed accidentally.

**Tech Stack:** Python 3.9+, argparse, pathlib, JSON, existing runtime output helper, unittest.

---

## File Structure

- Create `tools/agent_memory_runtime/eval_case_seed.py`
  - Owns template definitions and writes seed files.
  - Keeps templates static, deterministic, and editable.
- Modify `tools/agent_memory_runtime/cli.py`
  - Add `eval-seed-cases --target docs/eval/examples --json`.
  - Add `--force` to overwrite existing seed files.
- Modify `tools/agent_memory.py`
  - Import and register `eval_seed_cases_command`.
- Create `tests/test_eval_case_seed.py`
  - Verifies seed files are written under a safe default target.
  - Verifies JSON files are valid lists and contain the expected gate fixtures.
  - Verifies existing files are not overwritten without `--force`.
- Modify `docs/runtime.md`, `docs/usage-guide.md`, `skills/agent-memory-maintain/SKILL.md`, and `gitlog.md`.

## Seed Files

Write these files:

```text
golden-retrieval.json
golden-calibration.json
golden-governance.json
golden-log-signal.json
golden-evidence-attribution.json
README.md
```

Each JSON file is a valid list of example cases. Examples should use realistic ArkTS/log/memory wording, but they are not expected to pass until the project owner edits anchors to match local memory.

## Command Behavior

```bash
python tools/agent_memory.py eval-seed-cases --project . --target docs/eval/examples --json
```

Output:

```json
{
  "project_id": "...",
  "target": "docs/eval/examples",
  "written": ["..."],
  "skipped": [],
  "force": false,
  "next_steps": [
    "Edit examples so anchors match this project's memory.",
    "Copy edited files to docs/eval or run eval-quality with --cases-dir <edited-dir>."
  ]
}
```

Without `--force`, existing files are skipped. With `--force`, existing files are overwritten.

## Task 1: Write Failing Tests

**Files:**
- Create: `tests/test_eval_case_seed.py`

- [ ] **Step 1: Add CLI helper**

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


class EvalCaseSeedTests(unittest.TestCase):
    def memory_home(self, project: Path) -> Path:
        return project.parent / f"memory-home-{project.name}"

    def run_memory(self, project: Path, *args: str, memory_home: Optional[Path] = None) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(RUNTIME), *args, "--project", str(project)]
        command.extend(["--memory-home", str(memory_home or self.memory_home(project))])
        return subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=True, env=os.environ.copy())
```

- [ ] **Step 2: Add seed write test**

```python
    def test_eval_seed_cases_writes_safe_example_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            target = Path(temp_dir) / "docs" / "eval" / "examples"
            project.mkdir()

            result = self.run_memory(project, "eval-seed-cases", "--target", str(target), "--json")
            data = json.loads(result.stdout)

        self.assertEqual(str(target), data["target"])
        self.assertEqual(6, len(data["written"]))
        self.assertTrue((target / "README.md").exists())
        for name in [
            "golden-retrieval.json",
            "golden-calibration.json",
            "golden-governance.json",
            "golden-log-signal.json",
            "golden-evidence-attribution.json",
        ]:
            content = json.loads((target / name).read_text(encoding="utf-8"))
            self.assertIsInstance(content, list)
            self.assertGreaterEqual(len(content), 1)
```

- [ ] **Step 3: Add no-overwrite test**

```python
    def test_eval_seed_cases_skips_existing_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            target = Path(temp_dir) / "examples"
            project.mkdir()
            target.mkdir()
            existing = target / "golden-retrieval.json"
            existing.write_text("[{\"name\":\"custom\"}]", encoding="utf-8")

            result = self.run_memory(project, "eval-seed-cases", "--target", str(target), "--json")
            data = json.loads(result.stdout)

        self.assertIn(str(existing), data["skipped"])
        self.assertEqual([{"name": "custom"}], json.loads(existing.read_text(encoding="utf-8")))
```

- [ ] **Step 4: Add force overwrite test**

```python
    def test_eval_seed_cases_force_overwrites_existing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            target = Path(temp_dir) / "examples"
            project.mkdir()
            target.mkdir()
            existing = target / "golden-retrieval.json"
            existing.write_text("[{\"name\":\"custom\"}]", encoding="utf-8")

            result = self.run_memory(project, "eval-seed-cases", "--target", str(target), "--force", "--json")
            data = json.loads(result.stdout)

        self.assertIn(str(existing), data["written"])
        content = json.loads(existing.read_text(encoding="utf-8"))
        self.assertNotEqual([{"name": "custom"}], content)
```

- [ ] **Step 5: Run tests and verify failure**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_eval_case_seed
```

Expected: fails because `eval-seed-cases` is not registered.

## Task 2: Implement Seed Writer

**Files:**
- Create: `tools/agent_memory_runtime/eval_case_seed.py`
- Modify: `tools/agent_memory_runtime/cli.py`
- Modify: `tools/agent_memory.py`
- Test: `tests/test_eval_case_seed.py`

- [ ] **Step 1: Add static templates**

Create `SEED_FILES` with five JSON files and one README. Use `json.dumps(..., ensure_ascii=False, indent=2)` for JSON content so files are stable and readable.

- [ ] **Step 2: Add writer command**

Implement:

```python
def eval_seed_cases_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    data = write_eval_case_seed_pack(Path(args.target), force=bool(args.force))
    data["project_id"] = project.project_id
    output(data, args.json)
```

`write_eval_case_seed_pack` creates the target directory, writes missing files, skips existing files unless `force` is true, and returns `written`, `skipped`, `force`, and `next_steps`.

- [ ] **Step 3: Wire CLI**

Add:

```python
    p = sub.add_parser("eval-seed-cases")
    add_project(p)
    p.add_argument("--target", default="docs/eval/examples")
    p.add_argument("--force", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("eval_seed_cases_command"))
```

Add import and command map entry in `tools/agent_memory.py`.

- [ ] **Step 4: Run seed tests**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_eval_case_seed
```

Expected: 3 tests pass.

## Task 3: Docs And Regression

**Files:**
- Modify: `docs/runtime.md`
- Modify: `docs/usage-guide.md`
- Modify: `skills/agent-memory-maintain/SKILL.md`
- Modify: `gitlog.md`

- [ ] **Step 1: Document safe seed workflow**

Add:

```bash
python tools/agent_memory.py eval-seed-cases --project . --target docs/eval/examples --json
```

Explain that examples are not active until edited and copied to `docs/eval`, or until `eval-quality` is run with `--cases-dir docs/eval/examples`.

- [ ] **Step 2: Run focused verification**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_eval_case_seed tests.test_quality_gate_eval
PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/eval_case_seed.py tools/agent_memory_runtime/cli.py
git diff --check
ls -1 skills
```

Expected: tests and compile pass, diff has no whitespace errors, and only four official skills remain.

## Task 4: Commit And Push

- [ ] **Step 1: Review diff**

Run:

```bash
git status --short
git diff --stat
```

Expected: planned files changed plus existing untracked `memory.md`.

- [ ] **Step 2: Commit**

Run:

```bash
git add docs/runtime.md docs/usage-guide.md gitlog.md skills/agent-memory-maintain/SKILL.md tools/agent_memory.py tools/agent_memory_runtime/cli.py tools/agent_memory_runtime/eval_case_seed.py tests/test_eval_case_seed.py docs/superpowers/plans/2026-07-12-golden-case-seed-pack.md
git commit -m "Add golden eval case seed pack"
```

- [ ] **Step 3: Push**

Run:

```bash
git push
```

Expected: current branch pushes to GitHub.

## Self-Review

- Spec coverage: The plan covers safe template generation, no-overwrite behavior, forced overwrite behavior, CLI wiring, docs, regression, commit, and push.
- Placeholder scan: No TBD/TODO placeholders remain.
- Type consistency: The command uses `Path`, `dict[str, Any]`, and existing runtime output conventions consistently.
