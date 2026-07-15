# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any


def prepare_isolated_memory(
    workspace: Path,
    memory_home: Path,
    timeout: int,
    task_type: str,
) -> dict[str, Any]:
    runtime = Path(__file__).resolve().parents[1] / "agent_memory.py"
    common = ["--project", str(workspace), "--memory-home", str(memory_home)]
    run_runtime(runtime, ["init", *common], timeout)
    run_runtime(runtime, ["wiki-index", *common], timeout)
    query_command = design_command(runtime, workspace, memory_home) if task_type == "design" else diagnosis_command(
        runtime, workspace, memory_home
    )
    return {
        "runtime": str(runtime),
        "project": str(workspace),
        "memory_home": str(memory_home),
        "query_command": query_command,
        "isolated": True,
        "source_revision_only": True,
    }


def diagnosis_command(runtime: Path, workspace: Path, memory_home: Path) -> list[str]:
    return [
        sys.executable, str(runtime), "context",
        "--project", str(workspace), "--memory-home", str(memory_home),
        "--query", "<task-description-or-agent-extracted-term>", "--json",
    ]


def design_command(runtime: Path, workspace: Path, memory_home: Path) -> list[str]:
    return [
        sys.executable, str(runtime), "design-assist",
        "--project", str(workspace), "--memory-home", str(memory_home),
        "--query", "<task-description>", "--mode", "design-only", "--json",
    ]


def run_runtime(runtime: Path, arguments: list[str], timeout: int) -> None:
    try:
        process = subprocess.run(
            [sys.executable, str(runtime), *arguments],
            text=True,
            capture_output=True,
            timeout=max(30, timeout),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(f"benchmark memory preparation timed out: {arguments[0]}") from exc
    if process.returncode != 0:
        message = process.stderr.strip()[:1000] or process.stdout.strip()[:1000]
        raise SystemExit(f"benchmark memory preparation failed: {arguments[0]}: {message}")
