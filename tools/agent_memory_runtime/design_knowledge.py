# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .text import query_tokens


CATALOG_PATH = Path(__file__).with_name("resources") / "design_knowledge_catalog_v1.json"
DEFAULT_KNOWLEDGE = {"smallest_viable_design", "information_hiding"}
CONCERN_TERMS = {
    "performance": ("performance", "latency", "throughput", "cache", "性能", "延迟", "吞吐", "缓存"),
    "compatibility": ("compatibility", "compatible", "migration", "api", "兼容", "迁移", "接口"),
    "reliability": ("reliability", "failure", "retry", "timeout", "recovery", "可靠", "失败", "重试", "超时", "恢复"),
    "security": ("security", "permission", "auth", "privacy", "安全", "权限", "认证", "隐私"),
    "maintainability": ("maintain", "refactor", "coupling", "module", "维护", "重构", "耦合", "模块"),
    "modifiability": ("change", "extension", "variation", "修改", "扩展", "变化"),
    "testability": ("test", "mock", "verify", "测试", "验证", "可测"),
    "flexibility": ("policy", "provider", "variant", "strategy", "策略", "多实现", "规则"),
}


def load_design_catalog() -> dict[str, Any]:
    try:
        value = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"unable to load design knowledge catalog: {exc}") from exc
    if value.get("schema_version") != "design-knowledge-catalog/v1" or not isinstance(value.get("entries"), list):
        raise SystemExit("design knowledge catalog has an unsupported shape")
    return value


def routing_hints(query: str, explicit_concerns: list[str]) -> list[dict[str, Any]]:
    text = query.casefold()
    explicit = unique(explicit_concerns)
    hints: list[dict[str, Any]] = [
        {"concern": value, "origin": "agent_explicit", "matched_terms": []}
        for value in explicit
    ]
    for concern, terms in CONCERN_TERMS.items():
        if concern in explicit:
            continue
        matched = [term for term in terms if term.casefold() in text]
        if matched:
            hints.append({"concern": concern, "origin": "lexical_routing_hint", "matched_terms": matched[:4]})
    return hints[:10]


def select_design_knowledge(
    query: str,
    concerns: list[str],
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    catalog = load_design_catalog()
    concern_set = set(concerns)
    tokens = {token.casefold() for token in query_tokens(query) if len(token) > 2}
    ranked: list[tuple[int, str, dict[str, Any], list[str]]] = []
    for entry in catalog["entries"]:
        quality = set(entry["quality_attributes"])
        terms = {str(term).casefold() for term in entry["terms"]}
        concern_matches = sorted(concern_set & quality)
        term_matches = sorted(token for token in tokens if any(token in term or term in token for term in terms))
        baseline = entry["id"] in DEFAULT_KNOWLEDGE
        relevance = len(concern_matches) * 4 + len(term_matches) * 2 + int(baseline)
        if relevance:
            match_reasons = [*(f"concern:{value}" for value in concern_matches), *(f"term:{value}" for value in term_matches)]
            if baseline and not match_reasons:
                match_reasons.append("baseline:general_design_guardrail")
            ranked.append((relevance, entry["id"], entry, match_reasons))
    ranked.sort(key=lambda value: (-value[0], value[1]))
    selected = [knowledge_payload(entry, reasons) for _, _, entry, reasons in ranked[:limit]]
    return selected, {
        "catalog_schema": catalog["schema_version"],
        "catalog_sources": catalog["sources"],
        "entry_count": len(catalog["entries"]),
        "returned_count": len(selected),
        "truncated": len(ranked) > limit,
    }


def knowledge_payload(entry: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
    return {
        **entry,
        "authority": "general_advisory_knowledge",
        "applicability_status": "agent_must_evaluate",
        "match_reasons": reasons,
        "provenance": [{"kind": "catalog_source", "ref": value} for value in entry["source_refs"]],
    }


def unique(values: list[str] | None) -> list[str]:
    return list(dict.fromkeys(str(value).strip().casefold() for value in (values or []) if str(value).strip()))
