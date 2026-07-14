# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sys

from .calibration_eval import eval_calibration_command
from .cli import build_parser
from .code_wiki import learn_business, learn_entry, learn_path, maintain_refresh_scope, wiki_index, wiki_search
from .command_handlers import (
    analyze_runtime_log_command,
    conflict_apply,
    conflict_status,
    context,
    doctor,
    init_project,
    list_records,
    miss_list,
    miss_status,
    search,
    update,
)
from .eval_case_drafts import eval_draft_cases_command
from .eval_case_seed import eval_seed_cases_command
from .evidence_context import evidence_context_command
from .design_check import design_check_command
from .design_compare import design_compare_command
from .design_eval import eval_design_command
from .design_verify import design_verify_command
from .derived_rebuild import maintain_rebuild_derived
from .evidence_attribution import eval_evidence_attribution_command
from .experience_evidence_eval import eval_experience_evidence_command
from .experience_usage import experience_usage_command
from .governance import (
    maintain_health,
    maintain_incident_fingerprint_draft,
    maintain_incident_strategy_draft,
    maintain_merge,
    maintain_plan,
    maintain_promote,
    maintain_review,
    maintain_skill_draft,
    maintain_skill_package,
    maintain_skill_promotion_status,
    maintain_status,
    mark_stale,
    reflect_review,
)
from .governance_eval import eval_governance_command
from .graph_signal_eval import eval_graph_signal_command
from .impact_scope import impact_scope_command
from .impact_feedback import impact_feedback_command
from .incident_trace import incident_trace_command, incident_trace_status
from .log_signal_eval import eval_log_signal_command
from .quality_gate_eval import eval_quality_command
from .reflection_commands import reflect
from .retrieval_eval import eval_retrieval_command
from .retrieval_feedback import retrieval_feedback_command
from .semantic_eval import eval_semantic_command
from .vault import vault_export, vault_index, vault_init


def command_handlers() -> dict[str, object]:
    return {
        "init_project": init_project,
        "doctor": doctor,
        "update": update,
        "search": search,
        "context": context,
        "evidence_context_command": evidence_context_command,
        "design_check_command": design_check_command,
        "design_compare_command": design_compare_command,
        "eval_design_command": eval_design_command,
        "eval_semantic_command": eval_semantic_command,
        "design_verify_command": design_verify_command,
        "impact_scope_command": impact_scope_command,
        "impact_feedback_command": impact_feedback_command,
        "eval_retrieval_command": eval_retrieval_command,
        "eval_calibration_command": eval_calibration_command,
        "eval_experience_evidence_command": eval_experience_evidence_command,
        "eval_log_signal_command": eval_log_signal_command,
        "eval_graph_signal_command": eval_graph_signal_command,
        "eval_evidence_attribution_command": eval_evidence_attribution_command,
        "eval_governance_command": eval_governance_command,
        "eval_quality_command": eval_quality_command,
        "eval_draft_cases_command": eval_draft_cases_command,
        "eval_seed_cases_command": eval_seed_cases_command,
        "retrieval_feedback_command": retrieval_feedback_command,
        "experience_usage_command": experience_usage_command,
        "analyze_runtime_log_command": analyze_runtime_log_command,
        "reflect": reflect,
        "reflect_review": reflect_review,
        "list_records": list_records,
        "miss_list": miss_list,
        "miss_status": miss_status,
        "incident_trace_command": incident_trace_command,
        "incident_trace_status": incident_trace_status,
        "conflict_status": conflict_status,
        "conflict_apply": conflict_apply,
        "mark_stale": mark_stale,
        "maintain_health": maintain_health,
        "maintain_review": maintain_review,
        "maintain_plan": maintain_plan,
        "maintain_status": maintain_status,
        "maintain_merge": maintain_merge,
        "maintain_promote": maintain_promote,
        "maintain_skill_draft": maintain_skill_draft,
        "maintain_incident_strategy_draft": maintain_incident_strategy_draft,
        "maintain_incident_fingerprint_draft": maintain_incident_fingerprint_draft,
        "maintain_skill_package": maintain_skill_package,
        "maintain_skill_promotion_status": maintain_skill_promotion_status,
        "maintain_refresh_scope": maintain_refresh_scope,
        "maintain_rebuild_derived": maintain_rebuild_derived,
        "vault_init": vault_init,
        "vault_export": vault_export,
        "vault_index": vault_index,
        "wiki_index": wiki_index,
        "wiki_search": wiki_search,
        "learn_path": learn_path,
        "learn_entry": learn_entry,
        "learn_business": learn_business,
    }


def configure_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    configure_stdio()
    parser = build_parser(command_handlers())
    args = parser.parse_args(argv)
    args.func(args)
    return 0
