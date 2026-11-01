# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Run the existing basic regression profile in temporary project/Memory roots."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CASES = [
    "tests.test_agent_memory_part_01",
    "tests.test_agent_memory_part_02",
    "tests.test_installer",
    "tests.test_agent_memory_part_07.AgentMemoryRuntimePart07Tests.test_vault_export_writes_reflection_quality_dashboard",
    "tests.test_agent_memory_part_08.AgentMemoryRuntimePart08Tests.test_context_records_query_miss_when_all_result_sets_are_empty",
    "tests.test_agent_memory_part_12.AgentMemoryRuntimePart12Tests.test_source_excerpt_rejects_paths_outside_project",
    "tests.test_agent_memory_part_14.AgentMemoryRuntimePart14Tests.test_context_json_stdout_preserves_chinese_text",
]


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed_ids: list[str] = []

    def addSuccess(self, test):
        self.passed_ids.append(test.id())
        super().addSuccess(test)


def source_manifest() -> dict[str, str]:
    paths = [ROOT / "tools/agent_memory.py", ROOT / "install.py", Path(__file__), ROOT / "tests/agent_memory_test_base.py"]
    paths += sorted((ROOT / "tools/agent_memory_runtime").rglob("*.py"))
    paths += sorted((ROOT / "skills").rglob("*.md"))
    paths += [ROOT / ("/".join(name.split(".")[:2]) + ".py") for name in CASES]
    return {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(set(paths))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="Optional new JSON report in an existing directory; never overwrites a file.")
    args = parser.parse_args()
    report = args.report.expanduser().resolve() if args.report else None
    if report is not None and (report.exists() or not report.parent.is_dir()):
        parser.error("--report requires a new file in an existing directory")
    if Path.cwd().resolve() != ROOT:
        parser.error("Run from the repository root with python3 -m tests.run_basic_checks")
    before = source_manifest()
    started = time.monotonic()
    previous_tempdir = tempfile.tempdir
    with tempfile.TemporaryDirectory(prefix="agent-memory-basic-") as isolated_root:
        try:
            tempfile.tempdir = isolated_root
            with patch.dict(os.environ, {"TMPDIR": isolated_root, "AGENT_MEMORY_HOME": isolated_root + "/fallback-memory",
                                         "PYTHONDONTWRITEBYTECODE": "1"}):
                os.environ.pop("AGENT_MEMORY_REAL_HOST_VERIFY", None)
                suite = unittest.defaultTestLoader.loadTestsFromNames(CASES)
                if suite.countTestCases() == 0:
                    raise RuntimeError("The basic profile discovered no tests.")
                result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(suite)
        finally:
            tempfile.tempdir = previous_tempdir
    after = source_manifest()
    unchanged = before == after
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = None
    value = {"schema_version": "agent-memory-basic-checks/v1", "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "scope": "controlled_temporary_projects_and_memory_homes", "baseline_revision": revision,
             "python": sys.version.split()[0], "platform": platform.system() + "-" + platform.machine(),
             "profile": CASES, "tests_run": result.testsRun, "passed": len(result.passed_ids),
             "failures": len(result.failures), "errors": len(result.errors),
             "skipped": [{"id": test.id(), "reason": reason} for test, reason in result.skipped],
             "passed_test_ids": result.passed_ids, "failed_test_ids": [test.id() for test, _ in result.failures + result.errors],
             "elapsed_seconds": round(time.monotonic() - started, 3),
             "temporary_root_cleanup_completed": not Path(isolated_root).exists(), "source_unchanged_during_run": unchanged,
             "source_manifest": after,
             "source_manifest_digest": hashlib.sha256(json.dumps(after, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
             "outcome": "passed" if result.wasSuccessful() and unchanged else "failed",
             "model_invoked_by_runner": False, "production_or_sealed_evaluation": False}
    if report is not None:
        with report.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value[key] for key in ("outcome", "tests_run", "passed", "failures", "errors", "elapsed_seconds")}), flush=True)
    return 0 if value["outcome"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
