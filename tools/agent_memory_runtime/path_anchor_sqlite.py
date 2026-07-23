# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re

from .models import Project, QUERY_FTS_RECALL_LIMITS
from .path_context_models import AnchorResolution, LogAnchorMatch
from .query_candidate_recall import recall_candidate_ids
from .storage import connect
from .text import tokenize, unique_list


MIN_ANCHOR_SCORE = 0.84
MAX_ANCHOR_MATCHES = 5
RUNTIME_PREFIX = re.compile(
    r"^(?:\d{2}[-/]\d{2}\s+)?\d{2}:\d{2}:\d{2}(?:\.\d+)?\s+"
    r"(?:pid|tid|process)?[=:]?[^\s]+\s+",
    re.IGNORECASE,
)
RUNTIME_VALUE = re.compile(
    r"\b(?:0x[0-9a-f]+|[0-9a-f]{8}-[0-9a-f-]{27,}|\d{6,})\b",
    re.IGNORECASE,
)


class SQLiteLogAnchorResolver:
    def __init__(self, project: Project) -> None:
        self.project = project

    def resolve(self, query: str) -> AnchorResolution:
        normalized_query = normalize_log_text(query)
        if len(normalized_query) < 4:
            return AnchorResolution(False, "query_too_short")
        with connect(self.project) as conn:
            ids = recall_candidate_ids(
                conn,
                self.project,
                "code_log_statements",
                query,
                QUERY_FTS_RECALL_LIMITS["code_log_statements"],
            )
            if not ids:
                return AnchorResolution(False, "missing_log_anchor")
            rows = conn.execute(
                f"SELECT * FROM code_log_statements WHERE project_id = ? AND id IN ({','.join('?' for _ in ids)})",
                (self.project.project_id, *ids),
            ).fetchall()
        matches = [match_anchor(dict(row), normalized_query) for row in rows]
        strong = [item for item in matches if item and item.anchor_match_score >= MIN_ANCHOR_SCORE]
        strong.sort(key=lambda item: (item.anchor_match_score, len(item.message_template), -item.log_id), reverse=True)
        selected = tuple(strong[:MAX_ANCHOR_MATCHES])
        if not selected:
            return AnchorResolution(False, "no_strong_log_anchor", candidate_count=len(rows))
        reason = "exact_log_template" if selected[0].match_kind == "exact_template" else "strong_log_identity"
        return AnchorResolution(True, reason, selected, len(rows))


def match_anchor(row: dict[str, object], normalized_query: str) -> LogAnchorMatch | None:
    template = str(row.get("message_template") or "").strip()
    normalized_template = normalize_log_text(template)
    if len(normalized_template) < 4:
        return None
    logger = str(row.get("logger") or "").strip()
    event_name = str(row.get("business_event") or "").strip()
    match_kind = ""
    score = 0.0
    if normalized_template in normalized_query:
        match_kind = "exact_template"
        score = 1.0
    else:
        template_tokens = stable_tokens(normalized_template)
        query_tokens = set(stable_tokens(normalized_query))
        coverage = len(set(template_tokens) & query_tokens) / max(1, len(set(template_tokens)))
        logger_match = bool(logger and logger.casefold() in normalized_query)
        event_match = bool(event_name and normalize_log_text(event_name) in normalized_query)
        if coverage >= 0.8 and (logger_match or event_match or len(template_tokens) >= 3):
            match_kind = "stable_identity"
            score = 0.74 + min(0.16, coverage * 0.12) + (0.05 if logger_match else 0.0) + (0.05 if event_match else 0.0)
    if not match_kind:
        return None
    return LogAnchorMatch(
        log_id=int(row["id"]),
        message_template=template,
        logger=logger,
        event_name=event_name,
        file_path=str(row.get("file_path") or ""),
        function=str(row.get("function") or ""),
        line=int(row["line"]) if row.get("line") is not None else None,
        match_kind=match_kind,
        anchor_match_score=min(1.0, score),
    )


def normalize_log_text(value: str) -> str:
    text = RUNTIME_PREFIX.sub("", str(value or "").strip())
    text = RUNTIME_VALUE.sub("<value>", text)
    return " ".join(text.casefold().split())


def stable_tokens(value: str) -> list[str]:
    ignored = {"error", "info", "warn", "warning", "debug", "failed", "failure", "value"}
    return unique_list([token for token in tokenize(value) if len(token) > 1 and token not in ignored])
