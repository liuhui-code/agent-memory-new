# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .governance_utils import extract_path_like_values, stable_unique_strings

def infer_common_steps(
    followup_focuses: list[str],
    query_terms: list[str],
    verification_methods: list[str],
    inspection_targets: list[str],
) -> list[str]:
    steps: list[str] = []
    focus_set = {focus.lower() for focus in followup_focuses}
    joined_terms = " ".join(query_terms).lower()
    joined_targets = " ".join(inspection_targets).lower()
    joined_verification = " ".join(verification_methods).lower()

    if "route" in focus_set:
        steps.append("query route anchors")
        steps.append("inspect route target and page registration")
        if "router" in joined_terms or "pushurl" in joined_terms or "log" in joined_verification:
            steps.append("check related logs")
        steps.append("verify route mismatch")
    if "resource" in focus_set:
        steps.append("query resource anchors")
        steps.append("inspect resource usage and lookup sites")
        steps.append("verify resource resolution")
    if "log" in focus_set and "check related logs" not in steps:
        steps.append("query log anchors")
        steps.append("inspect matching log statements and nearby code")
    if "config" in focus_set:
        steps.append("query config anchors")
        steps.append("inspect config, permission, and module declarations")
        steps.append("verify config mismatch")

    if not steps:
        steps.append("query strongest anchors first")
    if inspection_targets and not any("inspect" in step for step in steps):
        steps.append("inspect shortlisted targets")
    if joined_verification and not any(step.startswith("verify ") for step in steps):
        steps.append("verify conclusion against source or reproduction path")
    return stable_unique_strings(steps)



def evaluate_skill_pattern_quality(candidate: dict[str, Any], grouped_rows: list[dict[str, Any]]) -> tuple[int, str, list[str]]:
    score = 0
    reasons: list[str] = []
    supporting_count = int(candidate.get("supporting_count") or 0)
    if supporting_count >= 3:
        score += 3
        reasons.append("has_three_or_more_supporting_reflections")
    elif supporting_count >= 2:
        score += 1
        reasons.append("has_minimum_supporting_reflections")
    else:
        reasons.append("insufficient_supporting_reflections")

    if candidate.get("common_steps"):
        score += 2
        reasons.append("has_common_steps")
    else:
        reasons.append("missing_common_steps")
    if candidate.get("common_stop_conditions"):
        score += 1
        reasons.append("has_stop_conditions")
    else:
        reasons.append("missing_stop_conditions")
    if candidate.get("expected_outputs"):
        score += 1
        reasons.append("has_expected_outputs")
    else:
        reasons.append("missing_expected_outputs")
    if candidate.get("failure_modes"):
        score += 1
        reasons.append("has_failure_modes")
    else:
        reasons.append("missing_failure_modes")

    helped = sum(1 for row in grouped_rows if row.get("last_outcome") == "helped")
    partial = sum(1 for row in grouped_rows if row.get("last_outcome") == "partial")
    misleading = sum(1 for row in grouped_rows if row.get("last_outcome") == "misleading")
    if helped >= 1:
        score += 2
        reasons.append("has_helped_reuse_signal")
    elif partial >= 1:
        score += 1
        reasons.append("has_partial_reuse_signal")
    else:
        reasons.append("missing_positive_reuse_signal")
    if misleading >= 1:
        score -= 2
        reasons.append("has_misleading_reuse_signal")

    anchor_health = candidate.get("anchor_health")
    if anchor_health == "fresh":
        score += 1
        reasons.append("supporting_anchors_are_fresh")
    elif anchor_health == "mixed":
        reasons.append("some_supporting_anchors_are_missing")
    elif anchor_health == "missing":
        reasons.append("supporting_anchors_are_missing")
    if score >= 8:
        readiness = "promotion_candidate"
    elif score >= 5:
        readiness = "review_candidate"
    else:
        readiness = "needs_more_evidence"
    return score, readiness, reasons



def supporting_anchor_health(project_root: Path, grouped_rows: list[dict[str, Any]]) -> dict[str, Any]:
    anchors = stable_unique_strings(
        [
            path
            for row in grouped_rows
            for path in extract_path_like_values(
                row.get("source_cases"),
                row.get("inspection_targets"),
                row.get("context_used"),
                row.get("evidence"),
                row.get("final_verification_path"),
            )
        ]
    )
    existing: list[str] = []
    missing: list[str] = []
    for anchor in anchors:
        candidate = project_root / anchor
        if candidate.exists():
            existing.append(anchor)
        else:
            missing.append(anchor)
    if not anchors:
        status = "unknown"
    elif not missing:
        status = "fresh"
    elif existing:
        status = "mixed"
    else:
        status = "missing"
    return {
        "anchor_paths": anchors,
        "existing_anchor_paths": existing,
        "missing_anchor_paths": missing,
        "anchor_health": status,
    }



def skill_candidate_draft_path(pattern_name: str) -> str:
    return f"docs/skill-candidates/{pattern_name}.md"



def skill_candidate_package_path(pattern_name: str) -> str:
    return f"skills/_candidates/{pattern_name}/SKILL.md"



def skill_candidate_promotion_checklist_path(pattern_name: str) -> str:
    return f"skills/_candidates/{pattern_name}/PROMOTION.md"



def read_frontmatter_metadata(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    lines = text.splitlines()
    metadata: dict[str, str] = {}
    for line in lines[1:]:
        if line == "---":
            break
        if ": " not in line:
            continue
        key, value = line.split(": ", 1)
        metadata[key.strip()] = value.strip().strip('"')
    return metadata



def artifact_has_human_review(metadata: dict[str, str]) -> bool:
    if not metadata:
        return False
    review_status = (metadata.get("review_status") or "").strip()
    reviewer = (metadata.get("reviewer") or "").strip()
    review_notes = (metadata.get("review_notes") or "").strip()
    if reviewer:
        return True
    if review_notes not in {"", "[]"}:
        return True
    return bool(review_status and review_status != "pending_review")



def guarded_write_artifact(path: Path, content: str) -> dict[str, Any]:
    existing_meta = read_frontmatter_metadata(path)
    if path.exists() and artifact_has_human_review(existing_meta):
        return {
            "write_action": "preserved_existing_reviewed_artifact",
            "warning": "existing artifact has human review metadata; runtime did not overwrite it",
            "existing_review_status": existing_meta.get("review_status", ""),
            "existing_reviewer": existing_meta.get("reviewer", ""),
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return {
        "write_action": "wrote_artifact",
        "warning": "",
        "existing_review_status": existing_meta.get("review_status", ""),
        "existing_reviewer": existing_meta.get("reviewer", ""),
    }



def build_review_guidance(candidate: dict[str, Any]) -> list[str]:
    guidance = [
        "Confirm reviewer, review status, and notes are updated in the artifact before formal promotion.",
        "Verify common steps, stop conditions, and expected outputs against the supporting reflections.",
    ]
    if candidate.get("promotion_stage") == "clustered":
        guidance.insert(0, "Write the draft artifact first, then begin human review.")
    elif candidate.get("promotion_stage") == "draft":
        guidance.insert(0, "Review the draft and record reviewer metadata before packaging it.")
    elif candidate.get("promotion_stage") == "candidate_package":
        guidance.insert(0, "Review the candidate package metadata and notes before considering manual promotion into skills/.")
    return guidance



def annotate_skill_pattern_artifacts(project_root: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    draft_path = candidate["draft_path"]
    package_path = skill_candidate_package_path(candidate["pattern_name"])
    promotion_checklist_path = skill_candidate_promotion_checklist_path(candidate["pattern_name"])
    draft_file = project_root / draft_path
    package_file = project_root / package_path
    promotion_checklist_file = project_root / promotion_checklist_path
    draft_exists = draft_file.exists()
    package_exists = package_file.exists()
    promotion_checklist_exists = promotion_checklist_file.exists()
    draft_meta = read_frontmatter_metadata(draft_file)
    package_meta = read_frontmatter_metadata(package_file)
    if package_exists:
        promotion_stage = "candidate_package"
    elif draft_exists:
        promotion_stage = "draft"
    else:
        promotion_stage = "clustered"
    return {
        **candidate,
        "draft_status": "written" if draft_exists else "not_written",
        "draft_review_status": draft_meta.get("review_status") or ("pending_review" if draft_exists else ""),
        "draft_reviewer": draft_meta.get("reviewer", ""),
        "package_path": package_path,
        "package_status": "written" if package_exists else "not_written",
        "package_review_status": package_meta.get("review_status") or ("pending_review" if package_exists else ""),
        "package_reviewer": package_meta.get("reviewer", ""),
        "promotion_checklist_path": promotion_checklist_path,
        "promotion_checklist_status": "written" if promotion_checklist_exists else "not_written",
        "promotion_stage": promotion_stage,
        "review_guidance": build_review_guidance(
            {
                **candidate,
                "promotion_stage": promotion_stage,
            }
        ),
    }



def format_frontmatter_sequence(values: list[Any]) -> str:
    if not values:
        return "[]"
    items = ", ".join(json.dumps(value, ensure_ascii=False) for value in values)
    return f"[{items}]"



def build_skill_candidate_frontmatter(
    candidate: dict[str, Any],
    artifact_type: str,
    promotion_status: str,
    source_draft: str | None = None,
) -> list[str]:
    lines = [
        "---",
        f"pattern_name: {json.dumps(candidate['pattern_name'], ensure_ascii=False)}",
        f"artifact_type: {json.dumps(artifact_type, ensure_ascii=False)}",
        f"promotion_status: {json.dumps(promotion_status, ensure_ascii=False)}",
        'review_status: "pending_review"',
        'reviewer: ""',
        "review_notes: []",
        f"experience_type: {json.dumps(candidate.get('experience_type') or 'procedure_experience', ensure_ascii=False)}",
        f"supporting_count: {int(candidate.get('supporting_count') or 0)}",
        f"supporting_reflection_ids: {format_frontmatter_sequence(candidate.get('supporting_reflection_ids', []))}",
        f"common_followup_focus: {format_frontmatter_sequence(candidate.get('common_followup_focus', []))}",
        f"supporting_cases: {format_frontmatter_sequence(candidate.get('supporting_cases', []))}",
        f"verification_methods: {format_frontmatter_sequence(candidate.get('verification_methods', []))}",
        f"source_runtime_command: {json.dumps('tools/agent_memory.py', ensure_ascii=False)}",
    ]
    if source_draft:
        lines.append(f"source_draft: {json.dumps(source_draft, ensure_ascii=False)}")
    lines.extend(["---", ""])
    return lines



def build_skill_candidate_markdown(candidate: dict[str, Any]) -> str:
    lines = build_skill_candidate_frontmatter(
        candidate,
        artifact_type="skill_candidate_draft",
        promotion_status="draft",
    ) + [
        f"# Skill Candidate: {candidate['pattern_name']}",
        "",
        "## Summary",
        "",
        "Generated from repeated `procedure_experience` reflections. Review before turning this into a real skill.",
        "",
        "## Trigger Cluster",
        "",
    ]
    for item in candidate.get("trigger_cluster", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Common Followup Focus", ""])
    for item in candidate.get("common_followup_focus", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Common Query Terms", ""])
    for item in candidate.get("common_query_terms", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Common Steps", ""])
    for item in candidate.get("common_steps", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Common Stop Conditions", ""])
    for item in candidate.get("common_stop_conditions", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Expected Outputs", ""])
    for item in candidate.get("expected_outputs", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Failure Modes", ""])
    for item in candidate.get("failure_modes", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Supporting Cases", ""])
    for item in candidate.get("supporting_cases", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Verification Methods", ""])
    for item in candidate.get("verification_methods", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Quality Signals", ""])
    lines.append(f"- Readiness: `{candidate.get('promotion_readiness', 'needs_more_evidence')}`")
    lines.append(f"- Quality score: `{candidate.get('quality_score', 0)}`")
    lines.append(f"- Helped reuse count: `{candidate.get('helped_reuse_count', 0)}`")
    lines.append(f"- Partial reuse count: `{candidate.get('partial_reuse_count', 0)}`")
    lines.append(f"- Misleading reuse count: `{candidate.get('misleading_reuse_count', 0)}`")
    lines.append(f"- Anchor health: `{candidate.get('anchor_health', 'unknown')}`")
    missing_anchors = candidate.get("missing_anchor_paths") or []
    if missing_anchors:
        lines.append("- Missing anchors:")
        for item in missing_anchors:
            lines.append(f"  - {item}")
    for item in candidate.get("quality_reasons", []):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Supporting Reflections",
            "",
            ", ".join(f"#{reflection_id}" for reflection_id in candidate.get("supporting_reflection_ids", [])),
            "",
            "## Review Notes",
            "",
            "- Reviewer: ",
            "- Review status: pending_review",
            "- Review notes:",
            "  - ",
            "- Confirm the trigger is stable across cases.",
            "- Remove noisy terms before turning this into a skill.",
            "- Add stop conditions and expected outputs before promotion.",
            "",
        ]
    )
    return "\n".join(lines)



def build_skill_candidate_package_markdown(candidate: dict[str, Any]) -> str:
    lines = build_skill_candidate_frontmatter(
        candidate,
        artifact_type="skill_candidate_package",
        promotion_status="candidate",
        source_draft=candidate["draft_path"],
    ) + [
        f"# Skill Candidate Package: {candidate['pattern_name']}",
        "",
        "Candidate package generated from repeated procedure_experience reflections.",
        "This is still a reviewed candidate artifact, not a formal installed skill.",
        "",
        f"Source draft: `{candidate['draft_path']}`",
        "",
        candidate["draft_markdown"].rstrip(),
        "",
    ]
    return "\n".join(lines)



def build_skill_promotion_checklist_markdown(candidate: dict[str, Any]) -> str:
    lines = [
        f"# Promotion Checklist: {candidate['pattern_name']}",
        "",
        "Use this checklist before manually promoting the candidate package into `skills/<name>/SKILL.md`.",
        "",
        "## Artifact Paths",
        "",
        f"- Draft: `{candidate['draft_path']}`",
        f"- Candidate package: `{skill_candidate_package_path(candidate['pattern_name'])}`",
        f"- Formal target: `skills/{candidate['pattern_name']}/SKILL.md`",
        "",
        "## Required Metadata",
        "",
        "- [ ] Candidate package `review_status` is no longer `pending_review`.",
        "- [ ] Candidate package `reviewer` is filled.",
        "- [ ] Candidate package `review_notes` explain remaining edits or approval basis.",
        "",
        "## Pattern Quality Checks",
        "",
        f"- [ ] Promotion readiness is acceptable (`{candidate.get('promotion_readiness', 'needs_more_evidence')}`).",
        f"- [ ] Quality score is acceptable for manual promotion review (`{candidate.get('quality_score', 0)}`).",
        f"- [ ] Anchor health is acceptable (`{candidate.get('anchor_health', 'unknown')}`).",
        f"- [ ] Supporting reflections are still sufficient (`{candidate['supporting_count']}` currently).",
        "- [ ] Trigger conditions are stable and explicit.",
        "- [ ] Common steps are executable in order.",
        "- [ ] Stop conditions are concrete.",
        "- [ ] Expected outputs are stable enough for reuse.",
        "- [ ] Failure modes are explicit enough to avoid misuse.",
        "",
        "## Promotion Steps",
        "",
        "- [ ] Review `docs/skill-promotion-rules.md`.",
        "- [ ] Copy or adapt the candidate package into `skills/<name>/SKILL.md` manually.",
        "- [ ] Keep user-facing behavior inside the existing four-skill interface.",
        "- [ ] Run the relevant runtime and workflow tests after promotion.",
        "- [ ] Update docs or examples if the new formal skill changes the recommended workflow.",
        "",
        "## Source Context",
        "",
        f"- Supporting reflections: {', '.join(f'#{reflection_id}' for reflection_id in candidate.get('supporting_reflection_ids', []))}",
    ]
    if candidate.get("common_followup_focus"):
        lines.append(f"- Common followup focus: {', '.join(candidate['common_followup_focus'])}")
    if candidate.get("supporting_cases"):
        lines.append(f"- Supporting cases: {', '.join(candidate['supporting_cases'])}")
    lines.append("")
    return "\n".join(lines)
