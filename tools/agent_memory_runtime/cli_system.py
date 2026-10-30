# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any, Callable


def add_system_parsers(sub: Any, add_project: Callable[[Any], None], command: Callable[[str], Any]) -> None:
    migration = sub.add_parser("maintain-system-migrate")
    add_project(migration)
    migration.add_argument("--target-version", required=True)
    migration.add_argument("--backup-file", required=True)
    migration.add_argument("--execute", action="store_true")
    migration.add_argument("--json", action="store_true")
    migration.set_defaults(func=command("maintain_system_migrate"))
    save = sub.add_parser("reflect-system")
    add_project(save)
    save.add_argument("--review-key", required=True)
    source = save.add_mutually_exclusive_group(required=True)
    source.add_argument("--payload")
    source.add_argument("--payload-file")
    save.add_argument("--json", action="store_true")
    save.set_defaults(func=command("reflect_system"))

    review = sub.add_parser("maintain-system")
    add_project(review)
    selector = review.add_mutually_exclusive_group()
    selector.add_argument("--review-key")
    selector.add_argument("--change-id", type=int)
    selector.add_argument("--run-key")
    selector.add_argument("--trigger-id", type=int)
    selector.add_argument("--candidate-key")
    selector.add_argument("--operation-key")
    review.add_argument("--status")
    review.add_argument("--limit", type=int, default=5)
    review.add_argument("--json", action="store_true")
    review.set_defaults(func=command("maintain_system"))

    status = sub.add_parser("maintain-system-status")
    add_project(status)
    status.add_argument("--id", type=int, required=True)
    status.add_argument("--expected-revision", type=int, required=True)
    status.add_argument("--status", required=True)
    status.add_argument("--note", required=True)
    status.add_argument("--development-root")
    status.add_argument("--artifact-file", action="append", default=[])
    status.add_argument("--base-version")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=command("maintain_system_status"))

    check = sub.add_parser("maintain-system-check")
    add_project(check)
    check.add_argument("--id", type=int, required=True)
    check.add_argument("--expected-revision", type=int, required=True)
    check.add_argument("--run-key", required=True)
    check.add_argument("--plan-file", required=True)
    check.add_argument("--execute", action="store_true")
    check.add_argument("--json", action="store_true")
    check.set_defaults(func=command("maintain_system_check"))

    trigger = sub.add_parser("reflect-system-trigger")
    add_project(trigger)
    trigger_source = trigger.add_mutually_exclusive_group(required=True)
    trigger_source.add_argument("--payload")
    trigger_source.add_argument("--payload-file")
    trigger.add_argument("--claim", action="store_true")
    trigger.add_argument("--json", action="store_true")
    trigger.set_defaults(func=command("reflect_system_trigger"))

    candidate = sub.add_parser("maintain-system-candidate")
    add_project(candidate)
    candidate.add_argument("--id", type=int, required=True)
    candidate.add_argument("--expected-revision", type=int, required=True)
    candidate.add_argument("--candidate-key", required=True)
    candidate.add_argument("--patch-file", required=True)
    candidate.add_argument("--candidate-home", required=True)
    candidate.add_argument("--execute", action="store_true")
    candidate.add_argument("--json", action="store_true")
    candidate.set_defaults(func=command("maintain_system_candidate"))

    for action in ("accept", "apply", "rollback", "follow-up", "resume", "resolve"):
        lifecycle = sub.add_parser("maintain-system-" + action)
        add_project(lifecycle)
        lifecycle.add_argument("--operation-key", required=True)
        lifecycle.add_argument("--execute", action="store_true")
        lifecycle.add_argument("--json", action="store_true")
        if action not in {"resume", "resolve"}:
            lifecycle.add_argument("--id", type=int, required=True)
            lifecycle.add_argument("--expected-revision", type=int, required=True)
        if action == "accept":
            lifecycle.add_argument("--acceptance-file", required=True)
            lifecycle.add_argument("--review-file", required=True)
        elif action == "apply":
            lifecycle.add_argument("--target-root", required=True)
            lifecycle.add_argument("--recovery-home", required=True)
            lifecycle.add_argument("--layout", choices=("source", "installed"), default="source")
        elif action == "rollback":
            lifecycle.add_argument("--application-key", required=True)
        elif action == "follow-up":
            lifecycle.add_argument("--status", required=True)
            lifecycle.add_argument("--note", required=True)
        lifecycle.set_defaults(func=command("maintain_system_lifecycle"), lifecycle_action=action)
