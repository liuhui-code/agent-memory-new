# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from typing import Any

from tools.agent_memory_runtime.source_exploration import (
    ALLOWED_EXPANSION_REASONS,
    EVIDENCE_BASES,
    EXPANSION_ROUND_LIMIT,
    FILES_PER_EXPANSION_LIMIT,
    SOURCE_FILE_LIMIT,
    SOURCE_READ_LINE_LIMIT,
    SOURCE_READS_PER_FILE_LIMIT,
    SOURCE_SEARCH_LIMIT,
    STOP_REASONS,
)


def build_prompt(
    request: dict[str, Any],
    memory_context: dict[str, Any] | None = None,
) -> str:
    case = request.get("case") or {}
    task = case.get("task") or {}
    lines = [
        "Act as the external coding Agent for a controlled benchmark.",
        "Do not modify files. Do not inspect Git history. Do not search the web.",
        f"Task type: {case.get('task_type', 'diagnosis')}",
        f"Task: {task.get('description', '')}",
    ]
    constraints = task.get("constraints") or []
    if constraints:
        lines.append("Constraints:")
        lines.extend(f"- {item}" for item in constraints)
    lines.append("Benchmark rules:")
    lines.extend(f"- {item}" for item in request.get("instructions") or [])
    if memory_context is not None:
        lines.extend(memory_protocol(memory_context))
    lines.extend(common_response_protocol(request))
    return "\n".join(lines)


def memory_protocol(memory_context: dict[str, Any]) -> list[str]:
    return [
        "Agent Memory context was queried once by the benchmark runner before this session:",
        json.dumps(memory_context, ensure_ascii=False),
        source_context_instruction(memory_context),
        source_budget_instruction(memory_context),
        "Evidence loop: TRIAGE -> GAP -> VERIFY -> STOP. TRIAGE: inspect the highest-ranked role=primary anchor first. Do not open every anchor by default.",
        ledger_instruction(memory_context),
        "GAP: Name exactly one allowed gap before opening expansion/non-anchor files; at most two new files per round. Put up to two representative files in expansion_trace and every opened file in investigated_files. Runner derives expansion accounting from investigated_files.",
        "VERIFY/STOP: sufficient evidence is a causal or repair-owner file showing a concrete operation, branch, state transition, boundary, or API misuse that explains the symptom; mechanism_evidence_files must include it. Inspect one supporting boundary only when required. Once sufficient evidence exists, run no more source search or read and return supported_cause_found with direct_source_mechanism. Otherwise use inference_only/no_new_evidence, or budget_exhausted_report_uncertainty before exceeding a limit.",
    ]


def source_context_instruction(memory_context: dict[str, Any]) -> str:
    handoff = memory_context.get("query_handoff")
    anchors = handoff.get("code_anchors") if isinstance(handoff, dict) else None
    has_bodies = any(
        isinstance(item, dict) and bool(item.get("source_excerpts"))
        for item in anchors or []
    )
    if has_bodies:
        return (
            "Treat Memory as context. source_excerpts were read from this current worktree; "
            "do not reread those lines. Open source only for a named evidence gap outside them."
        )
    return "Treat its output only as context. Verify all conclusions against current source."


def ledger_instruction(memory_context: dict[str, Any]) -> str:
    limits = source_limits(memory_context)
    return (
        "SEARCH LEDGER before every command: update searches_used. "
        "Count every rg/grep/egrep/fgrep/find/fd occurrence, including pipelines and "
        f"compound commands; never execute if searches_used would exceed {limits['searches']}. "
        "READ PLAN: Known anchor paths must be read directly, not searched. Read "
        "one source-read command per file for read_window; source_ranges are targets, not separate reads. Without "
        f"a window, read at most {limits['read_lines']} lines. Only one additional window "
        "is allowed after naming a gap; otherwise reuse output."
    )


def source_budget_instruction(memory_context: dict[str, Any]) -> str:
    values = source_limits(memory_context)
    return (
        "Hard Memory source limits: at most "
        f"{values['searches']} source-search invocations, "
        f"{values['files']} total investigated source files, "
        f"{values['rounds']} expansion rounds, "
        f"{values['round_files']} new files per round, "
        f"{values['reads_per_file']} source-read per file, and "
        f"{values['read_lines']} relevant lines per read."
    )


def source_limits(memory_context: dict[str, Any]) -> dict[str, int]:
    handoff = memory_context.get("query_handoff")
    exploration = handoff.get("source_exploration") if isinstance(handoff, dict) else None
    limits = exploration.get("limits") if isinstance(exploration, dict) else None
    values = limits if isinstance(limits, dict) else {}
    return {
        "searches": int(values.get("searches") or SOURCE_SEARCH_LIMIT),
        "files": int(values.get("files") or SOURCE_FILE_LIMIT),
        "rounds": int(values.get("rounds") or EXPANSION_ROUND_LIMIT),
        "round_files": int(values.get("round_files") or FILES_PER_EXPANSION_LIMIT),
        "reads_per_file": int(
            values.get("reads_per_file") or SOURCE_READS_PER_FILE_LIMIT
        ),
        "read_lines": int(values.get("read_lines") or SOURCE_READ_LINE_LIMIT),
    }


def common_response_protocol(request: dict[str, Any]) -> list[str]:
    return [
        "Inspect the smallest useful set of current source files.",
        "Put only root-cause or repair-owner files in predicted_files. Put inspected callers, boundaries, and corroborating files in supporting_files.",
        "Do not repeat a predicted file in supporting_files; include both groups in investigated_files.",
        "Report source_search_count, expansion_trace, and the final stop_reason.",
        "Return only the requested JSON object.",
        "Category precedence is: async concurrency, then the concrete failure domain, then low-level api or state implementation detail.",
        "Use async for parallel in-flight requests, races, ordering, or duplicate async side effects, even when a missing state flag is the guard. Use state only for a wrong stored or derived value without concurrency.",
        "Use media for WebM, video, audio, or image loading, decoding, playback, and local media-resource access, even when the mechanism is API misuse. Describe the API misuse in summary instead of changing the category to api.",
        "Use api only when an external or platform API contract is itself the primary failure domain and no stronger domain category applies. Other categories include route, lifecycle, ui_layout, resource, database_failure, and push.",
        "Do not include private reasoning, thoughts, or chain-of-thought.",
        "Response contract:",
        json.dumps(request.get("response_schema") or {}, ensure_ascii=False),
    ]


def benchmark_response_schema() -> dict[str, Any]:
    properties = {
        "schema_version": {"type": "string"},
        "case_id": {"type": "string"},
        "variant": {"type": "string"},
        "trial_index": {"type": "integer", "minimum": 1},
        "root_cause_category": {"type": "string"},
        "predicted_files": {"type": "array", "items": {"type": "string"}},
        "supporting_files": {"type": "array", "items": {"type": "string"}},
        "investigated_files": {"type": "array", "items": {"type": "string"}},
        "causal_level": {
            "type": "string",
            "enum": ["association", "supported", "verified", "rejected"],
        },
        "verification_status": {
            "type": "string",
            "enum": ["pass", "fail", "unknown"],
        },
        "query_rounds": {"type": "integer", "minimum": 0},
        "source_search_count": {"type": "integer", "minimum": 0},
        "expansion_trace": {
            "type": "array",
            "maxItems": EXPANSION_ROUND_LIMIT,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["reason", "files"],
                "properties": {
                    "reason": {
                        "type": "string",
                        "enum": list(ALLOWED_EXPANSION_REASONS),
                    },
                    "files": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": FILES_PER_EXPANSION_LIMIT,
                        "items": {"type": "string"},
                    },
                },
            },
        },
        "stop_reason": {"type": "string", "enum": list(STOP_REASONS)},
        "evidence_basis": {"type": "string", "enum": list(EVIDENCE_BASES)},
        "mechanism_evidence_files": {
            "type": "array",
            "items": {"type": "string"},
        },
        "token_estimate": {"type": "integer", "minimum": 0},
        "elapsed_ms": {"type": "integer", "minimum": 0},
        "summary": {"type": "string"},
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }
