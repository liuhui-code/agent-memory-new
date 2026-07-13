# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3

from .governance import (
    annotate_skill_pattern_artifacts,
    build_incident_strategy_candidates,
    build_recurring_incident_fingerprint_candidates,
    build_recent_refresh_drifts,
    build_scope_health_rows,
    build_skill_pattern_candidates,
    duplicate_candidates,
    is_complete_experience_candidate,
    reflection_quality_issues,
)
from .models import ACTIVE_STATUS, Project
from .query import normalize_query_miss
from .records import row_dict
from .storage import now_iso
from .text import json_list
from .vault_common import frontmatter, write_vault_file

def write_governance_dashboard(
    project: Project,
    facts: list[sqlite3.Row],
    reflections: list[sqlite3.Row],
    episodes: list[sqlite3.Row],
    query_misses: list[sqlite3.Row],
    reflection_reuse_events: list[sqlite3.Row],
    semantic_conflicts: list[sqlite3.Row],
) -> None:
    fact_rows = [row_dict(row) for row in facts]
    reflection_rows = [row_dict(row) for row in reflections]
    episode_rows = [row_dict(row) for row in episodes]
    query_miss_rows = [row_dict(row) for row in query_misses]
    reflection_reuse_rows = [row_dict(row) for row in reflection_reuse_events]
    semantic_conflict_rows = [row_dict(row) for row in semantic_conflicts]
    open_semantic_conflicts = [row for row in semantic_conflict_rows if row.get("status") == "open"]
    open_file_conflicts = [row for row in open_semantic_conflicts if row.get("entity_type") == "code_file"]
    open_symbol_conflicts = [row for row in open_semantic_conflicts if row.get("entity_type") == "code_symbol"]
    open_log_conflicts = [row for row in open_semantic_conflicts if row.get("entity_type") == "code_log_statement"]
    scope_health_rows = build_scope_health_rows(project)
    refresh_drifts = build_recent_refresh_drifts(project, 50)
    active_facts = [row for row in fact_rows if (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS and not row.get("is_stale")]
    active_reflections = [row for row in reflection_rows if (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS and not row.get("is_stale")]
    stale = [
        row for row in fact_rows + reflection_rows
        if row.get("is_stale") or row.get("status") == "stale"
    ]
    low_confidence = [
        row for row in fact_rows + reflection_rows
        if float(row.get("confidence") or 0.8) < 0.6
    ]
    duplicates = duplicate_candidates(active_facts, "semantic") + duplicate_candidates(active_reflections, "reflection")
    unreviewed_reflections = [
        row for row in reflection_rows
        if not row.get("reviewed_at") and (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS
    ]

    header = frontmatter("governance", project, now_iso())
    notice = "This file is generated. Edit memory through agent-memory-maintain or agent-memory-reflect.\n\n"

    health = header + "# Memory Health\n\n" + notice
    health += f"- Semantic facts: {len(fact_rows)}\n"
    health += f"- Reflections: {len(reflection_rows)}\n"
    health += f"- Episodes: {len(episode_rows)}\n"
    health += f"- Stale memories: {len(stale)}\n"
    health += f"- Low-confidence memories: {len(low_confidence)}\n"
    health += f"- Duplicate candidates: {len(duplicates)}\n"
    health += f"- Unreviewed reflections: {len(unreviewed_reflections)}\n"
    health += f"- Open query misses: {sum(1 for row in query_miss_rows if row.get('status') == 'open')}\n"
    health += f"- Open semantic conflicts: {len(open_semantic_conflicts)}\n"
    health += f"- Open file semantic conflicts: {len(open_file_conflicts)}\n"
    health += f"- Open symbol semantic conflicts: {len(open_symbol_conflicts)}\n"
    health += f"- Open log semantic conflicts: {len(open_log_conflicts)}\n"
    health += f"- Learn scopes: {len(scope_health_rows)}\n"
    health += f"- Scope drift queues: {sum(1 for row in scope_health_rows if row.get('health_status') in {'drift', 'high_drift'})}\n"
    health += f"- Missing-source scopes: {sum(1 for row in scope_health_rows if row.get('health_status') == 'missing_source')}\n"
    write_vault_file(project.vault_dir / "Governance" / "Health.md", health)

    review = header + "# Review Queue\n\n" + notice
    review += "## Unreviewed Reflections\n\n"
    for row in unreviewed_reflections[:30]:
        review += f"- reflection #{row['id']}: {row['task']}\n"
    review += "\n## Unreviewed Episodes\n\n"
    for row in episode_rows[:30]:
        if not row.get("reviewed_at") and (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS:
            review += f"- episode #{row['id']}: {row['task']}\n"
    review += "\n## Open Semantic Conflicts\n\n"
    for row in semantic_conflict_rows[:30]:
        if row.get("status") == "open":
            review += f"- conflict #{row['id']}: {row['target']}\n"
    review += "\n## Refresh Drift\n\n"
    for row in refresh_drifts[:30]:
        review += f"- scope #{row['scope_id']} ({row['scope_type']}): +{len(row['added_files'])} ~{len(row['changed_files'])} -{len(row['removed_files'])}\n"
    write_vault_file(project.vault_dir / "Governance" / "Review Queue.md", review)

    stale_doc = header + "# Stale Memories\n\n" + notice
    for row in stale[:50]:
        text = row.get("fact") or row.get("lesson") or row.get("task")
        stale_doc += f"- #{row['id']} ({row.get('status') or 'stale'}): {text}\n"
    write_vault_file(project.vault_dir / "Governance" / "Stale Memories.md", stale_doc)

    merge_doc = header + "# Merge Candidates\n\n" + notice
    for item in duplicates[:50]:
        merge_doc += f"- {item['type']} ids {item['ids']} similarity {item['similarity']}: {item['reason']}\n"
    write_vault_file(project.vault_dir / "Governance" / "Merge Candidates.md", merge_doc)

    low_doc = header + "# Low Confidence\n\n" + notice
    for row in low_confidence[:50]:
        text = row.get("fact") or row.get("lesson") or row.get("task")
        low_doc += f"- #{row['id']} confidence {row.get('confidence')}: {text}\n"
    write_vault_file(project.vault_dir / "Governance" / "Low Confidence.md", low_doc)

    reflection_quality = [
        {
            "id": row["id"],
            "task": row["task"],
            "issues": reflection_quality_issues(row),
        }
        for row in active_reflections
    ]
    reflection_quality = [item for item in reflection_quality if item["issues"]]
    quality_doc = header + "# Reflection Quality\n\n" + notice
    quality_doc += "## Reflection Quality Issues\n\n"
    for item in reflection_quality[:50]:
        quality_doc += f"- reflection #{item['id']} {item['task']}: {', '.join(item['issues'])}\n"
    write_vault_file(project.vault_dir / "Governance" / "Reflection Quality.md", quality_doc)

    experience_candidates = [
        row for row in active_reflections
        if is_complete_experience_candidate(row)
    ]
    candidates_doc = header + "# Experience Candidates\n\n" + notice
    candidates_doc += "These reflections have enough structure to review as reusable experience. They are not accepted experience until reviewed.\n\n"
    for row in experience_candidates[:50]:
        candidates_doc += f"## Reflection #{row['id']}: {row['task']}\n\n"
        if row.get("skill_candidate"):
            candidates_doc += f"- Skill candidate: `{row['skill_candidate']}`\n"
        if row.get("problem"):
            candidates_doc += f"- Problem: {row['problem']}\n"
        if row.get("trigger_condition"):
            candidates_doc += f"- Trigger: {row['trigger_condition']}\n"
        if row.get("verification_method"):
            candidates_doc += f"- Verification: {row['verification_method']}\n"
        if row.get("reuse_feedback"):
            candidates_doc += f"- Reuse feedback: {row['reuse_feedback']}\n"
        source_cases = json_list(row.get("source_cases"))
        if source_cases:
            candidates_doc += "- Source cases:\n"
            for item in source_cases:
                candidates_doc += f"  - {item}\n"
        hidden_assumptions = json_list(row.get("hidden_assumptions"))
        if hidden_assumptions:
            candidates_doc += "- Hidden assumptions:\n"
            for item in hidden_assumptions:
                candidates_doc += f"  - {item}\n"
        negative_preconditions = json_list(row.get("negative_preconditions"))
        if negative_preconditions:
            candidates_doc += "- Negative preconditions:\n"
            for item in negative_preconditions:
                candidates_doc += f"  - {item}\n"
        candidates_doc += "\n"
    write_vault_file(project.vault_dir / "Governance" / "Experience Candidates.md", candidates_doc)

    skill_pattern_candidates = [
        annotate_skill_pattern_artifacts(project.root, item)
        for item in build_skill_pattern_candidates(project, active_reflections)
    ]
    pattern_doc = header + "# Skill Pattern Candidates\n\n" + notice
    pattern_doc += "These grouped procedure experiences point to the same candidate workflow. Review them before drafting a formal skill.\n\n"
    pattern_doc += "Reviewed draft or candidate-package artifacts are preserved by the runtime when human review metadata is present.\n\n"
    for item in skill_pattern_candidates[:30]:
        pattern_doc += f"## {item['pattern_name']}\n\n"
        pattern_doc += f"- Promotion stage: `{item['promotion_stage']}`\n"
        pattern_doc += f"- Draft status: `{item['draft_status']}`\n"
        if item.get("draft_review_status"):
            pattern_doc += f"- Draft review status: `{item['draft_review_status']}`\n"
        if item.get("draft_reviewer"):
            pattern_doc += f"- Draft reviewer: `{item['draft_reviewer']}`\n"
        pattern_doc += f"- Draft path: `{item['draft_path']}`\n"
        pattern_doc += f"- Package status: `{item['package_status']}`\n"
        if item.get("package_review_status"):
            pattern_doc += f"- Package review status: `{item['package_review_status']}`\n"
        if item.get("package_reviewer"):
            pattern_doc += f"- Package reviewer: `{item['package_reviewer']}`\n"
        pattern_doc += f"- Package path: `{item['package_path']}`\n"
        pattern_doc += f"- Promotion checklist status: `{item['promotion_checklist_status']}`\n"
        pattern_doc += f"- Promotion checklist path: `{item['promotion_checklist_path']}`\n"
        pattern_doc += f"- Promotion readiness: `{item['promotion_readiness']}`\n"
        pattern_doc += f"- Quality score: `{item['quality_score']}`\n"
        pattern_doc += f"- Helped reuse count: `{item['helped_reuse_count']}`\n"
        pattern_doc += f"- Partial reuse count: `{item['partial_reuse_count']}`\n"
        pattern_doc += f"- Misleading reuse count: `{item['misleading_reuse_count']}`\n"
        pattern_doc += f"- Anchor health: `{item['anchor_health']}`\n"
        pattern_doc += f"- Supporting reflections: {', '.join(f'#{reflection_id}' for reflection_id in item['supporting_reflection_ids'])}\n"
        pattern_doc += f"- Supporting count: {item['supporting_count']}\n"
        if item.get("missing_anchor_paths"):
            pattern_doc += "- Missing anchors:\n"
            for anchor in item["missing_anchor_paths"]:
                pattern_doc += f"  - {anchor}\n"
        if item.get("common_followup_focus"):
            pattern_doc += f"- Common followup focus: {', '.join(item['common_followup_focus'])}\n"
        if item.get("common_query_terms"):
            pattern_doc += "- Common query terms:\n"
            for term in item["common_query_terms"]:
                pattern_doc += f"  - {term}\n"
        if item.get("common_steps"):
            pattern_doc += "- Common steps:\n"
            for step in item["common_steps"]:
                pattern_doc += f"  - {step}\n"
        if item.get("common_stop_conditions"):
            pattern_doc += "- Common stop conditions:\n"
            for condition in item["common_stop_conditions"]:
                pattern_doc += f"  - {condition}\n"
        if item.get("expected_outputs"):
            pattern_doc += "- Expected outputs:\n"
            for output in item["expected_outputs"]:
                pattern_doc += f"  - {output}\n"
        if item.get("failure_modes"):
            pattern_doc += "- Failure modes:\n"
            for mode in item["failure_modes"]:
                pattern_doc += f"  - {mode}\n"
        if item.get("supporting_cases"):
            pattern_doc += "- Supporting cases:\n"
            for case in item["supporting_cases"]:
                pattern_doc += f"  - {case}\n"
        if item.get("verification_methods"):
            pattern_doc += "- Verification methods:\n"
            for method in item["verification_methods"]:
                pattern_doc += f"  - {method}\n"
        if item.get("review_guidance"):
            pattern_doc += "- Review guidance:\n"
            for step in item["review_guidance"]:
                pattern_doc += f"  - {step}\n"
        if item.get("quality_reasons"):
            pattern_doc += "- Quality reasons:\n"
            for step in item["quality_reasons"]:
                pattern_doc += f"  - {step}\n"
        pattern_doc += "\n### Draft Preview\n\n"
        pattern_doc += "```md\n"
        pattern_doc += item["draft_markdown"].rstrip() + "\n"
        pattern_doc += "```\n\n"
    write_vault_file(project.vault_dir / "Governance" / "Skill Pattern Candidates.md", pattern_doc)

    incident_strategy_candidates = build_incident_strategy_candidates(project, active_reflections)
    incident_doc = header + "# Incident Strategy Candidates\n\n" + notice
    incident_doc += "These grouped runtime-log-backed procedure experiences describe reusable incident diagnosis strategies. Review them before turning them into a broader policy or a formal skill.\n\n"
    for item in incident_strategy_candidates[:30]:
        incident_doc += f"## {item['strategy_name']}\n\n"
        incident_doc += f"- Draft path: `{item['draft_path']}`\n"
        incident_doc += f"- Promotion readiness: `{item['promotion_readiness']}`\n"
        incident_doc += f"- Quality score: `{item['quality_score']}`\n"
        incident_doc += f"- Supporting reflections: {', '.join(f'#{reflection_id}' for reflection_id in item['supporting_reflection_ids'])}\n"
        incident_doc += f"- Supporting count: {item['supporting_count']}\n"
        if item.get("common_followup_focus"):
            incident_doc += f"- Common followup focus: {', '.join(item['common_followup_focus'])}\n"
        if item.get("goal_symptoms"):
            incident_doc += "- Goal symptoms:\n"
            for symptom in item["goal_symptoms"]:
                incident_doc += f"  - {symptom}\n"
        if item.get("common_log_events"):
            incident_doc += "- Common log events:\n"
            for event in item["common_log_events"]:
                incident_doc += f"  - {event}\n"
        if item.get("recommended_steps"):
            incident_doc += "- Recommended steps:\n"
            for step in item["recommended_steps"]:
                incident_doc += f"  - {step}\n"
        if item.get("verification_paths"):
            incident_doc += "- Verification paths:\n"
            for path in item["verification_paths"]:
                incident_doc += f"  - {path}\n"
        if item.get("misleading_signals"):
            incident_doc += "- Misleading signals:\n"
            for signal in item["misleading_signals"]:
                incident_doc += f"  - {signal}\n"
        if item.get("log_design_feedback"):
            incident_doc += "- Log design feedback:\n"
            for feedback in item["log_design_feedback"]:
                incident_doc += f"  - {feedback}\n"
        incident_doc += f"- Draft command: `python tools/agent_memory.py maintain-incident-strategy-draft --project . --strategy-name {item['strategy_name']} --json`\n"
        incident_doc += "\n### Draft Preview\n\n```md\n"
        incident_doc += item["draft_markdown"].rstrip() + "\n"
        incident_doc += "```\n\n"
    write_vault_file(project.vault_dir / "Governance" / "Incident Strategy Candidates.md", incident_doc)

    recurring_fingerprints = build_recurring_incident_fingerprint_candidates(project, active_reflections)
    fingerprint_doc = header + "# Recurring Incident Fingerprints\n\n" + notice
    fingerprint_doc += "These grouped runtime-log-backed reflections describe repeated incident fingerprints without preserving raw runtime history.\n\n"
    for item in recurring_fingerprints[:30]:
        fingerprint_doc += f"## {item['fingerprint_name']}\n\n"
        fingerprint_doc += f"- Draft path: `{item['draft_path']}`\n"
        fingerprint_doc += f"- Promotion readiness: `{item['promotion_readiness']}`\n"
        fingerprint_doc += f"- Quality score: `{item['quality_score']}`\n"
        fingerprint_doc += f"- Supporting reflections: {', '.join(f'#{reflection_id}' for reflection_id in item['supporting_reflection_ids'])}\n"
        fingerprint_doc += f"- Supporting count: {item['supporting_count']}\n"
        if item.get("goal_symptoms"):
            fingerprint_doc += "- Goal symptoms:\n"
            for symptom in item["goal_symptoms"]:
                fingerprint_doc += f"  - {symptom}\n"
        if item.get("common_log_events"):
            fingerprint_doc += "- Common log events:\n"
            for event in item["common_log_events"]:
                fingerprint_doc += f"  - {event}\n"
        if item.get("dominant_failure_signals"):
            fingerprint_doc += "- Dominant failure signals:\n"
            for signal in item["dominant_failure_signals"]:
                fingerprint_doc += f"  - {signal}\n"
        if item.get("misleading_signals"):
            fingerprint_doc += "- Misleading signals:\n"
            for signal in item["misleading_signals"]:
                fingerprint_doc += f"  - {signal}\n"
        fingerprint_doc += f"- Draft command: `python tools/agent_memory.py maintain-incident-fingerprint-draft --project . --fingerprint-name {item['fingerprint_name']} --json`\n"
        fingerprint_doc += "\n### Draft Preview\n\n```md\n"
        fingerprint_doc += item["draft_markdown"].rstrip() + "\n"
        fingerprint_doc += "```\n\n"
    write_vault_file(project.vault_dir / "Governance" / "Recurring Incident Fingerprints.md", fingerprint_doc)

    reuse_doc = header + "# Reflection Reuse\n\n" + notice
    reuse_doc += "These events show when a later reflection reused an earlier reflection and whether it helped.\n\n"
    for row in reflection_reuse_rows[:50]:
        reuse_doc += (
            f"- reuse event #{row['id']}: reused reflection #{row['reused_reflection_id']} "
            f"-> applying reflection #{row['applying_reflection_id']} "
            f"({row['outcome']})"
        )
        if row.get("task"):
            reuse_doc += f": {row['task']}"
        reuse_doc += "\n"
    write_vault_file(project.vault_dir / "Governance" / "Reflection Reuse.md", reuse_doc)

    conflicts_doc = header + "# Semantic Conflicts\n\n" + notice
    conflicts_doc += "These conflicts capture incompatible incoming business summaries that require source-grounded review before replacement.\n\n"
    for row in semantic_conflict_rows[:50]:
        conflicts_doc += f"## Conflict #{row['id']}: {row['target']}\n\n"
        conflicts_doc += f"- Field: {row['field']}\n"
        conflicts_doc += f"- Entity type: {row.get('entity_type') or 'code_file'}\n"
        conflicts_doc += f"- Status: {row.get('status') or 'open'}\n"
        conflicts_doc += f"- Source command: {row['source_command']}\n"
        conflicts_doc += f"- Observed at: {row['observed_at']}\n"
        if row.get("resolution"):
            conflicts_doc += f"- Resolution: {row['resolution']}\n"
        if row.get("decision_note"):
            conflicts_doc += f"- Decision note: {row['decision_note']}\n"
        if row.get("replacement_source"):
            conflicts_doc += f"- Replacement source: {row['replacement_source']}\n"
        conflicts_doc += f"\n### Existing\n\n{row.get('existing') or ''}\n\n"
        conflicts_doc += f"### Incoming\n\n{row.get('incoming') or ''}\n\n"
    write_vault_file(project.vault_dir / "Governance" / "Semantic Conflicts.md", conflicts_doc)

    misses_doc = header + "# Query Misses\n\n" + notice
    for row in query_miss_rows[:50]:
        miss_count = row.get("miss_count") or 1
        last_seen_at = row.get("last_seen_at") or row.get("created_at")
        misses_doc += f"- query miss #{row['id']} ({row['status']}, {row['source']}, misses {miss_count}, last seen {last_seen_at}): {row['query']}\n"
        if row.get("resolution"):
            misses_doc += f"  - resolution: {row['resolution']}\n"
    write_vault_file(project.vault_dir / "Governance" / "Query Misses.md", misses_doc)

    scopes_doc = header + "# Learned Scopes\n\n" + notice
    scopes_doc += "These are the persisted learn manifests used by `maintain-refresh-scope`.\n\n"
    for row in scope_health_rows[:50]:
        scopes_doc += f"## Scope #{row['id']} ({row['scope_type']})\n\n"
        scopes_doc += f"- Health: `{row['health_status']}`\n"
        scopes_doc += f"- Source root: `{row['source_root']}`\n"
        if row.get("target_path"):
            scopes_doc += f"- Target path: `{row['target_path']}`\n"
        if row.get("entry_path"):
            scopes_doc += f"- Entry path: `{row['entry_path']}`\n"
        if row.get("depth") is not None:
            scopes_doc += f"- Depth: `{row['depth']}`\n"
        scopes_doc += f"- Mode: `{row['mode']}`\n"
        scopes_doc += f"- File count: `{row['file_count']}`\n"
        scopes_doc += f"- Last refreshed at: `{row.get('last_refreshed_at') or ''}`\n"
        scopes_doc += f"- Drift count: `{row['drift_count']}`\n\n"
    write_vault_file(project.vault_dir / "Governance" / "Learned Scopes.md", scopes_doc)

    drift_doc = header + "# Refresh Drift\n\n" + notice
    drift_doc += "These rows summarize recent learned-scope refreshes that changed current source structure.\n\n"
    for row in refresh_drifts[:50]:
        drift_doc += f"## Scope #{row['scope_id']} ({row['scope_type']})\n\n"
        drift_doc += f"- Source root: `{row['source_root']}`\n"
        drift_doc += f"- Last refreshed at: `{row.get('last_refreshed_at') or ''}`\n"
        if row.get("target_path"):
            drift_doc += f"- Target path: `{row['target_path']}`\n"
        if row.get("entry_path"):
            drift_doc += f"- Entry path: `{row['entry_path']}`\n"
        drift_doc += f"- Added files: {len(row['added_files'])}\n"
        drift_doc += f"- Changed files: {len(row['changed_files'])}\n"
        drift_doc += f"- Removed files: {len(row['removed_files'])}\n"
        drift_doc += f"- Unchanged files: {row.get('unchanged_count', 0)}\n"
        if row["added_files"]:
            drift_doc += "- Added:\n"
            for item in row["added_files"]:
                drift_doc += f"  - {item}\n"
        if row["changed_files"]:
            drift_doc += "- Changed:\n"
            for item in row["changed_files"]:
                drift_doc += f"  - {item}\n"
        if row["removed_files"]:
            drift_doc += "- Removed:\n"
            for item in row["removed_files"]:
                drift_doc += f"  - {item}\n"
        targets = row.get("semantic_review_targets") or {}
        if targets.get("file_paths"):
            drift_doc += "- Semantic review targets:\n"
            for item in targets["file_paths"]:
                drift_doc += f"  - {item}\n"
        drift_doc += "\n"
    write_vault_file(project.vault_dir / "Governance" / "Refresh Drift.md", drift_doc)

    wiki_misses_doc = frontmatter("codebase-wiki", project, now_iso())
    wiki_misses_doc += "# Query Misses\n\n" + notice
    wiki_misses_doc += "These misses show where natural-language questions failed to retrieve learned code or memory context.\n\n"
    for row in query_miss_rows[:50]:
        miss_count = row.get("miss_count") or 1
        normalized = row.get("normalized_query") or normalize_query_miss(row["query"])
        last_seen_at = row.get("last_seen_at") or row.get("created_at")
        wiki_misses_doc += (
            f"- query miss #{row['id']} ({row['status']}, {row['source']}, "
            f"misses {miss_count}, last seen {last_seen_at}): {row['query']}\n"
        )
        wiki_misses_doc += f"  - normalized: `{normalized}`\n"
        if row.get("resolution"):
            wiki_misses_doc += f"  - resolution: {row['resolution']}\n"
    write_vault_file(project.vault_dir / "Codebase Wiki" / "query-misses.md", wiki_misses_doc)
