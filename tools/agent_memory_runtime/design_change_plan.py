# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

MAX_PLAN_STEPS = 200


def build_change_plan(proposal: dict[str, Any], architecture: dict[str, Any], revision: int) -> dict[str, Any]:
    targets = target_rows(proposal, architecture)
    steps = [build_step(index + 1, target, proposal) for index, target in enumerate(sorted(targets, key=target_key))]
    attach_dependencies(steps, architecture)
    cycles = find_cycles(steps)
    return {
        "schema_version": "change-plan/v1",
        "candidate_id": proposal["id"],
        "baseline_revision": revision,
        "status": "blocked" if cycles else "ready",
        "steps": steps[:MAX_PLAN_STEPS],
        "replan_triggers": [
            "baseline_revision_changed",
            "unexpected_consumer_discovered",
            "verification_obligation_failed",
        ],
        "cycles": cycles,
        "audit": {"bounded": True, "step_limit": MAX_PLAN_STEPS, "persisted": False},
    }


def target_rows(proposal: dict[str, Any], architecture: dict[str, Any]) -> list[dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for node_id in proposal["modify_nodes"]:
        rows[node_id] = {"id": node_id, "kind": "modify", "path": path_from_node_id(node_id) or "", "category": "implementation"}
    for node in proposal["add_nodes"]:
        node_id = str(node["id"])
        rows[node_id] = {
            "id": node_id,
            "kind": "add",
            "path": str(node.get("file_path") or path_from_node_id(node_id) or ""),
            "category": "implementation",
        }
    changed = set(rows)
    for edge in architecture["edges"]:
        if edge["target"] in changed and edge["source"] not in changed:
            rows[f"consumer:{edge['source']}"] = {
                "id": edge["source"],
                "kind": "review_consumer",
                "path": path_from_node_id(edge["source"]) or "",
                "category": "consumer",
            }
    for name in proposal["verification"]["tests"]:
        rows[f"test:{name}"] = {"id": f"test:{name}", "kind": "verify", "path": "", "category": "test"}
    for name in proposal["verification"]["observability"]:
        rows[f"observe:{name}"] = {"id": f"observe:{name}", "kind": "verify", "path": "", "category": "observability"}
    return list(rows.values())[:MAX_PLAN_STEPS]


def path_from_node_id(node_id: str) -> str | None:
    if node_id.startswith("file:"):
        return node_id[5:]
    if node_id.startswith("symbol:"):
        return node_id[7:].split("::", 1)[0]
    if node_id.startswith("log:"):
        return node_id[4:].rsplit(":", 1)[0]
    return None


def target_key(target: dict[str, str]) -> tuple[int, str]:
    category = target.get("category")
    path = target["path"].lower()
    node_id = target["id"].lower()
    if category == "consumer":
        rank = 30
    elif category == "test":
        rank = 50
    elif category == "observability":
        rank = 60
    elif any(term in node_id for term in ("schema", "api", "interface")):
        rank = 10
    elif any(term in path for term in ("service", "repository", "data", "core")):
        rank = 20
    elif any(term in path for term in ("page", "view", "component")):
        rank = 30
    elif any(term in path for term in ("config", "route", ".json")):
        rank = 40
    elif any(term in path for term in ("test", "spec")):
        rank = 50
    else:
        rank = 25
    return rank, target["id"]


def build_step(index: int, target: dict[str, str], proposal: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"step-{index:03d}",
        "order": index,
        "target": target["id"],
        "file_path": target["path"],
        "operation": target["kind"],
        "depends_on": [],
        "expected_delta": expected_delta(target["id"], proposal),
        "verification": {
            "tests": proposal["verification"]["tests"],
            "observability": proposal["verification"]["observability"],
            "invariants": proposal["invariants"],
        },
    }


def expected_delta(target: str, proposal: dict[str, Any]) -> dict[str, Any]:
    edges = [edge for edge in proposal["add_edges"] + proposal["remove_edges"] if target in {edge["source"], edge["target"]}]
    return {"node": target, "edges": edges[:20]}


def attach_dependencies(steps: list[dict[str, Any]], architecture: dict[str, Any]) -> None:
    step_by_target = {step["target"]: step for step in steps}
    for edge in architecture["edges"]:
        source = step_by_target.get(edge["source"])
        target = step_by_target.get(edge["target"])
        if source and target and target["order"] < source["order"]:
            source["depends_on"].append(target["id"])
    previous: str | None = None
    for step in steps:
        if previous and not step["depends_on"]:
            step["depends_on"].append(previous)
        step["depends_on"] = sorted(set(step["depends_on"]))
        previous = step["id"]


def find_cycles(steps: list[dict[str, Any]]) -> list[list[str]]:
    dependencies = {step["id"]: set(step["depends_on"]) for step in steps}
    remaining = set(dependencies)
    while remaining:
        ready = {node for node in remaining if not (dependencies[node] & remaining)}
        if not ready:
            return [sorted(remaining)]
        remaining -= ready
    return []
