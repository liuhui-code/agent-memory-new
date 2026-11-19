# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from typing import Any

from .models import Project
from .records import row_dict
from .query_language import (
    positive_retrieval_query, result_alternative_query,
    NEGATIVE_RESULT_CLAUSE_RE, COMPARISON_CLAUSE_RE,
)
from .query_qualified_exclusions import qualified_exclusions
from .query_target_scope import classify_target_scope
from .storage import connect
from .text import code_search_terms, json_list


INDIRECT_PATH_RE = re.compile(
    r"(?:controller|helper|adapter|bridge|service|repository)(?:\.[^.]+)?$",
    re.I,
)
CALLER_QUERY_MARKERS = (
    "actual caller", "caller context", "call site", "click owner",
    "button callback", "onclick", "调用方", "调用位置", "点击所有者",
)
CALLER_RELATIONS = ("calls", "awaits", "registers_callback")
MAX_SEED_PATHS = 4
MAX_CALLER_OWNERS = 2


def plural_caller_member(query):
    """One finite caller request, not global scope or a file-path target."""
    match = re.fullmatch(
        r"\s*Find\s+(?:the\s+)?actual\s+callers\s+of\s+"
        r"([A-Za-z_$][\w$]*\.[A-Za-z_$][\w$]*)\.?\s*",
        query, re.IGNORECASE,
    )
    return match.group(1) if match else None


class ResolvedCallerItem(dict):
    """Ephemeral query binding; dict/JSON projection deliberately loses it."""

    def __init__(self, item, query, targets):
        super().__init__(item)
        self.request_binding = (query, tuple(targets), caller_source_identity(self))


def collect_bounded_caller_owners(
    project: Project,
    matches: list[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    if not caller_owner_query(query):
        return []
    seed_scores = indirect_seed_scores(matches)
    if not seed_scores:
        return []
    paths = list(seed_scores)
    placeholders = ",".join("?" for _ in paths)
    relation_placeholders = ",".join("?" for _ in CALLER_RELATIONS)
    with connect(project) as conn:
        targets = conn.execute(
            f"SELECT id, file_path, symbol, owner_name FROM code_symbols "
            f"WHERE project_id = ? AND file_path IN ({placeholders})",
            (project.project_id, *paths),
        ).fetchall()
        def resolve_member(reference):
            owner, _, symbol = reference.rpartition(".")
            # Seed truncation is not identity disambiguation. Two project-wide
            # matches suffice to reject an ambiguous qualified member.
            return conn.execute(
                "SELECT id FROM code_symbols WHERE project_id = ? "
                "AND owner_name = ? AND symbol = ? LIMIT 2",
                (project.project_id, owner, symbol),
            ).fetchall()
        target_ids = explicit_caller_target_ids(targets, query, resolve_member)
        if target_ids == []:
            return []
        target_filter = ""
        target_params = []
        if target_ids is not None:
            target_filter = " AND targets.id IN (" + ",".join("?" for _ in target_ids) + ")"
            target_params = target_ids
        complete_targets = (explicit_caller_target_ids(targets, query, resolve_member, require_complete=True)
                            if target_ids and classify_target_scope(query).get("kind") == "multiple" else [])
        member = plural_caller_member(query)
        if member is not None:
            # Never certify a same-shaped file token as an Owner.member. The
            # complete project lookup must agree with the actual SQL filter.
            member_rows = resolve_member(member)
            complete_targets = ([int(member_rows[0]["id"])]
                                if len(member_rows) == 1 else [])
            if complete_targets != target_ids:
                complete_targets = []
        rows = conn.execute(
            f"""
            SELECT callers.*, files.summary AS caller_file_summary,
                   MAX(edges.confidence) AS caller_confidence,
                   GROUP_CONCAT(DISTINCT edges.relation) AS caller_relations
            FROM code_symbols AS targets
            JOIN memory_edges AS edges
              ON edges.project_id = targets.project_id
             AND edges.target_type = 'code_symbol'
             AND edges.target_id = targets.id
             AND edges.valid_to IS NULL
            JOIN code_symbols AS callers
              ON edges.source_type = 'code_symbol'
             AND callers.project_id = edges.project_id
             AND callers.id = edges.source_id
            JOIN code_files AS files
              ON files.project_id = callers.project_id
             AND files.file_path = callers.file_path
            WHERE targets.project_id = ?
              AND targets.file_path IN ({placeholders})
              AND edges.relation IN ({relation_placeholders})
              {target_filter}
              AND callers.file_path != targets.file_path
              AND files.summary LIKE '%uicallbackbinding%'
            GROUP BY callers.id
            ORDER BY caller_confidence DESC, callers.id DESC
            LIMIT 12
            """,
            (project.project_id, *paths, *CALLER_RELATIONS, *target_params),
        ).fetchall()
    selected = caller_items(rows, seed_scores)
    # Query-time provenance only; no new index fact or caller discovery.
    if complete_targets and complete_targets == target_ids:
        selected = [ResolvedCallerItem(item, query, complete_targets) for item in selected]
    return selected


def caller_owner_query(query: str) -> bool:
    # Match affirmative request text, not retrieval's retained negative names.
    # Unknown quoted/contrastive clauses keep the legacy interpretation.
    positive = query
    if not any(c in query for c in '`"“”‘’') and not re.search(r"(?<!\w)'[^'\n]*'", query):
        positive = result_alternative_query(query)
        _qualified, positive = qualified_exclusions(positive)
        def mask(match):
            clause = match.group()
            if (clause[0] not in ",;，；" and match.start()
                and re.match(r"[\w$]", match.string[match.start()-1])):
                return clause
            if re.search(r"\b(?:but|however|although|and|or|also|yet|instead)\b|但是|但也|不仅|不只", clause, re.I):
                return clause
            if re.search(r"\b(?:not|don't)\s+(?:return\s+)?(?:only|just|merely|solely|exclusively)\b", clause, re.I):
                return clause
            if not re.match(
                r"(?:[,;，；]\s*not\s+|rather\s+than\b|do\s+not\s+return\b|don't\s+return\b|"
                r"(?:excluding|exclude|ignore|omit|omitting)\b|不要返回|而不是|排除|忽略|"
                r"compared\s+(?:with|to)\b|unlike\b|versus\b|vs\b|opposite\s+to\b|相比|对比)",
                clause, re.I,
            ):
                return clause
            return " "
        positive = NEGATIVE_RESULT_CLAUSE_RE.sub(mask, positive)
        positive = COMPARISON_CLAUSE_RE.sub(mask, positive)
    lowered = positive.casefold()
    return any(marker in lowered for marker in CALLER_QUERY_MARKERS)


def indirect_seed_scores(
    matches: list[dict[str, Any]],
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for item in matches:
        path = str(item.get("file_path") or "")
        if not path or item.get("graph_depth") or not INDIRECT_PATH_RE.search(path):
            continue
        scores[path] = max(scores.get(path, 0.0), float(item.get("score") or 0.0))
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return dict(ranked[:MAX_SEED_PATHS])


def caller_items(
    rows: list[Any],
    seed_scores: dict[str, float],
) -> list[dict[str, Any]]:
    seed_score = max(seed_scores.values(), default=0.0)
    selected: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for row in rows:
        item = row_dict(row)
        path = str(item.get("file_path") or "")
        if not path or path in seen_paths:
            continue
        seen_paths.add(path)
        file_summary = str(item.pop("caller_file_summary", "") or "")
        confidence = float(item.pop("caller_confidence", 0.0) or 0.0)
        relations = str(item.pop("caller_relations", "") or "")
        item["kind"] = "symbol"
        item["score"] = round(seed_score * 0.9 + confidence * 5.0, 3)
        item["summary"] = f"{item.get('summary') or ''} {file_summary}".strip()
        item["business_terms"] = json_list(item.get("business_terms"))
        item["search_terms"] = code_search_terms("symbol", item)
        item["match_reasons"] = [
            "graph_neighbor", "graph_relation:caller_owner", "caller_owner",
        ]
        item["graph_depth"] = 1
        item["caller_relations"] = relations.split(",") if relations else []
        selected.append(item)
        if len(selected) >= MAX_CALLER_OWNERS:
            break
    return selected


def explicit_caller_target_ids(targets, query, resolve_member=None, *, require_complete=False):
    """Bind a qualified caller-of target to symbol IDs, not its whole file.

    Only an explicit English caller-of/for target clause is resolved here; generic
    and unknown request forms retain the old bounded file-seed behavior. A resolved
    clause with an unknown/ambiguous member grants no unrelated caller authority.
    """
    positive = positive_retrieval_query(query)
    if re.search(r"[\"']", positive):
        return None  # Do not treat quoted message text as a relation target.
    target_token = re.compile(r"`?([A-Za-z_$][\w$]*(?:[./][A-Za-z_$][\w$]*)+)`?")
    references = set()
    for clause in re.finditer(
        r"\b(?:actual callers?|caller context|call sites?)\s+(?:of|for)\s+(?:the\s+)?",
        positive, re.IGNORECASE,
    ):
        cursor = clause.end()
        while True:
            token = target_token.match(positive, cursor)
            if token is None:
                if require_complete:
                    return []
                break
            references.add(token.group(1))
            separator = re.match(r"\s*(?:,|and)\s+", positive[token.end():])
            if separator is None:
                if require_complete and not re.fullmatch(r"\s*[.!?]?\s*", positive[token.end():]):
                    return []
                break
            cursor = token.end() + separator.end()
    if not references:
        return None
    selected = set()
    for reference in references:
        files = [row for row in targets if row["file_path"] == reference]
        if files:
            selected.update(int(row["id"]) for row in files)
            continue
        matches = (resolve_member(reference) if resolve_member is not None else
                   [row for row in targets if row["owner_name"] and
                    f'{row["owner_name"]}.{row["symbol"]}' == reference])
        if len(matches) == 1:
            selected.add(int(matches[0]["id"]))
        elif require_complete:
            return []
    return sorted(selected)


def caller_source_identity(item):
    """A complete indexed source identity, not a presentation similarity key."""
    record_id, start, end = (item.get(k) for k in ("id", "start_line", "end_line"))
    path, key, digest = (item.get(k) for k in ("file_path", "symbol_key", "source_digest"))
    if (item.get("kind") != "symbol" or type(record_id) is not int or record_id <= 0
            or type(start) is not int or type(end) is not int or not 0 < start <= end
            or not isinstance(path, str) or not path.strip()
            or not isinstance(key, str) or not key.startswith("symbol:")
            or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
        return None
    return record_id, path, key, start, end, digest


def requested_caller_identities(items, query):
    """Keep an already selected plural caller set distinct during display diversity.

    This does not discover callers, certify completeness or override capacity.
    Unknown/legacy identities and generic request scope retain the old policy.
    """
    if (classify_target_scope(query).get("kind") != "multiple"
            and plural_caller_member(query) is None):
        return None
    by_id = {}
    for item in items:
        record_id = item.get("id")
        if item.get("kind") == "symbol" and type(record_id) is int:
            by_id.setdefault(record_id, set()).add(caller_source_identity(item))
    eligible = set()
    for item in items:
        identity = caller_source_identity(item)
        reasons = set(item.get("match_reasons") or [])
        binding = item.request_binding if isinstance(item, ResolvedCallerItem) else None
        complete_targets = (binding is not None and binding[0] == query
                            and binding[2] == identity and bool(binding[1])
                            and all(type(i) is int and i > 0 for i in binding[1]))
        if (complete_targets and identity is not None and len(by_id[identity[0]]) == 1
                and {"caller_owner", "graph_relation:caller_owner"} <= reasons
                and set(item.get("caller_relations") or []) & set(CALLER_RELATIONS)):
            eligible.add(identity)
    return (query, frozenset(eligible)) if len(eligible) >= 2 else None
