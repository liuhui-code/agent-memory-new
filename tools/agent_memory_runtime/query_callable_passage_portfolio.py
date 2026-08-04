# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .query_language import excluded_code_candidate
from .query_target_scope import classify_target_scope, permits_cross_file_portfolio
from .text import identifier_tokens, query_tokens


SCHEMA_VERSION = "agent-callable-passage-portfolio/v1"
MAX_MEMBERS = 3
QUERY_SUPPORT_REASONS = {
    "exact_function", "exact_identifier", "exact_symbol", "semantic_mechanism",
    "salient_query_evidence", "multi_term_method_evidence",
}
STRUCTURAL_PASSAGE_REASONS = {"salient_query_evidence", "multi_term_method_evidence"}


class CallablePassagePortfolioProvider(Protocol):
    def build(
        self,
        query: str,
        localization: dict[str, Any],
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class StaticCallablePassagePortfolioProvider:
    """Compose bounded source passages without inferring a diagnosis."""

    def build(
        self,
        query: str,
        localization: dict[str, Any],
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        primary = evidence.get("primary") if isinstance(evidence, dict) else None
        if not isinstance(primary, dict) or not primary.get("source_range"):
            return inactive("no_locatable_primary")
        scope = classify_target_scope(query)
        if scope.get("kind") != "multiple":
            return inactive("target_scope_not_composite")
        cross_file = permits_cross_file_portfolio(scope)
        candidates = records(localization.get("callable_candidates"))
        ranges = range_lookup(records(localization.get("source_ranges")))
        primary_identity = identity(primary)
        ordered = sorted(candidates, key=lambda item: identity(item) != primary_identity)
        eligible = [
            passage(item, ranges, query)
            for item in ordered
            if not excluded_code_candidate(query, item)
            and query_supported(item, query)
            and identity(item) in ranges
        ]
        eligible = dedupe(eligible)
        owner_eligible = [
            item for item in eligible if same_owner_scope(item, primary)
        ]
        explicit = [
            item for item in eligible
            if "query_symbol_terms" in item["support_reasons"]
        ]
        structural = [
            item for item in eligible
            if STRUCTURAL_PASSAGE_REASONS.issubset(set(item["support_reasons"]))
        ]
        cross_file = cross_file and len({item["file_path"] for item in eligible}) >= 2
        if cross_file:
            members = diverse_files(eligible)[:MAX_MEMBERS]
        else:
            owner_explicit = [item for item in explicit if item in owner_eligible]
            owner_structural = [item for item in structural if item in owner_eligible]
            supported = owner_explicit if len(owner_explicit) >= 2 else owner_structural
            members = supported[:MAX_MEMBERS]
        if len(members) < 2:
            return inactive("fewer_than_two_supported_callable_identities")
        basis = (
            "explicit_cross_file_targets" if cross_file
            else "explicit_callable_identity" if len(explicit) >= 2
            else "structural_query_support"
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "mode": "serving",
            "state": "composed",
            "target_scope": str(scope["kind"]),
            "members": members,
            "selection_basis": [
                "existing_localization", "same_owner_scope",
                basis, "bounded_passage_diversity",
            ],
            "candidate_recall_changed": False,
            "boundary": "source_passage_composition_not_diagnosis",
        }


def build_callable_passage_portfolio(
    query: str,
    localization: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return StaticCallablePassagePortfolioProvider().build(
        query, localization, evidence,
    )


def same_owner_scope(item: dict[str, Any], primary: dict[str, Any]) -> bool:
    if str(item.get("file_path") or "") != str(primary.get("file_path") or ""):
        return False
    owner = str(primary.get("owner_name") or "")
    return not owner or str(item.get("owner_name") or "") == owner


def query_supported(item: dict[str, Any], query: str) -> bool:
    return bool(support_reasons(item, query))


def passage(
    item: dict[str, Any],
    ranges: dict[tuple[str, str], dict[str, Any]],
    query: str = "",
) -> dict[str, Any]:
    path, symbol = identity(item)
    return {
        "file_path": path,
        "symbol": symbol,
        "owner_name": item.get("owner_name"),
        "source_range": ranges[(path, symbol)],
        "support_reasons": support_reasons(item, query),
    }


def support_reasons(item: dict[str, Any], query: str) -> list[str]:
    reasons = QUERY_SUPPORT_REASONS & set(strings(item.get("reasons")))
    symbol_terms = set(identifier_tokens(str(item.get("symbol") or "")))
    if symbol_terms and symbol_terms.issubset(set(query_tokens(query))):
        reasons.add("query_symbol_terms")
    return sorted(reasons)


def dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = identity(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def diverse_files(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    seen: set[str] = set()
    for item in items:
        path = str(item.get("file_path") or "")
        if not path or path in seen:
            continue
        seen.add(path)
        result.append(item)
    return result


def inactive(reason: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "serving",
        "state": "inactive",
        "members": [],
        "selection_basis": [reason],
        "candidate_recall_changed": False,
        "boundary": "source_passage_composition_not_diagnosis",
    }


def range_lookup(items: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        identity(item): {
            key: item.get(key)
            for key in (
                "start_line", "end_line", "selection_reason",
                "mechanism_kind", "mechanism_terms",
            )
            if item.get(key) not in (None, "", [])
        }
        for item in items if all(identity(item))
    }


def identity(item: dict[str, Any]) -> tuple[str, str]:
    return str(item.get("file_path") or ""), str(item.get("symbol") or "")


def records(value: object) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def strings(value: object) -> list[str]:
    return [str(item) for item in value if str(item)] if isinstance(value, list) else []
