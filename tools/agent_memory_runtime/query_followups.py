# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from typing import Any

from .text import json_list, tokenize, unique_list

FOCUS_PRIORITY_TERMS = {
    "route": ["route", "routes", "router", "pushurl", "replaceurl", "navigation", "page", "pages", "pagestack"],
    "resource": ["resource", "resources", "media", "image", "string", "app.media", "app.string", "$r"],
    "config": ["permission", "permissions", "dependency", "dependencies", "ability", "module", "json5", "config"],
    "log": ["log", "logger", "console", "hilog", "error", "warning", "exception", "failed", "failure", "debug"],
}


def focus_from_query(query: str) -> str | None:
    lowered = query.lower()
    if any(trigger in lowered for trigger in ("跳转", "路由", "导航", "白屏", "空白页", "打不开")):
        return "route"
    if any(trigger in lowered for trigger in ("资源", "图片", "图标", "文案", "字符串", "显示不出来", "不显示", "找不到资源")):
        return "resource"
    if any(trigger in lowered for trigger in ("权限", "授权", "依赖", "配置", "ability", "module")):
        return "config"
    if any(trigger in lowered for trigger in ("日志", "报错", "错误", "异常", "失败", "崩溃", "打印", "定位")):
        return "log"
    return None



def infer_followup_focus(query: str, data: dict[str, list[dict[str, Any]]]) -> str | None:
    focus = focus_from_query(query)
    if focus:
        return focus
    for row in data.get("wiki_matches", [])[:3]:
        symbol_type = str(row.get("symbol_type") or "")
        if symbol_type in {"route", "resource", "permission", "dependency", "ability"}:
            return "config" if symbol_type in {"permission", "dependency", "ability"} else symbol_type
    if data.get("code_log_matches"):
        return "log"
    return None



def rank_followup_seed_terms(query: str, terms: list[str], limit: int = 12, focus: str | None = None) -> list[str]:
    candidates: list[tuple[int, int, str]] = []
    order = 0
    focus = focus or focus_from_query(query)

    def add(priority: int, value: str | None) -> None:
        nonlocal order
        if not value:
            return
        stripped = str(value).strip()
        if not stripped:
            return
        candidates.append((priority, order, stripped))
        order += 1

    def classify_term_priority(term: str) -> int:
        lowered = term.lower()
        query_lowered = query.lower()
        if focus == "route":
            if lowered.startswith("pages/") and not lowered.endswith(".ets"):
                return 130
            if "router" in lowered or "route" in lowered:
                return 125
            if lowered.endswith(".ets"):
                return 78
            if "failed" in lowered or "error" in lowered or "log" in lowered:
                return 68
        if focus == "resource":
            if lowered.startswith("app.") or "$r" in lowered or "resource" in lowered or "media" in lowered or "string" in lowered:
                return 125
            if lowered.startswith("pages/"):
                return 68
        if focus == "config":
            if "权限" in query_lowered and "permission" in lowered:
                return 132
            if "依赖" in query_lowered and "dependency" in lowered:
                return 132
            if "ability" in query_lowered and "ability" in lowered:
                return 132
            if "permission" in lowered:
                return 126
            if "dependency" in lowered:
                return 124
            if "ability" in lowered:
                return 118
            if lowered.endswith(".json5"):
                return 125
            if lowered.startswith("pages/") or lowered.endswith(".ets"):
                return 68
        if focus == "log":
            if "failed" in lowered or "error" in lowered or "warn" in lowered or "log" in lowered or "hilog" in lowered:
                return 125
            if "session" in lowered or "invalid" in lowered or "401" in lowered or "permission denied" in lowered:
                return 118
            if lowered.startswith("pages/") or lowered.endswith(".ets"):
                return 68
        if lowered.startswith("pages/") or lowered.startswith("app.") or "$r" in lowered:
            return 96
        if "/" in lowered or "." in lowered:
            return 92
        if "failed" in lowered or "error" in lowered or "warn" in lowered or "log" in lowered:
            return 88
        if "route" in lowered or "router" in lowered or "resource" in lowered or "hilog" in lowered:
            return 84
        if "profile" in lowered or "load" in lowered or "user" in lowered:
            return 78
        return 70

    for term in terms:
        add(classify_term_priority(str(term)), str(term))

    seen: set[str] = set()
    ranked: list[str] = []
    for _, _, value in sorted(candidates, key=lambda item: (-item[0], item[1])):
        normalized = value.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ranked.append(normalized)
        if len(ranked) >= limit:
            break
    return ranked



def suggested_followup_terms(query: str, data: dict[str, list[dict[str, Any]]], limit: int = 12) -> list[str]:
    focus = infer_followup_focus(query, data)
    terms: list[str] = []
    for row in data.get("code_log_matches", [])[:5]:
        if row.get("message_template"):
            terms.append(str(row["message_template"]))
        if row.get("function"):
            terms.append(str(row["function"]))
        if row.get("file_path"):
            terms.append(str(row["file_path"]))
        terms.extend(json_list(row.get("business_terms")))
        terms.extend(row.get("search_terms") or [])

    for row in data.get("wiki_matches", [])[:5]:
        if row.get("symbol"):
            terms.append(str(row["symbol"]))
        if row.get("file_path"):
            terms.append(str(row["file_path"]))
        terms.extend(json_list(row.get("business_terms")))
        terms.extend(row.get("search_terms") or [])

    for row in data.get("semantic_facts", [])[:3]:
        terms.extend(tokenize(str(row.get("fact") or "")))
    for row in data.get("reflections", [])[:2]:
        terms.extend(tokenize(" ".join(str(row.get(key) or "") for key in ("task", "problem", "lesson", "future_rule"))))
    return rank_followup_seed_terms(query, terms, limit=limit, focus=focus)



def string_literals(text: str) -> list[str]:
    return [match.group(2) for match in re.finditer(r"""(['"])(.*?)(?<!\\)\1""", str(text or ""))]



def unique_preserved(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        stripped = str(value).strip()
        normalized = stripped.lower()
        if not stripped or normalized in seen:
            continue
        seen.add(normalized)
        result.append(stripped)
    return result



def log_logger_hints(row: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    logger = str(row.get("logger") or "")
    function = str(row.get("function") or "")
    raw_statement = str(row.get("raw_statement") or "")
    if logger:
        hints.append(logger)
    if function:
        hints.append(function)
    literals = string_literals(raw_statement)
    if logger == "hilog" and len(literals) >= 2:
        hints.append(literals[0])
    elif literals:
        hints.append(literals[0])
    return unique_preserved(hints)



def build_log_search_plan(query: str, data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    focus = infer_followup_focus(query, data)
    top_logs = data.get("code_log_matches", [])[:5]
    search_terms = rank_followup_seed_terms(
        query,
        [
            *suggested_followup_terms(query, data, limit=14),
            *[str(row.get("message_template") or "") for row in top_logs],
            *[str(row.get("business_summary") or "") for row in top_logs],
            *[str(row.get("business_event") or "") for row in top_logs],
            *[str(row.get("trigger_stage") or "") for row in top_logs],
            *[term for row in top_logs for term in json_list(row.get("symptom_terms"))],
            *[term for row in top_logs for term in json_list(row.get("likely_causes"))],
            *[str(row.get("process_hint") or "") for row in top_logs],
            *[term for row in top_logs for term in json_list(row.get("neighbor_terms"))],
        ],
        limit=14,
        focus=focus or "log",
    )
    logger_hints: list[str] = []
    function_hints: list[str] = []
    file_hints: list[str] = []
    candidate_log_events: list[dict[str, Any]] = []
    for row in top_logs:
        logger_hints.extend(log_logger_hints(row))
        if row.get("function"):
            function_hints.append(str(row["function"]))
        if row.get("file_path"):
            file_hints.append(str(row["file_path"]))
        candidate_log_events.append(
            {
                "message_template": str(row.get("message_template") or ""),
                "business_summary": str(row.get("business_summary") or ""),
                "business_terms": json_list(row.get("business_terms")),
                "business_event": str(row.get("business_event") or ""),
                "trigger_stage": str(row.get("trigger_stage") or ""),
                "symptom_terms": json_list(row.get("symptom_terms")),
                "likely_causes": json_list(row.get("likely_causes")),
                "process_hint": str(row.get("process_hint") or ""),
                "neighbor_terms": json_list(row.get("neighbor_terms")),
                "file_path": str(row.get("file_path") or ""),
                "function": str(row.get("function") or ""),
                "logger": str(row.get("logger") or ""),
            }
        )
    recommended_order = [
        "search failure/error logs for the target event first",
        "search preceding start/request/info logs around the same page or function",
        "compare neighboring logs that share the same logger, page, process, or business object",
    ]
    if focus == "route":
        recommended_order = [
            "search route jump failure logs and target page names first",
            "search neighboring router start/info logs for the same page transition",
            "compare related page registration or route target anchors in code memory",
        ]
    elif focus == "resource":
        recommended_order = [
            "search resource resolve or missing-resource logs first",
            "search preceding page/build/image logs around the same component",
            "compare resource keys and related code anchors before expanding scope",
        ]
    elif focus == "config":
        recommended_order = [
            "search permission/dependency/config failure logs first",
            "search neighboring ability/module startup logs for the same process",
            "compare config anchors and related code/wiki evidence before widening the search",
        ]
    return {
        "focus": focus or "log",
        "candidate_log_events": candidate_log_events,
        "search_terms": search_terms,
        "logger_hints": unique_preserved(logger_hints),
        "function_hints": unique_preserved(function_hints),
        "file_hints": unique_preserved(file_hints),
        "process_hints": unique_preserved(
            [str(item.get("process_hint") or "") for item in candidate_log_events if str(item.get("process_hint") or "").strip()]
        ),
        "recommended_order": recommended_order,
    }
