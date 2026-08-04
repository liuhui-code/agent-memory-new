# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from pathlib import PurePosixPath
import re
from typing import Any

from .source_path_policy import is_generated_source_path
from .text import query_tokens


IMPLEMENTATION = "implementation"
VALIDATION = "validation"
NEUTRAL = "neutral"
PRODUCTION = "production"
TEST = "test"
GENERATED = "generated"

VALIDATION_TERMS = {
    "assert", "assertion", "coverage", "regression", "spec", "test", "tests",
    "verify", "verification", "断言", "测试", "验证",
}
IMPLEMENTATION_TERMS = {
    "code", "implementation", "inspect", "locate", "production", "source",
    "实现", "定位", "方法", "源码", "生产",
}
TEST_DIRECTORIES = {"__tests__", "spec", "specs", "test", "tests"}
TEST_SUFFIX_RE = re.compile(r"(?:[._-](?:spec|test)|(?:Spec|Test))$", re.IGNORECASE)


def annotate_artifact_roles(
    items: list[dict[str, Any]], query: str,
) -> list[dict[str, Any]]:
    """Attach language-neutral artifact roles and bounded family competition."""
    intent = query_artifact_intent(query)
    annotated = [annotate(item, intent) for item in items]
    competing = competing_families(annotated)
    for item in annotated:
        family = str(item.get("artifact_family") or "")
        role = str(item.get("artifact_role") or "")
        if family not in competing:
            item["artifact_role_affinity"] = 1
            continue
        item["artifact_role_competition"] = True
        item["artifact_role_affinity"] = role_affinity(intent, role)
        reason = competition_reason(intent, role)
        if reason:
            item["localization_reasons"] = list(dict.fromkeys([
                *(item.get("localization_reasons") or []), reason,
            ]))
    attach_family_representatives(annotated, intent, competing)
    return annotated


def artifact_role_rank_score(item: dict[str, Any]) -> float:
    if item.get("artifact_role_representative"):
        return float(item.get("artifact_family_rank_score") or 0.0)
    return float(item.get("localization_score") or item.get("score") or 0.0)


def artifact_role_tiebreak(item: dict[str, Any]) -> int:
    return -int(bool(item.get("artifact_role_representative")))


def artifact_role_shadow_priority(item: dict[str, Any]) -> int:
    return int(bool(item.get("artifact_role_shadow")))


def query_artifact_intent(query: str) -> str:
    terms = set(query_tokens(query))
    validation = bool(terms & VALIDATION_TERMS)
    implementation = bool(terms & IMPLEMENTATION_TERMS)
    if validation and not implementation:
        return VALIDATION
    if validation and implementation:
        return NEUTRAL
    return IMPLEMENTATION


def artifact_role(file_path: str) -> str:
    if is_generated_source_path(file_path):
        return GENERATED
    path = PurePosixPath(file_path)
    directories = {part.casefold() for part in path.parts[:-1]}
    stem = path.stem
    if directories & TEST_DIRECTORIES or TEST_SUFFIX_RE.search(stem):
        return TEST
    return PRODUCTION


def artifact_family(file_path: str) -> str:
    stem = PurePosixPath(file_path).stem
    normalized = TEST_SUFFIX_RE.sub("", stem)
    return re.sub(r"[^a-z0-9]", "", normalized.casefold())


def annotate(item: dict[str, Any], intent: str) -> dict[str, Any]:
    result = dict(item)
    path = str(result.get("file_path") or "")
    result["artifact_role"] = artifact_role(path)
    result["artifact_family"] = artifact_family(path)
    result["artifact_query_intent"] = intent
    return result


def competing_families(items: list[dict[str, Any]]) -> set[str]:
    roles: dict[str, set[str]] = {}
    for item in items:
        family = str(item.get("artifact_family") or "")
        role = str(item.get("artifact_role") or "")
        if family:
            roles.setdefault(family, set()).add(role)
    return {
        family for family, values in roles.items()
        if PRODUCTION in values and TEST in values
    }


def attach_family_representatives(
    items: list[dict[str, Any]], intent: str, families: set[str],
) -> None:
    preferred_role = PRODUCTION if intent == IMPLEMENTATION else TEST if intent == VALIDATION else ""
    if not preferred_role:
        return
    for family in families:
        members = [item for item in items if item.get("artifact_family") == family]
        preferred = [item for item in members if item.get("artifact_role") == preferred_role]
        if not preferred:
            continue
        representative = min(preferred, key=lambda item: (
            -base_rank_score(item),
            str(item.get("file_path") or ""),
            int(item.get("start_line") or 0),
        ))
        representative["artifact_role_representative"] = True
        representative["artifact_family_rank_score"] = max(
            base_rank_score(item) for item in members
        )
        for item in members:
            if item.get("artifact_role") != preferred_role:
                item["artifact_role_shadow"] = True


def base_rank_score(item: dict[str, Any]) -> float:
    return float(item.get("localization_score") or item.get("score") or 0.0)


def role_affinity(intent: str, role: str) -> int:
    if intent == IMPLEMENTATION:
        return 2 if role == PRODUCTION else 0 if role == TEST else 1
    if intent == VALIDATION:
        return 2 if role == TEST else 0 if role == PRODUCTION else 1
    return 1


def competition_reason(intent: str, role: str) -> str:
    if intent == IMPLEMENTATION and role == PRODUCTION:
        return "implementation_artifact_role"
    if intent == IMPLEMENTATION and role == TEST:
        return "test_shadow_artifact_role"
    if intent == VALIDATION and role == TEST:
        return "validation_artifact_role"
    if intent == VALIDATION and role == PRODUCTION:
        return "production_shadow_artifact_role"
    return ""
