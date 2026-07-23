# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.agent_memory_runtime.code_wiki_extractors import extract_symbols, summarize_file
from tools.agent_memory_runtime.context_source_excerpt import (
    TOKEN_RESERVE,
    attach_source_excerpts,
    focused_source_range,
)
from tools.agent_memory_runtime.performance_scoring import estimate_payload_tokens


class ArktsUiContextTests(unittest.TestCase):
    def test_tight_excerpt_budget_covers_three_primary_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            anchors = []
            for index in range(3):
                name = f"Owner{index}.ets"
                (root / name).write_text(
                    "\n".join(
                        f"const owner{index}Step{line} = true"
                        for line in range(10)
                    ) + "\n",
                    encoding="utf-8",
                )
                anchors.append({"file_path": name, "role": "primary"})
            payload = {
                "query": "locate the owner step",
                "query_handoff": {"code_anchors": anchors},
            }
            budget = estimate_payload_tokens(payload) + TOKEN_RESERVE + 120

            attach_source_excerpts(payload, str(root), budget)

        self.assertTrue(all(anchor.get("source_excerpts") for anchor in anchors))

    def test_file_anchor_without_symbol_range_gets_query_focused_excerpt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "WarehouseFacetPage.ets"
            source.write_text(
                "@Component\n"
                "struct WarehouseFacetPage {\n"
                "  build() {\n"
                "    List() {\n"
                "      ListItem().onClick(() => {\n"
                "        this.pageStack.pushPathByName('ProductSearch', undefined)\n"
                "      })\n"
                "    }\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )
            payload = {
                "query": "Locate pageStack.pushPathByName in the route owner.",
                "query_handoff": {
                    "code_anchors": [{
                        "file_path": "WarehouseFacetPage.ets",
                        "role": "primary",
                    }]
                },
            }

            count = attach_source_excerpts(payload, str(root), 1500)

            excerpts = payload["query_handoff"]["code_anchors"][0]["source_excerpts"]
            self.assertEqual(1, count)
            self.assertIn("pushPathByName", excerpts[0]["content"])
            self.assertEqual("query_term_window", excerpts[0]["selection_reason"])

    def test_file_summary_indexes_bounded_arkts_operations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "InventoryList.ets"
            source.write_text(
                "@Component\nstruct InventoryList {\n  build() {\n"
                "    List()\n      .divider({ strokeWidth: 1 })\n      .padding(8)\n  }\n"
                "}\n",
                encoding="utf-8",
            )

            summary = summarize_file(source, "ArkTS")

        self.assertIn("operations: divider, padding", summary)

    def test_query_focus_prefers_matching_ui_modifier_over_component_header(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "InventoryList.ets"
            lines = ["const filler = 1" for _ in range(60)]
            lines[1] = "struct InventoryList {"
            lines[44] = ".divider({ strokeWidth: 1, color: Color.Gray })"
            source.write_text("\n".join(lines) + "\n", encoding="utf-8")

            focused = focused_source_range(
                source,
                {"symbol": "InventoryList", "start_line": 2, "end_line": 55},
                "inventory separator divider stroke width",
            )

        self.assertLessEqual(focused["start_line"], 45)
        self.assertGreaterEqual(focused["end_line"], 45)
        self.assertEqual(
            "query_term_window_within_anchor",
            focused["selection_reason"],
        )

    def test_query_focus_stays_inside_evidence_backed_symbol_range(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "StoreConfig.ets"
            lines = ["const filler = 1" for _ in range(80)]
            for index in range(5, 10):
                lines[index] = "// database store tokenizer security configuration docs"
            lines[49] = (
                "return relationalStore.getRdbStore({ securityLevel, tokenizer })"
            )
            source.write_text("\n".join(lines) + "\n", encoding="utf-8")

            focused = focused_source_range(
                source,
                {"symbol": "openStore", "start_line": 42, "end_line": 58},
                "Locate the database store tokenizer security configuration owner",
            )

        self.assertLessEqual(focused["start_line"], 50)
        self.assertGreaterEqual(focused["end_line"], 50)
        self.assertEqual(
            "query_term_window_within_anchor",
            focused["selection_reason"],
        )

    def test_query_focus_prefers_executable_style_over_dense_header_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "ArticleMarkupView.ets"
            lines = ["const filler = 1" for _ in range(140)]
            for index in range(8, 13):
                lines[index] = (
                    "// formatted article links code quote underline dark theme colors"
                )
            lines[104] = (
                "Span(entity.text).fontColor(this.themeColor).decoration({ "
                "type: TextDecorationType.Underline })"
            )
            source.write_text("\n".join(lines) + "\n", encoding="utf-8")

            focused = focused_source_range(
                source,
                {"symbol": "ArticleMarkupView", "start_line": 1, "end_line": 140},
                "formatted article links code quote underline dark theme colors",
            )

        self.assertLessEqual(focused["start_line"], 105)
        self.assertGreaterEqual(focused["end_line"], 105)

    def test_file_summary_indexes_bounded_member_behavior_calls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "FacetPage.ets"
            source.write_text(
                "@ComponentV2\nstruct FacetPage {\n  build() {\n"
                "    Text('facet').onClick(() => {\n"
                "      this.pageStack.pushPathByName('SearchPage', {})\n"
                "    })\n  }\n}\n",
                encoding="utf-8",
            )

            summary = summarize_file(source, "ArkTS")

        self.assertIn("pushPathByName", summary)

    def test_file_summary_indexes_reactive_aggregate_iteration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "QuarterLedger.ets"
            source.write_text(
                "@Component\nstruct QuarterLedger {\n"
                "  @State selectedQuarter: number = 1\n"
                "  private recalculate() {\n"
                "    this.entries.forEach((entry) => { this.total += entry.amount })\n"
                "  }\n}\n",
                encoding="utf-8",
            )

            summary = summarize_file(source, "ArkTS")

        self.assertIn("forEach", summary)

    def test_arkts_builder_calls_are_not_indexed_as_function_declarations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "InventoryList.ets"
            source.write_text(
                "@Component\nstruct InventoryList {\n"
                "  StickerView() { const marker = true }\n"
                "  build() {\n    List() {\n      ListItem() {}\n    }\n  }\n}\n",
                encoding="utf-8",
            )

            symbols = extract_symbols(source, "ArkTS")

        self.assertIn(("InventoryList", "component"), symbols)
        self.assertIn(("build", "function"), symbols)
        self.assertIn(("StickerView", "function"), symbols)
        self.assertNotIn(("List", "function"), symbols)
        self.assertNotIn(("ListItem", "function"), symbols)


if __name__ == "__main__":
    unittest.main()
