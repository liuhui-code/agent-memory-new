# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations


EXPLICIT_MEMORY_INTENTS = (
    "code_location",
    "code_business_semantics",
    "runtime_log_diagnosis",
    "procedure_reuse",
    "semantic_correction",
    "memory_maintenance",
    "general_context",
)

MEMORY_INTENT_ALIASES = {
    "code_location": "code_current",
    "code_business_semantics": "semantic_lookup",
    "runtime_log_diagnosis": "incident_diagnosis",
    "semantic_correction": "correction_guard",
    "memory_maintenance": "general_context",
}


def infer_memory_intent(query: str) -> str:
    return legacy_memory_intent(infer_memory_intent_v2(query))


def legacy_memory_intent(intent_v2: str) -> str:
    return MEMORY_INTENT_ALIASES.get(intent_v2, intent_v2)


def infer_memory_intent_v2(query: str) -> str:
    lowered = query.lower()
    if any(token in lowered for token in (
        "误导", "错误经验", "纠错", "冲突", "不要", "避免",
        "correction", "wrong", "misleading",
    )):
        return "semantic_correction"
    if "what does" in lowered:
        return "code_business_semantics"
    if any(token in lowered for token in (
        "业务语义", "业务含义", "语义", "semantic", "business meaning",
        "business_summary", "business_terms", "补充",
    )):
        return "code_business_semantics"
    if any(token in lowered for token in (
        "maintain", "治理", "维护", "淘汰", "刷新", "合并", "stale",
        "archive", "refresh",
    )):
        return "memory_maintenance"
    if any(token in lowered for token in (
        "日志", "报错", "错误", "异常", "失败", "崩溃", "incident", "log",
        "traceback", "exception", "error", "failed", "failure",
    )):
        return "runtime_log_diagnosis"
    if any(token in lowered for token in (
        "如何", "怎么", "步骤", "流程", "方案", "procedure", "playbook",
        "workflow", "how to",
    )):
        return "procedure_reuse"
    if any(token in lowered for token in (
        "代码", "函数", "文件", "调用", "当前", "source", "code", "function",
        "file", "在哪里", "位置", "path",
    )):
        return "code_location"
    return "general_context"


def resolve_memory_intent(query: str, explicit_intent: str | None = None) -> tuple[str, str, str]:
    if explicit_intent is not None and explicit_intent not in EXPLICIT_MEMORY_INTENTS:
        choices = ", ".join(EXPLICIT_MEMORY_INTENTS)
        raise ValueError(f"unsupported context intent {explicit_intent!r}; choose one of {choices}")
    intent_v2 = explicit_intent or infer_memory_intent_v2(query)
    source = "explicit" if explicit_intent else "inferred"
    return legacy_memory_intent(intent_v2), intent_v2, source
