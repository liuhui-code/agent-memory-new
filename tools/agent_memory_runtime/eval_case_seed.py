# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .records import output
from .storage import ensure_initialized, resolve_project


def eval_seed_cases_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    data = write_eval_case_seed_pack(Path(args.target), force=bool(getattr(args, "force", False)))
    data["project_id"] = project.project_id
    output(data, args.json)


def write_eval_case_seed_pack(target: Path, force: bool = False) -> dict[str, Any]:
    target.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    skipped: list[str] = []
    for filename, content in seed_files().items():
        path = target / filename
        if path.exists() and not force:
            skipped.append(str(path))
            continue
        path.write_text(content, encoding="utf-8")
        written.append(str(path))
    return {
        "target": str(target),
        "written": written,
        "skipped": skipped,
        "force": force,
        "next_steps": [
            "Edit examples so anchors match this project's memory.",
            "Copy edited files to docs/eval or run eval-quality with --cases-dir <edited-dir>.",
            "Keep unedited examples outside the default docs/eval gate directory.",
        ],
    }


def seed_files() -> dict[str, str]:
    return {
        "README.md": seed_readme(),
        "golden-retrieval.json": json_seed(
            [
                {
                    "name": "arkts-route-anchor",
                    "query": "ArkTS profile page blank screen route diagnosis",
                    "expected": [
                        {
                            "type": "code_symbols",
                            "field": "symbol",
                            "text": "router.pushUrl",
                        },
                        {
                            "type": "code_log_matches",
                            "field": "message_template",
                            "text": "profile",
                        },
                    ],
                    "must_not_include": [
                        {
                            "type": "reflections",
                            "text": "all blank screens are resource issues",
                        }
                    ],
                }
            ]
        ),
        "golden-calibration.json": json_seed(
            [
                {
                    "name": "verified-route-experience-trust",
                    "query": "ArkTS route blank screen diagnosis",
                    "expected_trust": [
                        {
                            "type": "reflections",
                            "text": "router.pushUrl",
                            "trust_level": "verified_experience",
                            "min_trust_score": 0.6,
                        }
                    ],
                    "must_not_trust": [
                        {
                            "type": "reflections",
                            "text": "unverified broad route guess",
                            "max_trust_score": 0.5,
                        }
                    ],
                }
            ]
        ),
        "golden-governance.json": json_seed(
            [
                {
                    "name": "cold-memory-tier-review",
                    "expected_actions": [
                        {
                            "action": "review_memory_tier",
                            "governance_lane": "memory_tiers",
                        }
                    ],
                    "must_not_actions": [
                        {
                            "action": "review_skill_pattern_candidate",
                            "governance_lane": "skill_evolution",
                        }
                    ],
                }
            ]
        ),
        "golden-log-signal.json": json_seed(
            [
                {
                    "name": "profile-route-runtime-log",
                    "logs": [
                        "07-11 12:00:00.100 EntryAbility E Router: event=route_failed route=pages/Profile request_id=req-1 session_id=sess-1 reason=target_missing result=failed",
                        "profile failed",
                    ],
                    "min_good_rate": 0.5,
                    "max_low_signal_rate": 0.5,
                }
            ]
        ),
        "golden-evidence-attribution.json": json_seed(
            [
                {
                    "name": "route-claim-grounding",
                    "query": "ArkTS route blank screen diagnosis",
                    "claims": [
                        "The profile blank screen is related to the router target or page registration."
                    ],
                    "min_grounded_rate": 0.8,
                    "max_unsupported_claims": 0,
                }
            ]
        ),
    }


def json_seed(data: list[dict[str, Any]]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def seed_readme() -> str:
    return """# Golden Eval Case Examples

These files are editable examples for Agent Memory quality gates.

They are intentionally written to `docs/eval/examples` by default. They are not active until you either:

1. edit them and copy the selected files to `docs/eval`, or
2. run `eval-quality` with `--cases-dir docs/eval/examples`.

Before using a case as a real golden gate, replace example anchors with records that exist in the current project's memory. Keep cases small and focused: one user problem, one expected anchor, and one distracting or forbidden anchor is usually enough.

Recommended flow:

```bash
python tools/agent_memory.py eval-seed-cases --project . --target docs/eval/examples --json
python tools/agent_memory.py context --project . --query "<real user problem>" --json
# edit examples with real ids/text from the context output
python tools/agent_memory.py eval-quality --project . --cases-dir docs/eval/examples --json
```
"""
