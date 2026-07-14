# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_FINGERPRINT_SCHEME = "owner-salted-sha256:v1"
PROJECT_FINGERPRINT = "sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77"

REQUIRED_TABLES = {
    "projects",
    "episodes",
    "semantic_facts",
    "reflections",
    "code_files",
    "code_symbols",
    "code_log_statements",
    "memory_edges",
    "learn_scopes",
    "query_misses",
    "reflection_reuse_events",
    "experience_usage_events",
    "semantic_conflicts",
    "impact_feedback",
    "design_outcomes",
}

VAULT_DIRS = [
    "Episodes",
    "Reflections",
    "Semantic Facts",
    "Codebase Wiki",
    "Governance",
    "Daily",
]

IGNORE_DIRS = {
    ".git",
    "node_modules",
    "build",
    "dist",
    ".dart_tool",
    "__pycache__",
    ".agent-memory",
    ".agent-skills",
}

CODE_EXTENSIONS = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".ets": "ArkTS",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".dart": "Dart",
    ".swift": "Swift",
    ".md": "Markdown",
    ".json5": "HarmonyOS Config",
}

ACTIVE_STATUS = "active"
NON_QUERY_STATUSES = {"stale", "merged", "archived", "rejected"}
VALID_MEMORY_STATUSES = {"active", "stale", "merged", "archived", "rejected"}
NETWORK_MAX_DEPTH = 1
NETWORK_EDGE_LIMIT = 10
EVIDENCE_CHAIN_LIMIT = 3
QUERY_ALLOWED_EDGE_RELATIONS = {"contains", "emits_log", "imports", "routes_to", "uses_resource"}
QUERY_FTS_RECALL_LIMITS = {
    "semantic_facts": 120,
    "reflections": 120,
    "episodes": 80,
    "code_files": 160,
    "code_symbols": 220,
    "code_log_statements": 180,
}
REVIEW_DUPLICATE_POOL_LIMIT = 2000

CODE_BUSINESS_COLUMNS = {
    "code_files": [
        ("business_summary", "TEXT"),
        ("business_terms", "TEXT"),
    ],
    "code_symbols": [
        ("business_summary", "TEXT"),
        ("business_terms", "TEXT"),
    ],
    "code_log_statements": [
        ("business_summary", "TEXT"),
        ("business_terms", "TEXT"),
        ("business_event", "TEXT"),
        ("trigger_stage", "TEXT"),
        ("symptom_terms", "TEXT"),
        ("likely_causes", "TEXT"),
        ("process_hint", "TEXT"),
        ("neighbor_terms", "TEXT"),
    ],
}

CODE_SEMANTIC_COLUMNS = {
    "code_symbols": [
        ("symbol_key", "TEXT"),
        ("qualified_name", "TEXT"),
        ("signature", "TEXT"),
        ("start_line", "INTEGER"),
        ("end_line", "INTEGER"),
        ("semantic_adapter", "TEXT"),
        ("source_digest", "TEXT"),
        ("evidence_class", "TEXT"),
    ],
}

GOVERNANCE_COLUMNS = {
    "semantic_facts": [
        ("status", "TEXT DEFAULT 'active'"),
        ("category", "TEXT"),
        ("scope", "TEXT"),
        ("evidence", "TEXT"),
        ("last_used_at", "TEXT"),
        ("use_count", "INTEGER DEFAULT 0"),
        ("reviewed_at", "TEXT"),
        ("merged_into_id", "INTEGER"),
        ("stale_reason", "TEXT"),
    ],
    "reflections": [
        ("status", "TEXT DEFAULT 'active'"),
        ("experience_type", "TEXT"),
        ("task_type", "TEXT"),
        ("outcome", "TEXT"),
        ("problem", "TEXT"),
        ("reasoning_summary", "TEXT"),
        ("context_used", "TEXT"),
        ("what_worked", "TEXT"),
        ("what_failed", "TEXT"),
        ("hidden_assumptions", "TEXT"),
        ("negative_preconditions", "TEXT"),
        ("query_rounds", "INTEGER"),
        ("trajectory_summary", "TEXT"),
        ("useful_followup_focus", "TEXT"),
        ("useful_followup_terms", "TEXT"),
        ("misleading_followup_terms", "TEXT"),
        ("inspection_targets", "TEXT"),
        ("final_verification_path", "TEXT"),
        ("related_cases", "TEXT"),
        ("verification_method", "TEXT"),
        ("reuse_feedback", "TEXT"),
        ("source_cases", "TEXT"),
        ("skill_candidate", "TEXT"),
        ("scope", "TEXT"),
        ("confidence", "REAL DEFAULT 0.8"),
        ("evidence", "TEXT"),
        ("trigger_condition", "TEXT"),
        ("anti_pattern", "TEXT"),
        ("repair_action", "TEXT"),
        ("applies_to", "TEXT"),
        ("does_not_apply_to", "TEXT"),
        ("anchor_type", "TEXT"),
        ("anchor_key", "TEXT"),
        ("semantic_field", "TEXT"),
        ("existing_value", "TEXT"),
        ("proposed_value", "TEXT"),
        ("patch_reason", "TEXT"),
        ("applies_to_current_code", "INTEGER DEFAULT 0"),
        ("superseded_by", "INTEGER"),
        ("misleading_score", "REAL DEFAULT 0.0"),
        ("last_used_at", "TEXT"),
        ("use_count", "INTEGER DEFAULT 0"),
        ("reviewed_at", "TEXT"),
        ("merged_into_id", "INTEGER"),
        ("stale_reason", "TEXT"),
        ("last_applied_at", "TEXT"),
        ("applied_count", "INTEGER DEFAULT 0"),
        ("last_outcome", "TEXT"),
    ],
    "episodes": [
        ("status", "TEXT DEFAULT 'active'"),
        ("importance", "REAL DEFAULT 0.5"),
        ("last_used_at", "TEXT"),
        ("use_count", "INTEGER DEFAULT 0"),
        ("reviewed_at", "TEXT"),
        ("derived_facts", "TEXT"),
        ("derived_reflections", "TEXT"),
    ],
}


@dataclass(frozen=True)
class Project:
    root: Path
    memory_home: Path
    memory_dir: Path
    db_path: Path
    vault_dir: Path
    runtime_dir: Path
    project_id: str
    project_name: str
