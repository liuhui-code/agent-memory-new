# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from typing import Any

from .governance_skill_artifacts import format_frontmatter_sequence


def incident_strategy_draft_path(strategy_name: str) -> str:
    return f"docs/incident-strategies/{strategy_name}.md"


def incident_strategy_frontmatter(candidate: dict[str, Any]) -> list[str]:
    return [
        "---",
        f"strategy_name: {json.dumps(candidate['strategy_name'], ensure_ascii=False)}",
        f"artifact_type: {json.dumps('incident_strategy_draft', ensure_ascii=False)}",
        f"promotion_status: {json.dumps('draft', ensure_ascii=False)}",
        'review_status: "pending_review"',
        'reviewer: ""',
        "review_notes: []",
        f"experience_type: {json.dumps('procedure_experience', ensure_ascii=False)}",
        f"supporting_count: {int(candidate.get('supporting_count') or 0)}",
        f"supporting_reflection_ids: {format_frontmatter_sequence(candidate.get('supporting_reflection_ids', []))}",
        f"common_followup_focus: {format_frontmatter_sequence(candidate.get('common_followup_focus', []))}",
        f"supporting_cases: {format_frontmatter_sequence(candidate.get('supporting_cases', []))}",
        f"source_runtime_command: {json.dumps('tools/agent_memory.py', ensure_ascii=False)}",
        "---",
        "",
    ]


def build_incident_strategy_markdown(candidate: dict[str, Any]) -> str:
    lines = incident_strategy_frontmatter(candidate) + [
        f"# Incident Strategy: {candidate['strategy_name']}",
        "",
        "## Summary",
        "",
        "Generated from repeated runtime-log-backed procedure experiences. Review before turning this into a broader diagnostic policy or formal skill.",
        "",
        "## Goal Symptoms",
        "",
    ]
    for item in candidate.get("goal_symptoms", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Common Log Events", ""])
    for item in candidate.get("common_log_events", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Common Followup Focus", ""])
    for item in candidate.get("common_followup_focus", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Recommended Steps", ""])
    for item in candidate.get("recommended_steps", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Verification Paths", ""])
    for item in candidate.get("verification_paths", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Misleading Signals", ""])
    for item in candidate.get("misleading_signals", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Log Design Feedback", ""])
    for item in candidate.get("log_design_feedback", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Supporting Cases", ""])
    for item in candidate.get("supporting_cases", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Quality Signals", ""])
    lines.append(f"- Readiness: `{candidate.get('promotion_readiness', 'needs_more_evidence')}`")
    lines.append(f"- Quality score: `{candidate.get('quality_score', 0)}`")
    for item in candidate.get("quality_reasons", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Review Notes", "", "- Reviewer: ", "- Review status: pending_review", "- Review notes:", "  - ", ""])
    return "\n".join(lines)


def recurring_incident_fingerprint_draft_path(fingerprint_name: str) -> str:
    return f"docs/incident-fingerprints/{fingerprint_name}.md"


def build_recurring_incident_fingerprint_markdown(candidate: dict[str, Any]) -> str:
    lines = [
        "---",
        f"artifact_type: {json.dumps('recurring_incident_fingerprint', ensure_ascii=False)}",
        f"promotion_status: {json.dumps('draft', ensure_ascii=False)}",
        f"supporting_reflection_ids: {json.dumps(candidate.get('supporting_reflection_ids') or [], ensure_ascii=False)}",
        "---",
        "",
        f"# Recurring Incident Fingerprint: {candidate['fingerprint_name']}",
        "",
        "## Goal Area",
        "",
        f"- `{candidate['goal_area']}`",
        "",
        "## Goal Symptoms",
        "",
    ]
    for item in candidate.get("goal_symptoms", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Common Log Events", ""])
    for item in candidate.get("common_log_events", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Dominant Failure Signals", ""])
    for item in candidate.get("dominant_failure_signals", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Misleading Signals", ""])
    for item in candidate.get("misleading_signals", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Supporting Cases", ""])
    for item in candidate.get("supporting_cases", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Quality Signals", ""])
    lines.append(f"- Readiness: `{candidate.get('promotion_readiness', 'needs_more_evidence')}`")
    lines.append(f"- Quality score: `{candidate.get('quality_score', 0)}`")
    for item in candidate.get("quality_reasons", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)
