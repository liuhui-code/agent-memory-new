# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Protocol

from .query_language import (
    excluded_code_candidate,
    excluded_result_identifiers,
    excluded_result_roles,
    positive_retrieval_query,
)
from .semantic_callable_profile import MULTI_TARGET_RE
from .text import identifier_tokens, unique_list


SCHEMA_VERSION = "agent-callable-evidence-set/v1"
MAX_MEMBERS = 3
IDENTITY_REASONS = {"exact_function", "exact_identifier", "exact_symbol"}
PRIMARY_SUPPORT_KINDS = {"typed_target_owner", "direct_identity", "graph_support"}
SINGLE_TARGET_RE = re.compile(
    r"\b(?:return|locate|find|identify)\s+(?:only\b|(?:the\s+)?(?:one|single)\b)|"
    r"\b(?:return|locate|find|identify)\s+the\s+"
    r"(?:ability|class|component|controller|coordinator|implementation|method|owner|"
    r"page|policy|repository|service|source|store|view|viewmodel)\b|"
    r"只返回|唯一(?:的)?(?:源码|方法|所有者|组件|页面|服务|协调器)",
    re.IGNORECASE,
)


class CallableEvidenceSetProvider(Protocol):
    def build(
        self,
        query: str,
        localization: dict[str, Any],
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class StaticCallableEvidenceSetProvider:
    """Build shadow set-level calibration facts without serving projection."""

    def build(
        self,
        query: str,
        localization: dict[str, Any],
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        candidates = records(localization.get("callable_candidates"))
        ranges = range_keys(records(localization.get("source_ranges")))
        ordered = primary_first(candidates, evidence)
        members = [member(query, item, ranges, index) for index, item in enumerate(
            ordered[:MAX_MEMBERS], start=1,
        )]
        scope = target_scope(query)
        competition = competition_facts(members)
        return {
            "schema_version": SCHEMA_VERSION,
            "mode": "shadow",
            "serving_projection_changed": False,
            "target_scope": scope,
            "members": members,
            "competition": competition,
            "calibration": calibration(scope, members, competition),
            "boundary": "retrieval_calibration_not_diagnosis",
        }


def build_callable_evidence_set(
    query: str,
    localization: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return StaticCallableEvidenceSetProvider().build(query, localization, evidence)


def target_scope(query: str) -> dict[str, Any]:
    positive = positive_retrieval_query(query)
    if MULTI_TARGET_RE.search(positive):
        return {"kind": "multiple", "basis": ["explicit_multi_target_cue"]}
    if SINGLE_TARGET_RE.search(positive):
        return {"kind": "single", "basis": ["explicit_single_target_cue"]}
    return {"kind": "unknown", "basis": ["no_explicit_target_scope"]}


def primary_first(
    candidates: list[dict[str, Any]], evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    primary = evidence.get("primary") if isinstance(evidence, dict) else None
    identity = candidate_identity(primary) if isinstance(primary, dict) else ("", "")
    selected = [item for item in candidates if candidate_identity(item) == identity]
    selected_ids = {id(item) for item in selected}
    selected.extend(item for item in candidates if id(item) not in selected_ids)
    return selected


def member(
    query: str,
    item: dict[str, Any],
    ranges: set[tuple[str, str]],
    position: int,
) -> dict[str, Any]:
    path, symbol = candidate_identity(item)
    reasons = strings(item.get("reasons"))
    support: list[str] = []
    if item.get("target_owner_kind_match"):
        support.append("typed_target_owner")
    if "structured_owner_kind" in reasons:
        support.append("structured_owner_kind")
    if IDENTITY_REASONS.intersection(reasons):
        support.append("direct_identity")
    if "semantic_mechanism" in reasons:
        support.append("semantic_mechanism")
    if int(item.get("graph_depth") or 0) > 0:
        support.append("graph_support")
    source_locatable = (path, symbol) in ranges
    if source_locatable:
        support.append("source_locatable")
    excluded = excluded_member(query, item)
    return clean({
        "position": position,
        "file_path": path,
        "symbol": symbol,
        "owner_name": item.get("owner_name"),
        "owner_kind": item.get("owner_kind"),
        "source_locatable": source_locatable,
        "support_kinds": unique_list(support),
        "graph_relations": strings(item.get("graph_relations"))[:4],
        "excluded_by_query": excluded,
    })


def excluded_member(query: str, item: dict[str, Any]) -> bool:
    if excluded_code_candidate(query, item):
        return True
    roles = excluded_result_roles(query)
    text = " ".join(
        str(item.get(key) or "") for key in ("file_path", "owner_name", "symbol")
    )
    normalized = re.sub(r"[^a-z0-9]", "", text.casefold())
    identifiers = excluded_result_identifiers(query)
    return bool(
        roles.intersection(identifier_tokens(text))
        or any(value in normalized for value in identifiers)
    )


def competition_facts(members: list[dict[str, Any]]) -> dict[str, Any]:
    primary = members[0] if members else {}
    alternatives = members[1:]
    owner_kind = str(primary.get("owner_kind") or "")
    return {
        "member_count": len(members),
        "distinct_file_count": len({item.get("file_path") for item in members if item.get("file_path")}),
        "same_owner_kind_alternative": bool(owner_kind) and any(
            str(item.get("owner_kind") or "") == owner_kind for item in alternatives
        ),
        "graph_backed_alternative": any(
            "graph_support" in item.get("support_kinds", []) for item in alternatives
        ),
        "excluded_member_count": sum(bool(item.get("excluded_by_query")) for item in members),
    }


def calibration(
    scope: dict[str, Any],
    members: list[dict[str, Any]],
    competition: dict[str, Any],
) -> dict[str, Any]:
    if not members or not members[0].get("source_locatable"):
        return {"state": "insufficient", "basis": ["no_locatable_primary"]}
    primary = members[0]
    if primary.get("excluded_by_query"):
        return {"state": "conflicted", "basis": ["primary_excluded_by_query"]}
    if scope.get("kind") == "multiple":
        return {"state": "portfolio_required", "basis": ["explicit_multi_target"]}
    if competition.get("graph_backed_alternative"):
        return {"state": "portfolio_required", "basis": ["graph_backed_competition"]}
    if not substantive_support(primary):
        return {"state": "insufficient", "basis": ["no_substantive_primary_support"]}
    if (
        scope.get("kind") == "single"
        and "typed_target_owner" in primary.get("support_kinds", [])
    ):
        return {
            "state": "single_candidate_supported",
            "basis": ["explicit_single_target", "typed_target_owner"],
        }
    basis = ["target_scope_unresolved"] if scope.get("kind") == "unknown" else [
        "primary_support_not_unique",
    ]
    if competition.get("same_owner_kind_alternative"):
        basis.append("same_owner_kind_competition")
    return {"state": "unresolved", "basis": basis}


def substantive_support(value: dict[str, Any]) -> bool:
    return bool(PRIMARY_SUPPORT_KINDS & set(value.get("support_kinds") or []))


def candidate_identity(value: dict[str, Any] | None) -> tuple[str, str]:
    item = value or {}
    return str(item.get("file_path") or ""), str(item.get("symbol") or "")


def range_keys(values: list[dict[str, Any]]) -> set[tuple[str, str]]:
    return {candidate_identity(item) for item in values if all(candidate_identity(item))}


def records(value: object) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def strings(value: object) -> list[str]:
    return [str(item) for item in value if str(item)] if isinstance(value, list) else []


def clean(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item not in (None, "", [])}
