# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
from collections.abc import Mapping
from typing import Any

from .models import VALID_MEMORY_STATUSES


def build_parser(commands: Mapping[str, Any]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent_memory.py")
    sub = parser.add_subparsers(dest="command", required=True)

    def command(name: str) -> Any:
        return commands.get(name)

    def add_project(p: argparse.ArgumentParser) -> None:
        p.add_argument("--project", default=".")
        p.add_argument("--memory-home")

    p = sub.add_parser("init")
    add_project(p)
    p.set_defaults(func=command("init_project"))

    p = sub.add_parser("doctor")
    add_project(p)
    p.set_defaults(func=command("doctor"))

    p = sub.add_parser("update")
    add_project(p)
    p.add_argument("--type", required=True, choices=["semantic", "episode"])
    p.add_argument("--fact")
    p.add_argument("--source", default="manual")
    p.add_argument("--confidence", type=float, default=0.8)
    p.add_argument("--category")
    p.add_argument("--scope")
    p.add_argument("--evidence")
    p.add_argument("--task")
    p.add_argument("--summary")
    p.add_argument("--outcome")
    p.add_argument("--files-touched")
    p.add_argument("--commands-run")
    p.add_argument("--importance", type=float, default=0.5)
    p.set_defaults(func=command("update"))

    p = sub.add_parser("search")
    add_project(p)
    p.add_argument("--query", required=True)
    p.add_argument("--cursor", type=int, default=0)
    p.add_argument("--per-type-limit", type=int)
    p.add_argument("--aggregate-limit", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("search"))

    p = sub.add_parser("context")
    add_project(p)
    p.add_argument("--query", required=True)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("context"))

    p = sub.add_parser("analyze-runtime-log")
    add_project(p)
    p.add_argument("--query", required=True)
    p.add_argument("--log-file", required=True)
    p.add_argument("--before-lines", type=int, default=2)
    p.add_argument("--after-lines", type=int, default=2)
    p.add_argument("--slice-limit", type=int, default=5)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("analyze_runtime_log_command"))

    p = sub.add_parser("reflect")
    add_project(p)
    p.add_argument("--payload")
    p.add_argument("--payload-file")
    p.add_argument("--task")
    p.add_argument("--summary")
    p.add_argument("--mistake")
    p.add_argument("--lesson")
    p.add_argument("--experience-type", choices=["procedure_experience", "correction_experience"])
    p.add_argument("--future-rule")
    p.add_argument("--scope")
    p.add_argument("--evidence")
    p.add_argument("--confidence", type=float, default=0.8)
    p.add_argument("--trigger-condition")
    p.add_argument("--anti-pattern")
    p.add_argument("--repair-action")
    p.add_argument("--applies-to")
    p.add_argument("--does-not-apply-to")
    p.add_argument("--used-reflection-ids")
    p.add_argument("--reflection-outcome", choices=["helped", "partial", "misleading", "unused"])
    p.set_defaults(func=command("reflect"))

    p = sub.add_parser("reflect-review")
    add_project(p)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("reflect_review"))

    p = sub.add_parser("list")
    add_project(p)
    p.add_argument(
        "--type",
        required=True,
        choices=[
            "semantic",
            "reflection",
            "episode",
            "code-file",
            "code-symbol",
            "code-log",
            "memory-edge",
            "learn-scope",
            "reflection-reuse",
            "semantic-conflict",
        ],
    )
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("list_records"))

    p = sub.add_parser("miss-list")
    add_project(p)
    p.add_argument("--status", choices=["open", "reviewed", "resolved", "ignored"])
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("miss_list"))

    p = sub.add_parser("miss-status")
    add_project(p)
    p.add_argument("--id", required=True, type=int)
    p.add_argument("--status", required=True, choices=["open", "reviewed", "resolved", "ignored"])
    p.add_argument("--resolution")
    p.set_defaults(func=command("miss_status"))

    p = sub.add_parser("conflict-status")
    add_project(p)
    p.add_argument("--id", required=True, type=int)
    p.add_argument("--status", required=True, choices=["open", "reviewed", "resolved", "ignored", "applied"])
    p.add_argument("--resolution")
    p.add_argument("--decision-note")
    p.add_argument("--replacement-source")
    p.set_defaults(func=command("conflict_status"))

    p = sub.add_parser("conflict-apply")
    add_project(p)
    p.add_argument("--id", required=True, type=int)
    p.add_argument("--resolution")
    p.add_argument("--decision-note")
    p.add_argument("--replacement-source")
    p.set_defaults(func=command("conflict_apply"))

    p = sub.add_parser("mark-stale")
    add_project(p)
    p.add_argument("--type", required=True, choices=["semantic", "reflection"])
    p.add_argument("--id", required=True, type=int)
    p.set_defaults(func=command("mark_stale"))

    p = sub.add_parser("maintain-health")
    add_project(p)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("maintain_health"))

    p = sub.add_parser("maintain-review")
    add_project(p)
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("maintain_review"))

    p = sub.add_parser("maintain-plan")
    add_project(p)
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("maintain_plan"))

    p = sub.add_parser("maintain-status")
    add_project(p)
    p.add_argument("--type", required=True, choices=["semantic", "reflection", "episode"])
    p.add_argument("--id", required=True, type=int)
    p.add_argument("--status", required=True, choices=sorted(VALID_MEMORY_STATUSES))
    p.add_argument("--reason")
    p.set_defaults(func=command("maintain_status"))

    p = sub.add_parser("maintain-merge")
    add_project(p)
    p.add_argument("--type", required=True, choices=["semantic", "reflection"])
    p.add_argument("--ids", required=True)
    p.add_argument("--fact")
    p.add_argument("--lesson")
    p.add_argument("--task")
    p.add_argument("--summary")
    p.add_argument("--future-rule")
    p.add_argument("--source", default="maintain-merge")
    p.add_argument("--confidence", type=float, default=0.85)
    p.add_argument("--category")
    p.add_argument("--scope")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("maintain_merge"))

    p = sub.add_parser("maintain-promote")
    add_project(p)
    p.add_argument("--episode-id", type=int)
    p.add_argument("--reflection-id", type=int)
    p.add_argument("--fact", required=True)
    p.add_argument("--confidence", type=float, default=0.85)
    p.add_argument("--category")
    p.add_argument("--scope")
    p.add_argument("--evidence")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("maintain_promote"))

    p = sub.add_parser("maintain-skill-draft")
    add_project(p)
    p.add_argument("--pattern-name", required=True)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("maintain_skill_draft"))

    p = sub.add_parser("maintain-skill-package")
    add_project(p)
    p.add_argument("--pattern-name", required=True)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("maintain_skill_package"))

    p = sub.add_parser("maintain-incident-strategy-draft")
    add_project(p)
    p.add_argument("--strategy-name", required=True)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("maintain_incident_strategy_draft"))

    p = sub.add_parser("maintain-incident-fingerprint-draft")
    add_project(p)
    p.add_argument("--fingerprint-name", required=True)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("maintain_incident_fingerprint_draft"))

    p = sub.add_parser("maintain-skill-promotion-status")
    add_project(p)
    p.add_argument("--pattern-name", required=True)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("maintain_skill_promotion_status"))

    p = sub.add_parser("maintain-refresh-scope")
    add_project(p)
    p.add_argument("--scope-id", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("maintain_refresh_scope"))

    p = sub.add_parser("vault-init")
    add_project(p)
    p.set_defaults(func=command("vault_init"))

    p = sub.add_parser("vault-export")
    add_project(p)
    p.set_defaults(func=command("vault_export"))

    p = sub.add_parser("vault-index")
    add_project(p)
    p.set_defaults(func=command("vault_index"))

    p = sub.add_parser("wiki-index")
    add_project(p)
    p.add_argument("--source")
    p.set_defaults(func=command("wiki_index"))

    p = sub.add_parser("wiki-search")
    add_project(p)
    p.add_argument("--query", required=True)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("wiki_search"))

    p = sub.add_parser("learn-path")
    add_project(p)
    p.add_argument("--source")
    p.add_argument("--path", required=True)
    p.add_argument("--replace", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("learn_path"))

    p = sub.add_parser("learn-entry")
    add_project(p)
    p.add_argument("--source")
    p.add_argument("--entry", required=True)
    p.add_argument("--depth", type=int, default=2)
    p.add_argument("--replace", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("learn_entry"))

    p = sub.add_parser("learn-business")
    add_project(p)
    p.add_argument("--source")
    p.add_argument("--payload", required=True)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command("learn_business"))

    return parser
