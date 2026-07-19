# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .experience_maturity import score_experience_maturity
from .experience_usage import apply_usage_adjustment, collect_usage_adjustments_by_type
from .feedback_policy import candidate_ids
from .incident_trace_models import INCIDENT_TRACE_SEARCH_LIMIT
from .incident_trace_query import collect_incident_trace_matches
from .log_signal_quality import score_log_signal
from .models import Project
from .quality_scoring import score_reflection_quality, score_semantic_quality
from .query_edges import collect_related_edge_candidates
from .query_code_focus import score_file_behavior_match
from .query_code_ranking import score_query_focus_coverage
from .query_candidate_recall import (
    CandidateRecallBatch,
    CandidateRecallPort,
    SQLiteCandidateRecall,
)
from .query_graph_neighbors import collect_result_graph_neighbors
from .records import memory_warning, row_dict
from .retrieval_feedback import collect_feedback_adjustments
from .storage import connect
from .text import (
    code_search_terms,
    json_list,
    matching_code_path_segments,
    query_tokens,
    score_identifier_identity,
    score_weighted_fields,
    tokenize,
    unique_list,
)

@dataclass(frozen=True)
class CollectedMatches:
    matches: dict[str, list[dict[str, Any]]]
    recall_audit: dict[str, Any]



def apply_feedback_penalty(item: dict[str, Any], penalties: dict[int, dict[str, Any]]) -> None:
    feedback = penalties.get(int(item.get("id") or 0))
    if not feedback:
        item["feedback_penalty"] = 0.0
        return
    item["feedback_penalty"] = feedback["penalty"]
    item["feedback_reasons"] = unique_list([str(reason) for reason in feedback.get("reasons", [])])
    item["feedback_ids"] = feedback.get("feedback_ids", [])



def apply_calibration_feedback(item: dict[str, Any], feedback_rows: dict[int, dict[str, Any]]) -> None:
    feedback = feedback_rows.get(int(item.get("id") or 0))
    if not feedback:
        item["calibration_feedback_bonus"] = 0.0
        item["calibration_feedback_penalty"] = 0.0
        return
    item["calibration_feedback_bonus"] = feedback.get("bonus", 0.0)
    item["calibration_feedback_penalty"] = feedback.get("penalty", 0.0)
    item["calibration_feedback_reasons"] = unique_list([str(reason) for reason in feedback.get("reasons", [])])
    item["calibration_feedback_ids"] = feedback.get("feedback_ids", [])



def collect_matches(project: Project, query: str) -> dict[str, list[dict[str, Any]]]:
    return collect_matches_with_audit(project, query).matches


def collect_matches_with_audit(
    project: Project,
    query: str,
    recall_port: CandidateRecallPort | None = None,
) -> CollectedMatches:
    tokens = query_tokens(query)
    original_terms = set(tokenize(query))
    expanded_terms = set(tokens) - original_terms
    results: dict[str, list[dict[str, Any]]] = {
        "semantic_facts": [],
        "reflections": [],
        "episodes": [],
        "wiki_matches": [],
        "code_log_matches": [],
        "edge_matches": [],
        "incident_trace_matches": [],
    }
    with connect(project) as conn:
        recalled = (recall_port or SQLiteCandidateRecall()).recall(conn, project, query)
    semantic = recalled.rows["semantic_facts"]
    reflections = recalled.rows["reflections"]
    episodes = recalled.rows["episodes"]
    files = recalled.rows["code_files"]
    symbols = recalled.rows["code_symbols"]
    logs = recalled.rows["code_log_statements"]
    results["incident_trace_matches"] = collect_incident_trace_matches(project, query, INCIDENT_TRACE_SEARCH_LIMIT)
    memory_candidate_ids = {
        "semantic": candidate_ids(semantic),
        "reflection": candidate_ids(reflections),
    }
    feedback, calibration = collect_feedback_adjustments(
        project, query, record_ids=memory_candidate_ids
    )
    usage = collect_usage_adjustments_by_type(
        project, query, record_ids=memory_candidate_ids
    )
    semantic_feedback = feedback["semantic"]
    reflection_feedback = feedback["reflection"]
    semantic_usage = usage["semantic"]
    reflection_usage = usage["reflection"]
    semantic_calibration_feedback = calibration["semantic"]
    reflection_calibration_feedback = calibration["reflection"]

    for row in semantic:
        score, reasons = score_weighted_fields(
            query,
            tokens,
            expanded_terms,
            [("semantic_fact", row["fact"], 1.0)],
            [("exact_semantic_fact", row["fact"], 2.0)],
        )
        if score:
            item = row_dict(row)
            attach_recall_metadata(item, recalled, "semantic_facts")
            quality = score_semantic_quality(item)
            item["score"] = score + float(row["confidence"] or 0)
            item["quality_score"] = quality["quality_score"]
            item["quality_band"] = quality["quality_band"]
            item["quality_reasons"] = quality["reasons"]
            apply_feedback_penalty(item, semantic_feedback)
            apply_usage_adjustment(item, semantic_usage)
            apply_calibration_feedback(item, semantic_calibration_feedback)
            item["rerank_score"] = round(
                item["score"]
                + item["quality_score"] * 3.0
                + float(item.get("usage_feedback_bonus") or 0.0) * 30.0
                - float(item.get("usage_feedback_penalty") or 0.0) * 40.0
                - item.get("feedback_penalty", 0.0),
                3,
            )
            item["match_reasons"] = reasons
            item["warning"] = memory_warning(item)
            results["semantic_facts"].append(item)

    for row in reflections:
        text = " ".join(
            str(row[key] or "")
            for key in (
                "task",
                "task_type",
                "outcome",
                "problem",
                "summary",
                "reasoning_summary",
                "context_used",
                "what_worked",
                "what_failed",
                "hidden_assumptions",
                "negative_preconditions",
                "verification_method",
                "reuse_feedback",
                "source_cases",
                "skill_candidate",
                "mistake",
                "lesson",
                "future_rule",
                "trigger_condition",
                "repair_action",
                "evidence",
            )
        )
        score, reasons = score_weighted_fields(
            query,
            tokens,
            expanded_terms,
            [("reflection", text, 1.0)],
            [("exact_reflection", text, 2.0)],
        )
        if score:
            item = row_dict(row)
            attach_recall_metadata(item, recalled, "reflections")
            quality = score_reflection_quality(item)
            item["score"] = score
            item["quality_score"] = quality["quality_score"]
            item["quality_band"] = quality["quality_band"]
            item["quality_reasons"] = quality["reasons"]
            item["experience_evidence_profile"] = quality.get("experience_evidence_profile")
            apply_feedback_penalty(item, reflection_feedback)
            apply_usage_adjustment(item, reflection_usage)
            apply_calibration_feedback(item, reflection_calibration_feedback)
            item.update(score_experience_maturity(item))
            item["match_reasons"] = reasons
            item["warning"] = memory_warning(item)
            results["reflections"].append(item)

    for row in episodes:
        text = f"{row['task']} {row['summary']} {row['outcome'] or ''}"
        score, reasons = score_weighted_fields(
            query,
            tokens,
            expanded_terms,
            [("episode", text, 0.8)],
            [("exact_episode", text, 1.5)],
        )
        if score:
            item = row_dict(row)
            attach_recall_metadata(item, recalled, "episodes")
            item["score"] = score
            item["match_reasons"] = reasons
            item["warning"] = memory_warning(item)
            results["episodes"].append(item)

    for row in files:
        search_terms = code_search_terms("file", row)
        score, reasons = score_weighted_fields(
            query,
            tokens,
            expanded_terms,
            [
                ("business_terms", " ".join(json_list(row["business_terms"])), 5.0),
                ("business_summary", row["business_summary"] or "", 3.0),
                ("file_path", row["file_path"], 3.0),
                ("file_summary", row["summary"] or "", 1.0),
                ("file_language", row["language"] or "", 0.6),
                ("search_terms", " ".join(search_terms), 0.8),
            ],
            [("exact_file_path", row["file_path"], 12.0)],
        )
        score, reasons = apply_path_segment_identity(
            query, row["file_path"], score, reasons
        )
        score, reasons = score_file_behavior_match(
            f"{row['file_path']} {row['summary'] or ''}",
            original_terms,
            query,
            score,
            reasons,
        )
        score, reasons = score_query_focus_coverage(
            query, " ".join(search_terms), score, reasons
        )
        if score:
            item = row_dict(row)
            attach_recall_metadata(item, recalled, "code_files")
            item["kind"] = "file"
            item["score"] = score
            item["search_terms"] = search_terms
            item["business_terms"] = json_list(row["business_terms"])
            item["match_reasons"] = reasons
            results["wiki_matches"].append(item)

    for row in symbols:
        search_terms = code_search_terms("symbol", row)
        score, reasons = score_weighted_fields(
            query,
            tokens,
            expanded_terms,
            [
                ("business_terms", " ".join(json_list(row["business_terms"])), 5.0),
                ("business_summary", row["business_summary"] or "", 3.0),
                ("file_path", row["file_path"], 2.0),
                ("symbol", row["symbol"], 4.0),
                ("symbol_type", row["symbol_type"] or "", 2.0),
                ("symbol_summary", row["summary"] or "", 1.5),
                ("search_terms", " ".join(search_terms), 1.0),
            ],
            [
                ("exact_symbol", row["symbol"], 12.0),
                ("exact_file_path", row["file_path"], 4.0),
            ],
        )
        score, reasons = apply_path_segment_identity(
            query, row["file_path"], score, reasons
        )
        score += score_identifier_identity(query, row["symbol"])
        score, reasons = score_query_focus_coverage(
            query, " ".join(search_terms), score, reasons
        )
        if row["symbol_type"] == "resource":
            score -= 8.0
        elif score > 0 and row["start_line"] and row["end_line"]:
            score += 2.0
            reasons = unique_list([*reasons, "source_locatable"])
        if score:
            item = row_dict(row)
            attach_recall_metadata(item, recalled, "code_symbols")
            item["kind"] = "symbol"
            item["score"] = score
            item["search_terms"] = search_terms
            item["business_terms"] = json_list(row["business_terms"])
            item["match_reasons"] = reasons
            results["wiki_matches"].append(item)

    for row in logs:
        search_terms = code_search_terms("log_statement", row)
        score, reasons = score_weighted_fields(
            query,
            tokens,
            expanded_terms,
            [
                ("business_terms", " ".join(json_list(row["business_terms"])), 5.0),
                ("symptom_terms", " ".join(json_list(row["symptom_terms"])), 5.0),
                ("likely_causes", " ".join(json_list(row["likely_causes"])), 4.0),
                ("business_summary", row["business_summary"] or "", 3.0),
                ("business_event", row["business_event"] or "", 4.0),
                ("trigger_stage", row["trigger_stage"] or "", 2.5),
                ("process_hint", row["process_hint"] or "", 2.5),
                ("neighbor_terms", " ".join(json_list(row["neighbor_terms"])), 2.0),
                ("log_message", row["message_template"], 3.0),
                ("log_context", " ".join(str(row[key] or "") for key in ("file_path", "function", "level", "logger", "raw_statement")), 1.2),
                ("search_terms", " ".join(search_terms), 1.0),
            ],
            [
                ("exact_log_message", row["message_template"], 12.0),
                ("exact_file_path", row["file_path"], 4.0),
                ("exact_function", row["function"] or "", 5.0),
                ("exact_business_event", row["business_event"] or "", 7.0),
            ],
        )
        score, reasons = score_query_focus_coverage(
            query, " ".join(search_terms), score, reasons
        )
        if score:
            item = row_dict(row)
            attach_recall_metadata(item, recalled, "code_log_statements")
            item["kind"] = "log_statement"
            item["score"] = score
            item["search_terms"] = search_terms
            item["business_terms"] = json_list(row["business_terms"])
            item["match_reasons"] = reasons
            item.update(score_log_signal(item))
            results["code_log_matches"].append(item)

    edge_targets: dict[str, set[int]] = {
        "code_file": set(),
        "code_symbol": set(),
        "code_log_statement": set(),
    }
    for item in results["wiki_matches"]:
        if item.get("kind") == "file":
            edge_targets["code_file"].add(int(item["id"]))
        elif item.get("kind") == "symbol":
            edge_targets["code_symbol"].add(int(item["id"]))
    for item in results["code_log_matches"]:
        edge_targets["code_log_statement"].add(int(item["id"]))
    if any(edge_targets.values()):
        results["edge_matches"] = collect_related_edge_candidates(project, edge_targets)
        results["wiki_matches"].extend(collect_result_graph_neighbors(project, results, query))

    for key in results:
        results[key].sort(key=lambda item: (item.get("rerank_score", item.get("score", 0)), item.get("created_at", "")), reverse=True)
    return CollectedMatches(results, recalled.audit)


def attach_recall_metadata(
    item: dict[str, Any],
    recalled: CandidateRecallBatch,
    table_name: str,
) -> None:
    item["recall_lanes"] = recalled.lanes_by_id.get(table_name, {}).get(
        int(item.get("id") or 0),
        [],
    )


def apply_path_segment_identity(
    query: str,
    file_path: str,
    score: float,
    reasons: list[str],
) -> tuple[float, list[str]]:
    matches = matching_code_path_segments(query, file_path)
    if not matches:
        return score, reasons
    return score + 20.0 + 2.0 * (len(matches) - 1), unique_list([
        *reasons,
        "exact_path_segment",
    ])
