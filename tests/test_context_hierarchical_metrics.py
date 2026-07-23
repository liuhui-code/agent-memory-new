# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from tools.agent_memory_runtime.context_capability import summarize_context
from tools.agent_memory_runtime.context_hierarchical_metrics import (
    assess_hierarchical_localization,
    localization_profile,
)


def test_hierarchical_metrics_keep_file_callable_owner_and_range_separate() -> None:
    observation = {
        "hierarchical_schema_version": "agent-hierarchical-localization/v1",
        "hierarchical_file_paths": ["src/services/SnapshotService.ets"],
        "hierarchical_callable_refs": [{
            "file_path": "src/services/SnapshotService.ets",
            "symbol": "restoreSnapshot",
            "start_line": 4,
            "end_line": 16,
        }],
        "hierarchical_owner_refs": [{
            "file_path": "src/pages/SnapshotPage.ets",
            "symbol": "refreshSnapshot",
            "start_line": 7,
            "end_line": 9,
            "graph_depth": 1,
        }],
        "hierarchical_source_ranges": [{
            "file_path": "src/services/SnapshotService.ets",
            "symbol": "restoreSnapshot",
            "start_line": 5,
            "end_line": 9,
        }],
        "hierarchical_audit_elapsed_ms": 18,
    }
    score = assess_hierarchical_localization(
        {"src/services/SnapshotService.ets"},
        {
            "required_source_spans": [{"file_path": "src/Wrong.ets", "symbol": "wrong"}],
            "hierarchical_callable_spans": [{
                "file_path": "src/services/SnapshotService.ets",
                "symbol": "restoreSnapshot", "start_line": 5, "end_line": 8,
            }],
            "hierarchical_owner_spans": [
                {"file_path": "src/pages/SnapshotPage.ets", "symbol": "refreshSnapshot"}
            ],
            "hierarchical_range_spans": [{
                "file_path": "src/services/SnapshotService.ets",
                "symbol": "restoreSnapshot", "start_line": 5, "end_line": 8,
            }],
        },
        observation,
    )

    assert score["observed"]
    assert score["file_recall"] == 1.0
    assert score["callable_recall"] == 1.0
    assert score["owner_recall"] == 1.0
    assert score["owner_precision"] == 1.0
    assert score["range_recall"] == 1.0


def test_missing_shadow_audit_is_informational_not_a_context_failure() -> None:
    score = assess_hierarchical_localization({"src/Profile.ets"}, {}, {})
    profile = localization_profile([{"hierarchical_localization": score}])

    assert not score["observed"]
    assert profile["status"] == "informational"
    assert profile["observed_case_count"] == 0
    assert profile["owner_evaluated_case_count"] == 0
    assert profile["file_recall"] is None


def test_context_summary_uses_full_audit_without_exposing_source_bodies() -> None:
    context = {
        "schema_version": "agent-context-compact/v1",
        "query_handoff": {"code_anchors": [], "log_anchors": []},
        "output_budget": {"estimated_tokens": 123},
    }
    audit = {
        "query_audit": {
            "candidate_recall": {"tables": {}},
            "hierarchical_localization": {
                "schema_version": "agent-hierarchical-localization/v1",
                "file_candidates": [{"file_path": "src/Service.ets"}],
                "callable_candidates": [
                    {"file_path": "src/Service.ets", "symbol": "restore"},
                ],
                "graph_owner_candidates": [
                    {"file_path": "src/Page.ets", "symbol": "refresh", "graph_depth": 1},
                ],
                "source_ranges": [{
                    "file_path": "src/Service.ets", "symbol": "restore",
                    "start_line": 5, "end_line": 8,
                }],
            },
        },
    }

    observed = summarize_context("case", context, 10, 4, audit, 16)

    assert observed["hierarchical_file_paths"] == ["src/Service.ets"]
    assert observed["hierarchical_owner_refs"][0]["symbol"] == "refresh"
    assert observed["hierarchical_source_ranges"][0]["start_line"] == 5
    assert "content" not in str(observed)
