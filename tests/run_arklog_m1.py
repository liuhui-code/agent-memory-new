# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""One bounded ArkLog development experiment; never a serving Runtime or M2 evaluator."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/arklog_m1"
CONTROLLER = "crates/arklog-tui/src/controller.rs"
RUNTIME = "crates/arklog-core/src/runtime.rs"
PROBE = "crates/arklog-tui/tests/support/m1_stream_contract.rs"
HOOK = '\n#[cfg(test)]\n#[path = "../tests/support/m1_stream_contract.rs"]\nmod m1_contract;\n'
FENCE = "self.active_stream.as_deref() == Some(&batch.stream_id)"
DEVICE_ONLY = "self.selected_device().is_some_and(|device| device.id == batch.device_id)"
LEGACY = "device_switch_discards_the_old_streams_late_partial_batch"
SUMMARY = re.compile(r"test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored;")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def git(source: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=source, text=True).strip()


def tracked_manifest(source: Path) -> dict[str, str]:
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=source).decode().split("\0")[:-1]
    if any(Path(name).name == "memory.md" for name in names):
        raise RuntimeError("memory.md is outside this experiment's readable scope")
    return {name: sha((source / name).read_bytes()) for name in names if (source / name).is_file()}


def prepare(source: Path) -> tuple[Path, dict]:
    base = "/private/tmp" if Path("/private/tmp").is_dir() else None
    root = Path(tempfile.mkdtemp(prefix="arklog-m1-", dir=base))
    snapshot = root / "baseline"
    snapshot.mkdir()
    archive = root / "baseline.tar"
    with archive.open("wb") as out:
        subprocess.run(["git", "archive", "HEAD"], cwd=source, stdout=out, check=True)
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            if not (snapshot / member.name).resolve().is_relative_to(snapshot.resolve()):
                raise RuntimeError("archive path escapes isolated snapshot")
        bundle.extractall(snapshot)
    cargo_home = root / "cargo-home"
    (cargo_home / "registry").mkdir(parents=True)
    for name in ("src", "cache", "index"):
        original = Path.home() / ".cargo/registry" / name
        if original.exists():
            (cargo_home / "registry" / name).symlink_to(original, target_is_directory=True)
    (root / "guard-bin").mkdir()
    (root / "tmp").mkdir()
    guard = root / "guard-bin/hdc"
    guard.write_text('#!/bin/sh\nprintf "unexpected real-hdc lookup blocked\\n" >&2\nexit 91\n')
    guard.chmod(0o755)
    manifest = tracked_manifest(source)
    meta = {"root": str(root), "source": str(source), "snapshot": str(snapshot),
            "baseline_revision": git(source, "rev-parse", "HEAD"),
            "baseline_tree": git(source, "rev-parse", "HEAD^{tree}"),
            "baseline_status": git(source, "status", "--porcelain=v1"), "baseline_manifest": manifest}
    write_json(root / "metadata.json", meta)
    return root, meta


class Experiment:
    def __init__(self, source: Path, output: Path, root: Path, meta: dict):
        self.source, self.output, self.root, self.meta = source, output, root, meta
        self.work = root / "baseline"
        self.original_controller = (self.work / CONTROLLER).read_text()
        self.original_runtime = (self.work / RUNTIME).read_text()
        self.parts: list[str] = []
        self.records: list[dict] = []
        self.memory_context_status = "not_run"
        self.environment = os.environ.copy()
        self.environment.update({"CARGO_HOME": str(root / "cargo-home"), "CARGO_TARGET_DIR": str(root / "target"),
            "CARGO_NET_OFFLINE": "true", "TMPDIR": str(root / "tmp"), "RUST_TEST_THREADS": "1",
            "ARKLOG_HDC_PATH": str(root / "guard-bin/hdc"),
            "PATH": str(root / "guard-bin") + os.pathsep + os.environ.get("PATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1"})
        (output / "logs").mkdir()
        (output / "sources").mkdir()

    def snapshot(self) -> str:
        names = [*self.meta["baseline_manifest"]]
        if (self.work / PROBE).exists():
            names.append(PROBE)
        value = {name: sha((self.work / name).read_bytes()) for name in sorted(names)}
        digest = sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())
        write_json(self.output / "sources" / (digest + ".json"), value)
        return digest

    def run(self, name: str, command: list[str], *, expected_tests: int | None = None,
            expected_failure: str | None = None, timeout: int = 180, cwd: Path | None = None) -> dict:
        before = self.snapshot()
        path = self.output / "logs" / (name + ".log")
        started = time.monotonic()
        timed_out = False
        with path.open("wb") as out:
            process = subprocess.Popen(command, cwd=cwd or self.work, env=self.environment,
                                       stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                returncode = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait()
        text = path.read_text(errors="replace")
        summaries = SUMMARY.findall(text)
        passed = sum(int(item[1]) for item in summaries)
        failed = sum(int(item[2]) for item in summaries)
        ignored = sum(int(item[3]) for item in summaries)
        failed_ids = re.findall(r"^    ([\w:]+)$", text, re.MULTILINE) if failed else []
        stable = before == self.snapshot()
        if expected_failure:
            ok = (not timed_out and returncode == 101 and failed == 1 and passed == 0 and ignored == 0
                  and any(test.endswith(expected_failure) for test in failed_ids) and stable)
            outcome = "expected_contract_rejection" if ok else "unexpected_result"
        else:
            ok = not timed_out and returncode == 0 and failed == 0 and ignored == 0 and stable
            outcome = "passed" if ok else "failed_or_unavailable"
        if expected_tests is not None:
            ok = ok and passed + failed == expected_tests and bool(summaries)
            if not ok:
                outcome = "failed_or_invalid_discovery"
        elif "test" in command and (not summaries or passed + failed == 0):
            ok = False
            outcome = "invalid_zero_test_discovery"
        value = {"name": name, "command": command, "cwd": str(cwd or self.work),
                 "operation_kind": "test" if "test" in command else "context" if "agent_memory.py" in " ".join(command) else "build",
                 "source_manifest_digest": before, "source_unchanged_during_command": stable,
                 "elapsed_seconds": round(time.monotonic() - started, 3), "returncode": returncode,
                 "timed_out": timed_out, "passed": passed, "failed": failed, "ignored": ignored,
                 "tests_executed": passed + failed, "failed_test_ids": failed_ids,
                 "expected_failure": expected_failure, "log": path.relative_to(self.output).as_posix(),
                 "log_sha256": sha(path.read_bytes()), "outcome": outcome, "expectation_met": ok}
        self.records.append(value)
        write_json(self.output / "commands.json", self.records)
        print(json.dumps({key: value[key] for key in ("name", "outcome", "tests_executed", "elapsed_seconds")}), flush=True)
        if not ok:
            raise RuntimeError(f"{name}: {outcome}; retained {path}")
        return value

    def restore(self) -> None:
        (self.work / CONTROLLER).write_text(self.original_controller + (HOOK if self.parts else ""))
        (self.work / RUNTIME).write_text(self.original_runtime)

    def add_probe(self, filename: str) -> None:
        self.parts.append(filename)
        path = self.work / PROBE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join((FIXTURES / name).read_text() for name in self.parts))
        self.restore()

    def replace_once(self, path: str, old: str, new: str) -> None:
        target = self.work / path
        text = target.read_text()
        if text.count(old) != 1:
            raise RuntimeError(f"mutation precondition changed: {path}")
        target.write_text(text.replace(old, new))

    def probe(self, name: str, test: str, expected_failure: bool = False) -> dict:
        return self.run(name, ["cargo", "test", "--offline", "--locked", "-p", "arklog", "--lib", test,
            "--", "--nocapture"], expected_tests=1,
            expected_failure=test if expected_failure else None)

    def execute(self, skip_gates: bool) -> None:
        # Existing closest public integration first. A surviving deliberate mutation
        # identifies an evidence gap, not a defect verdict about the real application.
        initial = self.root / "baseline-focused.log"
        if initial.is_file():
            shutil.copy2(initial, self.output / "logs/initial-baseline-focused.log")
            parsed = SUMMARY.findall(initial.read_text())
            if sum(int(item[1]) for item in parsed) != 32 or any(int(item[2]) for item in parsed):
                raise RuntimeError("prepared initial focused result is not 32 passing tests")
        else:
            self.run("initial-baseline-focused", ["cargo", "test", "--offline", "--locked", "-p", "arklog",
                     "--test", "controller_stream", "--test", "stream_intent_controller", "--test", "controller_desired_stream"],
                     expected_tests=32)
        self.replace_once(CONTROLLER, FENCE, DEVICE_ONLY)
        self.run("legacy-device-only-survives", ["cargo", "test", "--offline", "--locked", "-p", "arklog",
                 "--test", "controller_stream", LEGACY, "--", "--exact"], expected_tests=1)
        self.restore()

        self.add_probe("current_batch.rs")
        current = "controller::m1_contract::current_batch_is_accepted"
        self.probe("current-positive", current)
        self.replace_once(CONTROLLER, FENCE, "false")
        self.probe("drop-all-rejected", current, True)
        self.restore()
        self.probe("current-positive-restored", current)

        self.add_probe("same_device.rs")
        same = "controller::m1_contract::same_device_reconnect_rejects_prior_stream_batches"
        self.replace_once(CONTROLLER, FENCE, DEVICE_ONLY)
        self.probe("device-only-rejected", same, True)
        self.restore()
        self.run("generation-positive-restored", ["cargo", "test", "--offline", "--locked", "-p", "arklog",
                 "--lib", "m1_contract", "--", "--nocapture"], expected_tests=2)

        self.add_probe("completion_identity.rs")
        origin = "controller::m1_contract::completion_keeps_origin_while_another_stream_is_active"
        self.replace_once(RUNTIME, "stream_id: stream_id.to_string(),",
                          "stream_id: streams.keys().max().cloned().unwrap_or_default(),")
        self.probe("completion-rebound-rejected", origin, True)
        self.restore()
        self.probe("completion-positive-restored", origin)

        self.add_probe("cleanup_order.rs")
        order = "controller::m1_contract::retirement_receipt_precedes_replacement_commit"
        old = "            || self.stream_stop.is_running()\n            || self.stream_reap.is_running()\n"
        self.replace_once(CONTROLLER, old, "")
        self.probe("unsafe-completion-order-rejected", order, True)
        self.restore()
        self.run("all-contract-probes-green", ["cargo", "test", "--offline", "--locked", "-p", "arklog",
                 "--lib", "m1_contract", "--", "--nocapture"], expected_tests=4)

        # Memory provides evidence context only. Cargo/libtest executes the experiment.
        entry = str(ROOT / "tools/agent_memory.py")
        memory_args = ["--project", str(self.source), "--memory-home", str(self.root / "memory-home")]
        learn = self.run("memory-learn-context", [sys.executable, entry, "learn-path", *memory_args,
                 "--source", str(self.source), "--path", "crates/arklog-tui/src", "--json"], cwd=ROOT)
        context = self.run("memory-design-context", [sys.executable, entry, "design-context", *memory_args,
                 "--query", "ArkLogController active_stream stream_id pump_log_batches reconcile_stream", "--compact", "--json"], cwd=ROOT)
        data = json.loads((self.output / context["log"]).read_text())
        if not isinstance(data, dict):
            raise RuntimeError("Memory context is not an object")
        anchored = self.run("memory-explicit-anchor-feedback", [sys.executable, entry, "design-context", *memory_args,
            "--query", "ArkLog stream ownership and retirement", "--anchor", CONTROLLER, "--anchor", RUNTIME,
            "--concern", "testability", "--constraint", "Retire the old stream before committing a replacement; preserve valid manual Stop tail batches.",
            "--compact", "--json"], cwd=ROOT)
        anchored_data = json.loads((self.output / anchored["log"]).read_text())
        learned = json.loads((self.output / learn["log"]).read_text())
        source_anchors = anchored_data.get("current_repository", {}).get("source_anchors", [])
        self.memory_context_status = "source_context_available" if source_anchors else "rust_source_context_unavailable"
        write_json(self.output / "memory-context.json", {"files_indexed": learned["parse_stats"]["files_indexed"],
            "unanchored_source_anchors": len(data.get("current_repository", {}).get("source_anchors", [])),
            "explicit_anchor_source_anchors": len(source_anchors), "status": self.memory_context_status,
            "sufficiency": anchored_data.get("sufficiency"), "automatic_rust_source_context_proved": bool(source_anchors),
            "decision_basis": "Agent direct inspection of current source plus native Cargo tests",
            "advisory_catalog_is_not_source_evidence": True})
        self.run("live-only-capability", ["cargo", "test", "--offline", "--locked", "-p", "arklog-core",
                 "--test", "live_start"], expected_tests=1)
        if not skip_gates:
            self.run_gates()

    def run_gates(self, *, include_pnpm_test: bool = True) -> None:
        commands = [("pnpm-test", ["pnpm", "test"])] if include_pnpm_test else []
        commands += [("pnpm-build", ["pnpm", "build"]),
                     ("cargo-workspace", ["cargo", "test", "--workspace", "--locked", "--offline"]),
                     ("cargo-check", ["cargo", "check", "-p", "arklog", "--locked", "--offline"])]
        errors = []
        for name, command in commands:
            try:
                self.run(name, command, timeout=600)
            except RuntimeError as exc:
                errors.append(str(exc))
        if errors:
            raise RuntimeError("; ".join(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path, help="New directory; prior evidence is never overwritten")
    parser.add_argument("--prepared-root", type=Path, help="Reuse this task's clean temporary snapshot/compiler cache")
    parser.add_argument("--skip-gates", action="store_true", help="Exploratory probes only; never a completed M1 gate")
    args = parser.parse_args()
    source, output = args.source.resolve(), args.evidence.resolve()
    if not (source / CONTROLLER).is_file():
        parser.error("Missing the actual ArkLog workspace")
    if output.exists() or not output.parent.is_dir():
        parser.error("--evidence requires a new directory in an existing parent")
    if git(source, "status", "--porcelain=v1"):
        parser.error("This snapshot runner requires a clean source; preserve and review dirty work separately")
    before = tracked_manifest(source)
    if args.prepared_root:
        root = args.prepared_root.resolve()
        if not root.name.startswith("arklog-m1-") or root.parent not in {Path("/private/tmp"), Path("/tmp")}:
            parser.error("--prepared-root must be this task's temporary root")
        meta = json.loads((root / "metadata.json").read_text())
        if meta["source"] != str(source) or meta["baseline_manifest"] != before:
            parser.error("prepared snapshot does not match current source")
        for name, digest in before.items():
            if sha((root / "baseline" / name).read_bytes()) != digest:
                parser.error("prepared snapshot already changed: " + name)
    else:
        root, meta = prepare(source)
    output.mkdir()
    experiment = Experiment(source, output, root, meta)
    definitions = {p.name: sha(p.read_bytes()) for p in sorted(FIXTURES.glob("*.rs"))}
    versions = {}
    for tool in ("cargo", "rustc", "pnpm", "node"):
        try:
            versions[tool] = subprocess.check_output([tool, "--version"], text=True, timeout=15).strip()
        except (OSError, subprocess.SubprocessError) as exc:
            versions[tool] = {"unavailable": str(exc)}
    write_json(output / "input.json", {**meta, "check_definition": definitions, "runner_sha256": sha(Path(__file__).read_bytes()),
        "task": "M1: ArkLog device-session replacement and obsolete-event isolation; native-code design experiment",
        "versions": versions, "memory_source_revision": git(ROOT, "rev-parse", "HEAD"),
        "runtime_entry": str(ROOT / "tools/agent_memory.py"), "platform": platform.platform(),
        "python": sys.version.split()[0], "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "test_only_hook": HOOK, "real_devices_allowed": False, "production_source_writes_allowed": False})
    error = None
    completed = False
    try:
        experiment.execute(args.skip_gates)
        completed = True
    except Exception as exc:
        error = str(exc)
        print(error, file=sys.stderr)
    finally:
        unchanged = before == tracked_manifest(source) and not git(source, "status", "--porcelain=v1")
        valid = completed and error is None and unchanged and not args.skip_gates
        outcome = ("completed_with_context_gap" if experiment.memory_context_status == "rust_source_context_unavailable"
                   else "passed") if valid else "incomplete"
        write_json(output / "result.json", {"scope": "M1 controlled native-code development experiment",
            "outcome": outcome, "native_contract_and_gates_completed": valid,
            "memory_context_status": experiment.memory_context_status,
            "error": error, "source_unchanged": unchanged, "commands": len(experiment.records),
            "production_defect_claimed": False, "m2_started": False, "live_only_device_acceptance": "not_verified",
            "isolation_root": str(root), "temporary_root_retained_for_audit": True})
    return 0 if completed and error is None and unchanged and not args.skip_gates else 1


if __name__ == "__main__":
    raise SystemExit(main())
