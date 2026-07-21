# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import Project
from .text import bounded_query_tokens, unique_list


@dataclass(frozen=True)
class FieldedRetrieverSpec:
    channel: str
    source_type: str
    passage_kinds: tuple[str, ...]
    columns: tuple[str, ...]
    weights: tuple[float, ...]
    limit: int


@dataclass(frozen=True)
class FieldedPassageBatch:
    rankings: dict[str, list[int]]
    audit: dict[str, Any]


PASSAGE_COLUMNS = (
    "project_id", "source_type", "passage_kind", "source_id", "file_path", "symbol",
    "identity_terms", "semantic_terms", "body_terms", "string_terms",
    "mechanism_terms",
)


def fielded_passage_rankings(
    conn: Any,
    project: Project,
    query: str,
    limit: int,
    source_type: str | None = None,
) -> FieldedPassageBatch:
    tokens = unique_list(bounded_query_tokens(query, 16))
    rankings: dict[str, list[int]] = {}
    channel_audit: dict[str, dict[str, Any]] = {}
    if not tokens or limit <= 0:
        return FieldedPassageBatch(rankings, passage_audit(channel_audit))
    for spec in retriever_specs(limit):
        if source_type and spec.source_type != source_type:
            continue
        ids = passage_source_ids(conn, project, spec, tokens)
        rankings[spec.channel] = ids
        channel_audit[spec.channel] = {
            "source_type": spec.source_type,
            "passage_kinds": list(spec.passage_kinds),
            "columns": list(spec.columns),
            "candidate_count": len(ids),
            **weight_audit(spec),
        }
    return FieldedPassageBatch(rankings, passage_audit(channel_audit))


def retriever_specs(limit: int) -> tuple[FieldedRetrieverSpec, ...]:
    primary = max(8, min(limit, 32))
    secondary = max(8, min(limit // 2, 24))
    return (
        spec("file_identity_fts", "code_file", ("file",),
             ("file_path", "identity_terms"), (6.0, 9.0), primary),
        spec("file_semantic_fts", "code_file", ("file",),
             ("file_path", "semantic_terms"), (1.0, 7.0), secondary),
        spec("symbol_identity_fts", "code_symbol", ("symbol", "callable"),
             ("file_path", "symbol", "identity_terms"), (2.0, 8.0, 10.0), primary),
        spec("symbol_semantic_fts", "code_symbol", ("symbol", "callable"),
             ("symbol", "semantic_terms"), (2.0, 7.0), secondary),
        spec("method_body_fts", "code_symbol", ("callable",),
             ("body_terms",), (8.0,), secondary),
        spec("string_key_fts", "code_symbol", ("callable",),
             ("string_terms",), (9.0,), secondary),
        spec("semantic_mechanism_fts", "code_symbol", ("symbol", "callable"),
             ("mechanism_terms",), (9.0,), secondary),
    )


def spec(
    channel: str,
    source_type: str,
    passage_kinds: tuple[str, ...],
    columns: tuple[str, ...],
    selected_weights: tuple[float, ...],
    limit: int,
) -> FieldedRetrieverSpec:
    weights = tuple(
        selected_weights[columns.index(column)] if column in columns else 0.0
        for column in PASSAGE_COLUMNS
    )
    return FieldedRetrieverSpec(
        channel, source_type, passage_kinds, columns, weights, limit
    )


def passage_source_ids(
    conn: Any,
    project: Project,
    spec: FieldedRetrieverSpec,
    tokens: list[str],
) -> list[int]:
    expression = field_expression(spec.columns, tokens)
    placeholders = ",".join("?" for _ in spec.passage_kinds)
    weight_sql = ", ".join(str(value) for value in spec.weights)
    rows = conn.execute(
        f"""
        SELECT source_id
        FROM code_passage_fts
        WHERE code_passage_fts MATCH ?
          AND project_id = ?
          AND source_type = ?
          AND passage_kind IN ({placeholders})
        ORDER BY bm25(code_passage_fts, {weight_sql}), rowid
        LIMIT ?
        """,
        (
            expression, project.project_id, spec.source_type,
            *spec.passage_kinds, spec.limit,
        ),
    ).fetchall()
    return unique_positive_ids(row["source_id"] for row in rows)


def field_expression(columns: tuple[str, ...], tokens: list[str]) -> str:
    quoted = ['"' + token.replace('"', '""') + '"*' for token in tokens]
    return "{" + " ".join(columns) + "} : (" + " OR ".join(quoted) + ")"


def weight_audit(spec: FieldedRetrieverSpec) -> dict[str, float]:
    return {
        f"{column}_weight": spec.weights[PASSAGE_COLUMNS.index(column)]
        for column in spec.columns
    }


def passage_audit(channels: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "provider": "code_passage_fts/v2",
        "score_scope": "channel_local_bm25",
        "channels": channels,
    }


def candidate_refs(
    rows: list[Any],
    ordered_ids: list[int],
    lanes_by_id: dict[int, list[str]],
) -> list[dict[str, Any]]:
    by_id = {int(row["id"]): row for row in rows}
    refs: list[dict[str, Any]] = []
    for record_id in ordered_ids:
        row = by_id.get(record_id)
        if row is None or "file_path" not in row.keys():
            continue
        ref = {
            "id": record_id,
            "file_path": str(row["file_path"]),
            "channels": list(lanes_by_id.get(record_id, [])),
        }
        if "symbol" in row.keys() and row["symbol"]:
            ref["symbol"] = str(row["symbol"])
        refs.append(ref)
    return refs


def passage_candidate_refs(
    conn: Any,
    project: Project,
    source_type: str,
    ordered_ids: list[int],
    rankings: dict[str, list[int]],
) -> list[dict[str, Any]]:
    if not ordered_ids:
        return []
    placeholders = ",".join("?" for _ in ordered_ids)
    rows = conn.execute(
        f"SELECT source_id, file_path, symbol FROM code_passages "
        f"WHERE project_id = ? AND source_type = ? "
        f"AND source_id IN ({placeholders})",
        (project.project_id, source_type, *ordered_ids),
    ).fetchall()
    by_id = {int(row["source_id"]): row for row in rows}
    lanes = {
        record_id: [channel for channel, ids in rankings.items() if record_id in ids]
        for record_id in ordered_ids
    }
    return [
        {
            "id": record_id,
            "file_path": str(by_id[record_id]["file_path"]),
            "symbol": str(by_id[record_id]["symbol"] or ""),
            "channels": lanes[record_id],
        }
        for record_id in ordered_ids if record_id in by_id
    ]


def candidate_path_recall_at_k(
    expected_paths: set[str],
    refs: list[dict[str, Any]],
    k: int = 20,
) -> float:
    if not expected_paths:
        return 0.0
    observed = {
        str(item.get("file_path") or "")
        for item in refs[:max(0, k)]
        if item.get("file_path")
    }
    return round(len(expected_paths & observed) / len(expected_paths), 4)


def unique_positive_ids(values: Any) -> list[int]:
    result: list[int] = []
    seen: set[int] = set()
    for value in values:
        record_id = int(value)
        if record_id > 0 and record_id not in seen:
            seen.add(record_id)
            result.append(record_id)
    return result
