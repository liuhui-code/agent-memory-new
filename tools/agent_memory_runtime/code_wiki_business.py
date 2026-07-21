# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .code_wiki_edges import rebuild_code_memory_edges
from .code_passages import rebuild_code_passages
from .code_wiki_extractors import summarize_symbol
from .code_wiki_followup import finalize_semantic_followup, semantic_followup_template, semantic_quality_report
from .code_wiki_imports import project_for_learning_source
from .models import CODE_EXTENSIONS
from .records import output
from .storage import connect, ensure_initialized, now_iso, resolve_project
from .text import json_list, json_list_text, unique_list

def merge_business_terms(existing: Any, incoming: Any) -> str:
    merged: list[str] = []
    seen: set[str] = set()
    for value in [*json_list(existing), *json_list(incoming)]:
        stripped = str(value).strip()
        normalized = stripped.lower()
        if not stripped or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(stripped)
    return json.dumps(merged, ensure_ascii=False)



def merged_optional_text(existing: Any, incoming: Any) -> str | None:
    incoming_text = str(incoming or "").strip()
    if incoming_text:
        return incoming_text
    existing_text = str(existing or "").strip()
    return existing_text or None



def merged_business_summary(
    existing: Any,
    incoming: Any,
    target: str,
    entity_type: str,
    conflicts: list[dict[str, Any]],
) -> str | None:
    existing_text = str(existing or "").strip()
    incoming_text = str(incoming or "").strip()
    if not existing_text:
        return incoming_text or None
    if not incoming_text:
        return existing_text
    if existing_text == incoming_text:
        return existing_text
    conflicts.append(
        {
            "entity_type": entity_type,
            "target": target,
            "field": "business_summary",
            "existing": existing_text,
            "incoming": incoming_text,
            "resolution": "manual_review_required",
            "source_command": "learn-business",
        }
    )
    return existing_text



def learn_business(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    source_project = project_for_learning_source(project, args.source)
    try:
        payload = json.loads(args.payload)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid --payload JSON: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("files"), list):
        raise SystemExit("--payload must be an object with a files array")
    ts = now_iso()
    files_written = 0
    symbols_written = 0
    logs_written = 0
    conflicts: list[dict[str, Any]] = []
    with connect(source_project) as conn:
        for file_item in payload["files"]:
            if not isinstance(file_item, dict) or not file_item.get("file_path"):
                raise SystemExit("each file item must include file_path")
            file_path = str(file_item["file_path"])
            language = file_item.get("language") or CODE_EXTENSIONS.get(Path(file_path).suffix.lower()) or "unknown"
            summary = file_item.get("summary") or f"{language} file"
            existing_file = conn.execute(
                """
                SELECT file_path, summary, language, business_summary, business_terms
                FROM code_files
                WHERE project_id = ? AND file_path = ?
                """,
                (source_project.project_id, file_path),
            ).fetchone()
            file_business_summary = merged_business_summary(
                existing_file["business_summary"] if existing_file else None,
                file_item.get("business_summary"),
                file_path,
                "code_file",
                conflicts,
            )
            file_business_terms = merge_business_terms(
                existing_file["business_terms"] if existing_file else None,
                file_item.get("business_terms"),
            )
            conn.execute(
                """
                INSERT INTO code_files(
                  project_id, file_path, summary, language,
                  business_summary, business_terms, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, file_path) DO UPDATE SET
                  summary=excluded.summary,
                  language=excluded.language,
                  business_summary=excluded.business_summary,
                  business_terms=excluded.business_terms,
                  updated_at=excluded.updated_at
                """,
                (
                    source_project.project_id,
                    file_path,
                    summary,
                    language,
                    file_business_summary,
                    file_business_terms,
                    ts,
                ),
            )
            files_written += 1
            for symbol_item in file_item.get("symbols") or []:
                if not isinstance(symbol_item, dict) or not symbol_item.get("symbol"):
                    continue
                symbol = str(symbol_item["symbol"])
                symbol_type = symbol_item.get("symbol_type") or "symbol"
                symbol_summary = symbol_item.get("summary") or summarize_symbol(file_path, symbol, symbol_type, language)
                existing_symbol = conn.execute(
                    """
                    SELECT *
                    FROM code_symbols
                    WHERE project_id = ? AND file_path = ? AND symbol = ? AND COALESCE(symbol_type, 'symbol') = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (source_project.project_id, file_path, symbol, symbol_type),
                ).fetchone()
                symbol_business_summary = merged_business_summary(
                    existing_symbol["business_summary"] if existing_symbol else None,
                    symbol_item.get("business_summary"),
                    f"{file_path}::{symbol}",
                    "code_symbol",
                    conflicts,
                )
                symbol_business_terms = merge_business_terms(
                    existing_symbol["business_terms"] if existing_symbol else None,
                    symbol_item.get("business_terms"),
                )
                if existing_symbol:
                    conn.execute(
                        """
                        UPDATE code_symbols
                        SET symbol_type = ?, summary = ?, calls = ?,
                            business_summary = ?, business_terms = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            symbol_type,
                            symbol_summary,
                            symbol_item.get("calls") or existing_symbol["calls"] or "",
                            symbol_business_summary,
                            symbol_business_terms,
                            ts,
                            existing_symbol["id"],
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO code_symbols(
                          project_id, file_path, symbol, symbol_type, summary, calls,
                          business_summary, business_terms, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            source_project.project_id,
                            file_path,
                            symbol,
                            symbol_type,
                            symbol_summary,
                            symbol_item.get("calls") or "",
                            symbol_business_summary,
                            symbol_business_terms,
                            ts,
                        ),
                    )
                symbols_written += 1
            for log_item in file_item.get("logs") or []:
                if not isinstance(log_item, dict) or not log_item.get("message_template"):
                    continue
                message_template = str(log_item.get("message_template"))
                existing_log = conn.execute(
                    """
                    SELECT *
                    FROM code_log_statements
                    WHERE project_id = ? AND file_path = ?
                      AND message_template = ?
                      AND COALESCE(function, '') = COALESCE(?, '')
                      AND COALESCE(level, '') = COALESCE(?, '')
                      AND COALESCE(logger, '') = COALESCE(?, '')
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (
                        source_project.project_id,
                        file_path,
                        message_template,
                        log_item.get("function"),
                        log_item.get("level"),
                        log_item.get("logger"),
                    ),
                ).fetchone()
                log_target = f"{file_path}::{message_template}"
                log_business_summary = merged_business_summary(
                    existing_log["business_summary"] if existing_log else None,
                    log_item.get("business_summary"),
                    log_target,
                    "code_log_statement",
                    conflicts,
                )
                log_business_terms = merge_business_terms(
                    existing_log["business_terms"] if existing_log else None,
                    log_item.get("business_terms"),
                )
                log_business_event = merged_optional_text(
                    existing_log["business_event"] if existing_log else None,
                    log_item.get("business_event"),
                )
                log_trigger_stage = merged_optional_text(
                    existing_log["trigger_stage"] if existing_log else None,
                    log_item.get("trigger_stage"),
                )
                log_symptom_terms = merge_business_terms(
                    existing_log["symptom_terms"] if existing_log else None,
                    log_item.get("symptom_terms"),
                )
                log_likely_causes = merge_business_terms(
                    existing_log["likely_causes"] if existing_log else None,
                    log_item.get("likely_causes"),
                )
                log_process_hint = merged_optional_text(
                    existing_log["process_hint"] if existing_log else None,
                    log_item.get("process_hint"),
                )
                log_neighbor_terms = merge_business_terms(
                    existing_log["neighbor_terms"] if existing_log else None,
                    log_item.get("neighbor_terms"),
                )
                if existing_log:
                    conn.execute(
                        """
                        UPDATE code_log_statements
                        SET line = ?, function = ?, level = ?, logger = ?,
                            message_template = ?, raw_statement = ?,
                            business_summary = ?, business_terms = ?, business_event = ?,
                            trigger_stage = ?, symptom_terms = ?, likely_causes = ?,
                            process_hint = ?, neighbor_terms = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            log_item.get("line") if log_item.get("line") is not None else existing_log["line"],
                            log_item.get("function") if log_item.get("function") is not None else existing_log["function"],
                            log_item.get("level") if log_item.get("level") is not None else existing_log["level"],
                            log_item.get("logger") if log_item.get("logger") is not None else existing_log["logger"],
                            message_template,
                            log_item.get("raw_statement") if log_item.get("raw_statement") is not None else existing_log["raw_statement"],
                            log_business_summary,
                            log_business_terms,
                            log_business_event,
                            log_trigger_stage,
                            log_symptom_terms,
                            log_likely_causes,
                            log_process_hint,
                            log_neighbor_terms,
                            ts,
                            existing_log["id"],
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO code_log_statements(
                          project_id, file_path, line, function, level, logger,
                          message_template, raw_statement,
                          business_summary, business_terms, business_event, trigger_stage,
                          symptom_terms, likely_causes, process_hint, neighbor_terms, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            source_project.project_id,
                            file_path,
                            log_item.get("line"),
                            log_item.get("function"),
                            log_item.get("level"),
                            log_item.get("logger"),
                            message_template,
                            log_item.get("raw_statement"),
                            log_business_summary,
                            log_business_terms,
                            log_business_event,
                            log_trigger_stage,
                            log_symptom_terms,
                            log_likely_causes,
                            log_process_hint,
                            log_neighbor_terms,
                            ts,
                        ),
                    )
                logs_written += 1
        rebuild_code_memory_edges(conn, source_project)
        passage_stats = rebuild_code_passages(
            conn,
            source_project.project_id,
            [str(item["file_path"]) for item in payload["files"]],
        )
        edge_count = conn.execute(
            "SELECT COUNT(*) AS count FROM memory_edges WHERE project_id = ?",
            (source_project.project_id,),
        ).fetchone()["count"]
        for conflict in conflicts:
            conn.execute(
                """
                INSERT INTO semantic_conflicts(
                  project_id, entity_type, target, field, existing, incoming, resolution,
                  source_command, observed_at, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
                """,
                (
                    source_project.project_id,
                    conflict.get("entity_type") or "code_file",
                    conflict.get("target"),
                    conflict.get("field"),
                    conflict.get("existing"),
                    conflict.get("incoming"),
                    conflict.get("resolution"),
                    conflict.get("source_command") or "learn-business",
                    ts,
                ),
            )
        conn.commit()
    data = {
        "project_id": project.project_id,
        "source": str(source_project.root),
        "source_command": "learn-business",
        "observed_at": ts,
        "files_written": files_written,
        "symbols_written": symbols_written,
        "logs_written": logs_written,
        "passage_index": passage_stats,
        "memory_edges_total": edge_count,
    }
    if conflicts:
        for conflict in conflicts:
            conflict.setdefault("observed_at", ts)
        data["semantic_conflicts"] = conflicts
    semantic_quality = semantic_quality_report(payload["files"])
    data.update(semantic_quality)
    if any(semantic_quality["semantic_gaps"].values()):
        template = semantic_followup_template(payload["files"])
        followup = finalize_semantic_followup(template["files"])
        if followup:
            data["semantic_followup"] = followup
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_learn_business.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output(data, args.json)
