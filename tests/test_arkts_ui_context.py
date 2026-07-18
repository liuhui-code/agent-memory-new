# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.agent_memory_runtime.code_wiki_extractors import extract_symbols, summarize_file
from tools.agent_memory_runtime.context_source_excerpt import focused_source_range


class ArktsUiContextTests(unittest.TestCase):
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
        self.assertEqual("query_term_window", focused["selection_reason"])

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
