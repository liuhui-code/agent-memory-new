# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any, Callable


def add_benchmark_parsers(
    sub: Any,
    add_project: Callable[[Any], None],
    command: Callable[[str], Any],
) -> None:
    history = sub.add_parser("eval-harvest-history")
    add_project(history)
    history.add_argument("--source")
    history.add_argument("--target", required=True)
    history.add_argument("--limit", type=int, default=20)
    history.add_argument("--scan-limit", type=int, default=200)
    history.add_argument("--since")
    history.add_argument("--force", action="store_true")
    history.add_argument("--json", action="store_true")
    history.set_defaults(func=command("eval_harvest_history_command"))

    seal = sub.add_parser("eval-seal-cases")
    add_project(seal)
    seal.add_argument("--cases", required=True)
    seal.add_argument("--target", required=True)
    seal.add_argument("--source")
    seal.add_argument("--force", action="store_true")
    seal.add_argument("--json", action="store_true")
    seal.set_defaults(func=command("eval_seal_cases_command"))

    mutate = sub.add_parser("eval-mutate-arkts")
    add_project(mutate)
    mutate.add_argument("--source")
    mutate.add_argument("--target", required=True)
    mutate.add_argument("--limit", type=int, default=20)
    mutate.add_argument(
        "--operator",
        choices=["remove_await", "corrupt_route_target", "corrupt_resource_key"],
    )
    mutate.add_argument("--force", action="store_true")
    mutate.add_argument("--json", action="store_true")
    mutate.set_defaults(func=command("eval_mutate_arkts_command"))

    evaluate = sub.add_parser("eval-agent-benchmark")
    add_project(evaluate)
    evaluate.add_argument("--cases", required=True)
    evaluate.add_argument("--source")
    evaluate.add_argument("--runner")
    evaluate.add_argument("--responses")
    evaluate.add_argument("--runner-timeout", type=int, default=300)
    evaluate.add_argument("--limit", type=int, default=20)
    evaluate.add_argument("--case-id", action="append", default=[])
    evaluate.add_argument("--trials", type=int, default=1)
    evaluate.add_argument("--skip-memory-prepare", action="store_true")
    evaluate.add_argument("--output-responses")
    evaluate.add_argument("--allow-drafts", action="store_true")
    evaluate.add_argument("--fail-on-fail", action="store_true")
    evaluate.add_argument("--fail-on-efficiency-fail", action="store_true")
    evaluate.add_argument("--json", action="store_true")
    evaluate.set_defaults(func=command("eval_agent_benchmark_command"))

    context = sub.add_parser("eval-context-capability")
    add_project(context)
    context.add_argument("--cases", required=True)
    context.add_argument("--source")
    context.add_argument("--runner-timeout", type=int, default=300)
    context.add_argument("--limit", type=int)
    context.add_argument("--case-id", action="append", default=[])
    context.add_argument("--allow-drafts", action="store_true")
    context.add_argument("--fail-on-fail", action="store_true")
    context.add_argument("--json", action="store_true")
    context.set_defaults(func=command("eval_context_capability_command"))
