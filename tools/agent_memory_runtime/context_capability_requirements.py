# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .context_log_path_quality import log_path_requirements


def context_requirements(value: Any) -> dict[str, Any]:
    item = value if isinstance(value, dict) else {}
    return {
        "required_log_keywords": string_list(item.get("required_log_keywords"), fold=True),
        "required_log_template_literals": string_list(
            item.get("required_log_template_literals"), fold=True
        ),
        "runtime_observed_terms": string_list(item.get("runtime_observed_terms"), fold=True),
        "required_log_files": string_list(item.get("required_log_files")),
        "forbidden_log_keywords": string_list(item.get("forbidden_log_keywords"), fold=True),
        "forbidden_log_files": string_list(item.get("forbidden_log_files")),
        "required_experience_types": string_list(
            item.get("required_experience_types"), fold=True
        ),
        "required_main_experience_phrases": string_list(
            item.get("required_main_experience_phrases"), fold=True
        ),
        "forbidden_main_experience_phrases": string_list(
            item.get("forbidden_main_experience_phrases"), fold=True
        ),
        "required_guard_experience_phrases": string_list(
            item.get("required_guard_experience_phrases"), fold=True
        ),
        "required_path_files": string_list(item.get("required_path_files")),
        "required_path_relations": string_list(item.get("required_path_relations"), fold=True),
        "forbidden_path_files": string_list(item.get("forbidden_path_files")),
        "min_relation_hints": nonnegative_int(item.get("min_relation_hints")),
        "min_path_candidates": nonnegative_int(item.get("min_path_candidates")),
        "require_source_excerpt": bool(item.get("require_source_excerpt")),
        "require_expected_anchors": item.get("require_expected_anchors") is not False,
        "required_top_k": nonnegative_int(item.get("required_top_k")),
        "min_anchor_precision": optional_ratio(item.get("min_anchor_precision")),
        "required_source_spans": source_spans(item.get("required_source_spans")),
        "required_owner_spans": source_spans(item.get("required_owner_spans")),
        "hierarchical_callable_spans": source_spans(item.get("hierarchical_callable_spans")),
        "hierarchical_owner_spans": source_spans(item.get("hierarchical_owner_spans")),
        "hierarchical_range_spans": source_spans(item.get("hierarchical_range_spans")),
        "min_source_span_recall": optional_ratio(
            item.get("min_source_span_recall"), default=1.0
        ),
        "require_abstention": bool(item.get("require_abstention")),
        "required_evidence_gaps": string_list(item.get("required_evidence_gaps")),
        **log_path_requirements(item),
    }


def string_list(value: Any, fold: bool = False) -> list[str]:
    if not isinstance(value, list):
        return []
    items = [str(item).strip() for item in value if str(item).strip()]
    if fold:
        items = [item.casefold() for item in items]
    return list(dict.fromkeys(items))


def nonnegative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def optional_ratio(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise SystemExit("context capability ratio must be numeric") from exc
    if not 0.0 <= result <= 1.0:
        raise SystemExit("context capability ratio must be between 0 and 1")
    return result


def source_spans(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 20:
        raise SystemExit("required_source_spans must be a list with at most 20 items")
    result = []
    for item in value:
        if not isinstance(item, dict) or not str(item.get("file_path") or "").strip():
            raise SystemExit("required source span requires file_path")
        span = {"file_path": str(item["file_path"]).strip()}
        if item.get("symbol"):
            span["symbol"] = str(item["symbol"]).strip()
        if isinstance(item.get("start_line"), int) and isinstance(item.get("end_line"), int):
            if item["start_line"] <= 0 or item["end_line"] < item["start_line"]:
                raise SystemExit("required source span line range is invalid")
            span.update({"start_line": item["start_line"], "end_line": item["end_line"]})
        if "symbol" not in span and "start_line" not in span:
            raise SystemExit("required source span requires symbol or line range")
        result.append(span)
    return result
