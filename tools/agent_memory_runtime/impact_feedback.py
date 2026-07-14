# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .models import Project
from .records import output, row_dict
from .storage import connect, ensure_initialized, now_iso, resolve_project
from .text import tokenize, unique_list


IMPACT_OUTCOMES = {"pass", "fail", "partial", "unknown"}
GENERIC_PATH_TERMS = {
    "src", "source", "test", "tests", "spec", "specs", "app", "entry",
    "ets", "ts", "tsx", "js", "jsx", "py", "java", "kt", "cpp", "h",
}


def impact_feedback_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    changed_files, recommended = feedback_scope(project, args.files, args.recommended_tests)
    if args.outcome not in IMPACT_OUTCOMES:
        raise SystemExit(f"unsupported impact outcome: {args.outcome}")
    payload = {
        "project_id": project.project_id,
        "change_fingerprint": change_fingerprint(changed_files),
        "changed_files": changed_files,
        "recommended_tests": recommended,
        "executed_tests": csv_values(args.executed_tests),
        "outcome": args.outcome,
        "failed_tests": csv_values(args.failed_tests),
        "flaky_tests": csv_values(args.flaky_tests),
        "missed_targets": csv_values(args.missed_targets),
        "note": args.note,
        "created_at": now_iso(),
    }
    with connect(project) as conn:
        cursor = conn.execute(
            """
            INSERT INTO impact_feedback(
              project_id, change_fingerprint, changed_files, recommended_tests,
              executed_tests, outcome, failed_tests, flaky_tests, missed_targets,
              note, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                payload["change_fingerprint"],
                json.dumps(changed_files, ensure_ascii=False),
                json.dumps(recommended, ensure_ascii=False),
                json.dumps(payload["executed_tests"], ensure_ascii=False),
                args.outcome,
                json.dumps(payload["failed_tests"], ensure_ascii=False),
                json.dumps(payload["flaky_tests"], ensure_ascii=False),
                json.dumps(payload["missed_targets"], ensure_ascii=False),
                args.note,
                payload["created_at"],
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM impact_feedback WHERE id = ?", (cursor.lastrowid,)).fetchone()
    result = row_dict(row)
    for key in ("changed_files", "recommended_tests", "executed_tests", "failed_tests", "flaky_tests", "missed_targets"):
        result[key] = json.loads(result[key] or "[]")
    output(result, args.json)


def feedback_scope(
    project: Project,
    file_values: list[str] | None,
    recommended_values: list[str] | None,
) -> tuple[list[str], list[str]]:
    files = csv_values(file_values)
    recommended = csv_values(recommended_values)
    if files:
        return files, recommended
    path = project.runtime_dir / "last_impact_scope.json"
    if not path.exists():
        raise SystemExit("pass --files or run impact-scope first")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit("last impact scope is unreadable; pass --files") from exc
    files = [str(value) for value in data.get("changed_files") or []]
    if not recommended:
        recommended = [str(item.get("test_path")) for item in data.get("recommended_tests") or [] if item.get("test_path")]
    if not files:
        raise SystemExit("last impact scope has no changed files")
    return files, recommended


def recommend_tests(
    project: Project,
    changed_files: list[str],
    related_files: list[str] | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    static = static_test_candidates(project, changed_files, related_files or [])
    history = historical_test_scores(project, changed_files)
    candidates: dict[str, dict[str, Any]] = {}
    for path, score, reasons in static:
        candidates[path] = {"test_path": path, "score": score, "reasons": reasons, "flaky_warning": False}
    for path, values in history.items():
        item = candidates.setdefault(path, {"test_path": path, "score": 0.0, "reasons": [], "flaky_warning": False})
        item["score"] += values["score"]
        item["reasons"].extend(values["reasons"])
        item["flaky_warning"] = values["flaky"]
    ranked = list(candidates.values())
    for item in ranked:
        item["score"] = round(max(0.0, float(item["score"])), 3)
        item["reasons"] = unique_list([str(value) for value in item["reasons"]])
    ranked.sort(key=lambda item: (item["score"], item["test_path"]), reverse=True)
    return ranked[:limit]


def static_test_candidates(
    project: Project,
    changed_files: list[str],
    related_files: list[str],
) -> list[tuple[str, float, list[str]]]:
    terms = path_terms(changed_files)
    graph_terms = [term for term in path_terms(related_files) if term not in terms]
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT file_path, business_terms, business_summary
            FROM code_files
            WHERE project_id = ? AND (
              LOWER(file_path) LIKE '%test%' OR LOWER(file_path) LIKE '%spec%'
            )
            ORDER BY file_path LIMIT 500
            """,
            (project.project_id,),
        ).fetchall()
    candidates: list[tuple[str, float, list[str]]] = []
    for row in rows:
        text = f"{row['file_path']} {row['business_terms'] or ''} {row['business_summary'] or ''}".lower()
        matched = [term for term in terms if len(term) > 1 and term in text]
        graph_matched = [term for term in graph_terms if len(term) > 1 and term in text]
        if matched or graph_matched:
            score = min(20.0, 4.0 + len(matched) * 2.0 + len(graph_matched) * 1.0)
            reasons = (["static_name_or_semantic_match"] if matched else [])
            reasons.extend(["one_hop_graph_proximity"] if graph_matched else [])
            reasons.extend(matched[:2] + graph_matched[:2])
            candidates.append((str(row["file_path"]), score, reasons))
    return candidates


def path_terms(paths: list[str]) -> list[str]:
    values: list[str] = []
    for path in paths:
        stem = Path(path).stem
        values.append(stem.lower())
        values.extend(tokenize(path))
        values.extend(
            part.lower()
            for part in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", stem)
        )
    return [term for term in unique_list(values) if term not in GENERIC_PATH_TERMS]


def historical_test_scores(project: Project, changed_files: list[str]) -> dict[str, dict[str, Any]]:
    changed = set(changed_files)
    result: dict[str, dict[str, Any]] = {}
    with connect(project) as conn:
        rows = conn.execute(
            "SELECT * FROM impact_feedback WHERE project_id = ? ORDER BY id DESC LIMIT 200",
            (project.project_id,),
        ).fetchall()
    for row in rows:
        prior_changed = set(json.loads(row["changed_files"] or "[]"))
        similarity = len(changed & prior_changed) / max(1, len(changed | prior_changed))
        if similarity <= 0:
            continue
        failed = set(json.loads(row["failed_tests"] or "[]"))
        flaky = set(json.loads(row["flaky_tests"] or "[]"))
        executed = set(json.loads(row["executed_tests"] or "[]"))
        for path in failed | executed | flaky:
            item = result.setdefault(path, {"score": 0.0, "reasons": [], "flaky": False})
            if path in failed:
                item["score"] += 8.0 * similarity
                item["reasons"].append("historical_failure_for_similar_change")
            elif path in executed and row["outcome"] == "pass":
                item["score"] += 2.0 * similarity
                item["reasons"].append("historically_executed_for_similar_change")
            if path in flaky:
                item["score"] -= 4.0 * similarity
                item["reasons"].append("historically_flaky")
                item["flaky"] = True
    return result


def impact_feedback_summary(project: Project) -> dict[str, Any]:
    with connect(project) as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS count,
                   SUM(CASE WHEN outcome = 'fail' THEN 1 ELSE 0 END) AS failures,
                   SUM(CASE WHEN flaky_tests IS NOT NULL AND flaky_tests NOT IN ('', '[]') THEN 1 ELSE 0 END) AS flaky_cases,
                   SUM(CASE WHEN missed_targets IS NOT NULL AND missed_targets NOT IN ('', '[]') THEN 1 ELSE 0 END) AS missed_cases
            FROM impact_feedback WHERE project_id = ?
            """,
            (project.project_id,),
        ).fetchone()
    return {key: int(row[key] or 0) for key in ("count", "failures", "flaky_cases", "missed_cases")}


def change_fingerprint(changed_files: list[str]) -> str:
    material = "\n".join(sorted(path.strip() for path in changed_files if path.strip()))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def csv_values(values: list[str] | None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        for part in str(value).split(","):
            item = part.strip()
            key = item.casefold()
            if not item or key in seen:
                continue
            seen.add(key)
            result.append(item)
    return result
