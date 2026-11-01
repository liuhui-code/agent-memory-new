# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Opt-in installed R3 current-host handoff; controlled fixture, never real-task efficacy."""

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from tests import test_system_evolution_handoffs as fixtures
from tests.test_system_evolution_host import command_strings
from tools.agent_memory_runtime.system_evolution_check_process import stop_process
from tools.agent_memory_runtime.system_evolution_handoff_schema import TABLE


SOURCE = Path(__file__).resolve().parents[1]


def bundle_digest(base, skill_root):
    runtime = [base / "tools/agent_memory.py", *sorted((base / "tools/agent_memory_runtime").rglob("*.py"))]
    items = [(path.relative_to(base).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()) for path in runtime]
    items += [("skills/" + path.relative_to(skill_root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
              for path in sorted(skill_root.rglob("*.md"))]
    return hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()


@unittest.skipUnless(os.environ.get("AGENT_MEMORY_REAL_HOST_VERIFY") == "1", "Real R3 host/model execution requires explicit opt-in.")
class SystemEvolutionHandoffHostTests(unittest.TestCase):
    def test_installed_maintain_skill_claims_and_completes_one_window_review(self):
        executable = shutil.which("codex")
        self.assertIsNotNone(executable, "Codex CLI is unavailable.")
        evidence = {"schema_version": "system-meta-handoff-host-smoke/v1", "outcome": "not_completed",
                    "scope": "real_host_controlled_fixture", "production_task": False,
                    "model_selection": "existing_configured_default", "precise_model_identity": None,
                    "raw_transcript_stored_in_repository": False, "efficacy_verified": False}
        try:
            with tempfile.TemporaryDirectory(prefix="memory-r3-host-") as directory:
                owner = fixtures.SystemEvolutionHandoffTests()
                root, rounds, change, applied = owner.fixture(directory, installed=True)
                memory_home = owner.memory_home(root)
                archive = owner.project_memory_dir(root)
                request = fixtures.claim_request()
                request["task_ref"]["key"] = "synthetic-real-host-window-boundary"
                request["version_refs"]["archive_project_id"] = owner.project_id(root)
                (root / "window-handoff.json").write_text(json.dumps(request), encoding="utf-8")
                (root / "AGENTS.md").write_text(
                    "This is an isolated, synthetic window-follow-up integration test. Use only this project, "
                    "the explicitly supplied sibling Memory Home and installed local tools/Skills. "
                    "The pre-bound fixture authorization permits one model assessment and the associated local "
                    "handoff/assessment writes. Do not deploy, create a proposal, change inputs or apply a decision. "
                    "Do not read global auth/configuration files, other repositories, source checkout or launch other agents. "
                    "Do not install packages, initialize storage or run broad evaluations. Task data are controlled "
                    "declarations, not production results.\n", encoding="utf-8")
                source_bundle = bundle_digest(SOURCE, SOURCE / "skills")
                installed_bundle = bundle_digest(root, root / ".agents/skills")
                evidence.update(source_bundle_digest=source_bundle, installed_bundle_digest=installed_bundle)
                self.assertEqual(source_bundle, installed_bundle, "Installed Runtime/Skills differ from source.")
                evidence["host_version"] = subprocess.run([executable, "--version"], text=True, capture_output=True).stdout.strip()
                prompt = ("请使用本项目已安装的 $agent-memory-maintain 完成现有观察窗口的维护收尾。"
                          "窗口和当前轮次已经建立，边界输入在 window-handoff.json；使用其中的真实归档标识和稳定任务引用。"
                          "本测试允许按已绑定许可完成一次窗口复核及相应本地记录。不要创建新候选、部署或改变原观察文件。"
                          "准确保留未知结果和成本，给出简短收尾说明。Memory Home 为 " + str(memory_home) + "。")
                env = os.environ.copy()
                env.update(AGENT_MEMORY_HOME=str(memory_home), PYTHONDONTWRITEBYTECODE="1")
                stdout, stderr = root / "host-events.jsonl", root / "host-stderr.txt"
                with stdout.open("wb") as output, stderr.open("wb") as errors:
                    process = subprocess.Popen([executable, "--no-daemon", "--ask-for-approval", "never", "exec", "--ephemeral",
                                                "--sandbox", "workspace-write", "--add-dir", str(memory_home),
                                                "--skip-git-repo-check", "--cd", str(root), "--json", "-"], stdin=subprocess.PIPE,
                                               stdout=output, stderr=errors, env=env, start_new_session=os.name == "posix")
                    try:
                        process.stdin.write(prompt.encode("utf-8"))
                        process.stdin.close()
                        try:
                            process.wait(timeout=180)
                        except subprocess.TimeoutExpired:
                            evidence["host_error_category"] = "timeout"
                            raise
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
                evidence["event_types"] = sorted({item.get("type", "unknown") for item in records if isinstance(item, dict)})
                evidence["usage"] = next((item.get("usage") for item in reversed(records) if item.get("type") == "turn.completed"), None)
                evidence["usage_scope"] = "whole_host_turn_not_incremental_meta_cost"
                evidence["local_maintain_skill_read"] = any(
                    (str(root / ".agents/skills/agent-memory-maintain") in command or
                     re.search(r"(?:^|[\s'\"])\.agents/skills/agent-memory-maintain/", command) or
                     "$PWD/.agents/skills/agent-memory-maintain/" in command) and "SKILL.md" in command for command in commands)
                evidence["handoff_reference_read"] = any("system-handoffs.md" in command for command in commands)
                invocations = []
                for record in records:
                    item = record.get("item", {})
                    if item.get("type") == "command_execution" and "maintain-system-round-handoff" in item.get("command", ""):
                        invocations.append({"operation": "maintain-system-round-handoff", "exit_code": item.get("exit_code")})
                evidence["runtime_invocations"] = invocations
                error_text = stderr.read_text(encoding="utf-8", errors="replace")
                evidence["stderr_digest"] = hashlib.sha256(stderr.read_bytes()).hexdigest()
                evidence["host_error_category"] = ("permission" if "not permitted" in error_text.lower() or "permission denied" in error_text.lower()
                                                   else "authentication" if "unauthorized" in error_text.lower() or "401" in error_text
                                                   else "network" if "connect" in error_text.lower() else "other_or_none")
                self.assertEqual(0, process.returncode, "Host failed; inspect the sanitized category.")
                self.assertTrue(evidence["local_maintain_skill_read"], "Installed Maintain Skill read was not established.")
                self.assertTrue(evidence["handoff_reference_read"], "Window handoff reference was not read.")
                self.assertTrue(any(item["exit_code"] == 0 for item in invocations), "No successful handoff Runtime invocation observed.")
                with closing(sqlite3.connect(archive / "memory.db")) as conn:
                    conn.row_factory = sqlite3.Row
                    rows = conn.execute(f"SELECT phase,request_json,receipt_json,request_digest,receipt_digest FROM {TABLE} ORDER BY id").fetchall()
                    self.assertEqual(["claim", "finish"], [row["phase"] for row in rows])
                    finish = json.loads(rows[1]["receipt_json"])
                    self.assertEqual("recorded", finish["state"], "Host did not complete its one claimed review.")
                    self.assertEqual("complete", json.loads(rows[1]["request_json"])["action"])
                    assessments = conn.execute("SELECT request_json FROM system_evolution_round_events WHERE kind='assessment'").fetchall()
                    self.assertEqual(1, len(assessments))
                    assessment = json.loads(assessments[0][0])
                    self.assertIsNone(assessment["additional_cost"]["tokens"], "Incremental review tokens were not measured in this fixture.")
                    self.assertEqual("monitoring", conn.execute("SELECT state FROM system_change_proposals WHERE id=1").fetchone()[0])
                    self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM system_evolution_round_events WHERE kind='decision'").fetchone()[0])
                    evidence.update(claim_count=1, finish_state=finish["state"], assessment_count=1,
                                    finding=assessment["finding"], declared_review_cost=assessment["additional_cost"],
                                    claim_receipt_digest=rows[0]["receipt_digest"], finish_receipt_digest=rows[1]["receipt_digest"])
                retry = owner.handoff(root, request)
                self.assertFalse(retry["should_review"])
                evidence["post_completion_generation_suppressed"] = True
                evidence["outcome"] = "passed"
        finally:
            target = os.environ.get("AGENT_MEMORY_R3_HOST_EVIDENCE")
            if target:
                path = Path(target)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
