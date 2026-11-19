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

