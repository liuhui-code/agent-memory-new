# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any, Callable


def add_semantic_parsers(sub: Any, add_project: Callable[[Any], None], command: Callable[[str], Any]) -> None:
    evaluate = sub.add_parser("eval-semantic")
    add_project(evaluate)
    evaluate.add_argument("--cases", required=True)
    evaluate.add_argument("--mode", choices=["static", "auto", "external"], default="static")
    evaluate.add_argument("--json", action="store_true")
    evaluate.set_defaults(func=command("eval_semantic_command"))
