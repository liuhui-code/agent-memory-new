# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from collections import defaultdict
from typing import Any


def evaluate_rules(
    rules: list[dict[str, Any]],
    nodes: dict[str, dict[str, Any]],
    edges: list[dict[str, str]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for rule in rules:
        if rule["kind"] == "forbid_edge":
            findings.extend(forbidden_edge_findings(rule, nodes, edges))
        elif rule["kind"] == "require_edge":
            findings.extend(required_edge_findings(rule, nodes, edges))
        elif rule["kind"] == "single_owner":
            findings.extend(single_owner_findings(rule, edges))
    return findings


def forbidden_edge_findings(
    rule: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    edges: list[dict[str, str]],
) -> list[dict[str, Any]]:
    matches = [edge for edge in edges if edge_matches(rule, edge, nodes)]
    return [rule_finding(rule, "Forbidden architecture edge is present.", edge) for edge in matches]


def required_edge_findings(
    rule: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    edges: list[dict[str, str]],
) -> list[dict[str, Any]]:
    sources = [node for node in nodes.values() if node_matches(rule, node, "source")]
    covered = {edge["source"] for edge in edges if edge_matches(rule, edge, nodes, ignore_target_if_missing=True)}
    return [
        rule_finding(rule, "Required architecture edge is missing.", {"source": node["id"]})
        for node in sources if node["id"] not in covered
    ]


def single_owner_findings(rule: dict[str, Any], edges: list[dict[str, str]]) -> list[dict[str, Any]]:
    relation = str(rule.get("relation") or "owns_state")
    owners: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        if edge["relation"] == relation:
            owners[edge["target"]].add(edge["source"])
    return [
        rule_finding(rule, "Architecture target has multiple owners.", {"target": target, "owners": sorted(values)})
        for target, values in owners.items() if len(values) > 1
    ]


def edge_matches(
    rule: dict[str, Any],
    edge: dict[str, str],
    nodes: dict[str, dict[str, Any]],
    ignore_target_if_missing: bool = False,
) -> bool:
    relation = rule.get("relation")
    if relation and edge["relation"] != relation:
        return False
    source = nodes.get(edge["source"], {"id": edge["source"]})
    target = nodes.get(edge["target"], {"id": edge["target"]})
    if not node_matches(rule, source, "source"):
        return False
    target_filters = any(rule.get(f"target_{field}") for field in ("layer", "kind", "path_prefix"))
    return (ignore_target_if_missing and not target_filters) or node_matches(rule, target, "target")


def node_matches(rule: dict[str, Any], node: dict[str, Any], prefix: str) -> bool:
    layer = rule.get(f"{prefix}_layer")
    kind = rule.get(f"{prefix}_kind")
    path_prefix = rule.get(f"{prefix}_path_prefix")
    if layer and node.get("layer") != layer:
        return False
    if kind and node.get("kind") != kind:
        return False
    if path_prefix and not str(node.get("file_path") or "").startswith(str(path_prefix)):
        return False
    return True


def rule_finding(rule: dict[str, Any], message: str, evidence: Any) -> dict[str, Any]:
    return {
        "severity": rule["severity"],
        "code": f"rule:{rule['id']}",
        "message": message,
        "evidence": [evidence],
        "rule_id": rule["id"],
        "rationale": rule.get("rationale", ""),
    }
