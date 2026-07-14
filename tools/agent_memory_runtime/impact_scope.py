# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

from .evidence_collectors import collect_evidence_candidates, normalize_evidence
from .evidence_fusion import build_evidence_chains, evidence_gaps, evidence_tiers, fuse_evidence
from .design_evidence import EVIDENCE_RANK, evidence_class
from .goal_planner import build_goal_plan
from .impact_feedback import impact_feedback_summary, recommend_tests
from .models import Project
from .performance_scoring import append_performance_sample, build_performance_sample, estimate_payload_tokens, monotonic_ms
from .records import output, row_dict
from .repository_model import build_repository_model, public_repository_model
from .storage import connect, ensure_initialized, resolve_project
from .text import json_list, unique_list
from .usage_samples import record_query_usage


def impact_scope_command(args: argparse.Namespace) -> None:
    started_ms = monotonic_ms()
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    changed_files = resolve_changed_files(project, args.base, args.files, args.diff_file)
    payload = build_impact_scope(project, changed_files, args.query or "", args.max_items)
    persist_last_impact_scope(project, payload)
    usage_query = args.query or "change impact: " + " ".join(changed_files[:8])
    record_query_usage(project, "impact-scope", usage_query, _usage_view(payload))
    append_performance_sample(
        project,
        build_performance_sample(
            project,
            "impact-scope",
            monotonic_ms() - started_ms,
            payload["audit"]["counts_by_tier"],
            estimate_payload_tokens(payload),
        ),
    )
    output(payload, args.json)


def resolve_changed_files(
    project: Project,
    base: str,
    file_values: list[str] | None,
    diff_file: str | None,
    allow_empty: bool = False,
) -> list[str]:
    paths: list[str] = []
    for value in file_values or []:
        paths.extend(part.strip() for part in value.split(","))
    if diff_file:
        paths.extend(paths_from_diff(Path(diff_file).read_text(encoding="utf-8", errors="ignore")))
    if not paths:
        process = subprocess.run(
            ["git", "diff", "--name-only", base, "--"],
            cwd=project.root,
            text=True,
            capture_output=True,
            check=False,
        )
        if process.returncode:
            raise SystemExit(process.stderr.strip() or f"unable to read Git diff from {base}")
        paths.extend(process.stdout.splitlines())
    normalized = unique_preserved_paths(
        [normalize_project_path(project, path) for path in paths if path.strip()]
    )
    if not normalized and not allow_empty:
        raise SystemExit("no changed files found; pass --files, --diff-file, or a different --base")
    return normalized


def unique_preserved_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for path in paths:
        key = path.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def paths_from_diff(text: str) -> list[str]:
    paths: list[str] = []
    old_path: str | None = None
    for line in text.splitlines():
        if line.startswith("diff --git "):
            try:
                parts = shlex.split(line)
            except ValueError:
                parts = line.split()
            if len(parts) >= 4:
                paths.extend(_strip_diff_prefix(value) for value in parts[2:4])
            continue
        if line.startswith("--- "):
            value = line[4:].split("\t", 1)[0].strip()
            old_path = None if value == "/dev/null" else _strip_diff_prefix(value)
            continue
        if not line.startswith("+++ "):
            continue
        value = line[4:].split("\t", 1)[0].strip()
        if value == "/dev/null":
            if old_path:
                paths.append(old_path)
            continue
        paths.append(_strip_diff_prefix(value))
    return unique_preserved_paths(paths)


def _strip_diff_prefix(value: str) -> str:
    return value[2:] if value.startswith(("a/", "b/")) else value


def normalize_project_path(project: Project, value: str) -> str:
    candidate = Path(value.strip())
    absolute = candidate.resolve() if candidate.is_absolute() else (project.root / candidate).resolve()
    try:
        return absolute.relative_to(project.root).as_posix()
    except ValueError as exc:
        raise SystemExit(f"changed path is outside project: {value}") from exc


def build_impact_scope(
    project: Project,
    changed_files: list[str],
    user_query: str,
    max_items: int,
) -> dict[str, Any]:
    repository_model = build_repository_model(
        project,
        user_query or "change impact " + " ".join(changed_files[:8]),
        changed_files,
    )
    graph = collect_impact_graph(project, changed_files)
    query = build_impact_query(changed_files, graph["direct_rows"], user_query)
    plan = build_goal_plan(query, "change_impact", max_items)
    recalled, retrieval = collect_evidence_candidates(project, query)
    direct = [normalize_evidence(source, row) for source, row in graph["evidence_rows"]]
    changed_file_ids = {
        item.record_id for item in direct if item.kind == "code_file" and item.location in changed_files
    }
    for item in direct:
        if item.record_id in changed_file_ids and item.kind == "code_file":
            item.authority = "changed_source"
    ranked = fuse_evidence(deduplicate_evidence(direct + recalled), plan)
    risk = impact_risk(graph, ranked)
    related_files = unique_list(
        [str(link.get("source") or "") for link in graph["reverse_dependents"]]
        + [str(link.get("target") or "") for link in graph["outgoing_dependencies"]]
    )
    related_files = unique_preserved_paths([
        *related_files,
        *repository_related_files(repository_model, set(changed_files)),
    ])
    recommended_tests = recommend_tests(project, changed_files, related_files)
    tiers = evidence_tiers(ranked)
    gaps = evidence_gaps(ranked, plan)
    gaps.extend(
        {"kind": "unlearned_changed_file", "action": f"learn current source: {path}"}
        for path in graph["unlearned_files"]
    )
    return {
        "project_id": project.project_id,
        "project_path": str(project.root),
        "query": query,
        "goal_plan": plan.to_dict(),
        "repository_model": public_repository_model(repository_model),
        "changed_files": changed_files,
        "impact_summary": {
            "risk_score": risk["score"],
            "risk_band": risk["band"],
            "risk_reasons": risk["reasons"],
            "learned_changed_files": graph["learned_files"],
            "unlearned_changed_files": graph["unlearned_files"],
            "reverse_dependents": graph["reverse_dependents"],
            "outgoing_dependencies": graph["outgoing_dependencies"],
        },
        "evidence": tiers,
        "evidence_chains": build_evidence_chains(ranked),
        "evidence_gaps": gaps,
        "recommended_tests": recommended_tests,
        "verification_checklist": verification_checklist(graph, ranked, recommended_tests),
        "audit": {
            "graph_depth": 1,
            "candidate_counts": retrieval["candidate_counts"],
            "returned_count": len(ranked),
            "counts_by_tier": {key: len(value) for key, value in tiers.items()},
            "score_model": "bounded_change_impact_v1",
            "impact_feedback": impact_feedback_summary(project),
        },
    }


def repository_related_files(model: dict[str, Any], changed_files: set[str]) -> list[str]:
    architecture = model["architecture"]
    node_paths = {node["id"]: node["file_path"] for node in architecture["nodes"]}
    related: list[str] = []
    for edge in architecture["edges"]:
        source_path = node_paths.get(edge["source"], "")
        target_path = node_paths.get(edge["target"], "")
        if source_path in changed_files and target_path:
            related.append(target_path)
        if target_path in changed_files and source_path:
            related.append(source_path)
    return unique_preserved_paths(related)


def collect_impact_graph(project: Project, changed_files: list[str]) -> dict[str, Any]:
    placeholders = ",".join("?" for _ in changed_files)
    with connect(project) as conn:
        files = conn.execute(
            f"SELECT * FROM code_files WHERE project_id = ? AND file_path IN ({placeholders})",
            (project.project_id, *changed_files),
        ).fetchall()
        learned = {row["file_path"]: row_dict(row) for row in files}
        file_ids = {int(row["id"]): row["file_path"] for row in files}
        symbols = _rows_for_paths(conn, project, "code_symbols", changed_files)
        logs = _rows_for_paths(conn, project, "code_log_statements", changed_files)
        symbol_ids = {int(row["id"]): str(row["file_path"]) for row in symbols}
        edges = _edges_for_scope_ids(conn, project, list(file_ids), list(symbol_ids))
        endpoint_paths = _endpoint_paths(conn, project, edges)
        endpoint_paths.update({("code_file", key): value for key, value in file_ids.items()})
        endpoint_paths.update({("code_symbol", key): value for key, value in symbol_ids.items()})
    reverse, outgoing = classify_impact_edges(edges, set(changed_files), endpoint_paths)
    evidence_rows: list[tuple[str, dict[str, Any]]] = []
    evidence_rows.extend(("code", {**row, "kind": "file", "score": 100.0}) for row in learned.values())
    evidence_rows.extend(("code", {**row, "kind": "symbol", "score": 80.0}) for row in symbols)
    evidence_rows.extend(("log", {**row, "score": 80.0}) for row in logs)
    evidence_rows.extend(
        ("edge", {**row, "score": float(row.get("confidence") or 0.0) * 100.0})
        for row in edges
    )
    return {
        "direct_rows": list(learned.values()),
        "evidence_rows": evidence_rows,
        "learned_files": sorted(learned),
        "unlearned_files": sorted(set(changed_files) - set(learned)),
        "reverse_dependents": reverse,
        "outgoing_dependencies": outgoing,
        "symbols": symbols,
        "logs": logs,
        "edges": edges,
    }


def _rows_for_paths(conn: Any, project: Project, table: str, paths: list[str]) -> list[dict[str, Any]]:
    placeholders = ",".join("?" for _ in paths)
    rows = conn.execute(
        f"SELECT * FROM {table} WHERE project_id = ? AND file_path IN ({placeholders})",
        (project.project_id, *paths),
    ).fetchall()
    return [row_dict(row) for row in rows]


def _edges_for_scope_ids(
    conn: Any,
    project: Project,
    file_ids: list[int],
    symbol_ids: list[int],
) -> list[dict[str, Any]]:
    if not file_ids and not symbol_ids:
        return []
    file_placeholders = ",".join("?" for _ in file_ids) or "NULL"
    symbol_placeholders = ",".join("?" for _ in symbol_ids) or "NULL"
    rows = conn.execute(
        f"""
        SELECT * FROM memory_edges
        WHERE project_id = ? AND valid_to IS NULL AND (
          (source_type = 'code_file' AND source_id IN ({file_placeholders})) OR
          (target_type = 'code_file' AND target_id IN ({file_placeholders})) OR
          (source_type = 'code_symbol' AND source_id IN ({symbol_placeholders})) OR
          (target_type = 'code_symbol' AND target_id IN ({symbol_placeholders}))
        )
        ORDER BY confidence DESC, id DESC LIMIT 300
        """,
        (project.project_id, *file_ids, *file_ids, *symbol_ids, *symbol_ids),
    ).fetchall()
    return [row_dict(row) for row in rows]


def _endpoint_paths(conn: Any, project: Project, edges: list[dict[str, Any]]) -> dict[tuple[str, int], str]:
    result: dict[tuple[str, int], str] = {}
    for entity_type, table in (("code_file", "code_files"), ("code_symbol", "code_symbols")):
        ids = sorted({
            int(edge[key]) for edge in edges
            for type_key, key in (("source_type", "source_id"), ("target_type", "target_id"))
            if edge[type_key] == entity_type
        })
        if not ids:
            continue
        rows = conn.execute(
            f"SELECT id, file_path FROM {table} WHERE project_id = ? AND id IN ({','.join('?' for _ in ids)})",
            (project.project_id, *ids),
        ).fetchall()
        result.update({(entity_type, int(row["id"])): str(row["file_path"]) for row in rows})
    return result


def classify_impact_edges(
    edges: list[dict[str, Any]],
    changed_paths: set[str],
    paths: dict[tuple[str, int], str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    reverse: list[dict[str, Any]] = []
    outgoing: list[dict[str, Any]] = []
    for edge in edges:
        source = paths.get((str(edge["source_type"]), int(edge["source_id"])))
        target = paths.get((str(edge["target_type"]), int(edge["target_id"])))
        if target in changed_paths and source and source != target:
            reverse.append(_impact_link(edge, source, target))
        if source in changed_paths and target and source != target:
            outgoing.append(_impact_link(edge, source, target))
    return _unique_links(reverse), _unique_links(outgoing)


def _impact_link(edge: dict[str, Any], source: str | None, target: str | None) -> dict[str, Any]:
    precision = evidence_class(
        str(edge.get("evidence_kind") or "legacy"),
        str(edge.get("extractor_version") or "legacy"),
    )
    return {
        "source": source,
        "relation": edge.get("relation"),
        "target": target,
        "confidence": edge.get("confidence"),
        "evidence": edge.get("evidence"),
        "evidence_class": precision,
        "extractor_version": edge.get("extractor_version"),
    }


def _unique_links(links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    result: list[dict[str, Any]] = []
    ordered = sorted(
        links,
        key=lambda item: (
            -EVIDENCE_RANK.get(str(item.get("evidence_class") or "inferred"), 0),
            -float(item.get("confidence") or 0.0),
            str(item.get("source") or ""),
        ),
    )
    for link in ordered:
        key = (link["source"], link["relation"], link["target"])
        if key not in seen:
            result.append(link)
            seen.add(key)
    return result


def build_impact_query(changed: list[str], rows: list[dict[str, Any]], user_query: str) -> str:
    terms = [user_query]
    terms.extend(changed)
    for row in rows:
        terms.extend(json_list(row.get("business_terms")))
        if row.get("business_summary"):
            terms.append(str(row["business_summary"]))
    return " ".join(unique_list([term for term in terms if term]))[:2000]


def deduplicate_evidence(items: list[Any]) -> list[Any]:
    selected: dict[str, Any] = {}
    for item in items:
        previous = selected.get(item.evidence_id)
        if previous is None or item.original_score > previous.original_score:
            selected[item.evidence_id] = item
    return list(selected.values())


def impact_risk(graph: dict[str, Any], ranked: list[Any]) -> dict[str, Any]:
    reasons: list[str] = []
    score = min(35, len(graph["learned_files"]) * 8 + len(graph["unlearned_files"]) * 12)
    if graph["reverse_dependents"]:
        score += min(30, len(graph["reverse_dependents"]) * 10)
        reasons.append("reverse dependencies may be affected")
    high_logs = [row for row in graph["logs"] if str(row.get("level") or "").lower() in {"error", "fatal", "warn"}]
    if high_logs:
        score += min(15, len(high_logs) * 5)
        reasons.append("changed scope contains diagnostic warning/error logs")
    if graph["unlearned_files"]:
        reasons.append("some changed files are outside learned code coverage")
    if any(item.source == "incident" and item.final_score >= 60 for item in ranked):
        score += 10
        reasons.append("related incident evidence exists")
    score = min(100, score)
    band = "high" if score >= 70 else "medium" if score >= 30 else "low"
    return {"score": score, "band": band, "reasons": reasons or ["bounded direct change"]}


def verification_checklist(
    graph: dict[str, Any],
    ranked: list[Any],
    recommended_tests: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    for link in graph["reverse_dependents"][:5]:
        checks.append({"check": "dependent_path", "target": str(link.get("source") or "")})
    for row in graph["logs"][:3]:
        target = f"{row.get('file_path')}:{row.get('line')} {row.get('message_template')}"
        checks.append({"check": "runtime_signal", "target": target})
    for row in graph["symbols"][:5]:
        checks.append({"check": "changed_symbol", "target": f"{row.get('file_path')}::{row.get('symbol')}"})
    for item in recommended_tests or []:
        checks.append({"check": "recommended_test", "target": str(item.get("test_path") or "")})
    if not checks:
        checks.append({"check": "source_and_tests", "target": "inspect changed files and run focused tests"})
    return checks[:10]


def _usage_view(payload: dict[str, Any]) -> dict[str, Any]:
    counts = payload["audit"]["counts_by_tier"]
    return {
        "wiki_matches": [{} for _ in payload["impact_summary"]["learned_changed_files"]],
        "edge_matches": [{} for _ in payload["impact_summary"]["reverse_dependents"]],
        "code_log_matches": [],
        "semantic_facts": [],
        "reflections": [],
        "episodes": [],
        "incident_trace_matches": [],
        "followup_focus": "change_impact",
        "suggested_followup_terms": list(counts),
    }


def persist_last_impact_scope(project: Project, payload: dict[str, Any]) -> None:
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_impact_scope.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
