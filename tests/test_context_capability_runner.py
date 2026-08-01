# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from tools.agent_memory_runtime.context_capability_runner import (
    collect_context_capability_batch,
    isolated_memory_snapshot,
    observations_in_case_order,
    preparation_plan,
)


class ContextCapabilityRunnerTests(unittest.TestCase):
    def test_preparation_plan_groups_exact_source_and_setup_identity(self) -> None:
        cases = [
            case("one", source={"before_revision": "working-tree"}),
            case("two", source={"before_revision": "working-tree"}),
            case(
                "three",
                source={"before_revision": "working-tree"},
                setup={"reflections": [{"task": "bounded retry"}]},
            ),
            case(
                "four",
                source={
                    "before_revision": "working-tree",
                    "fixture_group": "event-owner-budget",
                },
            ),
        ]

        plan = preparation_plan(cases)

        self.assertEqual(2, len(plan))
        self.assertEqual([3, 1], [len(group["cases"]) for group in plan])
        self.assertEqual([2, 1], [len(group["setup_groups"]) for group in plan])
        self.assertEqual(
            [["one", "two"], ["three"]],
            [
                [item["id"] for item in group["cases"]]
                for group in plan[0]["setup_groups"]
            ],
        )

    def test_case_snapshot_does_not_mutate_prepared_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepared_home = root / "prepared"
            prepared_home.mkdir()
            state = prepared_home / "state.txt"
            state.write_text("clean", encoding="utf-8")
            memory = {"memory_home": str(prepared_home)}
            workspace = root / "workspace"
            workspace.mkdir()

            with isolated_memory_snapshot(memory, workspace, "diagnosis") as (first, _):
                first_state = Path(first["memory_home"]) / "state.txt"
                first_state.write_text("mutated", encoding="utf-8")

            with isolated_memory_snapshot(memory, workspace, "diagnosis") as (second, _):
                second_state = Path(second["memory_home"]) / "state.txt"
                self.assertEqual("clean", second_state.read_text(encoding="utf-8"))

            self.assertEqual("clean", state.read_text(encoding="utf-8"))

    def test_batch_observations_restore_input_order_after_grouped_execution(self) -> None:
        cases = [
            case("one", source={"fixture_group": "a"}),
            case("two", source={"fixture_group": "b"}),
            case("three", source={"fixture_group": "a"}),
        ]
        observations = [
            {"case_id": "one"},
            {"case_id": "three"},
            {"case_id": "two"},
        ]

        ordered = observations_in_case_order(cases, observations)

        self.assertEqual(["one", "two", "three"], [item["case_id"] for item in ordered])

    def test_batch_prepares_each_source_once_and_snapshots_each_case(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            cases = [
                case("one", source={"fixture_group": "a"}),
                case("two", source={"fixture_group": "b"}),
                case("three", source={"fixture_group": "a"}),
            ]
            prepare_calls: list[str] = []

            @contextmanager
            def fake_workspace(*_args: object):
                yield workspace

            def fake_prepare(*_args: object) -> dict[str, object]:
                prepare_calls.append("prepare")
                home = root / f"prepared-{len(prepare_calls)}"
                home.mkdir()
                (home / "clean.txt").write_text("clean", encoding="utf-8")
                return {"memory_home": str(home)}

            def observe(
                _workspace: Path,
                memory: dict[str, object],
                value: dict[str, object],
                *_args: object,
            ) -> dict[str, object]:
                home = Path(str(memory["memory_home"]))
                self.assertFalse((home / "query-write.txt").exists())
                (home / "query-write.txt").write_text(str(value["id"]), encoding="utf-8")
                return {"case_id": value["id"]}

            with patch(
                "tools.agent_memory_runtime.context_capability_runner.materialized_workspace",
                fake_workspace,
            ), patch(
                "tools.agent_memory_runtime.context_capability_runner.prepare_isolated_memory",
                fake_prepare,
            ):
                result = collect_context_capability_batch(root, cases, 30, observe)

            self.assertEqual(2, len(prepare_calls))
            self.assertEqual(
                ["one", "two", "three"],
                [item["case_id"] for item in result["observations"]],
            )
            self.assertEqual(2, result["execution"]["index_build_count"])
            self.assertEqual(3, result["execution"]["case_snapshot_count"])


def case(
    case_id: str,
    *,
    source: dict[str, object],
    setup: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "id": case_id,
        "task_type": "diagnosis",
        "source": source,
        "context_setup": setup,
    }


if __name__ == "__main__":
    unittest.main()
