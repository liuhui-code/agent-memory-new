# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from collections import Counter
from typing import Any


EVENT_RELATIONS = {"registers_callback", "dispatches_event", "handles_event"}


def build_design_guidance(
    model: dict[str, Any],
    intent: dict[str, Any],
) -> dict[str, Any]:
    architecture = model["architecture"]
    text = intent_text(intent)
    forces = detect_forces(text)
    existing = recognize_existing_patterns(architecture)
    candidates = match_pattern_candidates(text, forces, architecture)
    principles = evaluate_principles(forces, architecture)
    return {
        "schema_version": "design-guidance/v1",
        "forces": forces,
        "existing_patterns": existing,
        "pattern_candidates": candidates,
        "principle_checks": principles,
        "required_decisions": unique_strings(
            decision
            for candidate in candidates
            for decision in candidate["required_decisions"]
        )[:8],
        "pattern_policy": {
            "structural_evidence_required": True,
            "intent_name_alone_is_not_proof": True,
            "prefer_no_pattern_over_forced_pattern": True,
            "candidate_limit": 5,
        },
        "audit": {
            "llm_used": False,
            "persisted": False,
            "bounded": True,
            "node_count": len(architecture["nodes"]),
            "edge_count": len(architecture["edges"]),
        },
    }


def intent_text(intent: dict[str, Any]) -> str:
    values = [
        intent["goal"],
        *intent["constraints"],
        *intent["acceptance_criteria"],
        *intent["open_questions"],
    ]
    return " ".join(str(value).lower() for value in values)


def detect_forces(text: str) -> list[dict[str, Any]]:
    definitions = (
        ("performance", ("cache", "latency", "performance", "缓存", "延迟", "性能"), "Reduce repeated or expensive work."),
        ("state_ownership", ("state", "session", "profile", "状态", "会话", "资料"), "Keep mutable state ownership and invalidation explicit."),
        ("behavior_variation", ("algorithm", "policy", "provider", "variant", "算法", "策略", "规则", "多实现"), "Isolate a behavior that changes independently."),
        ("external_integration", ("sdk", "external", "third-party", "legacy", "第三方", "外部", "旧接口", "适配"), "Protect internal code from an external contract."),
        ("event_propagation", ("event", "notify", "callback", "reactive", "事件", "通知", "回调", "响应式"), "Coordinate change without hidden temporal coupling."),
        ("compatibility", ("compatible", "public api", "migration", "兼容", "公开接口", "迁移"), "Preserve consumers while changing implementation."),
        ("reliability", ("failure", "fallback", "retry", "timeout", "失败", "降级", "重试", "超时"), "Make failure handling and recovery observable."),
    )
    return [
        {"id": force_id, "reason": reason, "matched_terms": matched[:4]}
        for force_id, terms, reason in definitions
        if (matched := [term for term in terms if term in text])
    ]


def recognize_existing_patterns(architecture: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = architecture["nodes"]
    edges = architecture["edges"]
    layers = sorted({node["layer"] for node in nodes if node["layer"] not in {"config", "test"}})
    paths = [str(node.get("file_path") or "") for node in nodes]
    relations = Counter(str(edge["relation"]) for edge in edges)
    patterns: list[dict[str, Any]] = []
    if len(layers) >= 2:
        patterns.append(existing_pattern(
            "layered_boundaries",
            "Structural layers are present; preserve dependency direction unless the design explicitly replaces it.",
            [f"layer:{layer}" for layer in layers[:6]],
        ))
    repository_paths = sorted({path for path in paths if "repository" in path.lower()})
    if repository_paths:
        patterns.append(existing_pattern(
            "repository_boundary",
            "Repository-named code provides an existing data-access boundary.",
            repository_paths[:6],
        ))
    event_evidence = [relation for relation in sorted(EVENT_RELATIONS) if relations[relation]]
    if event_evidence:
        patterns.append(existing_pattern(
            "observer_collaboration",
            "Callback or event relations indicate observer-like collaboration.",
            [f"relation:{relation}" for relation in event_evidence],
        ))
    if relations["awaits"]:
        patterns.append(existing_pattern(
            "async_orchestration",
            "Await relations establish asynchronous control-flow boundaries.",
            ["relation:awaits"],
        ))
    return patterns[:6]


def existing_pattern(pattern_id: str, rationale: str, evidence: list[str]) -> dict[str, Any]:
    return {
        "id": pattern_id,
        "confidence": "structural",
        "rationale": rationale,
        "evidence": evidence,
    }


def match_pattern_candidates(
    text: str,
    forces: list[dict[str, Any]],
    architecture: dict[str, Any],
) -> list[dict[str, Any]]:
    force_ids = {item["id"] for item in forces}
    layers = {node["layer"] for node in architecture["nodes"]}
    relations = {str(edge["relation"]) for edge in architecture["edges"]}
    paths = [str(node.get("file_path") or "").lower() for node in architecture["nodes"]]
    candidates: list[dict[str, Any]] = []
    if "performance" in force_ids:
        candidates.append(pattern_candidate(
            "cache_aside",
            "candidate" if "data" in layers or any("repository" in path for path in paths) else "needs_evidence",
            "The goal includes repeated-work or latency pressure.",
            ["force:performance"],
            ["stable cache key", "bounded staleness or explicit invalidation", "source fallback"],
            ["strong consistency" if has_any(text, ("strong consistency", "强一致")) else ""],
            ["cache owner", "invalidation boundary", "concurrent miss behavior", "failure fallback"],
        ))
    if "behavior_variation" in force_ids:
        candidates.append(pattern_candidate(
            "strategy",
            "candidate" if architecture["extension_points"] else "needs_evidence",
            "The goal contains an independently varying policy or behavior.",
            ["force:behavior_variation"],
            ["at least two credible behaviors", "one stable caller contract"],
            ["single fixed behavior"],
            ["selection owner", "strategy lifetime", "fallback behavior"],
        ))
    if "external_integration" in force_ids:
        candidates.append(pattern_candidate(
            "adapter",
            "candidate" if "service" in layers or "consumes_api" in relations else "needs_evidence",
            "The goal crosses an external or legacy contract.",
            ["force:external_integration"],
            ["internal contract can remain stable", "translation boundary is identifiable"],
            ["external contract is already the internal domain contract"],
            ["translation owner", "error mapping", "version compatibility"],
        ))
    if "event_propagation" in force_ids:
        candidates.append(pattern_candidate(
            "observer",
            "candidate" if relations & EVENT_RELATIONS else "needs_evidence",
            "The goal requires one change to reach independent consumers.",
            ["force:event_propagation"],
            ["publisher does not require consumer results", "subscription lifecycle is controllable"],
            ["strict request-response ordering"],
            ["subscription owner", "delivery ordering", "unsubscription and failure behavior"],
        ))
    if has_any(text, ("repository", "persistence", "storage", "data source", "仓储", "持久化", "存储", "数据源")):
        candidates.append(pattern_candidate(
            "repository",
            "candidate" if "data" in layers else "needs_evidence",
            "The goal changes data access while callers need a stable domain-facing boundary.",
            ["layer:data"] if "data" in layers else ["gap:data_boundary"],
            ["data operations form a cohesive boundary"],
            ["simple local value with no data-source variation"],
            ["transaction owner", "domain-to-storage mapping", "failure semantics"],
        ))
    return candidates[:5]


def pattern_candidate(
    pattern_id: str,
    status: str,
    rationale: str,
    evidence: list[str],
    preconditions: list[str],
    contraindications: list[str],
    decisions: list[str],
) -> dict[str, Any]:
    return {
        "id": pattern_id,
        "status": "caution" if any(contraindications) else status,
        "rationale": rationale,
        "evidence": evidence,
        "preconditions": preconditions,
        "contraindications": [item for item in contraindications if item],
        "required_decisions": decisions,
    }


def evaluate_principles(
    forces: list[dict[str, Any]],
    architecture: dict[str, Any],
) -> list[dict[str, Any]]:
    force_ids = {item["id"] for item in forces}
    nodes = {node["id"]: node for node in architecture["nodes"]}
    ui_to_data = [
        edge for edge in architecture["edges"]
        if nodes.get(edge["source"], {}).get("layer") == "ui"
        and nodes.get(edge["target"], {}).get("layer") == "data"
    ]
    state_status = "needs_evidence" if "state_ownership" in force_ids and not architecture["state_owners"] else "apply"
    observability_status = (
        "needs_evidence"
        if force_ids & {"performance", "reliability", "event_propagation"}
        and not architecture["observability_anchors"]
        else "apply"
    )
    return [
        principle("smallest_viable_design", "apply", "Add abstraction only for a demonstrated variation, ownership, or boundary problem.", []),
        principle(
            "dependency_direction",
            "risk" if ui_to_data else "apply",
            "Keep UI and integration details from owning domain or data behavior.",
            [str(edge["id"]) for edge in ui_to_data[:6]],
        ),
        principle(
            "single_state_owner",
            state_status,
            "Keep mutable state ownership singular or define synchronization explicitly.",
            [item["owner"] for item in architecture["state_owners"][:6]],
        ),
        principle(
            "information_hiding",
            "apply",
            "Place changing implementation details behind the nearest stable responsibility boundary.",
            [item["id"] for item in architecture["extension_points"][:4]],
        ),
        principle(
            "observable_failure_semantics",
            observability_status,
            "Every new high-risk branch needs an inspectable result or failure path.",
            [item["id"] for item in architecture["observability_anchors"][:4]],
        ),
    ]


def principle(principle_id: str, status: str, guidance: str, evidence: list[str]) -> dict[str, Any]:
    return {"id": principle_id, "status": status, "guidance": guidance, "evidence": evidence}


def has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def unique_strings(values: Any) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))
