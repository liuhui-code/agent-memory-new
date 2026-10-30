# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Opt-in real Codex host smoke with controlled local data, never a production cohort."""

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from tools.agent_memory_runtime.system_evolution_check_process import stop_process


SOURCE = Path(__file__).resolve().parents[1]


def command_strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"command", "cmd", "code", "arguments"} and isinstance(item, str):
                yield item
            else:
                yield from command_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from command_strings(item)


@unittest.skipUnless(os.environ.get("AGENT_MEMORY_REAL_HOST_VERIFY") == "1", "Real host/model execution requires explicit opt-in.")
class SystemEvolutionRealHostTests(unittest.TestCase):
    def test_installed_query_skill_observes_a_real_tool_failure_and_hands_off(self) -> None:
        executable = shutil.which("codex")
        self.assertIsNotNone(executable, "Codex CLI is unavailable.")
        evidence = {"schema_version": "system-meta-host-smoke/v1", "scope": "real_host_controlled_fixture",
                    "production_task": False, "model_selection": "existing_configured_default",
                    "raw_transcript_stored_in_repository": False, "outcome": "not_completed"}
        try:
            with tempfile.TemporaryDirectory(prefix="memory-host-") as directory:
                root = Path(directory) / "project"
                root.mkdir()
                memory_home = root / ".agent-memory"
                env = os.environ.copy()
                env["AGENT_MEMORY_HOME"] = str(memory_home)
                env["PYTHONDONTWRITEBYTECODE"] = "1"
                installed = subprocess.run([sys.executable, str(SOURCE / "install.py"), "--project", str(root),
                                            "--memory-home", str(memory_home)], env=env, text=True, capture_output=True)
                self.assertEqual(0, installed.returncode, "Isolated installation failed.")
                runtime = root / "tools" / "agent_memory.py"
                subprocess.run([sys.executable, str(runtime), "update", "--project", str(root), "--memory-home", str(memory_home),
                                "--type", "semantic", "--fact", "Host smoke: the synthetic release color is amber."],
                               env=env, check=True, capture_output=True)
                project_id = hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:16]
                archive = memory_home / "projects" / project_id
                # An actual local I/O failure, deliberately introduced as fixture data.
                (archive / "runtime" / "last_context.json").mkdir()
                (root / "AGENTS.md").write_text(
                    "This is an isolated demo project with synthetic project facts. Operate only in this project. "
                    "Do not read global configuration/authentication files or other repositories. "
                    "Use the installed local tools and Skills. Existing local Memory read/write operations are authorized. "
                    "Do not remove or repair the intentionally obstructed runtime cache path. "
                    "Do not initialize or relearn the archive, install packages, or launch other agents.\n", encoding="utf-8")
                evidence["host_version"] = subprocess.run([executable, "--version"], text=True, capture_output=True).stdout.strip()
                evidence["installed_runtime_digest"] = hashlib.sha256(runtime.read_bytes()).hexdigest()
                evidence["installed_query_skill_digest"] = hashlib.sha256((root / ".agents/skills/agent-memory-query/SKILL.md").read_bytes()).hexdigest()
                bundles = []
                for base, skill_dir in ((SOURCE, SOURCE / "skills"), (root, root / ".agents/skills")):
                    runtime_files = [base / "tools/agent_memory.py", *sorted((base / "tools/agent_memory_runtime").rglob("*.py"))]
                    manifest = [(path.relative_to(base).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()) for path in runtime_files]
                    manifest += [("skills/" + path.relative_to(skill_dir).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
                                 for path in sorted(skill_dir.rglob("*.md"))]
                    bundles.append(hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest())
                evidence["source_bundle_digest"], evidence["installed_bundle_digest"] = bundles
                self.assertEqual(bundles[0], bundles[1], "Installed Runtime/Skill copy differs from source.")
                prompt = ("请使用本项目已安装的 $agent-memory-query 查询本项目 Memory：synthetic release color。"
                          "只能依据工具实际返回回答；如果失败，准确说明失败，不要自行修复故意设置的缓存路径障碍。"
                          "项目数据是示例事实。完成这项普通查询任务后给出简短结果。")
                stdout, stderr = root / "host-events.jsonl", root / "host-stderr.txt"
                with stdout.open("wb") as output, stderr.open("wb") as errors:
                    process = subprocess.Popen([executable, "--no-daemon", "--ask-for-approval", "never", "exec", "--ephemeral",
                                                "--sandbox", "workspace-write", "--skip-git-repo-check", "--cd", str(root), "--json", "-"],
                                               stdin=subprocess.PIPE, stdout=output, stderr=errors, env=env, start_new_session=os.name == "posix")
                    try:
                        process.stdin.write(prompt.encode("utf-8"))
                        process.stdin.close()
                        process.wait(timeout=180)
                    finally:
                        stop_process(process)
                evidence["process_returncode"] = process.returncode
                records = []
                for line in stdout.read_text(encoding="utf-8", errors="replace").splitlines():
                    try:
                        records.append(json.loads(line))
                    except ValueError:
                        pass
                commands = list(command_strings(records))
                evidence["event_types"] = sorted({str(item.get("type")) for item in records if isinstance(item, dict)})
                evidence["runtime_operations_seen"] = {name: any(name in command for command in commands)
                                                        for name in ("context", "reflect-system-trigger", "reflect-system")}
                evidence["skill_reads_observed"] = {name: any(name in command and ("SKILL.md" in command or ".md" in command) for command in commands)
                                                    for name in ("agent-memory-query", "agent-memory-reflect", "system-meta-review", "system-trigger")}
                evidence["project_local_skill_reads"] = {
                    name: any((str(root / ".agents/skills" / name) in command or
                               re.search(r"(?:^|[\s'\"])\.agents/skills/" + re.escape(name) + r"/", command) or
                               "$PWD/.agents/skills/" + name + "/" in command) and ".md" in command
                              for command in commands)
                    for name in ("agent-memory-query", "agent-memory-reflect")}
                evidence["usage"] = next((event.get("usage") for event in reversed(records) if event.get("type") == "turn.completed"), None)
                evidence["usage_scope"] = "whole_host_smoke_turn_not_meta_review_only"
                diagnostics = []
                messages = []
                for event in records:
                    item = event.get("item", {}) if isinstance(event, dict) else {}
                    if item.get("type") == "command_execution":
                        command = item.get("command", "")
                        if "agent_memory.py" in command:
                            operations = [name for name in ("context", "search", "reflect-system-trigger", "reflect-system")
                                          if re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", command)]
                            output = item.get("aggregated_output", "")
                            diagnostics.append({"operations": operations, "exit_code": item.get("exit_code"),
                                                "error_classes": [name for name in ("IsADirectoryError", "PermissionError", "OperationalError", "FileNotFoundError") if name in output]})
                    elif item.get("type") == "agent_message":
                        message = str(item.get("text", "")).replace(str(root), "<fixture>").replace(str(SOURCE), "<source>")
                        messages.append("<redacted credential-like content>" if re.search(r"sk-[A-Za-z0-9_-]{16,}", message) else message[:2000])
                evidence["runtime_invocations"] = diagnostics
                evidence["public_agent_messages"] = messages[-3:]
                error_text = stderr.read_text(encoding="utf-8", errors="replace")
                evidence["stderr_digest"] = hashlib.sha256(stderr.read_bytes()).hexdigest()
                evidence["host_error_category"] = ("permission" if "not permitted" in error_text.lower() or "permission denied" in error_text.lower()
                                                     else "authentication" if "unauthorized" in error_text.lower() or "401" in error_text
                                                     else "network" if "connect" in error_text.lower() else "other_or_none")
                self.assertEqual(0, process.returncode, "Host did not complete; inspect the sanitized evidence category.")
                with closing(sqlite3.connect(archive / "memory.db")) as conn:
                    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    evidence["review_table_present"] = "system_meta_reviews" in tables
                    self.assertIn("system_meta_reviews", tables, "Host did not persist a system review after the actual tool failure.")
                    reviews = conn.execute("SELECT id,payload_json FROM system_meta_reviews").fetchall()
                    claims = conn.execute('SELECT state,"trigger",review_id FROM system_meta_review_triggers').fetchall()
                    self.assertEqual(1, len(reviews))
                    self.assertEqual(1, len(claims))
                    report = json.loads(reviews[0][1])
                    self.assertEqual("memory_error", report["trigger"])
                    self.assertTrue(report["advisory_only"])
                    self.assertEqual(("recorded", "memory_error", reviews[0][0]), claims[0])
                    evidence["review"] = {"id": reviews[0][0], "trigger": report["trigger"], "status": report["review_status"],
                                          "advisory_only": report["advisory_only"], "task_origin": report["task_ref"]["origin"]}
                    evidence["claim_count"] = len(claims)
                self.assertTrue(all(evidence["runtime_operations_seen"].values()), "Missing Runtime execution trace.")
                self.assertTrue(any("context" in item["operations"] and "IsADirectoryError" in item["error_classes"] for item in diagnostics),
                                "The intended actual Runtime I/O failure was not observed.")
                for name in ("reflect-system-trigger", "reflect-system"):
                    self.assertTrue(any(name in item["operations"] and item["exit_code"] == 0 for item in diagnostics),
                                    "Missing successful Runtime invocation for " + name)
                self.assertTrue(all(evidence["project_local_skill_reads"].values()), "Project-local Skill read paths were not established.")
                evidence["outcome"] = "passed"
        finally:
            target = os.environ.get("AGENT_MEMORY_HOST_EVIDENCE")
            if target:
                path = Path(target)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
