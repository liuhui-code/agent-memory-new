# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from .evidence_models import GoalPlan
from .text import query_tokens, unique_list


GOAL_TERMS = {
    "design": (
        "设计", "方案", "重构", "模块划分", "接口设计", "状态流", "扩展点",
        "design", "refactor", "proposal", "tradeoff",
    ),
    "change_impact": (
        "影响", "改动", "修改", "变更", "diff", "change", "impact", "回归", "测试范围",
    ),
    "diagnosis": (
        "报错", "错误", "异常", "失败", "日志", "崩溃", "空白", "卡死", "定位", "原因",
        "事故", "debug", "error", "fail", "incident", "diagnos", "log",
    ),
    "governance": (
        "治理", "维护", "淘汰", "冲突", "过期", "质量", "合并", "归档", "stale", "governance",
    ),
    "experience_reuse": (
        "经验", "以前", "历史", "曾经", "复用", "教训", "规律", "experience", "lesson", "past",
    ),
}


SOURCE_WEIGHTS = {
    "design": {
        "code": 1.0, "edge": 1.0, "log": 0.55, "semantic": 0.5,
        "incident": 0.4, "reflection": 0.25, "episode": 0.2,
    },
    "diagnosis": {
        "incident": 1.0, "log": 1.0, "code": 0.9, "edge": 0.85,
        "reflection": 0.65, "semantic": 0.55, "episode": 0.45,
    },
    "change_impact": {
        "code": 1.0, "edge": 1.0, "log": 0.8, "incident": 0.7,
        "reflection": 0.6, "semantic": 0.55, "episode": 0.45,
    },
    "experience_reuse": {
        "reflection": 1.0, "semantic": 0.8, "incident": 0.7, "code": 0.65,
        "log": 0.55, "edge": 0.5, "episode": 0.6,
    },
    "governance": {
        "semantic": 0.9, "reflection": 1.0, "episode": 0.7, "code": 0.6,
        "log": 0.55, "edge": 0.6, "incident": 0.7,
    },
    "code_understanding": {
        "code": 1.0, "edge": 0.9, "log": 0.75, "semantic": 0.7,
        "incident": 0.55, "reflection": 0.5, "episode": 0.4,
    },
}


GOAL_REQUIREMENTS = {
    "design": ("current_architecture", "extension_point", "constraints", "verification"),
    "diagnosis": ("code", "log_or_incident", "verification"),
    "change_impact": ("changed_code", "reverse_dependency", "verification"),
    "experience_reuse": ("verified_experience", "current_code_anchor"),
    "governance": ("governance_signal", "current_source_check"),
    "code_understanding": ("code", "relationship"),
}

GLOBAL_QUERY_TERMS = (
    "整体", "全局", "架构", "主要模块", "高频", "趋势", "共性", "所有项目", "top themes",
    "architecture", "global", "recurring", "overview",
)


def infer_goal(query: str, explicit_goal: str | None = None) -> str:
    if explicit_goal:
        return explicit_goal
    lowered = query.lower()
    scores = {
        goal: sum(1 for term in terms if term in lowered)
        for goal, terms in GOAL_TERMS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] else "code_understanding"


def build_goal_plan(
    query: str,
    explicit_goal: str | None = None,
    max_items: int = 20,
    explicit_scope: str | None = None,
) -> GoalPlan:
    goal = infer_goal(query, explicit_goal)
    query_scope = infer_query_scope(query, explicit_scope, goal)
    weights = SOURCE_WEIGHTS[goal]
    lanes = tuple(
        source for source, _ in sorted(weights.items(), key=lambda item: item[1], reverse=True)
    )
    return GoalPlan(
        goal=goal,
        query=query,
        query_scope=query_scope,
        subqueries=build_subqueries(query, goal, query_scope),
        retrieval_lanes=lanes,
        source_weights=dict(weights),
        required_evidence=GOAL_REQUIREMENTS[goal],
        max_items=max(1, min(max_items, 50)),
    )


def infer_query_scope(
    query: str,
    explicit_scope: str | None = None,
    goal: str | None = None,
) -> str:
    if explicit_scope and explicit_scope != "auto":
        return explicit_scope
    if goal == "design":
        return "local"
    lowered = query.lower()
    return "global" if any(term in lowered for term in GLOBAL_QUERY_TERMS) else "local"


def build_subqueries(query: str, goal: str, query_scope: str) -> tuple[str, ...]:
    technical = " ".join(query_tokens(query)[:12])
    facet = {
        "design": "current responsibility boundary state owner consumers extension point tests observability",
        "diagnosis": "error log reason route resource request session verification",
        "change_impact": "changed file imports routes dependents tests regression",
        "experience_reuse": "trigger repair verification counter evidence",
        "governance": "stale conflict misleading quality evidence",
        "code_understanding": "file symbol imports routes state resource",
    }[goal]
    if query_scope == "global":
        facet = "architecture modules recurring incidents experience patterns"
    values = unique_list([query.strip(), f"{query} {technical}", f"{query} {facet}"])
    return tuple(values[:3])
