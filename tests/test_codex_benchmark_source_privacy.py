# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


RUNNER = Path(__file__).resolve().parents[1] / "examples" / "codex-agent-benchmark-runner.py"


class CodexBenchmarkSourcePrivacyTests(unittest.TestCase):
    def test_current_source_excerpts_are_not_reread(self) -> None:
        module = load_runner_module()
        prompt = module.build_prompt(
            benchmark_request(),
            {
                "query_handoff": {
                    "source_excerpt_policy": {"source": "current_worktree"},
                    "source_exploration": {"limits": {}},
                    "code_anchors": [{
                        "source_excerpts": [{"content": "const current = true"}],
                    }],
                }
            },
        )

        self.assertIn("source_excerpts were read from this current worktree", prompt)
        self.assertIn("do not reread those lines", prompt)

    def test_external_runner_redacts_source_excerpt_bodies(self) -> None:
        module = load_runner_module()
        context = {
            "query_handoff": {
                "source_excerpt_policy": {"source": "current_worktree"},
                "source_exploration": {"limits": {}},
                "code_anchors": [{
                    "file_path": "src/Profile.ets",
                    "source_excerpts": [{
                        "symbol": "Profile",
                        "start_line": 4,
                        "end_line": 8,
                        "content": "external-secret-source-body",
                        "source": "current_worktree",
                        "truncated": False,
                    }],
                }],
            }
        }

        redacted = module.external_memory_context(context)
        prompt = module.build_prompt(benchmark_request(), redacted)
        anchor = redacted["query_handoff"]["code_anchors"][0]

        self.assertNotIn("external-secret-source-body", json.dumps(redacted))
        self.assertNotIn("external-secret-source-body", prompt)
        self.assertNotIn("source_excerpts", anchor)
        self.assertEqual("Profile", anchor["source_excerpt_metadata"][0]["symbol"])
        self.assertIn("Verify all conclusions against current source", prompt)


def benchmark_request() -> dict:
    return {
        "case": {
            "task_type": "diagnosis",
            "task": {"description": "Profile does not load.", "constraints": []},
        },
        "instructions": [],
        "response_schema": {},
    }


def load_runner_module():
    spec = importlib.util.spec_from_file_location("codex_benchmark_runner_privacy", RUNNER)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
