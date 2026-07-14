# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any, Callable


def add_design_parsers(sub: Any, add_project: Callable[[Any], None], command: Callable[[str], Any]) -> None:
    prepare = sub.add_parser("design-prepare")
    add_project(prepare)
    prepare.add_argument("--intent", required=True)
    prepare.add_argument("--contract")
    prepare.add_argument("--rules")
    prepare.add_argument("--json", action="store_true")
    prepare.set_defaults(func=command("design_prepare_command"))

    check = sub.add_parser("design-check")
    add_project(check)
    add_common_inputs(check)
    check.set_defaults(func=command("design_check_command"))

    compare = sub.add_parser("design-compare")
    add_project(compare)
    compare.add_argument("--proposal", action="append", required=True)
    compare.add_argument("--contract")
    compare.add_argument("--intent")
    compare.add_argument("--rules")
    compare.add_argument("--json", action="store_true")
    compare.set_defaults(func=command("design_compare_command"))

    progress = sub.add_parser("design-progress")
    add_project(progress)
    add_common_inputs(progress)
    progress.add_argument("--base", default="HEAD~1")
    progress.add_argument("--files", action="append")
    progress.add_argument("--diff-file")
    progress.add_argument("--executed-tests", action="append")
    progress.add_argument("--test-evidence")
    progress.add_argument("--test-report", action="append")
    progress.add_argument("--verification-run")
    progress.add_argument("--completed-step", action="append")
    progress.set_defaults(func=command("design_progress_command"))

    verify = sub.add_parser("design-verify")
    add_project(verify)
    add_common_inputs(verify)
    verify.add_argument("--base", default="HEAD~1")
    verify.add_argument("--files", action="append")
    verify.add_argument("--diff-file")
    verify.add_argument("--executed-tests", action="append")
    verify.add_argument("--actual-symbols", action="append")
    verify.add_argument("--test-evidence")
    verify.add_argument("--test-report", action="append")
    verify.add_argument("--verification-run")
    verify.set_defaults(func=command("design_verify_command"))

    evaluate = sub.add_parser("eval-design")
    add_project(evaluate)
    evaluate.add_argument("--cases", required=True)
    evaluate.add_argument("--json", action="store_true")
    evaluate.set_defaults(func=command("eval_design_command"))

    outcome = sub.add_parser("design-outcome")
    add_project(outcome)
    outcome.add_argument("--verification", required=True)
    outcome.add_argument("--outcome", required=True, choices=["success", "partial", "failure"])
    outcome.add_argument("--json", action="store_true")
    outcome.set_defaults(func=command("design_outcome_command"))


def add_common_inputs(parser: Any) -> None:
    parser.add_argument("--proposal", required=True)
    parser.add_argument("--contract")
    parser.add_argument("--intent")
    parser.add_argument("--rules")
    parser.add_argument("--json", action="store_true")
