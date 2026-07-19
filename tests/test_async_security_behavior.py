# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from tools.agent_memory_runtime.arkts_behavior_markers import (
    extract_arkts_behavior_markers,
)
from tools.agent_memory_runtime.context_source_excerpt import selected_ranges
from tools.agent_memory_runtime.query_behavior_concepts import behavior_marker_terms
from tools.agent_memory_runtime.query_code_selection import diverse_code_matches


class AsyncSecurityBehaviorTests(unittest.TestCase):
    def test_serialized_checkpoint_and_final_barrier_are_distinct(self) -> None:
        queued = """
queueWrite(value: string): void {
  this.writeTail = this.writeTail.then(async () => {
    await this.repository.saveDraft(value)
  })
}
"""
        final = """
async finish(value: string): Promise<void> {
  await this.writeTail
  await this.repository.saveDraft(value)
}
"""

        self.assertIn("serializedwrite", extract_arkts_behavior_markers(queued))
        self.assertIn("writebarrier", extract_arkts_behavior_markers(final))

    def test_timeout_race_and_cancellation_guard_are_normalized(self) -> None:
        source = """
async start(): Promise<void> {
  const deadline = new Promise<void>((resolve) => setTimeout(resolve, 1000))
  await Promise.race([this.initialize(), deadline])
}
async initialize(): Promise<void> {
  await this.load()
  if (this.cancelled) { return }
  this.ready = true
}
"""

        self.assertTrue(
            {"timeoutboundary", "cancellationguard"}
            <= set(extract_arkts_behavior_markers(source))
        )

    def test_webview_access_and_scheme_policy_require_executable_dsl(self) -> None:
        owner = """
Web({ src: this.url, controller: this.controller })
  .fileAccess(false)
  .onLoadIntercept((event) => {
    const url = event.data.getRequestUrl().toLowerCase()
    return ['javascript:', 'data:', 'file:'].some((scheme) => url.startsWith(scheme))
  })
"""
        metadata = "blocked schemes: javascript data file; file access false"

        markers = set(extract_arkts_behavior_markers(owner))
        self.assertTrue({"webaccesspolicy", "urlschemeguard"} <= markers)
        self.assertFalse(
            {"webaccesspolicy", "urlschemeguard"}
            & set(extract_arkts_behavior_markers(metadata))
        )

    def test_bounded_cache_eviction_requires_scan_and_delete(self) -> None:
        owner = """
if (this.entries.size > this.capacity) {
  let oldestTime = Number.MAX_SAFE_INTEGER
  for (const [key, item] of this.entries) {
    if (item.updatedAt < oldestTime) { oldestTime = item.updatedAt }
  }
  this.entries.delete(key)
}
"""
        policy = "entry limit 100, oldest-first eviction"

        self.assertIn("cacheeviction", extract_arkts_behavior_markers(owner))
        self.assertNotIn("cacheeviction", extract_arkts_behavior_markers(policy))

    def test_queries_expand_to_new_structural_markers(self) -> None:
        scenarios = {
            "An incremental checkpoint overwrites the final saved draft.": {
                "serializedwrite", "writebarrier",
            },
            "Initialization continues after its timeout and completes late.": {
                "timeoutboundary", "cancellationguard",
            },
            "The embedded WebView permits a dangerous file URL scheme.": {
                "webaccesspolicy", "urlschemeguard",
            },
            "A full result cache fails to evict its oldest entry.": {
                "cacheeviction",
            },
        }
        for query, expected in scenarios.items():
            with self.subTest(query=query):
                self.assertTrue(expected <= set(behavior_marker_terms(query)))

        persistence_terms = set(behavior_marker_terms(
            "增量写入最终覆盖完整内容，请返回串行队列和等待屏障。"
        ))
        self.assertFalse(
            {"overlay", "backgroundcolor", "zindex", "stack", "position"}
            & persistence_terms
        )

    def test_complete_owners_suppress_lexical_neighbors(self) -> None:
        scenarios = [
            (
                "An incremental checkpoint overwrites the final saved draft.",
                "src/streaming/ConversationDraftStore.ets",
                "behavior: serializedwrite, writebarrier, asyncboundary",
            ),
            (
                "Initialization continues after its timeout and completes late.",
                "src/lifecycle/DeadlineBootstrapController.ets",
                "behavior: timeoutboundary, cancellationguard, asyncboundary",
            ),
            (
                "The embedded WebView permits a dangerous file URL scheme.",
                "src/web/SecureDocumentBrowser.ets",
                "behavior: webaccesspolicy, urlschemeguard, callbackboundary",
            ),
            (
                "A full result cache fails to evict its oldest entry.",
                "src/cache/BoundedResultCache.ets",
                "behavior: cacheeviction, conditionalbranch",
            ),
        ]
        for query, expected, summary in scenarios:
            candidates = [
                code_item(expected, 27.0, summary),
                code_item(
                    "src/config/FeaturePolicy.ets", 52.0,
                    "checkpoint timeout WebView scheme oldest cache policy",
                ),
                code_item(
                    "src/pages/FeatureStatusPage.ets", 48.0,
                    "checkpoint timeout browser cache status page",
                ),
            ]

            selected = diverse_code_matches(candidates, 5, query=query)

            self.assertEqual([expected], [item["file_path"] for item in selected])

    def test_two_persistence_methods_are_selected_from_one_file(self) -> None:
        source = fixture_source("streaming/ConversationDraftStore.ets")
        selected = select_from_source(
            "ConversationDraftStore.ets",
            source,
            "An incremental checkpoint can overwrite the final saved draft.",
        )

        self.assertEqual(2, len(selected))
        self.assertTrue(any(overlaps(item, 22, 27) for item in selected))
        self.assertTrue(any(overlaps(item, 37, 41) for item in selected))

    def test_timeout_owner_returns_deadline_and_initialization_methods(self) -> None:
        source = fixture_source("lifecycle/DeadlineBootstrapController.ets")
        selected = select_from_source(
            "DeadlineBootstrapController.ets",
            source,
            "Initialization continues after its timeout and completes late.",
        )

        self.assertEqual(
            {"startWithDeadline", "initializeWorkspace"},
            {str(item.get("symbol")) for item in selected},
        )

    def test_webview_policy_callback_is_selected(self) -> None:
        source = fixture_source("web/SecureDocumentBrowser.ets")
        selected = select_from_source(
            "SecureDocumentBrowser.ets",
            source,
            "The embedded WebView permits a dangerous file URL scheme.",
        )

        self.assertTrue(any(overlaps(item, 10, 16) for item in selected))


def code_item(file_path: str, score: float, summary: str) -> dict[str, object]:
    return {
        "file_path": file_path,
        "symbol": Path(file_path).stem,
        "score": score,
        "summary": summary,
        "match_reasons": ["structural_behavior"],
    }


def fixture_source(relative: str) -> str:
    root = Path(__file__).parents[1] / "docs/eval/fixtures/system-capability/src"
    return (root / relative).read_text(encoding="utf-8")


def select_from_source(name: str, source: str, query: str) -> list[dict[str, object]]:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / name
        path.write_text(source, encoding="utf-8")
        return selected_ranges({"source_ranges": []}, path, query)


def overlaps(item: dict[str, object], start: int, end: int) -> bool:
    return int(item["start_line"]) <= end and start <= int(item["end_line"])


if __name__ == "__main__":
    unittest.main()
