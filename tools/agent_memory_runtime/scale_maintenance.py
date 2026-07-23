# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import contextlib
import io
import json
import time
from pathlib import Path
from typing import Any, Callable

from .code_wiki_indexing import record_learn_scope
from .code_wiki_refresh import maintain_refresh_scope
from .models import Project
from .scope_changes import GitChangeError, run_git


TARGET_PATH = "src/domain01/Service1.ets"
NOISE_PATH = "noise/Unrelated.ets"
MAINTENANCE_SLO_MS = {
    "incremental_no_change": 500.0,
    "incremental_outside_scope": 500.0,
    "incremental_single_file": 2000.0,
    "incremental_large_method_file": 5000.0,
}


def benchmark_incremental_maintenance(
    project: Project,
    repetitions: int,
) -> dict[str, Any]:
    scope_id = prepare_git_scope(project)
    operations = {
        "incremental_no_change": measure_refreshes(
            project,
            scope_id,
            repetitions,
            None,
            expected_files=[],
            target_ms=MAINTENANCE_SLO_MS["incremental_no_change"],
        ),
        "incremental_outside_scope": measure_refreshes(
            project,
            scope_id,
            repetitions,
            lambda index: commit_noise(project.root, index),
            expected_files=[],
            target_ms=MAINTENANCE_SLO_MS["incremental_outside_scope"],
        ),
        "incremental_single_file": measure_refreshes(
            project,
            scope_id,
            repetitions,
            lambda index: commit_methods(project.root, 20, index + 1),
            expected_files=[TARGET_PATH],
            target_ms=MAINTENANCE_SLO_MS["incremental_single_file"],
        ),
        "incremental_large_method_file": measure_refreshes(
            project,
            scope_id,
            repetitions,
            lambda index: commit_methods(project.root, 500, index + 100),
            expected_files=[TARGET_PATH],
            target_ms=MAINTENANCE_SLO_MS["incremental_large_method_file"],
        ),
    }
    return {
        "status": "pass" if all(item["pass"] for item in operations.values()) else "fail",
        "scope_id": scope_id,
        "operations": operations,
    }


def prepare_git_scope(project: Project) -> int:
    target = project.root / TARGET_PATH
    noise = project.root / NOISE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    noise.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(method_source(20, 0), encoding="utf-8")
    noise.write_text("export const unrelated = 0\n", encoding="utf-8")
    initialize_git(project.root)
    commit_all(project.root, "initial scale maintenance scope")
    return record_learn_scope(
        project,
        project.root,
        "path",
        "merge",
        [target],
        target_path=TARGET_PATH,
    )


def initialize_git(root: Path) -> None:
    run_git(root, ["init", "-q"])
    run_git(root, ["config", "user.email", "scale-benchmark@example.invalid"])
    run_git(root, ["config", "user.name", "Scale Benchmark"])


def commit_noise(root: Path, version: int) -> None:
    (root / NOISE_PATH).write_text(
        f"export const unrelated = {version + 1}\n",
        encoding="utf-8",
    )
    commit_all(root, f"outside scope {version + 1}")


def commit_methods(root: Path, method_count: int, version: int) -> None:
    (root / TARGET_PATH).write_text(
        method_source(method_count, version),
        encoding="utf-8",
    )
    commit_all(root, f"scope methods {method_count} version {version}")


def commit_all(root: Path, message: str) -> None:
    run_git(root, ["add", "--all"])
    run_git(root, ["commit", "-q", "-m", message])


def method_source(method_count: int, version: int) -> str:
    methods = "\n".join(
        f"  method{index:04d}(): void {{ const revision = {version}; }}"
        for index in range(1, method_count + 1)
    )
    return f"export class Service1 {{\n{methods}\n}}\n"


def measure_refreshes(
    project: Project,
    scope_id: int,
    repetitions: int,
    mutate: Callable[[int], None] | None,
    expected_files: list[str],
    target_ms: float,
) -> dict[str, Any]:
    samples: list[float] = []
    evidence: list[dict[str, Any]] = []
    phase_samples: dict[str, list[float]] = {}
    for index in range(repetitions):
        if mutate:
            mutate(index)
        started = time.perf_counter()
        result = run_changed_only_refresh(project, scope_id)
        samples.append((time.perf_counter() - started) * 1000.0)
        scope = result["scopes"][0]
        phase_ms = scope.get("parse_stats", {}).get("phase_ms", {})
        for name, value in phase_ms.items():
            phase_samples.setdefault(str(name), []).append(float(value or 0.0))
        evidence.append(
            {
                "status": scope["status"],
                "provider": scope.get("change_set", {}).get("provider"),
                "candidate_file_count": scope.get("change_set", {}).get("candidate_file_count"),
                "refreshed_files": scope.get("refreshed_files", []),
            }
        )
    ordered = sorted(samples)
    p95 = ordered[int(round((len(ordered) - 1) * 0.95))]
    evidence_pass = all(
        item["status"] == "refreshed"
        and item["provider"] == "git/v1"
        and item["refreshed_files"] == expected_files
        for item in evidence
    )
    return {
        "samples": len(samples),
        "p50_ms": round(ordered[len(ordered) // 2], 3),
        "p95_ms": round(p95, 3),
        "target_p95_ms": target_ms,
        "pass": p95 <= target_ms and evidence_pass,
        "evidence_pass": evidence_pass,
        "last_evidence": evidence[-1],
        "phase_p95_ms": {
            name: percentile(values, 0.95) for name, values in sorted(phase_samples.items())
        },
    }


def percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * ratio))
    return round(ordered[index], 3)


def run_changed_only_refresh(project: Project, scope_id: int) -> dict[str, Any]:
    args = argparse.Namespace(
        project=str(project.root),
        memory_home=str(project.memory_home),
        scope_id=scope_id,
        changed_only=True,
        json=True,
    )
    with contextlib.redirect_stdout(io.StringIO()):
        maintain_refresh_scope(args)
    return json.loads(
        (project.runtime_dir / "last_refresh_scope.json").read_text(encoding="utf-8")
    )


__all__ = [
    "GitChangeError",
    "MAINTENANCE_SLO_MS",
    "TARGET_PATH",
    "benchmark_incremental_maintenance",
    "method_source",
]
