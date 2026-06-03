# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any


QUERY_EXPANSION_RULES = [
    (
        ("跳转", "路由", "导航", "打开页面", "页面跳", "白屏", "空白页", "打不开"),
        ("route", "routes", "router", "pushurl", "replaceurl", "navigation", "page", "pages", "pagestack"),
    ),
    (
        ("资源", "图片", "图标", "文案", "字符串", "显示不出来", "不显示", "找不到资源"),
        ("resource", "resources", "media", "image", "string", "app.media", "app.string", "$r"),
    ),
    (
        ("日志", "报错", "错误", "异常", "失败", "崩溃", "打印", "定位"),
        ("log", "logger", "console", "hilog", "error", "warning", "exception", "failed", "failure", "debug"),
    ),
    (
        ("加载", "请求", "接口", "网络", "用户", "资料", "数据"),
        ("load", "request", "fetch", "network", "profile", "account", "user", "data"),
    ),
    (
        ("权限", "授权", "网络权限", "依赖", "配置", "ability", "module"),
        ("permission", "permissions", "dependency", "dependencies", "ability", "module", "json5", "config"),
    ),
    (
        ("鸿蒙", "harmony", "harmonyos", "arkts", "ets"),
        ("harmonyos", "arkts", "ets", "entry", "ability", "stage"),
    ),
]


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[\w\u4e00-\u9fff]+", text.lower())
    expanded: list[str] = []
    for token in tokens:
        expanded.append(token)
        if re.search(r"[\u4e00-\u9fff]", token) and len(token) > 1:
            expanded.extend(token[i : i + 2] for i in range(len(token) - 1))
    return [token for token in expanded if token]


def query_tokens(query: str) -> list[str]:
    tokens = tokenize(query)
    lowered = query.lower()
    for triggers, expansions in QUERY_EXPANSION_RULES:
        if any(trigger in lowered for trigger in triggers):
            tokens.extend(expansions)
    seen: set[str] = set()
    deduped: list[str] = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def score_text(query_tokens: list[str], text: str) -> int:
    lowered = text.lower()
    return sum(1 for token in query_tokens if token in lowered)


def unique_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def terms_from_text(text: str) -> list[str]:
    return [token for token in tokenize(text) if token]


def json_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, list):
        return [str(value) for value in values if str(value).strip()]
    if isinstance(values, str):
        stripped = values.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return [part.strip() for part in stripped.split(",") if part.strip()]
        if isinstance(parsed, list):
            return [str(value) for value in parsed if str(value).strip()]
        return [str(parsed)]
    return [str(values)]


def json_list_text(values: Any) -> str:
    return json.dumps(unique_list(json_list(values)), ensure_ascii=False)


def reflection_list_text(values: Any) -> str:
    seen: set[str] = set()
    result: list[str] = []
    for value in json_list(values):
        stripped = value.strip()
        normalized = stripped.lower()
        if not stripped or normalized in seen:
            continue
        seen.add(normalized)
        result.append(stripped)
    return json.dumps(result, ensure_ascii=False)


def code_search_terms(kind: str, row: sqlite3.Row | dict[str, Any]) -> list[str]:
    get = row.get if isinstance(row, dict) else lambda key, default=None: row[key] if key in row.keys() else default
    terms: list[str] = []
    file_path = str(get("file_path") or "")
    language = str(get("language") or "")
    summary = str(get("summary") or "")
    symbol = str(get("symbol") or "")
    symbol_type = str(get("symbol_type") or "")
    level = str(get("level") or "")
    logger = str(get("logger") or "")
    message_template = str(get("message_template") or "")
    function = str(get("function") or "")
    raw_statement = str(get("raw_statement") or "")
    business_summary = str(get("business_summary") or "")
    business_terms = json_list(get("business_terms"))
    business_event = str(get("business_event") or "")
    trigger_stage = str(get("trigger_stage") or "")
    symptom_terms = json_list(get("symptom_terms"))
    likely_causes = json_list(get("likely_causes"))
    process_hint = str(get("process_hint") or "")
    neighbor_terms = json_list(get("neighbor_terms"))
    terms.extend([file_path, language, summary, symbol, symbol_type, level, logger, message_template, function])
    terms.extend([business_summary, *business_terms])
    terms.extend([business_event, trigger_stage, process_hint, *symptom_terms, *likely_causes, *neighbor_terms])
    terms.extend(terms_from_text(" ".join(terms + [raw_statement])))
    if language == "ArkTS" or file_path.endswith(".ets"):
        terms.extend(["arkts", "harmonyos", "ets", "component", "page"])
    if symbol_type == "route" or "routes:" in summary.lower():
        terms.extend(["route", "routes", "router", "pushurl", "replaceurl", "navigation", "page", "pages"])
    if symbol_type == "resource" or "resources:" in summary.lower() or symbol.startswith("app."):
        terms.extend(["resource", "resources", "media", "image", "string", "app.media", "app.string", "$r"])
    if kind == "log_statement":
        terms.extend(["log", "logger", "console", "hilog", "debug", "error", "warning", "failed", "failure"])
    return unique_list(terms)


def score_weighted_fields(
    query: str,
    tokens: list[str],
    expanded_terms: set[str],
    weighted_fields: list[tuple[str, str, float]],
    exact_fields: list[tuple[str, str, float]],
) -> tuple[float, list[str]]:
    query_lower = query.strip().lower()
    score = 0.0
    reasons: list[str] = []
    for reason, value, weight in exact_fields:
        lowered = value.lower()
        if query_lower and lowered and (query_lower in lowered or lowered in query_lower):
            score += weight
            reasons.append(reason)
    for reason, value, weight in weighted_fields:
        lowered = value.lower()
        matched = [token for token in tokens if token and token in lowered]
        if not matched:
            continue
        score += len(matched) * weight
        if any(token in expanded_terms for token in matched):
            reasons.append(f"expanded_query:{reason}")
        else:
            reasons.append(reason)
    return score, unique_list(reasons)
