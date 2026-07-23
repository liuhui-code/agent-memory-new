# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.agent_memory_runtime.benchmark_case_seal_command import source_revision_audit

from tests.test_benchmark_case_seal import reviewed_pack


class BenchmarkCaseSealCommandTests(unittest.TestCase):
    def test_source_revision_audit_verifies_revisions_and_changed_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before, after = create_history(root)
            pack = reviewed_pack()
            case = pack["cases"][0]
            case["source"].update({
                "before_revision": before,
                "after_revision": after,
                "changed_files": ["entry/src/main/ets/pages/Index.ets"],
            })
            case["provenance"]["fix_commit"] = after
            audit = source_revision_audit(root, pack)
        self.assertEqual("verified", audit["status"])
        self.assertEqual(1, audit["case_count"])

    def test_source_revision_audit_rejects_incorrect_changed_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before, after = create_history(root)
            pack = reviewed_pack()
            case = pack["cases"][0]
            case["source"].update({
                "before_revision": before,
                "after_revision": after,
                "changed_files": ["wrong.ets"],
            })
            case["provenance"]["fix_commit"] = after
            with self.assertRaisesRegex(SystemExit, "changed files do not match"):
                source_revision_audit(root, pack)


def create_history(root: Path) -> tuple[str, str]:
    run_git(root, "init")
    run_git(root, "config", "user.email", "tests@example.test")
    run_git(root, "config", "user.name", "Agent Memory Tests")
    path = root / "entry/src/main/ets/pages/Index.ets"
    path.parent.mkdir(parents=True)
    path.write_text("@Entry\nstruct Index {}\n", encoding="utf-8")
    run_git(root, "add", ".")
    run_git(root, "commit", "-m", "initial")
    before = run_git(root, "rev-parse", "HEAD").stdout.strip()
    path.write_text("@Entry\nstruct Index { private route: string = 'home' }\n", encoding="utf-8")
    run_git(root, "add", ".")
    run_git(root, "commit", "-m", "fix route owner")
    after = run_git(root, "rev-parse", "HEAD").stdout.strip()
    return before, after


def run_git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )


if __name__ == "__main__":
    unittest.main()
