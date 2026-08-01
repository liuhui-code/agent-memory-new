# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

from .benchmark_context_setup import apply_context_setup
from .benchmark_memory import isolated_memory_access, prepare_isolated_memory
from .benchmark_workspace import materialized_workspace


EXECUTION_SCHEMA = "agent-context-capability-execution/v1"
ObserveCase = Callable[
    [Path, dict[str, Any], dict[str, Any], int, int, dict[str, int]],
    dict[str, Any],
]


def collect_context_capability_batch(
    source: Path,
    cases: list[dict[str, Any]],
    timeout: int,
    observe_case: ObserveCase,
) -> dict[str, Any]:
    started = time.monotonic()
    observations: list[dict[str, Any]] = []
    source_audits: list[dict[str, Any]] = []
    totals = {
        "source_materialize_ms": 0,
        "index_prepare_ms": 0,
        "setup_prepare_ms": 0,
        "case_snapshot_ms": 0,
    }
    plan = preparation_plan(cases)
    setup_group_count = sum(len(group["setup_groups"]) for group in plan)
    for source_group in plan:
        source_audit = collect_source_group(
            source,
            source_group,
            timeout,
            observe_case,
            observations,
        )
        source_audits.append(source_audit)
        for key in totals:
            totals[key] += int(source_audit[key])
    return {
        "observations": observations_in_case_order(cases, observations),
        "execution": {
            "schema_version": EXECUTION_SCHEMA,
            "strategy": "shared-index-isolated-case-snapshot",
            "expanded_case_count": len(cases),
            "source_group_count": len(plan),
            "setup_group_count": setup_group_count,
            "index_build_count": len(plan),
            "case_snapshot_count": len(cases),
            "avoided_index_build_count": max(0, len(cases) - len(plan)),
            **totals,
            "batch_elapsed_ms": elapsed_ms(started),
            "source_groups": source_audits,
        },
    }


def collect_source_group(
    source: Path,
    group: dict[str, Any],
    timeout: int,
    observe_case: ObserveCase,
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    materialize_started = time.monotonic()
    with materialized_workspace(source, group["cases"][0]) as workspace:
        materialize_ms = elapsed_ms(materialize_started)
        index_started = time.monotonic()
        base_memory = prepare_isolated_memory(
            workspace,
            workspace.parent / "indexed-memory",
            timeout,
            str(group["cases"][0]["task_type"]),
        )
        index_ms = elapsed_ms(index_started)
        setup_ms = 0
        snapshot_ms = 0
        setup_audits: list[dict[str, Any]] = []
        for setup_index, setup_group in enumerate(group["setup_groups"]):
            with prepared_setup_snapshot(
                base_memory,
                workspace,
                setup_group,
                timeout,
                setup_index,
            ) as (setup_memory, fixture_counts, prepared_ms):
                setup_ms += prepared_ms
                case_copy_ms = collect_setup_group(
                    workspace,
                    setup_memory,
                    setup_group,
                    timeout,
                    index_ms + prepared_ms,
                    fixture_counts,
                    observe_case,
                    observations,
                )
                snapshot_ms += case_copy_ms
                setup_audits.append({
                    "setup_digest": setup_group["setup_digest"],
                    "task_type": setup_group["task_type"],
                    "case_count": len(setup_group["cases"]),
                    "reflection_count": fixture_counts["reflection_count"],
                    "setup_prepare_ms": prepared_ms,
                    "case_snapshot_ms": case_copy_ms,
                })
        return {
            "source_digest": group["source_digest"],
            "case_count": len(group["cases"]),
            "setup_group_count": len(group["setup_groups"]),
            "source_materialize_ms": materialize_ms,
            "index_prepare_ms": index_ms,
            "setup_prepare_ms": setup_ms,
            "case_snapshot_ms": snapshot_ms,
            "setup_groups": setup_audits,
        }


def collect_setup_group(
    workspace: Path,
    setup_memory: dict[str, Any],
    setup_group: dict[str, Any],
    timeout: int,
    shared_prepare_ms: int,
    fixture_counts: dict[str, int],
    observe_case: ObserveCase,
    observations: list[dict[str, Any]],
) -> int:
    snapshot_total_ms = 0
    for case in setup_group["cases"]:
        with isolated_memory_snapshot(
            setup_memory,
            workspace,
            str(case["task_type"]),
        ) as (case_memory, snapshot_ms):
            snapshot_total_ms += snapshot_ms
            observations.append(observe_case(
                workspace,
                case_memory,
                case,
                timeout,
                shared_prepare_ms + snapshot_ms,
                fixture_counts,
            ))
    return snapshot_total_ms


@contextmanager
def prepared_setup_snapshot(
    base_memory: dict[str, Any],
    workspace: Path,
    setup_group: dict[str, Any],
    timeout: int,
    setup_index: int,
) -> Iterator[tuple[dict[str, Any], dict[str, int], int]]:
    setup = setup_group["context_setup"]
    if setup in (None, {}):
        yield base_memory, {"reflection_count": 0}, 0
        return
    started = time.monotonic()
    with isolated_memory_snapshot(
        base_memory,
        workspace,
        str(setup_group["task_type"]),
        prefix=f"agent-memory-setup-{setup_index}-",
    ) as (memory, _):
        fixture_counts = apply_context_setup(memory, setup, timeout)
        prepared_ms = elapsed_ms(started)
        yield memory, fixture_counts, prepared_ms


@contextmanager
def isolated_memory_snapshot(
    prepared_memory: dict[str, Any],
    workspace: Path,
    task_type: str,
    prefix: str = "agent-memory-case-",
) -> Iterator[tuple[dict[str, Any], int]]:
    source_home = Path(str(prepared_memory.get("memory_home") or "")).resolve()
    if not source_home.is_dir():
        raise SystemExit(f"prepared benchmark memory not found: {source_home}")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix=prefix, dir=workspace.parent) as directory:
        target_home = Path(directory) / "memory-home"
        shutil.copytree(source_home, target_home)
        memory = isolated_memory_access(workspace, target_home, task_type)
        yield memory, elapsed_ms(started)


def preparation_plan(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_groups: dict[str, dict[str, Any]] = {}
    for case in cases:
        source_value = case.get("source") if isinstance(case.get("source"), dict) else {}
        source_identity = canonical_json(source_value)
        source_group = source_groups.setdefault(source_identity, {
            "source_digest": digest(source_identity),
            "cases": [],
            "setup_groups": [],
            "_setup_by_identity": {},
        })
        source_group["cases"].append(case)
        setup_value = {
            "task_type": str(case.get("task_type") or ""),
            "context_setup": case.get("context_setup"),
        }
        setup_identity = canonical_json(setup_value)
        setup_group = source_group["_setup_by_identity"].get(setup_identity)
        if setup_group is None:
            setup_group = {
                "setup_digest": digest(setup_identity),
                "task_type": setup_value["task_type"],
                "context_setup": setup_value["context_setup"],
                "cases": [],
            }
            source_group["_setup_by_identity"][setup_identity] = setup_group
            source_group["setup_groups"].append(setup_group)
        setup_group["cases"].append(case)
    for group in source_groups.values():
        group.pop("_setup_by_identity", None)
    return list(source_groups.values())


def observations_in_case_order(
    cases: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    order = {str(case["id"]): index for index, case in enumerate(cases)}
    return sorted(
        observations,
        key=lambda item: order.get(str(item.get("case_id") or ""), len(order)),
    )


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))
