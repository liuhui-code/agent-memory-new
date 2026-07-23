from __future__ import annotations

from typing import Any

from .models import Project
from .records import row_dict
from .storage import connect


CALLABLE_TYPES = ("function", "method")
SYMBOL_OWNER_RELATIONS = (
    "calls", "awaits", "registers_callback", "renders_component",
    "passes_property",
)
FILE_OWNER_RELATIONS = ("renders_component", "passes_property")


def load_one_hop_owners(
    project: Project,
    seed_ids: list[int],
    limit: int,
) -> list[dict[str, Any]]:
    seeds = sorted({int(value) for value in seed_ids if int(value) > 0})
    if not seeds:
        return []
    direct = symbol_owners(project, seeds, limit)
    remaining = max(0, limit - len(direct))
    flow = file_flow_owners(project, seeds, remaining)
    return dedupe_owners([*direct, *flow])[:limit]


def symbol_owners(
    project: Project,
    seed_ids: list[int],
    limit: int,
) -> list[dict[str, Any]]:
    query = """
        SELECT owners.*, MAX(edges.confidence) AS owner_confidence,
               GROUP_CONCAT(DISTINCT edges.relation) AS owner_relations
        FROM memory_edges AS edges
        JOIN code_symbols AS owners
          ON owners.project_id = edges.project_id AND owners.id = edges.source_id
        WHERE edges.project_id = ? AND edges.valid_to IS NULL
          AND edges.source_type = 'code_symbol' AND edges.target_type = 'code_symbol'
          AND edges.target_id IN ({seeds}) AND edges.relation IN ({relations})
          AND owners.symbol_type IN ({types})
        GROUP BY owners.id
        ORDER BY owner_confidence DESC, owners.id
        LIMIT ?
        """.format(
        seeds=placeholders(seed_ids), relations=placeholders(SYMBOL_OWNER_RELATIONS),
        types=placeholders(CALLABLE_TYPES),
    )
    bindings = (project.project_id, *seed_ids, *SYMBOL_OWNER_RELATIONS, *CALLABLE_TYPES, limit)
    with connect(project) as conn:
        rows = conn.execute(query, bindings).fetchall()
    return [owner_record(row_dict(row)) for row in rows]


def file_flow_owners(
    project: Project,
    seed_ids: list[int],
    limit: int,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    query = """
        WITH seed_components AS (
          SELECT components.id
          FROM code_symbols AS seeds
          JOIN code_symbols AS components
            ON components.project_id = seeds.project_id
           AND components.file_path = seeds.file_path
          WHERE seeds.project_id = ? AND seeds.id IN ({seeds})
            AND components.symbol_type = 'component'
        ), flow AS (
          SELECT edges.source_id, MAX(edges.confidence) AS owner_confidence,
                 GROUP_CONCAT(DISTINCT edges.relation) AS owner_relations
          FROM memory_edges AS edges
          WHERE edges.project_id = ? AND edges.valid_to IS NULL
            AND edges.source_type = 'code_file' AND edges.target_type = 'code_symbol'
            AND edges.target_id IN (SELECT id FROM seed_components)
            AND edges.relation IN ({relations})
          GROUP BY edges.source_id
        ), ranked AS (
          SELECT owners.*, flow.owner_confidence, flow.owner_relations,
                 ROW_NUMBER() OVER (
                   PARTITION BY flow.source_id
                   ORDER BY CASE owners.symbol WHEN 'build' THEN 0 ELSE 1 END,
                            owners.start_line, owners.id
                 ) AS owner_rank
          FROM flow
          JOIN code_files AS files ON files.project_id = ? AND files.id = flow.source_id
          JOIN code_symbols AS owners
            ON owners.project_id = files.project_id AND owners.file_path = files.file_path
          WHERE owners.symbol_type IN ({types})
        )
        SELECT * FROM ranked WHERE owner_rank = 1
        ORDER BY owner_confidence DESC, id LIMIT ?
        """.format(
        seeds=placeholders(seed_ids), relations=placeholders(FILE_OWNER_RELATIONS),
        types=placeholders(CALLABLE_TYPES),
    )
    bindings = (
        project.project_id, *seed_ids, project.project_id,
        *FILE_OWNER_RELATIONS, project.project_id, *CALLABLE_TYPES, limit,
    )
    with connect(project) as conn:
        rows = conn.execute(query, bindings).fetchall()
    return [owner_record(row_dict(row)) for row in rows]


def owner_record(item: dict[str, Any]) -> dict[str, Any]:
    item["file_rank"] = 9
    item["direct_score"] = 0.0
    item["direct_match_reasons"] = []
    item["direct_recall_lanes"] = []
    item["graph_depth"] = 1
    item["graph_confidence"] = float(item.pop("owner_confidence", 0.0) or 0.0)
    relations = str(item.pop("owner_relations", "") or "")
    item["graph_relations"] = sorted(value for value in relations.split(",") if value)
    return item


def dedupe_owners(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for item in items:
        record_id = int(item.get("id") or 0)
        if record_id > 0 and record_id not in result:
            result[record_id] = item
    return list(result.values())


def placeholders(values: tuple[str, ...] | list[int]) -> str:
    return ",".join("?" for _ in values)
