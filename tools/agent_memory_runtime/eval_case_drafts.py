# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .models import Project
from .records import output, row_dict
from .storage import connect, ensure_initialized, resolve_project


def eval_draft_cases_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    data = write_eval_case_drafts(
        project,
        Path(args.target),
        limit=int(getattr(args, "limit", 5) or 5),
        force=bool(getattr(args, "force", False)),
    )
    output(data, args.json)


def write_eval_case_drafts(project: Project, target: Path, limit: int = 5, force: bool = False) -> dict[str, Any]:
    target.mkdir(parents=True, exist_ok=True)
    drafts = build_eval_case_drafts(project, limit)
    written: list[str] = []
    skipped: list[str] = []
    for filename, cases in drafts.items():
        if not cases:
            continue
        path = target / filename
        if path.exists() and not force:
            skipped.append(str(path))
            continue
        path.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(str(path))
    readme = target / "README.md"
    if not readme.exists() or force:
        readme.write_text(draft_readme(), encoding="utf-8")
        written.append(str(readme))
    return {
        "project_id": project.project_id,
        "target": str(target),
        "draft_counts": {name: len(cases) for name, cases in drafts.items()},
        "written": written,
        "skipped": skipped,
        "force": force,
        "next_steps": [
            "Review every draft before moving it into docs/eval.",
            "Replace TODO anchors with concrete expected records or claims.",
            "Run eval-quality with --cases-dir <draft-dir> before activating any draft.",
        ],
    }


def build_eval_case_drafts(project: Project, limit: int) -> dict[str, list[dict[str, Any]]]:
    return {
        "golden-retrieval.draft.json": query_miss_retrieval_drafts(project, limit),
        "golden-evidence-attribution.draft.json": weak_evidence_claim_drafts(project, limit),
    }


def query_miss_retrieval_drafts(project: Project, limit: int) -> list[dict[str, Any]]:
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT id, query, source, miss_count, last_seen_at, result_counts
            FROM query_misses
            WHERE project_id = ? AND status = 'open'
            ORDER BY miss_count DESC, last_seen_at DESC, id DESC
            LIMIT ?
            """,
            (project.project_id, limit),
        ).fetchall()
    cases: list[dict[str, Any]] = []
    for row in rows:
        item = row_dict(row)
        cases.append(
            {
                "name": f"draft-query-miss-{item['id']}",
                "query": item.get("query"),
                "expected_memory_intent_v2": "general_context",
                "expected": [
                    {
                        "type": "semantic_facts",
                        "text": "TODO: replace with expected anchor after learning or reflection",
                    }
                ],
                "must_not_include": [],
                "draft_source": {
                    "kind": "query_miss",
                    "id": item.get("id"),
                    "source": item.get("source"),
                    "miss_count": item.get("miss_count"),
                    "last_seen_at": item.get("last_seen_at"),
                },
            }
        )
    return cases


def weak_evidence_claim_drafts(project: Project, limit: int) -> list[dict[str, Any]]:
    trace = read_runtime_json(project, "last_task_trace.json")
    quality = trace.get("auto_summary_quality") if isinstance(trace.get("auto_summary_quality"), dict) else {}
    missing = set(quality.get("missing_fields") or [])
    template = trace.get("reflection_payload_template") if isinstance(trace.get("reflection_payload_template"), dict) else {}
    if "evidence" not in missing and "verification_method" not in missing:
        return []
    query = str(template.get("problem") or (trace.get("queries") or [""])[-1] or "").strip()
    claim = str(template.get("reasoning_summary") or trace.get("auto_summary") or "TODO: replace with the exact claim to ground").strip()
    if not query:
        return []
    return [
        {
            "name": "draft-weak-evidence-claim",
            "query": query,
            "claims": [claim[:240]],
            "min_grounded_rate": 0.8,
            "max_unsupported_claims": 0,
            "draft_source": {
                "kind": "last_task_trace",
                "sample_id": trace.get("sample_id"),
                "missing_fields": list(missing)[:limit],
            },
        }
    ]


def read_runtime_json(project: Project, filename: str) -> dict[str, Any]:
    path = project.runtime_dir / filename
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def draft_readme() -> str:
    return """# Draft Golden Eval Cases

These files are generated from runtime signals such as query misses and weak evidence traces.

They are review-only drafts. Do not copy them into `docs/eval` until a human or Agent has replaced TODO anchors with project-specific expected records, claims, or log examples.
"""
