# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_memory_test_base import AgentMemoryTestBase


class QueryGraphNeighborTests(AgentMemoryTestBase):
    def test_import_neighbor_becomes_source_locatable_code_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            model = project / "src" / "model" / "DomainState.ets"
            view = project / "src" / "views" / "CheckoutPanel.ets"
            model.parent.mkdir(parents=True)
            view.parent.mkdir(parents=True)
            model.write_text(
                "export class DomainState {\n  ready: boolean = false\n}\n",
                encoding="utf-8",
            )
            view.write_text(
                "import { DomainState } from '../model/DomainState'\n\n"
                "@Component\nstruct CheckoutPanel {\n"
                "  private state: DomainState = new DomainState()\n"
                "  build() { Text('Checkout') }\n}\n",
                encoding="utf-8",
            )
            self.run_memory(project, "learn-path", "--path", "src")

            result = self.run_memory(
                project,
                "context",
                "--query",
                "checkout panel rendering",
                "--compact",
                "--json",
            )
            anchors = json.loads(result.stdout)["query_handoff"]["code_anchors"]

        neighbor = next(
            item for item in anchors
            if item["file_path"] == "src/model/DomainState.ets"
        )
        self.assertTrue(neighbor["source_ranges"])

    def test_named_nav_path_creates_route_edge_to_unique_component_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            sender = project / "src" / "views" / "SenderAction.ets"
            target = project / "src" / "pages" / "ChatDetail.ets"
            sender.parent.mkdir(parents=True)
            target.parent.mkdir(parents=True)
            sender.write_text(
                "@Component\nstruct SenderAction {\n"
                "  stack: NavPathStack = new NavPathStack()\n"
                "  open() { this.stack.pushPath({ name: 'ChatDetail' }) }\n}\n",
                encoding="utf-8",
            )
            target.write_text(
                "@Component\nexport struct ChatDetail { build() {} }\n",
                encoding="utf-8",
            )
            self.run_memory(project, "learn-path", "--path", "src")

            edges = self.list_records(project, "memory-edge")

        route = next(item for item in edges if item["relation"] == "routes_to")
        self.assertEqual(
            "src/views/SenderAction.ets -> src/pages/ChatDetail.ets",
            route["evidence"],
        )

    def test_component_property_flow_recovers_two_upstream_components(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            page = project / "src" / "pages" / "TimelinePage.ets"
            row = project / "src" / "views" / "TimelineRow.ets"
            bubble = project / "src" / "views" / "EventBubble.ets"
            page.parent.mkdir(parents=True)
            row.parent.mkdir(parents=True)
            page.write_text(
                "import { TimelineRow } from '../views/TimelineRow'\n"
                "@Component\nstruct TimelinePage {\n"
                "  shouldShowHeader(): boolean { return true }\n"
                "  build() { TimelineRow({ showHeader: this.shouldShowHeader() }) }\n}\n",
                encoding="utf-8",
            )
            row.write_text(
                "import { EventBubble } from './EventBubble'\n"
                "@Component\nexport struct TimelineRow {\n"
                "  @Prop showHeader: boolean = true\n"
                "  // EventBubble({ ignoredProperty: true })\n"
                "  build() { EventBubble({ showHeader: this.showHeader }) }\n}\n",
                encoding="utf-8",
            )
            bubble.write_text(
                "@Component\nexport struct EventBubble {\n"
                "  @Prop showHeader: boolean = true\n"
                "  build() { if (this.showHeader) { Text('Category') } }\n}\n",
                encoding="utf-8",
            )
            self.run_memory(project, "learn-path", "--path", "src")

            edges = self.list_records(project, "memory-edge")
            result = self.run_memory(
                project,
                "context",
                "--query",
                "event bubble category label visibility",
                "--compact",
                "--json",
            )
            anchors = json.loads(result.stdout)["query_handoff"]["code_anchors"]

        property_edges = [edge for edge in edges if edge["relation"] == "passes_property"]
        self.assertEqual(2, len(property_edges))
        self.assertTrue(all("showHeader" in edge["evidence"] for edge in property_edges))
        self.assertEqual(
            {
                "src/pages/TimelinePage.ets",
                "src/views/TimelineRow.ets",
                "src/views/EventBubble.ets",
            },
            {item["file_path"] for item in anchors},
        )


if __name__ == "__main__":
    unittest.main()
