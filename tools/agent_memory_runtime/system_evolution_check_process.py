# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path
from time import monotonic
from typing import Any

from .storage import now_iso


def stop_process(process: subprocess.Popen) -> None:
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        process.kill()
    process.wait()


def execute_check(check: dict[str, Any], root: Path) -> dict[str, Any]:
    started = monotonic()
    result: dict[str, Any] = {"key": check["key"], "assertion_indices": check["assertion_indices"],
                              "started_at": now_iso(), "exit_code": None, "process_started": False}
    process = None
    try:
        process = subprocess.Popen(
            check["argv"], cwd=root, shell=False, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=os.name == "posix",
        )
        result["process_started"] = True
        try:
            code = process.wait(timeout=check["timeout_seconds"])
            result.update(exit_code=code, outcome="exit_zero" if code == 0 else "exit_nonzero")
        except subprocess.TimeoutExpired:
            result["outcome"] = "timed_out"
    except OSError:
        result["outcome"] = "process_error"
    finally:
        if process is not None:
            stop_process(process)
            if result.get("outcome") == "timed_out":
                result["exit_code"] = process.returncode
        result["completed_at"] = now_iso()
        result["elapsed_ms"] = round((monotonic() - started) * 1000, 3)
    return result
