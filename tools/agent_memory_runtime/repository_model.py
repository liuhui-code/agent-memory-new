# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .architecture_slice import build_architecture_slice
from .graph_quality_snapshot import load_graph_revision
from .models import Project
from .storage import connect


VIEW_RELATIONS = {
    "topology": set(),
    "ownership": {"defines_state", "owns_state", "reads_state", "writes_state"},
    "behavior": {"calls", "registers_callback", "dispatches_event", "handles_event", "awaits"},
    "data": {"reads_state", "writes_state", "uses_service", "consumes_api"},
    "failure": {"emits_log", "observed_by_log", "awaits"},
    "runtime": {"emits_log", "observed_by_log"},
    "change": {"imports", "calls", "consumes_api", "tested_by", "configured_by"},
}


def build_repository_model(
    project: Project,
    goal: str,
    scope_paths: list[str] | None = None,
    max_nodes: int = 80,
    max_edges: int = 160,
) -> dict[str, Any]:
    architecture = build_architecture_slice(
        project,
        [],
        goal,
        explicit_paths=scope_paths or [],
        max_nodes=max_nodes,
        max_edges=max_edges,
    )
    snapshot = repository_snapshot(project, architecture)
    views = {
        name: build_view(name, architecture, relations)
        for name, relations in VIEW_RELATIONS.items()
    }
    capabilities = [name for name, view in views.items() if view["status"] != "unsupported"]
    return {
        "schema_version": "repository-model/v2",
        "project_id": project.project_id,
        "goal": goal,
        "snapshot": snapshot,
        "capabilities": capabilities,
        "baseline_entry_points": architecture.get("baseline_entry_points", []),
        "scope_entry_points": architecture.get("scope_entry_points", []),
        "views": views,
        "architecture": architecture,
        "evidence_gaps": architecture["evidence_gaps"],
        "audit": {
            "candidate_independent_baseline": True,
            "bounded": True,
            "persisted": False,
        },
    }


def repository_snapshot(project: Project, architecture: dict[str, Any]) -> dict[str, Any]:
    with connect(project) as conn:
        revision = load_graph_revision(conn, project.project_id)
        counts = {
            table: int(conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE project_id = ?",
                (project.project_id,),
            ).fetchone()[0])
            for table in ("code_files", "code_symbols", "code_log_statements")
        }
        active_edges = int(conn.execute(
            "SELECT COUNT(*) FROM memory_edges WHERE project_id = ? AND valid_to IS NULL",
            (project.project_id,),
        ).fetchone()[0])
    gaps = architecture.get("evidence_gaps") or []
    return {
        "schema_version": "repository-snapshot/v2",
        "graph_revision": revision,
        **source_freshness(project, architecture, counts["code_files"]),
        "counts": {**counts, "active_edges": active_edges},
        "truncated": bool(
            architecture["audit"].get("truncated_nodes")
            or architecture["audit"].get("truncated_edges")
        ),
        "gap_count": len(gaps),
    }


def source_freshness(project: Project, architecture: dict[str, Any], file_count: int) -> dict[str, Any]:
    if not file_count:
        return {"freshness": "empty", "stale_paths": []}
    stale: list[str] = []
    checked = 0
    for node in architecture["nodes"]:
        if node["entity_type"] != "code_file":
            continue
        checked += 1
        source = Path(project.root) / node["file_path"]
        learned_at = parse_time(node.get("updated_at"))
        if not source.exists() or learned_at is None or source.stat().st_mtime > learned_at.timestamp() + 1.0:
            stale.append(node["file_path"])
    if stale:
        return {"freshness": "stale", "stale_paths": stale[:12], "freshness_checked_files": checked}
    if checked:
        return {"freshness": "current", "stale_paths": [], "freshness_checked_files": checked}
    return {"freshness": "unknown", "stale_paths": [], "freshness_checked_files": 0}


def parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def build_view(name: str, architecture: dict[str, Any], relations: set[str]) -> dict[str, Any]:
    edges = architecture["edges"] if not relations else [
        edge for edge in architecture["edges"] if edge["relation"] in relations
    ]
    node_ids = {value for edge in edges for value in (edge["source"], edge["target"])}
    if name == "runtime":
        node_ids.update(node["id"] for node in architecture["nodes"] if node["kind"] == "log")
    nodes = [node for node in architecture["nodes"] if node["id"] in node_ids]
    relation_counts = Counter(edge["relation"] for edge in edges)
    return {
        "status": "available" if edges or nodes or name == "topology" else "gap",
        "node_ids": [node["id"] for node in nodes[:12]],
        "edge_ids": [edge["id"] for edge in edges[:12]],
        "relations": dict(relation_counts),
        "truncated": len(nodes) > 12 or len(edges) > 12,
    }


def architecture_from_model(model: dict[str, Any]) -> dict[str, Any]:
    return model["architecture"]


def public_repository_model(model: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in model.items()
        if key != "architecture"
    }
