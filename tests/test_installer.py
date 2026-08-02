from __future__ import annotations

# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import install


REPO_ROOT = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def test_local_install_is_executable_and_places_four_discoverable_skills(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            process = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "install.py"),
                    "--project",
                    str(project),
                    "--local-skills",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, process.returncode, process.stderr)
            runtime = project / "tools" / "agent_memory.py"
            package = project / "tools" / "agent_memory_runtime"
            skills = project / ".agents" / "skills"
            self.assertTrue(runtime.is_file())
            self.assertTrue((package / "runtime_entry.py").is_file())
            self.assertEqual(
                [
                    "agent-memory-learn",
                    "agent-memory-maintain",
                    "agent-memory-query",
                    "agent-memory-reflect",
                ],
                sorted(path.name for path in skills.iterdir() if path.is_dir()),
            )
            self.assertFalse((project / ".agent-skills").exists())
            for skill_file in skills.rglob("*.md"):
                self.assertNotIn(
                    "python tools/agent_memory.py",
                    skill_file.read_text(encoding="utf-8"),
                )

            reflect_skill = skills / "agent-memory-reflect" / "SKILL.md"
            reflect_text = reflect_skill.read_text(encoding="utf-8")
            self.assertIn("correction_experience", reflect_text)
            self.assertIn("a narrow `trigger_condition`", reflect_text)

            doctor = subprocess.run(
                [sys.executable, str(runtime), "doctor", "--project", str(project)],
                cwd=project,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, doctor.returncode, doctor.stderr)

            review = subprocess.run(
                [
                    sys.executable,
                    str(runtime),
                    "maintain-review",
                    "--project",
                    str(project),
                    "--json",
                ],
                cwd=project,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, review.returncode, review.stderr)

    def test_skill_roots_follow_open_agent_skill_locations(self) -> None:
        project = Path("/workspace/project")
        self.assertEqual(project / ".agents" / "skills", install.local_skill_root(project))
        self.assertEqual(
            Path.home() / ".agents" / "skills",
            install.user_skill_root(),
        )


if __name__ == "__main__":
    unittest.main()
