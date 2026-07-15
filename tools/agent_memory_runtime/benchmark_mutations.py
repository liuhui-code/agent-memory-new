# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Iterator, Optional

from .agent_benchmark_cases import generation_result, new_pack, write_case_pack
from .models import IGNORE_DIRS
from .records import output
from .storage import ensure_initialized, resolve_project


MutationBuilder = Callable[[str], Optional[tuple[str, str, int]]]


def eval_mutate_arkts_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    source = Path(args.source).expanduser().resolve() if args.source else project.root
    cases = build_mutation_cases(source, int(args.limit), args.operator)
    if not cases:
        raise SystemExit("no eligible ArkTS/TypeScript mutation sites found")
    pack = new_pack("arkts-mutation/v1", str(source), cases)
    pack["audit"] = {
        "case_count": len(cases),
        "source_modified": False,
        "mutation_materialized": False,
        "oracle_known_by_construction": True,
    }
    target = Path(args.target).expanduser()
    write_case_pack(target, pack, bool(args.force))
    output(generation_result(pack, target), args.json)


def build_mutation_cases(root: Path, limit: int, selected_operator: str | None) -> list[dict[str, Any]]:
    revision = git_revision(root)
    builders = mutation_builders(selected_operator)
    cases: list[dict[str, Any]] = []
    for path in source_files(root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for operator, builder in builders:
            mutation = builder(text)
            if not mutation:
                continue
            original, replacement, start = mutation
            relative = path.relative_to(root).as_posix()
            line = text[:start].count("\n") + 1
            occurrence = text[:start].count(original) + 1
            cases.append(mutation_case(
                relative, revision, operator, line, original, replacement, occurrence, text
            ))
            if len(cases) >= max(1, limit):
                return cases
    return cases


def mutation_builders(selected: str | None) -> list[tuple[str, MutationBuilder]]:
    builders: list[tuple[str, MutationBuilder]] = [
        ("remove_await", remove_await),
        ("corrupt_route_target", corrupt_route_target),
        ("corrupt_resource_key", corrupt_resource_key),
    ]
    if selected:
        builders = [item for item in builders if item[0] == selected]
        if not builders:
            raise SystemExit(f"unsupported mutation operator: {selected}")
    return builders


def remove_await(text: str) -> tuple[str, str, int] | None:
    match = re.search(r"\bawait\s+(?=[A-Za-z_$])", text)
    return (match.group(0), "", match.start()) if match else None


def corrupt_route_target(text: str) -> tuple[str, str, int] | None:
    match = re.search(
        r"(?i)(?:pushUrl|replaceUrl|pushPath|replacePath)[\s\S]{0,160}?(['\"])(pages/[^'\"]+)\1",
        text,
    )
    if not match:
        return None
    original = match.group(2)
    return original, original + "__missing__", match.start(2)


def corrupt_resource_key(text: str) -> tuple[str, str, int] | None:
    match = re.search(r"\$r\(\s*(['\"])([^'\"]+)\1\s*\)", text)
    if not match:
        return None
    original = match.group(2)
    return original, original + "__missing__", match.start(2)


def mutation_case(
    file_path: str,
    revision: str,
    operator: str,
    line: int,
    original: str,
    replacement: str,
    occurrence: int,
    source_text: str,
) -> dict[str, Any]:
    category = {
        "remove_await": "async",
        "corrupt_route_target": "route",
        "corrupt_resource_key": "resource",
    }[operator]
    digest = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    case_hash = hashlib.sha256(f"{revision}:{file_path}:{operator}:{line}".encode()).hexdigest()[:12]
    return {
        "id": f"mutation-{case_hash}",
        "task_type": "diagnosis",
        "review_status": "validated",
        "task": {
            "description": mutation_symptom(operator),
            "constraints": ["Locate the injected regression without reading the hidden oracle"],
        },
        "source": {
            "before_revision": revision,
            "mutation": {
                "operator": operator,
                "file_path": file_path,
                "line": line,
                "source_digest": digest,
                "original": original,
                "replacement": replacement,
                "occurrence": occurrence,
            },
        },
        "provenance": {"kind": "mutation", "generator": "arkts-mutation/v1"},
        "oracle": {
            "expected_files": [file_path],
            "forbidden_files": [],
            "root_cause_category": category,
            "expected_causal_level": "supported",
            "verification_tests": [],
        },
        "leakage_guard": {"hidden_fields": ["oracle", "source.mutation.original"]},
    }


def mutation_symptom(operator: str) -> str:
    return {
        "remove_await": "An asynchronous operation now exposes an ordering or incomplete-result regression.",
        "corrupt_route_target": "Navigation reaches a missing target and the destination page does not open.",
        "corrupt_resource_key": "A referenced UI resource can no longer be resolved at runtime.",
    }[operator]


def source_files(root: Path) -> Iterator[Path]:
    for directory, names, files in os.walk(root):
        names[:] = sorted(name for name in names if name not in IGNORE_DIRS)
        for filename in sorted(files):
            path = Path(directory) / filename
            if path.suffix.lower() in {".ets", ".ts"}:
                yield path


def git_revision(root: Path) -> str:
    process = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=False
    )
    return process.stdout.strip() if process.returncode == 0 else "working-tree"
