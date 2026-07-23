# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from .agent_benchmark_cases import load_case_pack
from .benchmark_case_seal import case_pack_seal_audit, seal_case_pack
from .records import output
from .storage import ensure_initialized, now_iso, resolve_project


def eval_seal_cases_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    source_path = getattr(args, "source", None)
    source = (
        Path(source_path).expanduser().resolve()
        if source_path else project.root
    )
    if not source.is_dir():
        raise SystemExit(f"benchmark seal source directory not found: {source}")
    case_path = Path(args.cases).expanduser()
    pack = load_case_pack(case_path)
    source_audit = source_revision_audit(source, pack)
    sealed = seal_case_pack(pack, now_iso())
    target = Path(args.target).expanduser()
    if target.exists() and not bool(args.force):
        raise SystemExit(f"sealed case target already exists: {target}; pass --force to replace")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(sealed, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output({
        "schema_version": "agent-benchmark-case-seal-result/v1",
        "source_case_file": str(case_path),
        "sealed_case_file": str(target),
        "source_project": str(source),
        "source_revision_audit": source_audit,
        "case_seal": case_pack_seal_audit(sealed),
        "next_gate": "eval-context-capability",
    }, args.json)


def source_revision_audit(source: Path, pack: dict[str, Any]) -> dict[str, Any]:
    if not (source / ".git").exists():
        raise SystemExit(f"benchmark seal source is not a Git repository: {source}")
    audited = []
    for case in pack.get("cases") or []:
        audited.append(audit_case_revision(source, case))
    return {
        "status": "verified",
        "case_count": len(audited),
        "cases": audited,
    }


def audit_case_revision(source: Path, case: dict[str, Any]) -> dict[str, Any]:
    case_id = str(case.get("id") or "<unknown>")
    source_spec = case.get("source") if isinstance(case.get("source"), dict) else {}
    before = str(source_spec.get("before_revision") or "").strip()
    after = str(source_spec.get("after_revision") or "").strip()
    verify_commit(source, before, case_id, "before_revision")
    verify_commit(source, after, case_id, "after_revision")
    provenance = (
        case.get("provenance") if isinstance(case.get("provenance"), dict) else {}
    )
    fix_commit = str(provenance.get("fix_commit") or "").strip()
    if fix_commit and resolved_commit(source, fix_commit) != resolved_commit(source, after):
        raise SystemExit(f"sealed case {case_id} fix commit does not match after revision")
    expected = set(string_list(source_spec.get("changed_files")))
    observed = set(changed_files(source, before, after))
    if not expected or not expected <= observed:
        missing = sorted(expected - observed) or ["<empty expected changed_files>"]
        raise SystemExit(
            f"sealed case {case_id} changed files do not match Git diff: {', '.join(missing)}"
        )
    return {
        "case_id": case_id,
        "before_revision": resolved_commit(source, before),
        "after_revision": resolved_commit(source, after),
        "changed_file_count": len(observed),
        "expected_changed_files_verified": len(expected),
    }


def verify_commit(source: Path, revision: str, case_id: str, label: str) -> None:
    if not revision:
        raise SystemExit(f"sealed case {case_id} requires {label}")
    process = run_git(source, "cat-file", "-e", f"{revision}^{{commit}}")
    if process.returncode != 0:
        raise SystemExit(f"sealed case {case_id} has unknown {label}: {revision}")


def resolved_commit(source: Path, revision: str) -> str:
    process = run_git(source, "rev-parse", f"{revision}^{{commit}}")
    if process.returncode != 0:
        raise SystemExit(f"failed to resolve benchmark revision: {revision}")
    return process.stdout.strip()


def changed_files(source: Path, before: str, after: str) -> list[str]:
    process = run_git(source, "diff", "--name-only", before, after)
    if process.returncode != 0:
        raise SystemExit("failed to inspect benchmark revision diff")
    return [line.strip() for line in process.stdout.splitlines() if line.strip()]


def run_git(source: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=source,
        text=True,
        capture_output=True,
        check=False,
    )


def string_list(value: Any) -> list[str]:
    return [str(item).strip() for item in value or [] if str(item).strip()]
