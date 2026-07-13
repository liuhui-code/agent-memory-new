# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3
from typing import Any

from .models import Project
from .storage import connect
from .text import json_list, terms_from_text, unique_list

FOLLOWUP_FILE_LIMIT = 5
FOLLOWUP_SYMBOL_LIMIT = 5
FOLLOWUP_LOG_LIMIT = 5

def has_business_summary(value: Any) -> bool:
    return bool(str(value or "").strip())



def has_business_terms(value: Any) -> bool:
    return bool(json_list(value))



def semantic_quality_report(payload_files: list[dict[str, Any]]) -> dict[str, Any]:
    stats = {
        "files_total": 0,
        "files_with_business_summary": 0,
        "files_with_business_terms": 0,
        "symbols_total": 0,
        "symbols_with_business_summary": 0,
        "symbols_with_business_terms": 0,
        "logs_total": 0,
        "logs_with_business_summary": 0,
        "logs_with_business_terms": 0,
    }
    gaps = {
        "files_missing_business_summary": [],
        "files_missing_business_terms": [],
        "symbols_missing_business_summary": [],
        "symbols_missing_business_terms": [],
        "logs_missing_business_summary": [],
        "logs_missing_business_terms": [],
    }
    for file_item in payload_files:
        if not isinstance(file_item, dict) or not file_item.get("file_path"):
            continue
        file_path = str(file_item["file_path"])
        stats["files_total"] += 1
        if has_business_summary(file_item.get("business_summary")):
            stats["files_with_business_summary"] += 1
        else:
            gaps["files_missing_business_summary"].append(file_path)
        if has_business_terms(file_item.get("business_terms")):
            stats["files_with_business_terms"] += 1
        else:
            gaps["files_missing_business_terms"].append(file_path)

        for symbol_item in file_item.get("symbols") or []:
            if not isinstance(symbol_item, dict) or not symbol_item.get("symbol"):
                continue
            symbol_name = str(symbol_item["symbol"])
            symbol_key = f"{file_path}::{symbol_name}"
            stats["symbols_total"] += 1
            if has_business_summary(symbol_item.get("business_summary")):
                stats["symbols_with_business_summary"] += 1
            else:
                gaps["symbols_missing_business_summary"].append(symbol_key)
            if has_business_terms(symbol_item.get("business_terms")):
                stats["symbols_with_business_terms"] += 1
            else:
                gaps["symbols_missing_business_terms"].append(symbol_key)

        for log_item in file_item.get("logs") or []:
            if not isinstance(log_item, dict) or not log_item.get("message_template"):
                continue
            message_template = str(log_item["message_template"])
            log_key = f"{file_path}::{message_template}"
            stats["logs_total"] += 1
            if has_business_summary(log_item.get("business_summary")):
                stats["logs_with_business_summary"] += 1
            else:
                gaps["logs_missing_business_summary"].append(log_key)
            if has_business_terms(log_item.get("business_terms")):
                stats["logs_with_business_terms"] += 1
            else:
                gaps["logs_missing_business_terms"].append(log_key)
    return {"semantic_stats": stats, "semantic_gaps": gaps}



def semantic_followup_workflow_steps() -> list[str]:
    return [
        "Read the listed files, symbols, and logs in current source.",
        "Fill missing business_summary and business_terms in followup_payload_template.",
        "Write the completed payload with learn-business.",
        "Re-run learn-business, query, or maintain-plan to confirm the semantic gap is reduced.",
    ]



def followup_hint_terms(*values: Any) -> list[str]:
    raw = " ".join(str(value or "") for value in values if str(value or "").strip())
    return unique_list(terms_from_text(raw))



def followup_hint_context(*values: Any) -> list[str]:
    context: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text:
            context.append(text)
    return context



def followup_item_score(path: str, kind: str) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    lower_path = path.lower()
    if kind == "file":
        if lower_path.endswith(".ets"):
            score += 8
            reasons.append("arkts_page_or_module")
        elif lower_path.endswith(".json5"):
            score += 4
            reasons.append("harmonyos_config")
    elif kind == "log":
        score += 24
        reasons.append("missing_log_semantics")
    elif kind == "symbol":
        score += 12
        reasons.append("missing_symbol_semantics")
    return score, reasons



def prioritize_followup_file(
    file_output: dict[str, Any],
    file_missing_summary: bool,
    file_missing_terms: bool,
) -> dict[str, Any]:
    score, reasons = followup_item_score(file_output["file_path"], "file")
    if file_missing_summary:
        score += 6
        reasons.append("missing_file_business_summary")
    if file_missing_terms:
        score += 6
        reasons.append("missing_file_business_terms")

    prioritized_symbols: list[dict[str, Any]] = []
    for symbol in file_output["symbols"]:
        item_score, item_reasons = followup_item_score(file_output["file_path"], "symbol")
        if not has_business_summary(symbol.get("business_summary")):
            item_score += 4
            item_reasons.append("missing_symbol_business_summary")
        if not has_business_terms(symbol.get("business_terms")):
            item_score += 4
            item_reasons.append("missing_symbol_business_terms")
        enriched = dict(symbol)
        enriched["priority_score"] = item_score
        enriched["priority_reasons"] = item_reasons
        enriched["hint_terms"] = followup_hint_terms(
            file_output["file_path"],
            symbol.get("symbol"),
            symbol.get("symbol_type"),
            symbol.get("summary"),
        )
        enriched["hint_context"] = followup_hint_context(
            file_output["file_path"],
            symbol.get("symbol"),
            symbol.get("symbol_type"),
            symbol.get("summary"),
        )
        prioritized_symbols.append(enriched)

    prioritized_logs: list[dict[str, Any]] = []
    for log in file_output["logs"]:
        item_score, item_reasons = followup_item_score(file_output["file_path"], "log")
        if not has_business_summary(log.get("business_summary")):
            item_score += 4
            item_reasons.append("missing_log_business_summary")
        if not has_business_terms(log.get("business_terms")):
            item_score += 4
            item_reasons.append("missing_log_business_terms")
        enriched = dict(log)
        enriched["priority_score"] = item_score
        enriched["priority_reasons"] = item_reasons
        enriched["hint_terms"] = followup_hint_terms(
            file_output["file_path"],
            log.get("message_template"),
            log.get("function"),
            log.get("level"),
            log.get("logger"),
            log.get("raw_statement"),
            log.get("business_event"),
            log.get("trigger_stage"),
            " ".join(json_list(log.get("symptom_terms"))),
            " ".join(json_list(log.get("likely_causes"))),
            log.get("process_hint"),
            " ".join(json_list(log.get("neighbor_terms"))),
        )
        enriched["hint_context"] = followup_hint_context(
            file_output["file_path"],
            log.get("message_template"),
            log.get("function"),
            log.get("level"),
            log.get("logger"),
            log.get("raw_statement"),
            log.get("business_event"),
            log.get("trigger_stage"),
            " ".join(json_list(log.get("symptom_terms"))),
            " ".join(json_list(log.get("likely_causes"))),
            log.get("process_hint"),
            " ".join(json_list(log.get("neighbor_terms"))),
        )
        prioritized_logs.append(enriched)

    prioritized_symbols.sort(
        key=lambda item: (item["priority_score"], item.get("symbol_type") == "function", item["symbol"]),
        reverse=True,
    )
    prioritized_logs.sort(
        key=lambda item: (item["priority_score"], item.get("level") == "error", item["message_template"]),
        reverse=True,
    )

    score += sum(item["priority_score"] for item in prioritized_symbols[:FOLLOWUP_SYMBOL_LIMIT])
    score += sum(item["priority_score"] for item in prioritized_logs[:FOLLOWUP_LOG_LIMIT])
    for item in prioritized_symbols[:FOLLOWUP_SYMBOL_LIMIT]:
        for reason in item["priority_reasons"]:
            if reason not in reasons:
                reasons.append(reason)
    for item in prioritized_logs[:FOLLOWUP_LOG_LIMIT]:
        for reason in item["priority_reasons"]:
            if reason not in reasons:
                reasons.append(reason)
    enriched_file = dict(file_output)
    enriched_file["priority_score"] = score
    enriched_file["priority_reasons"] = reasons
    enriched_file["hint_terms"] = followup_hint_terms(
        file_output["file_path"],
        file_output.get("summary"),
        " ".join(symbol.get("symbol", "") for symbol in prioritized_symbols[:FOLLOWUP_SYMBOL_LIMIT]),
        " ".join(log.get("message_template", "") for log in prioritized_logs[:FOLLOWUP_LOG_LIMIT]),
    )
    enriched_file["hint_context"] = followup_hint_context(
        file_output["file_path"],
        file_output.get("summary"),
        " ".join(symbol.get("symbol", "") for symbol in prioritized_symbols[:FOLLOWUP_SYMBOL_LIMIT]),
        " ".join(log.get("message_template", "") for log in prioritized_logs[:FOLLOWUP_LOG_LIMIT]),
    )
    enriched_file["symbols"] = prioritized_symbols[:FOLLOWUP_SYMBOL_LIMIT]
    enriched_file["logs"] = prioritized_logs[:FOLLOWUP_LOG_LIMIT]
    enriched_file["truncated_counts"] = {
        "symbols": max(0, len(prioritized_symbols) - len(enriched_file["symbols"])),
        "logs": max(0, len(prioritized_logs) - len(enriched_file["logs"])),
    }
    return enriched_file



def finalize_semantic_followup(files: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not files:
        return None
    files.sort(key=lambda item: (item["priority_score"], item["file_path"]), reverse=True)
    truncated = len(files) > FOLLOWUP_FILE_LIMIT
    visible_files = files[:FOLLOWUP_FILE_LIMIT]
    remaining_files = max(0, len(files) - len(visible_files))
    return {
        "command_template": "python tools/agent_memory.py learn-business --project . --payload '<json>' --json",
        "workflow_steps": semantic_followup_workflow_steps(),
        "recommended_next_action": "run_learn_business_now",
        "truncated": truncated,
        "returned_counts": {
            "files": len(visible_files),
            "symbols": sum(len(file_item["symbols"]) for file_item in visible_files),
            "logs": sum(len(file_item["logs"]) for file_item in visible_files),
        },
        "remaining_counts": {
            "files": remaining_files,
            "symbols": sum(file_item["truncated_counts"]["symbols"] for file_item in visible_files),
            "logs": sum(file_item["truncated_counts"]["logs"] for file_item in visible_files),
        },
        "followup_payload_template": {"files": visible_files},
    }



def semantic_followup_template(payload_files: list[dict[str, Any]]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for file_item in payload_files:
        if not isinstance(file_item, dict) or not file_item.get("file_path"):
            continue
        file_path = str(file_item["file_path"])
        file_output = {
            "file_path": file_path,
            "summary": file_item.get("summary") or "",
            "business_summary": "" if not has_business_summary(file_item.get("business_summary")) else "",
            "business_terms": [],
            "symbols": [],
            "logs": [],
        }
        for symbol_item in file_item.get("symbols") or []:
            if not isinstance(symbol_item, dict) or not symbol_item.get("symbol"):
                continue
            if has_business_summary(symbol_item.get("business_summary")) and has_business_terms(symbol_item.get("business_terms")):
                continue
            file_output["symbols"].append(
                {
                    "symbol": str(symbol_item["symbol"]),
                    "symbol_type": symbol_item.get("symbol_type"),
                    "summary": symbol_item.get("summary") or "",
                    "business_summary": "",
                    "business_terms": [],
                }
            )
        for log_item in file_item.get("logs") or []:
            if not isinstance(log_item, dict) or not log_item.get("message_template"):
                continue
            if has_business_summary(log_item.get("business_summary")) and has_business_terms(log_item.get("business_terms")):
                continue
            file_output["logs"].append(
                {
                    "message_template": str(log_item["message_template"]),
                    "function": log_item.get("function"),
                    "level": log_item.get("level"),
                    "logger": log_item.get("logger"),
                    "raw_statement": log_item.get("raw_statement"),
                    "business_event": log_item.get("business_event"),
                    "trigger_stage": log_item.get("trigger_stage"),
                    "symptom_terms": log_item.get("symptom_terms") or [],
                    "likely_causes": log_item.get("likely_causes") or [],
                    "process_hint": log_item.get("process_hint"),
                    "neighbor_terms": log_item.get("neighbor_terms") or [],
                    "business_summary": "",
                    "business_terms": [],
                }
            )
        if (
            not has_business_summary(file_item.get("business_summary"))
            or not has_business_terms(file_item.get("business_terms"))
            or file_output["symbols"]
            or file_output["logs"]
        ):
            files.append(
                prioritize_followup_file(
                    file_output,
                    not has_business_summary(file_item.get("business_summary")),
                    not has_business_terms(file_item.get("business_terms")),
                )
            )
    return {"files": files}



def semantic_followup_from_db(project: Project, file_paths: list[str]) -> dict[str, Any] | None:
    seen_paths: set[str] = set()
    unique_paths: list[str] = []
    for raw_path in file_paths:
        path = str(raw_path or "").strip()
        if not path or path in seen_paths:
            continue
        seen_paths.add(path)
        unique_paths.append(path)
    if not unique_paths:
        return None
    files: list[dict[str, Any]] = []
    with connect(project) as conn:
        for file_path in unique_paths:
            file_row = conn.execute(
                """
                SELECT file_path, summary, business_summary, business_terms
                FROM code_files
                WHERE project_id = ? AND file_path = ?
                """,
                (project.project_id, file_path),
            ).fetchone()
            if not file_row:
                continue
            file_output = {
                "file_path": file_path,
                "summary": file_row["summary"] or "",
                "business_summary": "",
                "business_terms": [],
                "symbols": [],
                "logs": [],
            }
            file_missing = (
                not has_business_summary(file_row["business_summary"])
                or not has_business_terms(file_row["business_terms"])
            )
            symbol_rows = conn.execute(
                """
                SELECT symbol, symbol_type, summary, business_summary, business_terms
                FROM code_symbols
                WHERE project_id = ? AND file_path = ?
                ORDER BY symbol
                """,
                (project.project_id, file_path),
            ).fetchall()
            for row in symbol_rows:
                if has_business_summary(row["business_summary"]) and has_business_terms(row["business_terms"]):
                    continue
                file_output["symbols"].append(
                    {
                        "symbol": row["symbol"],
                        "symbol_type": row["symbol_type"],
                        "summary": row["summary"] or "",
                        "business_summary": "",
                        "business_terms": [],
                    }
                )
            log_rows = conn.execute(
                """
                SELECT message_template, function, level, logger, raw_statement, business_summary, business_terms,
                       business_event, trigger_stage, symptom_terms, likely_causes, process_hint, neighbor_terms
                FROM code_log_statements
                WHERE project_id = ? AND file_path = ?
                ORDER BY message_template
                """,
                (project.project_id, file_path),
            ).fetchall()
            for row in log_rows:
                if has_business_summary(row["business_summary"]) and has_business_terms(row["business_terms"]):
                    continue
                file_output["logs"].append(
                {
                    "message_template": row["message_template"],
                    "function": row["function"],
                    "level": row["level"],
                    "logger": row["logger"],
                    "raw_statement": row["raw_statement"],
                    "business_event": row["business_event"],
                    "trigger_stage": row["trigger_stage"],
                    "symptom_terms": json_list(row["symptom_terms"]),
                    "likely_causes": json_list(row["likely_causes"]),
                    "process_hint": row["process_hint"],
                    "neighbor_terms": json_list(row["neighbor_terms"]),
                    "business_summary": "",
                    "business_terms": [],
                }
                )
            if file_missing or file_output["symbols"] or file_output["logs"]:
                files.append(prioritize_followup_file(file_output, not has_business_summary(file_row["business_summary"]), not has_business_terms(file_row["business_terms"])))
    return finalize_semantic_followup(files)
