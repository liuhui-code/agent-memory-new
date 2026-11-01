# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import sqlite3

from .records import output
from .storage import resolve_project
from .system_evolution_contract import load_report
from .system_evolution_checks import check_change
from .system_evolution_candidates import prepare_candidate
from .system_evolution_store import read_registry, save_review, transition_change
from .system_evolution_trigger_contract import load_trigger
from .system_evolution_triggers import decide_trigger
from .system_evolution_migrations import migrate_governance
from .system_evolution_acceptance import accept_change
from .system_evolution_application import apply_change, resume_application, rollback_change
from .system_evolution_follow_up import follow_up_change, resolve_nonapplication
from .system_evolution_contract import SystemEvolutionError
from .system_evolution_outcomes import outcome_context
from .system_evolution_rounds import read_round, record_round
from .system_evolution_rounds_contract import load_round_record
from .system_evolution_handoff_contract import load_handoff
from .system_evolution_handoffs import handoff_round
from .system_evolution_campaign_readiness import campaign_readiness


def maintain_system_campaign_readiness(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    output(campaign_readiness(project, args.protocol_file, args.campaign_manifest, args.intent), args.json)


def maintain_system_round_handoff(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    output(handoff_round(project, load_handoff(args.payload_file), args.execute), args.json)


def maintain_system_round(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    output(read_round(project, args.round_key, args.revision, args.limit), args.json)


def maintain_system_round_record(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    output(record_round(project, load_round_record(args.payload_file), args.execute), args.json)


def maintain_system_outcome(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    output(outcome_context(project, args.id, args.application_key, args.plan_file, args.observations_file), args.json)


def maintain_system_lifecycle(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    action = args.lifecycle_action
    try:
        if action == "accept":
            result = accept_change(project, args.id, args.expected_revision, args.operation_key, args.acceptance_file, args.review_file, args.execute)
        elif action == "apply":
            result = apply_change(project, args.id, args.expected_revision, args.operation_key, args.target_root, args.recovery_home, args.execute, args.layout)
        elif action == "rollback":
            result = rollback_change(project, args.id, args.expected_revision, args.operation_key, args.application_key, args.execute)
        elif action == "follow-up":
            result = follow_up_change(project, args.id, args.expected_revision, args.operation_key, args.status, args.note, args.execute)
        elif action == "resume":
            result = resume_application(project, args.operation_key, args.execute)
        else:
            result = resolve_nonapplication(project, args.operation_key, args.execute)
    except (OSError, ValueError, RuntimeError) as error:
        if isinstance(error, SystemEvolutionError):
            raise
        raise SystemEvolutionError("invalid_lifecycle_input", "Cannot safely read or operate on the declared lifecycle material; inspect the operation history.") from error
    output(result, args.json)
    if (result.get("schema_version") == "system-change-lifecycle/v1"
            and action != "resolve" and result["operation"]["state"] != "completed"):
        raise SystemExit(1)


def maintain_system_migrate(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    try:
        result = migrate_governance(project, args.target_version, args.backup_file, args.execute)
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as error:
        if isinstance(error, SystemEvolutionError):
            raise
        raise SystemEvolutionError("invalid_migration_input", "Cannot safely open the declared migration inputs.") from error
    output(result, args.json)


def reflect_system(args: argparse.Namespace) -> None:
    report = load_report(args.payload, args.payload_file)
    project = resolve_project(args.project, args.memory_home)
    output(save_review(project, args.review_key, report), args.json)


def maintain_system(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    output(read_registry(project, args.limit, args.review_key, args.change_id, args.status,
                         args.run_key, args.trigger_id, args.candidate_key, args.operation_key), args.json)


def maintain_system_status(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    result = transition_change(
        project, args.id, args.expected_revision, args.status, args.note,
        args.development_root, args.artifact_file, args.base_version,
    )
    output(result, args.json)


def maintain_system_check(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    result = check_change(project, args.id, args.expected_revision, args.run_key, args.plan_file, args.execute)
    output(result, args.json)
    if "run" in result and result["run"]["receipt"]["outcome"] != "all_exit_zero":
        raise SystemExit(1)


def reflect_system_trigger(args: argparse.Namespace) -> None:
    request = load_trigger(args.payload, args.payload_file)
    project = resolve_project(args.project, args.memory_home)
    output(decide_trigger(project, request, args.claim), args.json)


def maintain_system_candidate(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    result = prepare_candidate(project, args.id, args.expected_revision, args.candidate_key,
                               args.patch_file, args.candidate_home, args.execute)
    output(result, args.json)
    if "candidate" in result and result["candidate"]["state"] != "ready":
        raise SystemExit(1)
